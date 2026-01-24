# persona_core/memory/salience.py
"""
salience.py
===========================
人格OSにおける「重要度（Salience）」判定モジュール。

目的：
- ユーザー/AIの発言が「会話の核」か「流れてよい雑音」かを数値化する
- SessionMemory の圧縮・要約・長期記憶への移送に使う前段

重要：
- ここは「感情を表現」しない
- ここは「診断」しない
- ここは「保存」しない
- ここは「重要っぽさ」を判定して返すだけ（制御用スコア）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Role = Literal["user", "assistant"]


# =========================
# 結果型
# =========================

@dataclass(frozen=True)
class SalienceResult:
    """
    重要度判定の結果。

    score:
        0.0 ~ 1.0 の連続値。
        高いほど「会話の核」である可能性が高い。

    reasons:
        スコアに影響した要因のラベル。
        デバッグ・将来の学習用。
    """
    score: float
    reasons: tuple[str, ...] = ()

    @property
    def is_memorable(self) -> bool:
        """
        長期記憶候補かどうかの目安。

        ※ このクラス自身は保存処理を行わない。
           server / memory manager 側で判断に使う。
        """
        return self.score >= 0.5


# =========================
# Salience Evaluator
# =========================

class SalienceEvaluator:
    """
    発言重要度を推定するクラス。

    - 文脈理解は行わない
    - 意味解釈もしない
    - あくまで「信号の強さ」を見る
    """

    def __init__(self) -> None:
        # 会話の核になりやすい語
        self._high_signal_keywords = [
            "助けて",
            "相談",
            "悩み",
            "不安",
            "怖い",
            "つらい",
            "苦しい",
            "限界",
            "死にそう",
            "やばい",
            "本題",
            "結論",
            "要するに",
            "大事",
        ]

        # 意思決定・方針固定を示す語
        self._commitment_keywords = [
            "やる",
            "決めた",
            "進める",
            "方針",
            "ルール",
            "前提",
            "必須",
            "固定",
        ]

        # 記憶参照・継続性トリガー
        self._memory_trigger_keywords = [
            "前に",
            "さっき",
            "この前",
            "覚えて",
            "記憶",
            "引き継ぎ",
            "前提",
        ]

        # 明確な雑談マーカー
        self._smalltalk_markers = [
            "w",
            "笑",
            "草",
            "うける",
            "眠い",
            "腹減った",
            "暇",
        ]

    # =========================
    # public API
    # =========================

    def evaluate(
        self,
        text: str,
        *,
        role: Role = "user",
        intent_kind: Optional[str] = None,
        is_metaphor: bool = False,
    ) -> SalienceResult:
        """
        発言テキストから salience を算出する。

        intent_kind は補助情報としてのみ使用し、
        判定の主軸はあくまでテキスト信号とする。
        """
        raw = text.strip()
        if not raw:
            return SalienceResult(score=0.0, reasons=("empty",))

        # ベースライン（前振り・文脈維持用）
        score = 0.30
        reasons: list[str] = []

        # -------------------------
        # 1) 長さ・構造
        # -------------------------
        length = len(raw)
        if length >= 120:
            score += 0.10
            reasons.append("long_text")
        elif length <= 12:
            # 相談文脈では短さを理由に落としすぎない
            if intent_kind != "consultation":
                score -= 0.05
                reasons.append("very_short")

        if raw.count("\n") >= 2:
            score += 0.10
            reasons.append("structured_lines")

        # -------------------------
        # 2) 質問シグナル
        # -------------------------
        if "?" in raw or "？" in raw:
            score += 0.08
            reasons.append("question")

        # -------------------------
        # 3) キーワード群
        # -------------------------
        if self._contains_any(raw, self._high_signal_keywords):
            score += 0.25
            reasons.append("high_signal_keyword")

        if self._contains_any(raw, self._commitment_keywords):
            score += 0.20
            reasons.append("commitment_keyword")

        if self._contains_any(raw, self._memory_trigger_keywords):
            score += 0.15
            reasons.append("memory_trigger_keyword")

        # -------------------------
        # 4) intent 補正
        # -------------------------
        if intent_kind == "consultation":
            score += 0.15
            reasons.append("intent_consultation")

        if intent_kind == "smalltalk":
            score -= 0.10
            reasons.append("intent_smalltalk")

        if intent_kind == "metaphor" or is_metaphor:
            score += 0.06
            reasons.append("intent_metaphor")

        # -------------------------
        # 5) role 補正
        # -------------------------
        if role == "assistant":
            score -= 0.05
            reasons.append("assistant_bias_down")

        # -------------------------
        # 6) 明確な雑談マーカー
        # -------------------------
        if self._contains_any(raw, self._smalltalk_markers):
            score -= 0.08
            reasons.append("smalltalk_marker")

        # -------------------------
        # 7) 相談文脈の最低保証
        # -------------------------
        if (
            intent_kind == "consultation"
            and "high_signal_keyword" in reasons
            and score < 0.45
        ):
            score = 0.45
            reasons.append("consultation_floor")

        score = self._clamp(score, 0.0, 1.0)
        return SalienceResult(score=score, reasons=tuple(reasons))

    # =========================
    # helper
    # =========================

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        for k in keywords:
            if k in text:
                return True
        return False

    def _clamp(self, v: float, lo: float, hi: float) -> float:
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v