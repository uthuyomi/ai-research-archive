# persona_core/output/repair.py
"""
repair.py
===========================
LLM の応答が「文法的には正しいが、会話としてズレている」
場合に、人格を維持したまま軌道修正を行うレイヤ。

位置づけ：
- builder.py     : 人格・振る舞いを設計する
- constraints.py: 思考・行動の制約を与える
- repair.py     : 出てしまった文章を「現実側」に戻す
- guard.py      : 表現・AI臭の最終整形

この層は人格OSにおける
「言い直し」「踏み込み抑制」「暴走初期対応」に相当する。

重要：
- kernel（phase / tone）の決定を壊さない
- 意味・判断・結論は変更しない
"""

from typing import List, Optional


class OutputRepair:
    """
    出力文の「ズレ」を検知し、必要に応じて軽く言い直す。

    重要原則：
    - 新しい意味を追加しない
    - 意味を反転させない
    - 文脈を広げない
    - kernel 決定（phase / tone）を最優先する
    """

    def __init__(self):
        # -------------------------
        # 過剰介入を示しやすい語句
        # -------------------------
        self.over_supportive_markers: List[str] = [
            "今すぐ",
            "必ず",
            "まずは",
            "してください",
            "しなければ",
        ]

        # -------------------------
        # メタ視点・説明者ズレ
        # -------------------------
        self.meta_shift_markers: List[str] = [
            "比喩でも",
            "例え話ですが",
            "一般的には",
            "客観的に見ると",
            "言い換えると",
        ]

        # -------------------------
        # 会話を勝手に拡張しがちな兆候
        # -------------------------
        self.topic_expansion_markers: List[str] = [
            "ちなみに",
            "ところで",
            "そういえば",
        ]

    # =========================
    # public API
    # =========================

    def repair(
        self,
        text: str,
        *,
        allow_intervention: bool = True,
        phase: Optional[str] = None,
        tone: Optional[str] = None,
    ) -> str:
        """
        text を受け取り、必要に応じて言い直しを行う。

        allow_intervention:
            False の場合は一切触らない

        phase:
            explore / discuss / work / review
        tone:
            relaxed / neutral / strict
        """

        if not text:
            return text

        if not allow_intervention:
            return text

        # ---------------------------------
        # kernel 尊重：作業・レビューでは触らない
        # ---------------------------------
        if phase in {"work", "review"}:
            return text

        repaired = text

        # 1. 支援・介入が強すぎないか（relaxed / neutral のみ）
        if tone != "strict" and self._is_over_supportive(repaired):
            repaired = self._soften_support(repaired)

        # 2. メタ視点へ逸脱していないか
        if self._has_meta_shift(repaired):
            repaired = self._pull_back_to_character(repaired, tone=tone)

        # 3. 勝手に話題を広げていないか
        if self._has_topic_expansion(repaired):
            repaired = self._trim_topic_expansion(repaired)

        return repaired

    # =========================
    # ズレ検知ロジック
    # =========================

    def _is_over_supportive(self, text: str) -> bool:
        """
        キャラが「支援AI」「助言者」方向へ
        踏み込みすぎていないかを検知。
        """
        hit_count = 0
        for marker in self.over_supportive_markers:
            if marker in text:
                hit_count += 1

        return hit_count >= 2

    def _has_meta_shift(self, text: str) -> bool:
        """
        説明者・観測者視点への逸脱検知。
        """
        for marker in self.meta_shift_markers:
            if marker in text:
                return True
        return False

    def _has_topic_expansion(self, text: str) -> bool:
        """
        不要な話題拡張の検知。
        """
        for marker in self.topic_expansion_markers:
            if marker in text:
                return True
        return False

    # =========================
    # 修正ロジック
    # =========================

    def _soften_support(self, text: str) -> str:
        """
        介入しすぎた文を距離感のある表現へ戻す。
        """
        softened = text

        softened = softened.replace("今すぐ", "")
        softened = softened.replace("必ず", "")
        softened = softened.replace("してください", "してみてもいいかもしれません")
        softened = softened.replace("しなければ", "できれば")

        softened = softened.lstrip("……")
        softened = "……" + softened

        return softened.strip()

    def _pull_back_to_character(self, text: str, *, tone: Optional[str]) -> str:
        """
        メタ視点からキャラ視点へ引き戻す。
        tone が strict の場合は余韻付加をしない。
        """
        repaired = text

        for marker in self.meta_shift_markers:
            repaired = repaired.replace(marker, "")

        repaired = repaired.strip()

        if tone != "strict":
            repaired += "……少なくとも、私の感覚ではそうですね。"

        return repaired

    def _trim_topic_expansion(self, text: str) -> str:
        """
        話題の横滑りを抑止。
        """
        trimmed = text
        for marker in self.topic_expansion_markers:
            trimmed = trimmed.replace(marker, "")
        return trimmed.strip()