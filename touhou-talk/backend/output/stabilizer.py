# persona_core/output/stabilizer.py
"""
stabilizer.py
===========================
会話が長期化した際に発生しやすい

- 詩的密度の上昇
- 問い返しループ
- キャラの語り過多
- 意味の横滑り

を「静かに減衰させる」ための安定化レイヤ。

位置づけ：
- builder.py     : 人格設計
- constraints.py: 思考制限
- repair.py     : ズレ修正
- stabilizer.py : 長期安定化（物理ダンパ）
- guard.py      : 最終整形

重要：
ここでは **判断しない・解釈しない・説教しない**
ただ数値的に「抑える」だけ。
"""

from typing import Optional
import re
import math


class OutputStabilizer:
    """
    出力を「落ち着いた状態」に保つためのスタビライザ。

    人格を変えず、
    会話の“熱量”と“密度”だけを制御する。
    """

    def __init__(self):
        # -------------------------
        # 安定化パラメータ
        # -------------------------

        # 会話がこのターン数を超えると抑制を開始
        self.turn_threshold: int = 8

        # 抑制が最大になるターン数
        self.max_turn: int = 20

        # 詩的表現・比喩の減衰率（開始点）
        self.poetic_decay_rate: float = 0.5

        # 質問文の減衰率（開始点）
        self.question_decay_rate: float = 0.4

    # =========================
    # public API
    # =========================

    def stabilize(
        self,
        text: str,
        *,
        turn_count: int,
        allow_intervention: bool = True
    ) -> str:
        """
        出力テキストを安定化させる。

        turn_count:
            会話の累積ターン数（ユーザー＋AI合計）

        allow_intervention:
            False の場合は完全スルー（安全弁）
        """

        if not text:
            return text

        if not allow_intervention:
            return text

        # ターン数が少ない場合は一切触らない
        if turn_count < self.turn_threshold:
            return text

        stabilized = text

        # ターン数に応じた抑制強度を計算
        pressure = self._calc_pressure(turn_count)

        # 1. 詩的・比喩的な装飾を抑える（※切らない）
        stabilized = self._decay_poetic_expression(stabilized, pressure)

        # 2. 問い返しを抑える（※削除しない）
        stabilized = self._decay_questions(stabilized, pressure)

        return stabilized

    # =========================
    # 内部ロジック
    # =========================

    def _calc_pressure(self, turn_count: int) -> float:
        """
        会話ターン数から抑制圧を算出する。

        0.0 〜 1.0 の範囲。

        ※ 線形ではなく緩やかなカーブで立ち上げる
        """
        if turn_count >= self.max_turn:
            return 1.0

        raw = (turn_count - self.turn_threshold) / (
            self.max_turn - self.turn_threshold
        )

        # ease-in カーブ（急激に抑えすぎない）
        return min(1.0, math.sqrt(max(raw, 0.0)))

    def _decay_poetic_expression(self, text: str, pressure: float) -> str:
        """
        詩的・情緒的な装飾を減衰させる。

        方針（安全版）：
        - 文を切らない
        - 段落・改行を壊さない
        - 強調記号のみを圧縮
        """

        if pressure <= self.poetic_decay_rate:
            return text

        result = text

        # 「……」が3回以上連続している場合のみ圧縮
        result = re.sub(r"(……){2,}", "……", result)

        # 伸ばし表現の軽減（例: ーーー → ー）
        result = re.sub(r"(ー){3,}", "ー", result)

        return result

    def _decay_questions(self, text: str, pressure: float) -> str:
        """
        無限質問ループを防ぐため、
        問い返しを段階的に減衰させる。

        方針（安全版）：
        - 文は削除しない
        - 強圧でも意味は残す
        """

        if "？" not in text:
            return text

        # 強い抑制：疑問を断定に寄せる
        if pressure >= 0.8:
            return text.replace("？", "。")

        # 中程度：疑問符を1つだけ残す
        if pressure >= self.question_decay_rate:
            return re.sub(r"？{2,}", "？", text)

        # 軽い抑制：そのまま
        return text