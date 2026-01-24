# persona_core/api/server.py
"""
server.py
===========================
人格OSの API エントリーポイント（最新版 / DB文脈版）。

重要：
- Swagger が固まる原因の多くは「import 時に重い処理が走る」こと。
- そのため、このファイルでは “import 時” に DB/LLM/Kernel/各Evaluator を初期化しない。
- /chat が呼ばれたタイミングで必要モジュールを lazy import し、キャッシュして使う。

仕様は削らない：
- TemporalAxis / Salience / Boundary / Policy / Kernel / Output pipeline は維持
- 文脈は DB(messages) が正。session/in-memory は補助
- DB role が `ai` でも文脈に取り込む（ai -> assistant）
"""


from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()  # env は import 最初に読む（dotenv 自体は軽い）

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from typing import Any, Dict, Optional, List, TypedDict
import inspect
import logging

logger = logging.getLogger(__name__)


# =========================
# FastAPI 初期化
# =========================

app = FastAPI(
    title="Persona OS API",
    description="人格OS 中核API（DB文脈版）",
    version="0.2.7",
)

# =========================
# Request / Response
# =========================

class ChatRequest(BaseModel):
    # ★追加（整合性修正）：
    # - conversations.user_id は users.id を参照する想定（FK）
    # - そのため /chat では「Supabase Auth の user_id(UUID)」を受け取る必要がある
    # - session_id は「API 上のセッション文字列」（補助）として扱う
    user_id: str = Field(..., description="Supabase Auth user_id (UUID)")

    session_id: str
    character_id: str
    text: str


class ChatResponse(BaseModel):
    session_id: str
    character_id: str
    reply: str
    meta: dict = Field(default_factory=dict)


# =========================
# セッション管理（補助）
# - 重要：会話文脈の正は DB messages
# =========================

# ここは import-time に core.state を触らない（Swagger固まり回避）
SESSION_STATES: dict[str, Any] = {}
SESSION_MEMORY: dict[str, Any] = {}

# 長期記憶（保存専用）
SESSION_LONG_TERM: dict[str, Any] = {}


# =========================
# Temporal Axis
# =========================

VALID_TEMPORAL_AXES = {"past", "present", "future", "if", "unknown"}


# =========================
# DB role 正規化
# =========================

ROLE_MAP: Dict[str, str] = {
    "user": "user",
    "assistant": "assistant",
    "ai": "assistant",
    "system": "system",
}


# =========================
# lazy import / cache
# =========================

class _Deps(TypedDict):
    ConversationState: Any
    IntentParser: Any
    resolve_intent: Any
    PolicyEngine: Any
    PolicyDecision: Any
    CharacterProfile: Any
    get_character_profile: Any
    ConversationKernel: Any
    SessionMemory: Any
    SalienceEvaluator: Any
    BoundaryEvaluator: Any
    BoundaryResult: Any
    PromptBuilder: Any
    LLMClient: Any
    OutputRepair: Any
    PronounNormalizer: Any
    OutputStabilizer: Any
    OutputGuard: Any
    read_messages: Any

    # ★追加：conversation_id(UUID) を user_id+session_key から取得/作成
    get_or_create_conversation_id: Any

    LongTermMemory: Any  # Optional (None if unavailable)


_DEPS_CACHE: Optional[_Deps] = None
_SINGLETONS: Dict[str, Any] = {}


