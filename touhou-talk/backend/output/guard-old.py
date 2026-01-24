# persona_core/output/guard.py
"""
guard.py
===========================
LLM の出力をそのままユーザーに返さず、
日本語・会話・人格の破綻を防ぐための最終ガード層。

役割の整理：
- builder.py            : 人格・振る舞いを「指示」として組み立てる
- constraints.py        : 思考制限
- repair.py             : 意味的ズレ修正
- stabilizer.py         : 熱量・密度の減衰
- pronoun_normalizer.py : 自己参照の安定化
- guard.py              : 最終的な発声・表現の整形（ここ）

ここは人格OSにおける
「声帯」「発声調整」「ノイズ除去」に相当する。

重要：
- 意味は変えない
- 判断・説教・再解釈をしない
- kernel が決めた output_format を最優先で強制する
"""

from __future__ import annotations

import re
from typing import List, Optional


class OutputGuard:
    """
    出力テキストの最終調整クラス。

    このクラスでは「意味の改変」は行わない。
    行うのはあくまで：
    - AI臭の除去
    - 会話圧の軽減
    - 表現ノイズの削減

    ただし output_format が指定された場合は、
    その形式を最優先で保持する。
    """

    def __init__(self):
        # -------------------------
        # AIっぽさが出やすい定型句
        # -------------------------
        self.ai_phrases: List[str] = [
            "一般的に",
            "通常は",
            "〜と言えるでしょう",
            "考えられます",
            "〜の可能性があります",
            "AIとして",
            "私はAIなので",
            "システムとして",
        ]

    # =========================
    # public API
    # =========================

    def process(
        self,
        text: str,
        *,
        output_format: Optional[str] = None,
    ) -> str:
        """
        LLM の生出力を受け取り、最終ガード処理を行う。

        output_format:
            - prose   : 通常会話（すべてのガード有効）
            - bullets : 箇条書き（会話ガードを抑制）
            - diff    : 差分提示（整形のみ、会話調整しない）
            - code    : コード（一切加工しない）
        """

        if not text:
            return text

        # 段落・改行を保持するため、改行は strip しない
        result = text.strip("\n")

        # =========================
        # 0. output_format 強制
        # =========================

        if output_format == "code":
            # コードは一切触らない
            return result

        if output_format == "diff":
            # diff は軽い行末空白整理のみ
            return result.rstrip()

        if output_format == "bullets":
            # 箇条書きは完全保持
            return result

        # ここから下は prose（通常会話）のみ

        # =========================
        # 1. 明確なAI説明臭の除去
        # =========================
        result = self._remove_ai_explanation(result)

        # =========================
        # 2. 箇条書き・命令ラッシュの緩和
        # =========================
        result = self._soften_list_expression(result)

        # =========================
        # 3. 文末表現・句読点の破綻防止
        # =========================
        result = self._fix_sentence_endings(result)

        # =========================
        # 4. 問いかけ過多による圧の軽減
        # =========================
        result = self._reduce_excessive_questions(result)

        return result

    # =========================
    # 各ガード処理
    # =========================

    def _remove_ai_explanation(self, text: str) -> str:
        """
        AIが「解説者」「外部視点」になろうとする癖を抑える。

        ※ 改行・段落は保持する
        """
        result = text
        for phrase in self.ai_phrases:
            result = result.replace(phrase, "")

        # 改行を含まない空白のみ正規化（段落は壊さない）
        result = re.sub(r"[ \t]{2,}", " ", result)
        return result

    def _soften_list_expression(self, text: str) -> str:
        """
        突然の箇条書きを会話寄りに緩和する。

        ※ 構造・記号・改行は保持する
        ※ 「消す」のではなく「何もしない」ことで安全性を担保
        """
        return text

    def _fix_sentence_endings(self, text: str) -> str:
        """
        文末・句読点の破綻防止。

        ※ 行構造は変更しない
        """
        result = text
        result = re.sub(r"(です。){2,}", "です。", result)
        result = re.sub(r"(ます。){2,}", "ます。", result)
        result = re.sub(r"(でしょうか？){2,}", "でしょうか？", result)
        result = re.sub(r"(。){2,}", "。", result)
        return result

    def _reduce_excessive_questions(self, text: str) -> str:
        """
        問いかけ過多による圧迫感を軽減。

        ※ 改行・段落は保持
        """
        count = text.count("？")
        if count < 3:
            return text

        parts = text.split("？")
        return "？".join(parts[:-1]) + "？"