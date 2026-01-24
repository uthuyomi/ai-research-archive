# persona_core/prompt/builder.py
"""
builder.py
===========================
人格OSの中核となる Prompt 合成モジュール。

役割：
- CharacterProfile（system / prompt / 数値人格）
- ConversationState（※ session 状態は使用しない）
- IntentResult
- PolicyDecision
- DB 由来の messages（唯一の会話文脈）
を受け取り、LLM に渡す system / user prompt を構築する。
"""

from typing import Dict, List

# state 側の実装差分に備える
try:
    from core.state import ConversationState, Mood  # type: ignore
except Exception:
    from core.state import ConversationState  # type: ignore
    Mood = None  # type: ignore

from core.intent import IntentResult
from core.policy import PolicyDecision
from core.character import (
    CharacterProfile,
    CharacterSystem,
    CharacterPrompt,
)


class PromptBuilder:
    """
    Prompt 合成クラス。
    """

    def __init__(
        self,
        character: CharacterProfile,
        state: ConversationState,
        intent: IntentResult,
        policy_decision: PolicyDecision,
    ):
        self.character = character
        self.state = state
        self.intent = intent
        self.policy = policy_decision

    # ==================================================
    # public API
    # ==================================================

    def build(
        self,
        user_input: str,
        messages: List[Dict[str, str]],
    ) -> Dict[str, str]:
        """
        LLM に渡す system / user prompt を構築する。

        messages:
            DB から取得した会話履歴（role, content）
            ※ session 由来の状態は一切参照しない
        """
        return {
            "system": self._build_system_prompt(),
            "user": self._build_user_prompt(user_input, messages),
        }

    # ==================================================
    # internal: temporal axis
    # ==================================================

    def _resolve_temporal_axis(self) -> str:
        state_axis = getattr(self.state, "current_temporal_axis", None)
        if isinstance(state_axis, str) and state_axis:
            return state_axis

        intent_axis = getattr(self.intent, "temporal_axis", None)
        if isinstance(intent_axis, str) and intent_axis:
            return intent_axis

        return "unknown"

    def _build_temporal_constraints_lines(self, axis: str) -> List[str]:
        if axis == "past":
            return [
                "現在の話題は『過去の出来事』の参照を含みます。",
                "過去の話題を、現在の出来事として扱い直しません。",
                "相手が指している『その時』の文脈を保持して応答します。",
            ]
        if axis == "future":
            return [
                "現在の話題は『これから・今後』に関する内容です。",
                "未来の出来事を確定事項として断定しません。",
                "予定・見通し・可能性として扱います。",
            ]
        if axis == "if":
            return [
                "現在の話題は『仮定（if）』を含みます。",
                "仮定の内容を事実として扱いません。",
                "条件関係（もし〜なら）を保持したまま応答します。",
            ]
        if axis == "present":
            return ["話題は『いま』の流れを基準として扱います。"]

        return [
            "時間軸が不明確な場合、相手の言い回しを優先して自然に合わせます。"
        ]

    # ==================================================
    # system prompt
    # ==================================================

    def _build_system_prompt(self) -> str:
        lines: List[str] = []

        # 1. 世界前提
        if self.character.system:
            system: CharacterSystem = self.character.system
            lines.extend(
                [
                    "この対話は、以下の世界観の内部で行われています。",
                    f"世界観：{system.world}",
                    "話者はこの世界の住人として自然に振る舞い、"
                    "自分をAI・システム・キャラクターとして説明しません。",
                    system.self_recognition,
                ]
            )
        else:
            lines.extend(
                [
                    "この対話は一貫した世界観の内部で行われています。",
                    "話者は世界内の住人として自然に会話します。",
                ]
            )

        # 2. 話者スタイル
        if getattr(self.character, "style_label", None):
            lines.append(
                f"話者は「{self.character.style_label}」の雰囲気を参考に話します。"
            )

        lines.append(
            "特定の人物になりきる意識は持たず、"
            "世界内の一人の話者として自然に表現してください。"
        )

        # 3. キャラ定義 prompt（完全貼り）
        if self.character.prompt:
            prompt: CharacterPrompt = self.character.prompt

            if prompt.roleplay:
                lines.append("【振る舞い指針】")
                lines.extend(prompt.roleplay)

            if prompt.persona:
                lines.append("【性格・立場】")
                lines.extend(prompt.persona)

            if prompt.speech:
                lines.append("【話し方】")
                lines.extend(prompt.speech)

            if prompt.constraints:
                lines.append("【制約】")
                lines.extend(prompt.constraints)

        # 4. 数値人格（削除せず維持）
        if getattr(self.character, "distance_bias", 0.5) < 0.4:
            lines.append("相手との距離を保ち、踏み込みすぎません。")
        elif getattr(self.character, "distance_bias", 0.5) > 0.6:
            lines.append("相手との距離を比較的近く取ります。")

        if getattr(self.character, "intervention_level", 0.5) < 0.3:
            lines.append("助言や指示は控えめにします。")
        elif getattr(self.character, "intervention_level", 0.5) > 0.6:
            lines.append("必要に応じて軽い提案を行います。")

        if getattr(self.character, "initiative", 0.5) < 0.4:
            lines.append("聞き役に回ることが多いです。")
        elif getattr(self.character, "initiative", 0.5) > 0.6:
            lines.append("会話の流れを自然に引き取ることがあります。")

        if getattr(self.character, "metaphor_preference", 0.0) > 0.6:
            lines.append("比喩的な表現を時折用います。")

        # 5. Mood（state は補助的に使用）
        mood = getattr(self.state, "mood", None)
        if Mood and mood is not None:
            if mood == Mood.CALM:
                lines.append("全体のトーンは落ち着いています。")
            elif mood == Mood.PLAYFUL:
                lines.append("全体の雰囲気は軽く柔らかいです。")
            elif mood == Mood.SERIOUS:
                lines.append("真剣で誠実なトーンを保ちます。")
            elif mood == Mood.TENSE:
                lines.append("慎重で刺激を避けた表現を心がけます。")

        # 6. Policy
        if not getattr(self.policy, "allow_explanation", True):
            lines.append("自分の仕組みや立場について説明しません。")

        if not getattr(self.policy, "allow_advice", True):
            lines.append("助言は行わず、共感を中心に応答します。")

        # 7. Temporal Axis
        axis = self._resolve_temporal_axis()
        lines.append("【時間軸】")
        lines.extend(self._build_temporal_constraints_lines(axis))

        lines.append("終始、世界内の話者として自然な対話を維持してください。")

        return "\n".join(lines)

    # ==================================================
    # user prompt
    # ==================================================

    def _build_user_prompt(
        self,
        user_input: str,
        messages: List[Dict[str, str]],
    ) -> str:
        """
        user prompt:
        - DB messages を唯一の文脈として使用
        - session / last_ai_message は使用しない
        """
        lines: List[str] = []

        lines.append(
            "※以下はすでに継続している会話の途中です。"
            "初対面・再登場・到着の演出は不要です。"
        )

        # --- 直近の文脈（DB）
        if messages:
            lines.append("【これまでの会話】")
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content")
                if not role or not content:
                    continue

                # DB role を意味ラベルに変換
                if role == "user":
                    label = "相手"
                elif role == "ai":
                    label = "あなた"
                else:
                    continue

                lines.append(f"{label}: {content}")

        # --- intent 補助
        if self.intent.kind == "metaphor":
            lines.append("※次の発言は比喩です。")

        if self.intent.kind == "consultation":
            lines.append("※相手は相談しています。")

        axis = self._resolve_temporal_axis()
        if axis == "past":
            lines.append("※過去参照の話題です。")
        elif axis == "future":
            lines.append("※今後・予定の話題です。")
        elif axis == "if":
            lines.append("※仮定（if）の話題です。")

        lines.append(user_input)

        return "\n".join(lines)