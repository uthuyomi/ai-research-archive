# persona_core/core/dialogue_control/drift_detector.py
"""
drift_detector.py
===========================
会話ドリフト（話題・前提・役割の逸脱）を検知するモジュール。

ここでいう「ドリフト」とは
--------------------------------
- ユーザーが言っていない前提をAIが確定扱いする
- 会話の主題が、合意なく別方向へ滑っていく
- 推測 → 事実 → 新しい質問、という暴走連鎖
- キャラ人格を維持したまま、中身だけズレていく現象

※ キャラ崩壊とは別。
※ 文体や口調は正常なまま起きるのが特徴。

本モジュールの役割
--------------------------------
- 「おかしくなり始めた瞬間」を検知
- 修正・制御レイヤーに通知
- LLMを賢くしない（暴走させない）

設計思想
--------------------------------
- LLMを信用しない
- 状態と履歴のみを見る
- 言語理解は外部に委譲（intent_parser 等）

このモジュールは
「ブレーキ」であって「ハンドル」ではない。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


# ============================================================
# Drift 種別定義
# ============================================================

class DriftType(str, Enum):
    """
    検知対象となるドリフトの種類
    """

    ASSUMPTION_LEAP = "assumption_leap"
    TOPIC_SHIFT = "topic_shift"
    OBJECT_OVERCOMMIT = "object_overcommit"
    DENIAL_IGNORED = "denial_ignored"
    SPECULATION_CHAIN = "speculation_chain"
    QUESTION_LOOP = "question_loop"


# ============================================================
# Drift イベント
# ============================================================

@dataclass
class DriftEvent:
    """
    検知されたドリフトイベント。
    """
    drift_type: DriftType
    turn_index: int
    description: str
    severity: float = 0.5


# ============================================================
# DriftDetector
# ============================================================

class DriftDetector:
    """
    会話ドリフト検知器。

    ※ 判断はしない
    ※ 修正もしない
    ※ 兆候だけを列挙する
    """

    def __init__(self) -> None:
        self._last_turn_checked: int = -1
        self._recent_questions: List[int] = []
        self._recent_speculation: List[int] = []

    # --------------------------------------------------------
    # main entry
    # --------------------------------------------------------

    def detect(
        self,
        *,
        turn_index: int,
        user_intent: dict,
        ai_intent: dict,
        topic_before: Optional[str],
        topic_after: Optional[str],
        object_events: List[dict],
    ) -> List[DriftEvent]:

        events: List[DriftEvent] = []

        # 重複チェック防止
        if turn_index <= self._last_turn_checked:
            return events

        # ====================================================
        # ① 話題ジャンプ検知（明示切替は除外）
        # ====================================================

        if topic_before and topic_after and topic_before != topic_after:
            if not user_intent.get("explicit_topic_change", False):
                events.append(
                    DriftEvent(
                        drift_type=DriftType.TOPIC_SHIFT,
                        turn_index=turn_index,
                        description=(
                            f"Topic shifted from '{topic_before}' "
                            f"to '{topic_after}' without explicit user consent"
                        ),
                        severity=0.6,
                    )
                )

        # ====================================================
        # ② 未確認オブジェクトの過剰確定
        # ====================================================

        for ev in object_events:
            ev_type = ev.get("type")
            name = ev.get("name")

            if ev_type == "assumed":
                events.append(
                    DriftEvent(
                        drift_type=DriftType.OBJECT_OVERCOMMIT,
                        turn_index=turn_index,
                        description=f"Object '{name}' treated as existing without confirmation",
                        severity=0.7,
                    )
                )

            if ev_type == "denied_but_used":
                events.append(
                    DriftEvent(
                        drift_type=DriftType.DENIAL_IGNORED,
                        turn_index=turn_index,
                        description=f"Denied object '{name}' referenced again",
                        severity=0.9,
                    )
                )

        # ====================================================
        # ③ 推測ジャンプ（要求されていない推測）
        # ====================================================

        if ai_intent.get("speculation", False):
            self._recent_speculation.append(turn_index)
            self._recent_speculation = self._recent_speculation[-3:]

            if not user_intent.get("requested_speculation", False):
                events.append(
                    DriftEvent(
                        drift_type=DriftType.ASSUMPTION_LEAP,
                        turn_index=turn_index,
                        description="AI introduced speculative premise without user request",
                        severity=0.6,
                    )
                )

        # ====================================================
        # ④ 質問ループ（連続性を見る）
        # ====================================================

        if ai_intent.get("is_question", False):
            self._recent_questions.append(turn_index)
            self._recent_questions = self._recent_questions[-5:]

            # 連続3回以上かつ、ユーザーが切替を示していない
            if (
                len(self._recent_questions) >= 3
                and not user_intent.get("explicit_topic_change", False)
            ):
                events.append(
                    DriftEvent(
                        drift_type=DriftType.QUESTION_LOOP,
                        turn_index=turn_index,
                        description="AI is repeatedly asking questions without resolution",
                        severity=0.5,
                    )
                )

        # ====================================================
        # ⑤ 推測連鎖（履歴ベース）
        # ====================================================

        if (
            len(self._recent_speculation) >= 2
            and ai_intent.get("followup_question", False)
        ):
            events.append(
                DriftEvent(
                    drift_type=DriftType.SPECULATION_CHAIN,
                    turn_index=turn_index,
                    description="Speculative reasoning chained across multiple turns",
                    severity=0.8,
                )
            )

        self._last_turn_checked = turn_index
        return events

    # --------------------------------------------------------
    # utility
    # --------------------------------------------------------

    def has_critical_drift(self, events: List[DriftEvent]) -> bool:
        """
        即座に修正が必要なドリフトがあるか。
        """
        return any(ev.severity >= 0.8 for ev in events)