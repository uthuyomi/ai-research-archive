# persona_core/memory/session.py
"""
session.py
===========================
人格OSにおける「短期会話記憶（Session Memory）」を管理するモジュール。

役割：
- 直近のユーザー発言 / AI応答を保持
- 会話の流れを“最低限”つなぐ
- conversation_mode ごとに文脈を分離保持する

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

ConversationMode = Literal["technical", "casual"]


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

    - conversation_mode ごとに独立した履歴を持つ
    - mode 切替後は、以前の mode の履歴を参照しない
    """

    max_turns: int = 6

    # mode 別メッセージバッファ
    buffers: Dict[ConversationMode, List[Message]] = field(
        default_factory=lambda: {
            "technical": [],
            "casual": [],
        }
    )

    # 現在の会話モード（外部から明示的に切替）
    current_mode: ConversationMode = "technical"

    # =========================
    # 追加系 API
    # =========================

    def set_mode(self, mode: ConversationMode) -> None:
        """
        会話モードを切り替える。
        ここでは履歴を触らない。
        """
        if mode in self.buffers:
            self.current_mode = mode

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
        self._current_buffer().append(
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
        self._current_buffer().append(
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
        現在の conversation_mode のみ参照する。
        """
        return [
            {"role": m.role, "content": m.content}
            for m in self._current_buffer()
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
            for m in self._current_buffer()
        ]

    def get_last_user_message(self) -> Optional[str]:
        for m in reversed(self._current_buffer()):
            if m.role == "user":
                return m.content
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        for m in reversed(self._current_buffer()):
            if m.role == "assistant":
                return m.content
        return None

    # =========================
    # 内部処理
    # =========================

    def _current_buffer(self) -> List[Message]:
        return self.buffers[self.current_mode]

    def _trim(self, *, phase: Optional[Phase]) -> None:
        """
        phase に応じて保持戦略を切り替える。

        explore / discuss:
            - 従来通り max_turns * 2 を保持

        work / review:
            - 直近 2 ターン分のみ保持
        """

        buffer = self._current_buffer()

        if phase in {"work", "review"}:
            max_messages = 4
        else:
            max_messages = self.max_turns * 2

        if len(buffer) > max_messages:
            overflow = len(buffer) - max_messages
            self.buffers[self.current_mode] = buffer[overflow:]

    # =========================
    # デバッグ・管理
    # =========================

    def debug(self) -> str:
        lines = [f"[SessionMemory mode={self.current_mode}]"]
        for i, m in enumerate(self._current_buffer()):
            lines.append(
                f"{i:02d} {m.role} ({m.axis}): {m.content}"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        """
        現在モードのセッションをリセット。
        """
        self.buffers[self.current_mode].clear()

    def clear_all(self) -> None:
        """
        全モードの履歴を完全にリセット。
        """
        for buf in self.buffers.values():
            buf.clear()