def _get_deps() -> _Deps:
    """
    Swagger の import 段階で重い初期化が走らないように、
    依存モジュールは /chat が呼ばれたときに初めて import する。
    """
    global _DEPS_CACHE
    if _DEPS_CACHE is not None:
        return _DEPS_CACHE

    # ---- core
    from core.state import ConversationState
    from core.intent import IntentParser, resolve_intent
    from core.policy import PolicyEngine, PolicyDecision
    from core.character import CharacterProfile, get_character_profile
    from core.conversation_kernel import ConversationKernel

    # ---- memory
    from memory.session import SessionMemory
    from memory.salience import SalienceEvaluator
    from memory.boundary import BoundaryEvaluator, BoundaryResult

    # ---- db
    # server.py は `read_messages` 前提なので、messages_reader.py 側は必ず read_messages を提供している必要がある
    from db.messages_reader import read_messages

    # ★追加：conversation_id(UUID) の取得/生成（DBに任せる）
    # ここで UUID を Python 側生成しない
    from db.conversation_reader import get_or_create_conversation_id

    # ---- prompt
    from prompt.builder import PromptBuilder

    # ---- llm
    from llm.client import LLMClient

    # ---- output
    from output.repair import OutputRepair
    from output.pronoun_normalizer import PronounNormalizer
    from output.stabilizer import OutputStabilizer
    from output.guard import OutputGuard

    # ---- long_term (optional)
    try:
        from memory.long_term import LongTermMemory  # type: ignore
    except Exception:
        LongTermMemory = None  # type: ignore

    _DEPS_CACHE = {
        "ConversationState": ConversationState,
        "IntentParser": IntentParser,
        "resolve_intent": resolve_intent,
        "PolicyEngine": PolicyEngine,
        "PolicyDecision": PolicyDecision,
        "CharacterProfile": CharacterProfile,
        "get_character_profile": get_character_profile,
        "ConversationKernel": ConversationKernel,
        "SessionMemory": SessionMemory,
        "SalienceEvaluator": SalienceEvaluator,
        "BoundaryEvaluator": BoundaryEvaluator,
        "BoundaryResult": BoundaryResult,
        "PromptBuilder": PromptBuilder,
        "LLMClient": LLMClient,
        "OutputRepair": OutputRepair,
        "PronounNormalizer": PronounNormalizer,
        "OutputStabilizer": OutputStabilizer,
        "OutputGuard": OutputGuard,
        "read_messages": read_messages,

        # ★追加
        "get_or_create_conversation_id": get_or_create_conversation_id,

        "LongTermMemory": LongTermMemory,
    }
    return _DEPS_CACHE


def _singleton(name: str, factory):
    """
    Evaluator 等は毎回 new しても良いが、遅延のぶれを減らすため singleton で持つ。
    """
    if name in _SINGLETONS:
        return _SINGLETONS[name]
    obj = factory()
    _SINGLETONS[name] = obj
    return obj


# =========================
# 内部ユーティリティ（型は Any で受ける：import-time の依存を避ける）
# =========================

def _ensure_state_runtime_fields(state: Any) -> None:
    if not hasattr(state, "turn_count"):
        setattr(state, "turn_count", 0)

    if not hasattr(state, "current_temporal_axis"):
        setattr(state, "current_temporal_axis", "present")
    if not hasattr(state, "temporal_history"):
        setattr(state, "temporal_history", [])
    if not hasattr(state, "past_topics"):
        setattr(state, "past_topics", [])
    if not hasattr(state, "hypothetical_buffer"):
        setattr(state, "hypothetical_buffer", [])


def _get_state_mood_name(state: Any) -> str | None:
    if not hasattr(state, "mood"):
        return None
    mood = getattr(state, "mood", None)
    if mood is None:
        return None
    if hasattr(mood, "name"):
        return str(mood.name)
    return str(mood)


def _get_policy_allow_advice(policy_decision: Any) -> bool:
    return bool(getattr(policy_decision, "allow_advice", False))


def _get_character_first_person(character: Any) -> str:
    return str(getattr(character, "first_person", "私"))


def _safe_axis(axis: Any) -> str:
    if axis is None:
        return "unknown"
    a = str(axis).strip().lower()
    if a in VALID_TEMPORAL_AXES:
        return a
    return "unknown"


def _decide_temporal_axis(*, state: Any, intent_axis: Any) -> str:
    prev = _safe_axis(getattr(state, "current_temporal_axis", "present"))
    ax = _safe_axis(intent_axis)

    if ax in {"past", "future", "if"}:
        return ax

    if ax == "present":
        if prev in {"past", "future", "if"}:
            return prev
        return "present"

    if prev in VALID_TEMPORAL_AXES:
        return prev
    return "present"


def _extract_past_topic(text: str) -> Optional[str]:
    s = (text or "").strip()
    if not s:
        return None

    s = (
        s.replace("この前", "")
         .replace("さっき", "")
         .replace("昨日", "")
         .replace("前に", "")
         .replace("以前", "")
    ).strip()

    if len(s) > 40:
        s = s[:40].rstrip()
    if len(s) < 4:
        return None
    return s


def _extract_hypothetical(text: str) -> Optional[str]:
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
    state: Any,
    role: str,
    content: str,
    temporal_axis: str,
    past_topic: Optional[str] = None,
    hypothetical: Optional[str] = None,
) -> None:
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

    try:
        messages = getattr(state, "messages", None)
        if isinstance(messages, list):
            messages.append(msg)
        else:
            setattr(state, "messages", [msg])
    except Exception:
        pass

    try:
        setattr(state, "current_temporal_axis", temporal_axis)
        hist = getattr(state, "temporal_history", None)
        if isinstance(hist, list):
            hist.append(temporal_axis)
        else:
            setattr(state, "temporal_history", [temporal_axis])
    except Exception:
        pass

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
    deps: _Deps,
    character_id: str,
    intent_like: Any,
    decided_axis: str,
    boundary_result: Optional[Any],
) -> Any:
    PolicyEngine = deps["PolicyEngine"]

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


