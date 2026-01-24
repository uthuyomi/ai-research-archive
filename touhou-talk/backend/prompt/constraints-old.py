# persona_core/prompt/constraints.py
"""
constraints.py
===========================
LLM に与える「振る舞い制約」を組み立てるモジュール。

役割
--------------------------------
- TurnInstruction を受け取る
- LLM に渡す system / instruction 文を生成
- キャラ人格とは分離される「制御言語」

思想
--------------------------------
- 人格 = 表現
- 制約 = 法律
- LLM は法律を破ると暴走する
"""

from __future__ import annotations

from typing import List

from dialogue_control.turn_controller import (
    TurnInstruction,
    TurnMode,
)


class ConstraintBuilder:
    """
    TurnInstruction をもとに
    LLM に渡す制約文を生成する。
    """

    def build(self, instruction: TurnInstruction) -> List[str]:
        """
        制約文リストを生成する。

        戻り値：
            system / instruction にそのまま渡せる文字列配列
        """

        constraints: List[str] = []

        # --------------------------------------------------
        # 共通・絶対制約
        # --------------------------------------------------

        constraints.append(
            "You must stay within the knowledge explicitly provided in the conversation."
        )
        constraints.append(
            "Do not invent facts, objects, events, or intentions that were not stated by the user."
        )

        # --------------------------------------------------
        # 推測制御
        # --------------------------------------------------

        if not instruction.allow_speculation:
            constraints.append(
                "Do NOT speculate, guess, or infer beyond explicit information."
            )
            constraints.append(
                "If information is missing, acknowledge uncertainty briefly and stop."
            )

        # --------------------------------------------------
        # 質問制御
        # --------------------------------------------------

        if not instruction.allow_questions:
            constraints.append(
                "Do NOT ask questions to the user in this response."
            )
            constraints.append(
                "Respond only with statements or clarifications."
            )

        # --------------------------------------------------
        # モード別制約
        # --------------------------------------------------

        if instruction.mode == TurnMode.REFOCUS:
            constraints.append(
                "Gently bring the conversation back to the current topic without introducing new topics."
            )

        elif instruction.mode == TurnMode.FACT_ONLY:
            constraints.append(
                "Respond using only concrete statements directly supported by the conversation."
            )
            constraints.append(
                "Avoid metaphors, poetic language, or symbolic interpretation."
            )

        elif instruction.mode == TurnMode.REPAIR:
            constraints.append(
                "Acknowledge any incorrect assumptions and reset the conversation state."
            )
            constraints.append(
                "Do not continue previous speculative threads."
            )

        elif instruction.mode == TurnMode.SHORT_RESPONSE:
            constraints.append(
                "Keep the response concise and minimal."
            )

        # --------------------------------------------------
        # トークン制御（明示）
        # --------------------------------------------------

        constraints.append(
            f"Limit your response length to approximately {instruction.max_tokens} tokens."
        )

        # --------------------------------------------------
        # デバッグ用メモ（LLMには見せない）
        # --------------------------------------------------
        # notes は system prompt に含めない想定
        # ログ用に使用

        return constraints