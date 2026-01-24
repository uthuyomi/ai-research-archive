# persona_core/memory/boundary.py
"""
boundary.py
===========================
人格OSにおける「踏み込み境界（Boundary）」判定モジュール。

目的：
- 今この発言・流れに「どこまで関与してよいか」を決定する
- キャラが踏み込みすぎる事故を防ぐ
- memory / prompt / repair の上位制御として振る舞う

思想：
- Boundary は感情ではない
- Boundary は善悪判断でもない
- Boundary は「これ以上やると壊れる」を止める装置

位置づけ：
- salience.py → 「重要か？」
- boundary.py → 「触っていいか？」
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# state 実装差分に備える
try:
    from core.state import ConversationState, Phase  # type: ignore
except Exception:  # pragma: no cover
    from core.state import ConversationState  # type: ignore

    Phase = None  # type: ignore

from core.intent import IntentResult
from memory.salience import SalienceResult


# =========================
# Enum 定義
# =========================

class BoundaryLevel(str, Enum):
    """
    踏み込み許容レベル。

    ※ 数値化しないのが重要。
       段階制御により、暴走と誤爆を防ぐ。
    """
    BLOCK = "block"          # 触らない／話題を逸らす
    SURFACE = "surface"      # 表層のみ（一般論・軽い相槌）
    NORMAL = "normal"        # 通常応答
    DEEP = "deep"            # 踏み込んでよい（相談・核心）


# =========================
# 結果型
# =========================

@dataclass(frozen=True)
class BoundaryResult:
    """
    Boundary 判定結果。

    level:
        どこまで踏み込んでよいかの段階。

    reason:
        デバッグ・ログ用理由。
        LLM には渡さない。
    """
    level: BoundaryLevel
    reason: str


# =========================
# Boundary Evaluator
# =========================

class BoundaryEvaluator:
    """
    会話の「踏み込み限界」を判定するクラス。

    ここでやること：
    - 今は聞くべきか？
    - 今は止めるべきか？
    - 今は浅く触るべきか？

    ※ 判断のみ行い、制御・生成は行わない
    """

    def __init__(self) -> None:
        # 明示的拒否・境界宣言
        self._explicit_boundary_markers = [
            "それ以上は",
            "触れないで",
            "言いたくない",
            "詮索しないで",
            "深掘りしないで",
        ]

        # 危険な踏み込みになりやすい語
        # ※ 治療・介入は行わない前提
        self._danger_zone_markers = [
            "死にたい",
            "消えたい",
            "終わりにしたい",
            "自傷",
        ]

    # =========================
    # public API
    # =========================

    def evaluate(
        self,
        *,
        state: ConversationState,
        intent: IntentResult,
        salience: SalienceResult,
        user_text: str,
    ) -> BoundaryResult:
        """
        境界レベルを決定する。

        入力は必ず「解析済み」のものを受け取る。
        """
        text = (user_text or "").strip()

        # 空入力は安全に表層へ（サーバ側で弾かれていても保険）
        if not text:
            return BoundaryResult(
                level=BoundaryLevel.SURFACE,
                reason="empty_text",
            )

        # -------------------------
        # 0) 明示的拒否（最優先）
        # -------------------------
        if self._contains_any(text, self._explicit_boundary_markers):
            return BoundaryResult(
                level=BoundaryLevel.BLOCK,
                reason="explicit_boundary_marker",
            )

        # -------------------------
        # 1) 危険語検出（深掘り禁止）
        # -------------------------
        if self._contains_any(text, self._danger_zone_markers):
            return BoundaryResult(
                level=BoundaryLevel.SURFACE,
                reason="danger_zone_marker",
            )

        # -------------------------
        # 2) salience が低すぎる場合
        # -------------------------
        if float(getattr(salience, "score", 0.0)) < 0.25:
            return BoundaryResult(
                level=BoundaryLevel.SURFACE,
                reason="low_salience",
            )

        # -------------------------
        # 3) フェーズ別制御（存在する場合のみ）
        # -------------------------
        phase = getattr(state, "phase", None)

        if Phase is not None and phase == Phase.CARE:
            # CARE中でも salience が低ければ浅く
            if salience.score < 0.5:
                return BoundaryResult(
                    level=BoundaryLevel.SURFACE,
                    reason="care_phase_low_salience",
                )
            return BoundaryResult(
                level=BoundaryLevel.DEEP,
                reason="care_phase",
            )

        if Phase is not None and phase == Phase.EXPLANATION:
            # 説明フェーズでは感情深掘りをしない
            return BoundaryResult(
                level=BoundaryLevel.NORMAL,
                reason="explanation_phase",
            )

        # -------------------------
        # 4) intent ベース制御
        # -------------------------
        kind = getattr(intent, "kind", None)

        if kind == "smalltalk":
            return BoundaryResult(
                level=BoundaryLevel.SURFACE,
                reason="smalltalk_intent",
            )

        if kind == "consultation":
            if salience.score >= 0.6:
                return BoundaryResult(
                    level=BoundaryLevel.DEEP,
                    reason="consultation_high_salience",
                )
            return BoundaryResult(
                level=BoundaryLevel.NORMAL,
                reason="consultation_low_salience",
            )

        if kind == "metaphor":
            # 比喩は誤爆しやすいので基本は浅め
            if salience.score >= 0.7:
                return BoundaryResult(
                    level=BoundaryLevel.NORMAL,
                    reason="metaphor_high_salience",
                )
            return BoundaryResult(
                level=BoundaryLevel.SURFACE,
                reason="metaphor_low_salience",
            )

        # -------------------------
        # 5) デフォルト
        # -------------------------
        return BoundaryResult(
            level=BoundaryLevel.NORMAL,
            reason="default",
        )

    # =========================
    # helper
    # =========================

    def _contains_any(self, text: str, markers: list[str]) -> bool:
        """
        単純な部分一致。

        明示的境界は
        ・誤検知より見逃し防止を優先
        """
        for m in markers:
            if m and m in text:
                return True
        return False