def _update_session_memory_best_effort(memory: Any, user_text: str, ai_text: str) -> None:
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


def _get_long_term_memory(deps: _Deps, session_id: str) -> Optional[Any]:
    LongTermMemory = deps["LongTermMemory"]
    if LongTermMemory is None:
        return None

    ltm = SESSION_LONG_TERM.get(session_id)
    if ltm is not None:
        return ltm

    try:
        ltm = LongTermMemory()
        SESSION_LONG_TERM[session_id] = ltm
        return ltm
    except Exception:
        return None


def _normalize_db_role(role: Any) -> Optional[str]:
    if role is None:
        return None
    r = str(role).strip().lower()
    if not r:
        return None
    return ROLE_MAP.get(r)


# ★変更：ここは session_id を conversation_id(UUID) に置き換えて使う
# ただし「仕様は削らない」ので、関数構造は維持しつつ引数名だけ正しくする
def _load_context_messages_from_db(
    deps: _Deps,
    *,
    conversation_id: str,
    limit: int = 12
) -> List[Dict[str, str]]:
    read_messages = deps["read_messages"]

    try:
        # messages_reader の引数名は session_id のままでも良いが、
        # ここで渡す値は UUID(conversation_id) に統一する
        msgs = read_messages(session_id=conversation_id, limit=limit)
        if not isinstance(msgs, list):
            return []

        out: List[Dict[str, str]] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue

            role_raw = m.get("role")
            content = m.get("content")

            role = _normalize_db_role(role_raw)
            if role not in {"user", "assistant"}:
                continue

            if not isinstance(content, str) or not content.strip():
                continue

            out.append({"role": role, "content": content.strip()})

        return out
    except Exception as e:
        # DB が落ちても chat 自体は落とさない
        logger.exception("DB context load failed: %s", e)
        return []


# =========================
# 追加：軽いヘルスチェック（Swagger切り分けに効く）
# =========================

@app.get("/ping")
def ping():
    return {"ok": True}


