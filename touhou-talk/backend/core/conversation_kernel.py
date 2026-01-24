# core/conversation_kernel.py
"""
conversation_kernel.py
======================
Conversation Control Kernel

役割：
- 会話フェーズ / トーン / 編集権限 / 出力形式 を一元決定する
- LLM・Prompt・Policy・DialogueControl の上位に立つ「判断専用レイヤ」
- 生成・人格・装飾には一切関与しない

設計原則：
- 判断は kernel、生成は LLM
- 明示がない限り安全側（勝手にまとめない・書き換えない）
- 一般利用者 / 雑談 / 作業 / 編集を同一ロジックで扱う
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# ==================================================
# Decision Data Structures
# ==================================================

@dataclass
class ConversationDecision:
    """
    kernel が最終的に確定する対話制御情報
    """
    phase: str               # explore | discuss | work | review
    tone: str                # relaxed | neutral | strict
    edit_permission: str     # none | suggest | patch
    output_format: str       # prose | bullets | diff | code

    def as_dict(self) -> Dict[str, str]:
        return {
            "phase": self.phase,
            "tone": self.tone,
            "edit_permission": self.edit_permission,
            "output_format": self.output_format,
        }


# ==================================================
# Kernel
# ==================================================

class ConversationKernel:
    """
    ConversationKernel

    入力：
    - state        : ConversationState（実装差分を許容）
    - intent       : Intent / intent-like object
    - boundary     : BoundaryResult or None
    - salience     : SalienceResult or None
    - user_text    : str

    出力：
    - ConversationDecision
    """

    # ------------------------------
    # public
    # ------------------------------

    def decide(
        self,
        *,
        state: Any,
        intent: Any,
        boundary: Optional[Any],
        salience: Optional[Any],
        user_text: str,
    ) -> ConversationDecision:
        """
        kernel の唯一の公開 API
        """

        phase = self._decide_phase(state, intent, user_text)
        tone = self._decide_tone(phase, boundary, salience)
        edit_permission = self._decide_edit_permission(intent, user_text)
        output_format = self._decide_output_format(phase, edit_permission, intent)

        decision = ConversationDecision(
            phase=phase,
            tone=tone,
            edit_permission=edit_permission,
            output_format=output_format,
        )

        # state に保持（存在しなくても落とさない）
        self._attach_to_state(state, decision)

        return decision

    # ==================================================
    # Phase Decision
    # ==================================================

    def _decide_phase(self, state: Any, intent: Any, text: str) -> str:
        """
        会話フェーズ決定
        """
        # intent.kind を最優先
        kind = getattr(intent, "kind", None)

        if kind in {"edit", "modify", "refactor"}:
            return "work"

        if kind in {"review", "check", "inspect"}:
            return "review"

        if kind in {"explain", "analyze", "design"}:
            return "discuss"

        # 明示コマンド語
        lowered = (text or "").lower()
        if any(k in lowered for k in ["直して", "書き換え", "修正", "実装"]):
            return "work"

        if any(k in lowered for k in ["どう思う", "相談", "考え"]):
            return "discuss"

        # 直前フェーズの継続（人間的挙動）
        prev = getattr(state, "phase", None)
        if prev in {"explore", "discuss"}:
            return prev

        # デフォルト
        return "explore"

    # ==================================================
    # Tone Decision
    # ==================================================

    def _decide_tone(
        self,
        phase: str,
        boundary: Optional[Any],
        salience: Optional[Any],
    ) -> str:
        """
        口調・厳密さの制御
        """
        # 境界が強いときは常に慎重
        if boundary is not None:
            level = getattr(boundary, "level", None)
            if level is not None:
                try:
                    if level.name in {"HIGH", "CRITICAL"}:
                        return "strict"
                except Exception:
                    pass

        if phase in {"work", "review"}:
            return "strict"

        if phase == "discuss":
            return "neutral"

        # explore / 雑談
        return "relaxed"

    # ==================================================
    # Edit Permission Decision
    # ==================================================

    def _decide_edit_permission(self, intent: Any, text: str) -> str:
        """
        編集権限の決定（安全最優先）
        """
        kind = getattr(intent, "kind", None)

        if kind in {"edit", "modify"}:
            # 明示的な書き換え許可があるか
            if any(k in (text or "") for k in ["このファイル", "全部書き換え", "完全に修正"]):
                return "patch"
            return "suggest"

        # 明示語チェック
        lowered = (text or "").lower()
        if any(k in lowered for k in ["直して", "修正案", "diff"]):
            return "suggest"

        return "none"

    # ==================================================
    # Output Format Decision
    # ==================================================

    def _decide_output_format(
        self,
        phase: str,
        edit_permission: str,
        intent: Any,
    ) -> str:
        """
        出力形式の決定
        """
        if edit_permission == "patch":
            return "code"

        if edit_permission == "suggest":
            return "diff"

        if phase == "review":
            return "bullets"

        return "prose"

    # ==================================================
    # State Attachment (non-destructive)
    # ==================================================

    def _attach_to_state(self, state: Any, decision: ConversationDecision) -> None:
        """
        ConversationState に情報を保持（存在しない場合は追加）
        """
        try:
            # 個別フィールド（既存互換）
            setattr(state, "phase", decision.phase)
            setattr(state, "tone", decision.tone)
            setattr(state, "edit_permission", decision.edit_permission)
            setattr(state, "output_format", decision.output_format)

            # まとめた decision（server / prompt / UI 用）
            setattr(state, "conversation_decision", decision)
        except Exception:
            # state が immutable / 特殊実装でも落とさない
            pass