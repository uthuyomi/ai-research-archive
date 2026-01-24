from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal, Optional


# intent.py と合わせるための型
TemporalAxis = Literal[
    "past",
    "present",
    "future",
    "if",
    "unknown",
]


@dataclass
class ConversationState:
    """
    会話全体の状態を保持するクラス。

    ここでは「判断」は一切しない。
    あくまで各モジュールが参照できる
    “事実の置き場”としての State。
    """

    # =========================
    # 基本会話情報
    # =========================

    # 全メッセージ履歴（raw / 整形後どちらも可）
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # ターン数
    turn_count: int = 0

    # =========================
    # Temporal Axis
    # =========================

    # 直近ターンの時間軸
    current_temporal_axis: TemporalAxis = "present"

    # 過去に参照された時間軸の履歴（軽量）
    temporal_history: List[TemporalAxis] = field(default_factory=list)

    # 明示的に「過去の話題」として保持したい要素
    past_topics: List[str] = field(default_factory=list)

    # if軸（仮定・想像）で出た内容の一時置き場
    hypothetical_buffer: List[str] = field(default_factory=list)

    # =========================
    # Conversation Kernel 連携用（判断はしない）
    # =========================

    # 現在の会話フェーズ（explore / discuss / work / review）
    phase: Optional[str] = None

    # 現在のトーン（relaxed / neutral / strict）
    tone: Optional[str] = None

    # 編集権限（none / suggest / patch）
    edit_permission: Optional[str] = None

    # 出力形式（prose / bullets / diff / code）
    output_format: Optional[str] = None

    # Kernel が返した判断結果（まとめ）
    # 型を固定しないことで kernel 実装差分に耐える
    conversation_decision: Optional[Any] = None

    # =========================
    # Turn Registration
    # =========================

    def register_turn(
        self,
        *,
        message: Dict[str, Any],
        temporal_axis: TemporalAxis,
        past_topic: Optional[str] = None,
        hypothetical: Optional[str] = None,
    ) -> None:
        """
        1ターン分の情報を安全に登録する。

        ※ 判断しない
        ※ 書き込むだけ
        """

        self.messages.append(message)
        self.turn_count += 1

        # 時間軸更新
        self.current_temporal_axis = temporal_axis
        self.temporal_history.append(temporal_axis)

        # 過去トピック保存
        if temporal_axis == "past" and past_topic:
            self.past_topics.append(past_topic)

        # if軸内容保存（恒久記憶にしない前提）
        if temporal_axis == "if" and hypothetical:
            self.hypothetical_buffer.append(hypothetical)