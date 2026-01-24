# persona_core/memory/session.py
"""
session.py
===========================
人格OSにおける「短期会話記憶（Session Memory）」を管理するモジュール。

役割：
- 直近のユーザー発言 / AI応答を保持
- 会話の流れを“最低限”つなぐ
- kernel（phase）に応じて保持密度を調整

重要：
- 判断しない
- 解釈しない
- 永続化しない
"""

from dataclasses import dataclass, field
from typing import List, Literal, Dict, Optional


# =========================
# 型定義
# =========================

Role = Literal["user", "assistant"]

TimeAxis = Literal["present", "past", "future", "if"]

Phase = Literal["explore", "discuss", "work", "review"]


@dataclass
class Message:
    """
    会話1発言分の構造。

    axis:
        いつの話か（意味付けはしない）
    """
    role: Role
    content: str
    axis: TimeAxis = "present"


# =========================
# Session Memory 本体
# =========================

@dataclass
class SessionMemory:
    """
    短期会話記憶クラス。

    - kernel が決めた phase を尊重する
    - 作業時は“流れ”より“直近”を優先
    """

    max_turns: int = 6
    messages: List[Message] = field(default_factory=list)

    # =========================
    # 追加系 API
    # =========================

    def add_user(
        self,
        text: str,
        axis: TimeAxis = "present",
        *,
        phase: Optional[Phase] = None,
    ) -> None:
        """
        ユーザー発言を追加。
        """
        self.messages.append(
            Message(
                role="user",
                content=text.strip(),
                axis=axis,
            )
        )
        self._trim(phase=phase)

    def add_assistant(
        self,
        text: str,
        axis: TimeAxis = "present",
        *,
        phase: Optional[Phase] = None,
    ) -> None:
        """
        AI応答を追加。
        """
        self.messages.append(
            Message(
                role="assistant",
                content=text.strip(),
                axis=axis,
            )
        )
        self._trim(phase=phase)

    # =========================
    # 取得系 API
    # =========================

    def get_messages(self) -> List[Dict[str, str]]:
        """
        LLM に渡す用（互換重視）。
        """
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]

    def get_messages_with_axis(self) -> List[Dict[str, str]]:
        """
        デバッグ・内部処理用。
        """
        return [
            {
                "role": m.role,
                "content": m.content,
                "axis": m.axis,
            }
            for m in self.messages
        ]

    def get_last_user_message(self) -> Optional[str]:
        for m in reversed(self.messages):
            if m.role == "user":
                return m.content
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        for m in reversed(self.messages):
            if m.role == "assistant":
                return m.content
        return None

    # =========================
    # 内部処理
    # =========================

    def _trim(self, *, phase: Optional[Phase]) -> None:
        """
        phase に応じて保持戦略を切り替える。

        explore / discuss:
            - 従来通り max_turns * 2 を保持

        work / review:
            - 直近 2 ターン分のみ保持
            - 作業ノイズを残さない
        """

        if phase in {"work", "review"}:
            # 作業・レビューは直近重視
            max_messages = 4  # user + assistant × 2
        else:
            max_messages = self.max_turns * 2

        if len(self.messages) > max_messages:
            overflow = len(self.messages) - max_messages
            self.messages = self.messages[overflow:]

    # =========================
    # デバッグ・管理
    # =========================

    def debug(self) -> str:
        lines = ["[SessionMemory]"]
        for i, m in enumerate(self.messages):
            lines.append(
                f"{i:02d} {m.role} ({m.axis}): {m.content}"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        """
        セッションを完全にリセット。
        """
        self.messages.clear()