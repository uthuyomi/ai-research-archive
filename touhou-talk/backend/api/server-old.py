# persona_core/api/server.py
"""
server.py
===========================
人格OSの API エントリーポイント（最新版）。

役割：
- 各レイヤ（intent / state / policy / prompt / llm）を正しい順序で接続
- 人格判断や生成ロジックは一切持たない
- 「配線」と「状態管理」だけを行う

この版での主目的
----------------
- TemporalAxis（past / present / future / if）を「確定」する場所を server に集約する
- state 実装差分（fields / register_turn の有無）に耐える
- 会話の時間軸が途中で崩れにくいように、軸の継続・戻しを配線で制御する

フェーズ②（今回の追加）
----------------
- Salience を「長期記憶（LongTermMemory）」へ渡す（保存専用）
- SessionMemory へは salience を渡さない（直近会話維持のみ）
- 長期記憶は参照しない（Prompt/生成に使わない）
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from typing import Any, Dict, Optional
import inspect

# =========================
# group-chat router（配線のみ）
# =========================
try:
    # api/group_chat.py が APIRouter を `router` として公開している前提
    from api.group_chat import router as group_chat_router  # type: ignore
except Exception:
    group_chat_router = None  # type: ignore

# =========================
# core
# =========================

from core.state import ConversationState
from core.intent import IntentParser, resolve_intent

# PolicyDecision 実装差分を吸収するため、型は import するが attribute access は全部 getattr で扱う
from core.policy import PolicyEngine, PolicyDecision
from core.character import CharacterProfile, get_character_profile

# =========================
# memory
# =========================

from memory.session import SessionMemory
from memory.salience import SalienceEvaluator
from memory.boundary import BoundaryEvaluator, BoundaryResult, BoundaryLevel

# Long-term Memory（フェーズ②）
# ※ ファイルが未配置でも server が落ちないように optional import
try:
    from memory.long_term import LongTermMemory  # type: ignore
except Exception:  # pragma: no cover
    LongTermMemory = None  # type: ignore

# =========================
# prompt
# =========================

from prompt.builder import PromptBuilder

# =========================
# llm
# =========================

from llm.client import LLMClient

# =========================
# output
# =========================

from output.repair import OutputRepair
from output.pronoun_normalizer import PronounNormalizer
from output.stabilizer import OutputStabilizer
from output.guard import OutputGuard


# =========================
# FastAPI 初期化
# =========================

app = FastAPI(
    title="Persona OS API",
    description="人格OS 中核API（最新版）",
    version="0.2.6",
)

# =========================
# group-chat router 登録（配線のみ）
# =========================
if group_chat_router is not None:
    app.include_router(group_chat_router)
# =========================
# Request / Response
# =========================

class ChatRequest(BaseModel):
    session_id: str
    character_id: str
    text: str


class ChatResponse(BaseModel):
    session_id: str
    character_id: str
    reply: str
    meta: dict = Field(default_factory=dict)


# =========================
# 簡易セッション管理
# =========================

SESSION_STATES: dict[str, ConversationState] = {}
SESSION_MEMORY: dict[str, SessionMemory] = {}

# 長期記憶（フェーズ②）
# - 保存専用
# - Prompt/生成で参照しない
SESSION_LONG_TERM: dict[str, Any] = {}


# =========================
# Temporal Axis（server 側の確定ロジック用）
# =========================

VALID_TEMPORAL_AXES = {"past", "present", "future", "if", "unknown"}


# =========================
# 内部ユーティリティ
# =========================

def _ensure_state_runtime_fields(state: ConversationState) -> None:
    """
    ConversationState 実装が薄い/途中でも落とさないための安全弁。
    server が参照する最小フィールドだけ補う。
    """
    if not hasattr(state, "turn_count"):
        setattr(state, "turn_count", 0)

    # Temporal axis 系が無い実装でも落とさない
    if not hasattr(state, "current_temporal_axis"):
        setattr(state, "current_temporal_axis", "present")
    if not hasattr(state, "temporal_history"):
        setattr(state, "temporal_history", [])
    if not hasattr(state, "past_topics"):
        setattr(state, "past_topics", [])
    if not hasattr(state, "hypothetical_buffer"):
        setattr(state, "hypothetical_buffer", [])


def _get_state_mood_name(state: ConversationState) -> str | None:
    if not hasattr(state, "mood"):
        return None

    mood = getattr(state, "mood", None)
    if mood is None:
        return None

    if hasattr(mood, "name"):
        return str(mood.name)

    return str(mood)


def _get_policy_allow_advice(policy_decision: PolicyDecision) -> bool:
    """
    allow_advice が無ければ False（保守的に介入を減らす）
    """
    return bool(getattr(policy_decision, "allow_advice", False))


def _get_character_first_person(character: CharacterProfile) -> str:
    """
    CharacterProfile に first_person が定義されていればそれを使う。
    無ければ安全に '私' にフォールバック。
    """
    return str(getattr(character, "first_person", "私"))


def _safe_axis(axis: Any) -> str:
    """
    受け取った axis を安全に正規化する。
    """
    if axis is None:
        return "unknown"
    a = str(axis).strip().lower()
    if a in VALID_TEMPORAL_AXES:
        return a
    return "unknown"


def _decide_temporal_axis(*, state: ConversationState, intent_axis: Any) -> str:
    """
    TemporalAxis を server が最終確定する。

    方針（崩れにくさ優先）：
    - intent が past/future/if を明示したらその軸へ切替
    - intent が present の場合：
        - 直前が past/future/if なら、その軸を「維持」する（会話の継続性を優先）
        - 直前が present/unknown なら present
    - unknown の場合：
        - state.current_temporal_axis を維持（安全側）
    """
    prev = _safe_axis(getattr(state, "current_temporal_axis", "present"))
    ax = _safe_axis(intent_axis)

    if ax in {"past", "future", "if"}:
        return ax

    if ax == "present":
        if prev in {"past", "future", "if"}:
            return prev
        return "present"

    # unknown は維持
    if prev in VALID_TEMPORAL_AXES:
        return prev

    return "present"


def _extract_past_topic(text: str) -> Optional[str]:
    """
    過去軸のときに「過去話題っぽい断片」を軽量に抜く。
    精度は捨てる。誤爆しにくさ優先で “短く”。
    """
    s = (text or "").strip()
    if not s:
        return None

    s = s.replace("この前", "").replace("さっき", "").replace("昨日", "").replace("前に", "").replace("以前", "")
    s = s.strip()

    if len(s) > 40:
        s = s[:40].rstrip()

    if len(s) < 4:
        return None

    return s


def _extract_hypothetical(text: str) -> Optional[str]:
    """
    if軸のときの内容を一時置き場へ回す。
    恒久記憶化しない前提なので短く。
    """
    s = (text or "").strip()
    if not s:
        return None
    if len(s) > 60:
        s = s[:60].rstrip()
    if len(s) < 4:
        return None
    return s


def _register_turn_if_possible(
    *,
    state: ConversationState,
    role: str,
    content: str,
    temporal_axis: str,
    past_topic: Optional[str] = None,
    hypothetical: Optional[str] = None,
) -> None:
    """
    ConversationState に register_turn があれば必ず通す。
    無ければ messages append + axis 更新を最小で行う。
    """
    msg = {"role": role, "content": content}

    if hasattr(state, "register_turn"):
        try:
            state.register_turn(
                message=msg,
                temporal_axis=temporal_axis,
                past_topic=past_topic,
                hypothetical=hypothetical,
            )
            return
        except Exception:
            pass

    # フォールバック：最低限の事実保存
    try:
        messages = getattr(state, "messages", None)
        if isinstance(messages, list):
            messages.append(msg)
        else:
            setattr(state, "messages", [msg])
    except Exception:
        pass

    # 軸保持
    try:
        setattr(state, "current_temporal_axis", temporal_axis)
        hist = getattr(state, "temporal_history", None)
        if isinstance(hist, list):
            hist.append(temporal_axis)
        else:
            setattr(state, "temporal_history", [temporal_axis])
    except Exception:
        pass

    # 過去話題 / ifバッファも、あれば軽く追加
    try:
        if temporal_axis == "past" and past_topic:
            pt = getattr(state, "past_topics", None)
            if isinstance(pt, list):
                pt.append(past_topic)
            else:
                setattr(state, "past_topics", [past_topic])

        if temporal_axis == "if" and hypothetical:
            hb = getattr(state, "hypothetical_buffer", None)
            if isinstance(hb, list):
                hb.append(hypothetical)
            else:
                setattr(state, "hypothetical_buffer", [hypothetical])
    except Exception:
        pass


def _decide_policy_with_compat(
    *,
    character_id: str,
    intent_like: Any,
    decided_axis: str,
    boundary_result: Optional[BoundaryResult],
) -> PolicyDecision:
    """
    policy.py の実装差分（引数追加/未追加）に耐えつつ、渡せるものは渡す。

    - 旧：decide(character_id, intent)
    - 中：decide(character_id, intent, temporal_axis=...)
    - 新：decide(character_id, intent, temporal_axis=..., boundary_level=...)
    """
    try:
        sig = inspect.signature(PolicyEngine.decide)
        params = sig.parameters

        kwargs: Dict[str, Any] = {}
        if "temporal_axis" in params:
            kwargs["temporal_axis"] = decided_axis

        if boundary_result is not None and "boundary_level" in params:
            lvl = getattr(boundary_result, "level", None)
            kwargs["boundary_level"] = lvl.value if hasattr(lvl, "value") else lvl

        return PolicyEngine.decide(
            character_id=character_id,
            intent=intent_like,
            **kwargs,
        )
    except Exception:
        return PolicyEngine.decide(
            character_id=character_id,
            intent=intent_like,
        )


def _update_session_memory_best_effort(memory: SessionMemory, user_text: str, ai_text: str) -> None:
    """
    SessionMemory 実装差分に合わせて、確実に “直近会話” を積む。

    注意：
    - salience をここに渡さない（フェーズ②の方針）
    - Session は “作業記憶” なので、重要度で歪めない
    """
    if hasattr(memory, "add_user") and hasattr(memory, "add_assistant"):
        try:
            memory.add_user(user_text)
            memory.add_assistant(ai_text)
            return
        except Exception:
            pass

    if hasattr(memory, "add"):
        try:
            memory.add(user=user_text, ai=ai_text)
            return
        except Exception:
            pass

    if hasattr(memory, "append"):
        try:
            memory.append(user=user_text, ai=ai_text)
            return
        except Exception:
            pass

    try:
        msgs = getattr(memory, "messages", None)
        if isinstance(msgs, list):
            msgs.append({"role": "user", "content": (user_text or "").strip()})
            msgs.append({"role": "assistant", "content": (ai_text or "").strip()})
    except Exception:
        pass


def _get_long_term_memory(session_id: str) -> Optional[Any]:
    """
    LongTermMemory を session_id ごとに用意する。

    - memory.long_term が存在しない環境では None を返す（落とさない）
    - 参照用途では使わない（保存専用）
    """
    if LongTermMemory is None:
        return None

    ltm = SESSION_LONG_TERM.get(session_id)
    if ltm is not None:
        return ltm

    try:
        # 閾値や上限は long_term.py 側のデフォルトに任せる
        ltm = LongTermMemory()
        SESSION_LONG_TERM[session_id] = ltm
        return ltm
    except Exception:
        return None


# =========================
# API エンドポイント
# =========================

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:

    # =========================
    # 1. セッション取得 / 初期化
    # =========================

    state = SESSION_STATES.setdefault(req.session_id, ConversationState())
    memory = SESSION_MEMORY.setdefault(req.session_id, SessionMemory())

    _ensure_state_runtime_fields(state)

    # turn_count（Stabilizer 参照用、LLM 前に進める）
    try:
        state.turn_count = int(getattr(state, "turn_count", 0)) + 1
    except Exception:
        state.turn_count = 1

    # =========================
    # 2. キャラクター取得
    # =========================

    try:
        character: CharacterProfile = get_character_profile(req.character_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown character_id: {req.character_id}",
        )

    # =========================
    # 3. Intent 解析
    # =========================

    intent_raw = IntentParser.parse(req.text)
    intent = resolve_intent(intent_raw, text=req.text)

    # =========================
    # 3.5 Temporal Axis 確定（server が唯一の決定者）
    # =========================

    intent_axis = getattr(intent, "temporal_axis", "unknown")
    decided_axis = _decide_temporal_axis(state=state, intent_axis=intent_axis)

    past_topic = _extract_past_topic(req.text) if decided_axis == "past" else None
    hypothetical = _extract_hypothetical(req.text) if decided_axis == "if" else None

    _register_turn_if_possible(
        state=state,
        role="user",
        content=req.text,
        temporal_axis=decided_axis,
        past_topic=past_topic,
        hypothetical=hypothetical,
    )

    # =========================
    # 4. Salience 判定
    # =========================

    salience = SalienceEvaluator().evaluate(
        req.text,
        role="user",
        intent_kind=getattr(intent, "kind", "chat"),
        is_metaphor=bool(getattr(intent_raw, "is_metaphor", False)),
    )

    # =========================
    # 5. Boundary 判定
    # =========================

    boundary_result: BoundaryResult = BoundaryEvaluator().evaluate(
        state=state,
        intent=intent,
        salience=salience,
        user_text=req.text,
    )

    # =========================
    # 6. State 更新（ユーザー入力）
    # =========================

    if hasattr(state, "on_user_input"):
        state.on_user_input(
            is_emotional=bool(getattr(intent_raw, "is_emotional", False)),
            is_metaphor=bool(getattr(intent_raw, "is_metaphor", False)),
            is_question=bool(getattr(intent_raw, "is_question", False)),
            is_casual=bool(getattr(intent_raw, "is_casual", False)),
        )

    # =========================
    # 7. Policy 決定（TemporalAxis / Boundary を渡せるだけ渡す）
    # =========================

    policy_decision: PolicyDecision = _decide_policy_with_compat(
        character_id=req.character_id,
        intent_like=intent_raw,
        decided_axis=decided_axis,
        boundary_result=boundary_result,
    )

    # =========================
    # 8. Prompt 構築
    # =========================

    prompt = PromptBuilder(
        character=character,
        state=state,
        intent=intent,
        policy_decision=policy_decision,
    ).build(req.text)

    # =========================
    # 9. LLM 呼び出し
    # =========================

    raw_output = LLMClient().generate(
        system=prompt["system"],
        user=prompt["user"],
    )

    # =========================
    # 10. Repair（意味・距離感修正）
    # =========================

    repaired = OutputRepair().repair(
        raw_output,
        allow_intervention=_get_policy_allow_advice(policy_decision),
    )

    # =========================
    # 11. Pronoun Normalizer（自己参照安定化）
    # =========================

    pronoun_normalized = PronounNormalizer(
        first_person=_get_character_first_person(character)
    ).normalize(
        repaired,
        allow_intervention=True,
    )

    # =========================
    # 12. Stabilizer（長期安定化）
    # =========================

    try:
        turn_count = int(getattr(state, "turn_count", 0))
    except Exception:
        turn_count = 0

    stabilized = OutputStabilizer().stabilize(
        pronoun_normalized,
        turn_count=turn_count,
        allow_intervention=True,
    )

    # =========================
    # 13. Guard（最終整形）
    # =========================

    final_text = OutputGuard().process(stabilized)

    # AI 出力も state に登録（同じ decided_axis を維持）
    _register_turn_if_possible(
        state=state,
        role="assistant",
        content=final_text,
        temporal_axis=decided_axis,
        past_topic=None,
        hypothetical=None,
    )

    # =========================
    # 14. Memory 更新
    # =========================
    # 14-A) SessionMemory：直近会話維持（作業記憶）
    _update_session_memory_best_effort(memory, req.text, final_text)

    # 14-B) LongTermMemory：salience を使って保存（参照はしない）
    ltm = _get_long_term_memory(req.session_id)
    long_term_stored = False

    if ltm is not None:
        try:
            # long_term.py の add() へ “保存判断” を委譲する
            # ※ salience.is_memorable は server 都合の分岐に使ってもいいが、
            #   ここでは add() の内部フィルタを信頼し、単純に渡す。
            long_term_stored = bool(
                ltm.add(
                    user_text=req.text,
                    ai_text=final_text,
                    salience=salience,
                    tags=None,
                )
            )
        except Exception:
            # 長期記憶が壊れても chat を落とさない
            long_term_stored = False

    # =========================
    # 15. AI 応答後 State 更新
    # =========================

    if hasattr(state, "on_ai_response"):
        state.on_ai_response()

    # =========================
    # 16. Response
    # =========================

    meta: Dict[str, Any] = {
        "turn": turn_count,
        "temporal_axis": decided_axis,
        "salience": float(getattr(salience, "score", 0.0)),
        "boundary_level": (
            boundary_result.level.value
            if hasattr(boundary_result.level, "value")
            else str(boundary_result.level)
        ),
        # フェーズ②：保存したかどうか（デバッグ用）
        "long_term_stored": bool(long_term_stored),
    }

    mood_name = _get_state_mood_name(state)
    if mood_name is not None:
        meta["mood"] = mood_name

    return ChatResponse(
        session_id=req.session_id,
        character_id=req.character_id,
        reply=final_text,
        meta=meta,
    )


# =========================
# Health Check
# =========================

@app.get("/")
def health_check():
    return {"status": "ok"}