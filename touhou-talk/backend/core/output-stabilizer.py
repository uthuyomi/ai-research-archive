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
- builder.py        : 人格設計（初期条件）
- constraints.py   : 思考制限（禁止事項）
- repair.py        : ズレ修正（意味補正）
- stabilizer.py    : 長期安定化（物理ダンパ）
- guard.py         : 最終整形（安全・表現）

重要：
ここでは **判断しない・解釈しない・説教しない**
ただ数値的に「抑える」だけ。
"""

from __future__ import annotations

from typing import Optional


class OutputStabilizer:
    """
    出力を「落ち着いた状態」に保つためのスタビライザ。

    人格・内容・意図には触れず、
    会話の“熱量”と“密度”だけを制御する。
    """

    def __init__(
        self,
        *,
        turn_threshold: int = 8,
        max_turn: int = 20,
        poetic_decay_rate: float = 0.5,
        question_decay_rate: float = 0.4,
    ):
        """
        Parameters
        ----------
        turn_threshold:
            抑制を開始する累積ターン数

        max_turn:
            抑制が最大になるターン数

        poetic_decay_rate:
            詩的装飾を強く削り始める圧の閾値

        question_decay_rate:
            質問抑制を強くかける圧の閾値
        """

        self.turn_threshold = turn_threshold
        self.max_turn = max_turn
        self.poetic_decay_rate = poetic_decay_rate
        self.question_decay_rate = question_decay_rate

    # =========================
    # public API
    # =========================

    def stabilize(
        self,
        text: str,
        *,
        turn_count: int,
        allow_intervention: bool = True,
    ) -> str:
        """
        出力テキストを安定化させる。

        Parameters
        ----------
        text:
            LLM 出力テキスト

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

        pressure = self._calc_pressure(turn_count)

        stabilized = text
        stabilized = self._decay_poetic_expression(stabilized, pressure)
        stabilized = self._decay_questions(stabilized, pressure)

        return stabilized.strip()

    # =========================
    # 内部ロジック
    # =========================

    def _calc_pressure(self, turn_count: int) -> float:
        """
        会話ターン数から抑制圧を算出する。

        Returns
        -------
        float
            0.0 〜 1.0 の範囲
        """

        if turn_count <= self.turn_threshold:
            return 0.0

        if turn_count >= self.max_turn:
            return 1.0

        return (turn_count - self.turn_threshold) / (
            self.max_turn - self.turn_threshold
        )

    # -------------------------
    # 詩的装飾の減衰
    # -------------------------

    def _decay_poetic_expression(self, text: str, pressure: float) -> str:
        """
        詩的・情緒的な装飾を減衰させる。

        対象：
        - 「……」の過剰使用
        - 無意味な余韻の引き伸ばし

        NOTE:
        - 意味や感情は壊さない
        - 文字装飾のみを対象にする
        """

        if pressure <= 0:
            return text

        result = text

        if "……" in result:
            # 圧が高いほど残す数を減らす
            if pressure >= self.poetic_decay_rate:
                max_keep = 1
            else:
                max_keep = 2

            parts = result.split("……")
            result = "……".join(parts[: max_keep + 1])

        return result

    # -------------------------
    # 問い返しの減衰
    # -------------------------

    def _decay_questions(self, text: str, pressure: float) -> str:
        """
        問い返しループを防ぐための減衰処理。

        方針：
        - 弱圧：疑問符を除去
        - 強圧：疑問文そのものを削除
        """

        if "？" not in text:
            return text

        # 強圧：質問文ごと削除
        if pressure >= self.question_decay_rate:
            sentences = text.split("。")
            filtered = [s for s in sentences if "？" not in s]
            return "。".join(filtered)

        # 弱圧：疑問符のみ除去
        return text.replace("？", "")