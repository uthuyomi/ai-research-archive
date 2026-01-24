# persona_core/output/pronoun_normalizer.py
"""
pronoun_normalizer.py
===========================
キャラクター出力における

- 一人称のブレ
- 観測者視点への滑落
- 「自分は◯◯である」という自己軸の希薄化

を抑制するための語用論的ノーマライザ。

位置づけ：
- builder.py        : 人格設計（初期条件）
- constraints.py   : 思考制限
- repair.py        : 意味ズレ修正
- stabilizer.py    : 熱量・密度制御
- pronoun_normalizer.py : 自己参照安定化（ここ）
- guard.py         : 最終整形

重要：
- 内容は変更しない
- 判断・説教・再解釈はしない
- 「語りの立ち位置」だけを矯正する
"""

from __future__ import annotations

import re
from typing import Optional


class PronounNormalizer:
    """
    キャラクターの一人称・自己参照を安定させるためのノーマライザ。

    目的：
    - 観測者・解説者への変質を防ぐ
    - 「私は〜だと思われる」等の距離化を抑える
    - キャラが“その場で話している話者”として留まる
    """

    def __init__(
        self,
        *,
        first_person: str = "私",
        allow_soft_ellipsis: bool = True,
    ):
        """
        Parameters
        ----------
        first_person:
            正規化後に使わせたい一人称
            （例: 私 / あたい / 俺 / 自分 など）

        allow_soft_ellipsis:
            「……」などの間を許容するか
        """
        self.first_person = first_person
        self.allow_soft_ellipsis = allow_soft_ellipsis

        # 観測者・解説者化しやすい表現
        self._observer_patterns = [
            r"一般的に言うと",
            r"〜と言われている",
            r"〜と考えられている",
            r"客観的に見ると",
            r"第三者から見ると",
        ]

        # 自己距離化しやすい表現
        self._detached_self_patterns = [
            r"私は.*と思われる",
            r"私自身としては",
            r"私という存在は",
            r"私の立場からすると",
        ]

    # =========================
    # public API
    # =========================

    def normalize(
        self,
        text: str,
        *,
        allow_intervention: bool = True,
    ) -> str:
        """
        出力テキストの一人称・自己参照を正規化する。

        Parameters
        ----------
        text:
            LLM 出力テキスト

        allow_intervention:
            False の場合は完全スルー
        """

        if not text:
            return text

        if not allow_intervention:
            return text

        result = text

        # 1. 一人称のブレを正規化
        result = self._normalize_first_person(result)

        # 2. 観測者的フレーズを除去・弱化
        result = self._suppress_observer_phrases(result)

        # 3. 自己距離化表現を抑制
        result = self._suppress_detached_self(result)

        return result.strip()

    # =========================
    # 内部ロジック
    # =========================

    def _normalize_first_person(self, text: str) -> str:
        """
        一人称の揺れを正規化する。

        対象：
        - 私 / 自分 / あたい / 俺 などの混在
        """

        # よくある一人称候補
        pronouns = ["私", "自分", "あたい", "俺", "僕"]

        result = text
        for p in pronouns:
            if p != self.first_person:
                # 文頭・助詞直前のみ置換（暴走防止）
                result = re.sub(
                    rf"(?<!\w){p}(?=[はがをに、。])",
                    self.first_person,
                    result,
                )

        return result

    def _suppress_observer_phrases(self, text: str) -> str:
        """
        観測者・解説者に滑りやすいフレーズを抑制する。
        """

        result = text
        for pattern in self._observer_patterns:
            result = re.sub(pattern, "", result)

        return result

    def _suppress_detached_self(self, text: str) -> str:
        """
        自己を一段引いて語る表現を抑制する。

        方針：
        - 削除はするが、意味は壊さない
        """

        result = text
        for pattern in self._detached_self_patterns:
            result = re.sub(pattern, self.first_person, result)

        return result