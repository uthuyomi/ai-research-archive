# persona_core/core/dialogue_control/turn_controller.py
"""
turn_controller.py
===========================
会話ターン制御の最終判断モジュール。

役割
--------------------------------
- 検知されたドリフトを元に
  「このターンで何を許可・禁止するか」を決定
- LLMに「自由に考えさせない」
- 生成前に“枠”を与える

この層があることで：
--------------------------------
- 会話が勝手に膨らまない
- 推測が連鎖しない
- 質問が止まる
- キャラ口調は保ったまま、中身だけ制御できる

思想
--------------------------------
- LLMはエンジン、ここはブレーキ＆ギア
- 回答内容を作らない
- 回答「方針」だけを決める
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from .drift_detector import DriftEvent, DriftType


# ============================================================
# ターン制御モード
# ============================================================

class TurnMode(str, Enum):
    """
    このターンで AI が取るべき振る舞いモード
    """

    # 通常応答
    NORMAL = "normal"

    # 話題を戻す
    REFOCUS = "refocus"

    # 推測禁止
    FACT_ONLY = "fact_only"

    # 質問禁止（応答のみ）
    NO_QUESTION = "no_question"

    # 修復モード（前提破棄）
    REPAIR = "repair"

    # 強制短縮
    SHORT_RESPONSE = "short_response"


# ============================================================
# ターン制御指示
# ============================================================

@dataclass
class TurnInstruction:
    """
    LLM に渡す最終制御指示。

    - mode:
        主制御モード
    - allow_speculation:
        推測許可フラグ
    - allow_questions:
        質問許可フラグ
    - max_tokens:
        応答長制限
    - notes:
        デバッグ用説明
    """

    mode: TurnMode
    allow_speculation: bool
    allow_questions: bool
    max_tokens: int
    notes: List[str]


# ============================================================
# TurnController
# ============================================================

class TurnController:
    """
    DriftDetector の結果を受けて
    このターンの「応答ルール」を決定する。
    """

    def __init__(self) -> None:
        pass

    # --------------------------------------------------------
    # main entry
    # --------------------------------------------------------

    def decide(
        self,
        *,
        drift_events: List[DriftEvent],
    ) -> TurnInstruction:
        """
        ターン制御のメイン関数。

        入力
        ----
        drift_events:
            DriftDetector が検知したイベント群

        出力
        ----
        TurnInstruction
        """

        notes: List[str] = []

        # デフォルト
        mode = TurnMode.NORMAL
        allow_speculation = True
        allow_questions = True
        max_tokens = 300

        # ----------------------------------------------------
        # ドリフト重要度判定
        # ----------------------------------------------------

        critical = any(ev.severity >= 0.8 for ev in drift_events)

        # ----------------------------------------------------
        # 個別ドリフト対応
        # ----------------------------------------------------

        for ev in drift_events:
            if ev.drift_type == DriftType.OBJECT_OVERCOMMIT:
                # 未確認オブジェクト → 推測禁止
                allow_speculation = False
                notes.append("Disable speculation due to object overcommit")

            if ev.drift_type == DriftType.ASSUMPTION_LEAP:
                allow_speculation = False
                notes.append("Prevent assumption leap")

            if ev.drift_type == DriftType.DENIAL_IGNORED:
                # これはかなり危険
                mode = TurnMode.REPAIR
                allow_questions = False
                allow_speculation = False
                max_tokens = 150
                notes.append("Repair mode due to denial ignored")

            if ev.drift_type == DriftType.TOPIC_SHIFT:
                mode = TurnMode.REFOCUS
                notes.append("Refocus conversation topic")

            if ev.drift_type == DriftType.QUESTION_LOOP:
                allow_questions = False
                max_tokens = 180
                notes.append("Question loop detected, disable questions")

            if ev.drift_type == DriftType.SPECULATION_CHAIN:
                mode = TurnMode.FACT_ONLY
                allow_speculation = False
                allow_questions = False
                max_tokens = 200
                notes.append("Speculation chain stopped")

        # ----------------------------------------------------
        # 重大ドリフト時の上書き
        # ----------------------------------------------------

        if critical:
            mode = TurnMode.REPAIR
            allow_speculation = False
            allow_questions = False
            max_tokens = min(max_tokens, 150)
            notes.append("Critical drift override applied")

        # ----------------------------------------------------
        # 応答短縮（複数ドリフト同時）
        # ----------------------------------------------------

        if len(drift_events) >= 3:
            max_tokens = min(max_tokens, 120)
            notes.append("Multiple drift events, enforce short response")

        # ----------------------------------------------------
        # 最終決定
        # ----------------------------------------------------

        return TurnInstruction(
            mode=mode,
            allow_speculation=allow_speculation,
            allow_questions=allow_questions,
            max_tokens=max_tokens,
            notes=notes,
        )