# =========================
# API エンドポイント
# =========================

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    deps = _get_deps()

    ConversationState = deps["ConversationState"]
    SessionMemory = deps["SessionMemory"]
    IntentParser = deps["IntentParser"]
    resolve_intent = deps["resolve_intent"]
    get_character_profile = deps["get_character_profile"]
    ConversationKernel = deps["ConversationKernel"]

    SalienceEvaluator = deps["SalienceEvaluator"]
    BoundaryEvaluator = deps["BoundaryEvaluator"]

    PromptBuilder = deps["PromptBuilder"]
    LLMClient = deps["LLMClient"]

    OutputRepair = deps["OutputRepair"]
    PronounNormalizer = deps["PronounNormalizer"]
    OutputStabilizer = deps["OutputStabilizer"]
    OutputGuard = deps["OutputGuard"]

    # ★追加：conversation_id 取得/生成
    get_or_create_conversation_id = deps["get_or_create_conversation_id"]

    # =========================
    # 0. conversation_id(UUID) 確定（DB文脈の唯一キー）
    # =========================
    # 重要：
    # - messages.conversation_id は UUID
    # - req.user_id は Supabase Auth の user_id(UUID)
    # - req.session_id は API 上のセッション文字列（補助）
    # - user_id + character_id + session_key で conversations を一意決定し、
    #   その UUID(conversation_id) を DB 文脈キーとして以後使う
    #
    # ※ session_key の切り方は運用で変えて良いが、ここでは固定 "default" にする
    conversation_id = get_or_create_conversation_id(
        user_id=req.user_id,
        character_id=req.character_id,
        session_key="default",
    )

    # =========================
    # 1. セッション取得 / 初期化（補助情報）
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
        character = get_character_profile(req.character_id)
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

    salience_eval = _singleton("SalienceEvaluator", lambda: SalienceEvaluator())
    salience = salience_eval.evaluate(
        req.text,
        role="user",
        intent_kind=getattr(intent, "kind", "chat"),
        is_metaphor=bool(getattr(intent_raw, "is_metaphor", False)),
    )

    # =========================
    # 5. Boundary 判定
    # =========================

    boundary_eval = _singleton("BoundaryEvaluator", lambda: BoundaryEvaluator())
    boundary_result = boundary_eval.evaluate(
        state=state,
        intent=intent,
        salience=salience,
        user_text=req.text,
    )

    # =========================
    # 6. State 更新（ユーザー入力）
    # =========================

    if hasattr(state, "on_user_input"):
        try:
            state.on_user_input(
                is_emotional=bool(getattr(intent_raw, "is_emotional", False)),
                is_metaphor=bool(getattr(intent_raw, "is_metaphor", False)),
                is_question=bool(getattr(intent_raw, "is_question", False)),
                is_casual=bool(getattr(intent_raw, "is_casual", False)),
            )
        except Exception:
            pass

    # =========================
    # 7. Policy 決定
    # =========================

    policy_decision = _decide_policy_with_compat(
        deps=deps,
        character_id=req.character_id,
        intent_like=intent_raw,
        decided_axis=decided_axis,
        boundary_result=boundary_result,
    )

    # =========================
    # 7.5 Conversation Kernel
    # =========================

    try:
        ConversationKernel().decide(
            state=state,
            intent=intent,
            boundary=boundary_result,
            salience=salience,
            user_text=req.text,
        )
    except Exception:
        pass

    # =========================
    # 8. DB 文脈ロード（唯一の文脈）
    # =========================

    context_messages = _load_context_messages_from_db(
        deps,
        conversation_id=conversation_id,
        limit=12,
    )

    # =========================
    # 9. Prompt 構築（DB messages を注入）
    # =========================

    prompt = PromptBuilder(
        character=character,
        state=state,
        intent=intent,
        policy_decision=policy_decision,
    ).build(
        user_input=req.text,
        messages=context_messages,
    )

    # =========================
    # 10. LLM 呼び出し
    # =========================

    llm = _singleton("LLMClient", lambda: LLMClient())
    raw_output = llm.generate(
        system=prompt["system"],
        user=prompt["user"],
    )

    # =========================
    # 11. Repair
    # =========================

    repaired = OutputRepair().repair(
        raw_output,
        allow_intervention=_get_policy_allow_advice(policy_decision),
    )

    # =========================
    # 12. Pronoun Normalizer
    # =========================

    pronoun_normalized = PronounNormalizer(
        first_person=_get_character_first_person(character)
    ).normalize(
        repaired,
        allow_intervention=True,
    )

    # =========================
    # 13. Stabilizer
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
    # 14. Guard
    # =========================

    final_text = OutputGuard().process(stabilized)

    _register_turn_if_possible(
        state=state,
        role="assistant",
        content=final_text,
        temporal_axis=decided_axis,
        past_topic=past_topic,
        hypothetical=hypothetical,
    )
    
    # =========================
    # 15. Session Memory 更新（補助）
    # =========================

    try:
        _update_session_memory_best_effort(
            memory=memory,
            user_text=req.text,
            ai_text=final_text,
        )
    except Exception:
        pass

    # =========================
    # 16. LongTermMemory（存在すれば）更新（補助）
    # =========================

    try:
        ltm = _get_long_term_memory(deps, req.session_id)
        if ltm is not None:
            # 実装差異を吸収（best-effort）
            if hasattr(ltm, "add"):
                try:
                    ltm.add(user=req.text, assistant=final_text)
                except Exception:
                    pass
            elif hasattr(ltm, "append"):
                try:
                    ltm.append({"role": "user", "content": (req.text or "").strip()})
                    ltm.append({"role": "assistant", "content": (final_text or "").strip()})
                except Exception:
                    pass
    except Exception:
        pass

    # =========================
    # 17. meta 構築
    # =========================

    meta: Dict[str, Any] = {}
    try:
        meta["conversation_id"] = str(conversation_id)
    except Exception:
        pass

    try:
        meta["temporal_axis"] = str(decided_axis)
    except Exception:
        pass

    try:
        meta["salience"] = salience if salience is not None else None
    except Exception:
        pass

    try:
        # BoundaryResult がある場合だけ入れる（型差異吸収）
        if boundary_result is not None:
            lvl = getattr(boundary_result, "level", None)
            if lvl is not None and hasattr(lvl, "value"):
                meta["boundary_level"] = lvl.value
            else:
                meta["boundary_level"] = lvl
    except Exception:
        pass

    try:
        meta["mood"] = _get_state_mood_name(state)
    except Exception:
        pass

    # policy_decision は型が変わり得るので safe に
    try:
        meta["policy"] = {
            "allow_advice": _get_policy_allow_advice(policy_decision),
        }
    except Exception:
        pass

    # =========================
    # 18. Response
    # =========================

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