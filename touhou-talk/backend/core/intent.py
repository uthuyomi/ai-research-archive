"""
intent.py
---------------------------------
ユーザー入力を解析し、
「この発言は何を意図しているのか」を分類するモジュール。

ここでやるのは意味理解ではない。
LLMに渡す前段階の「雑音除去」と「事故防止」。
"""

from dataclasses import dataclass
from typing import Literal
import re


# =========================
# Intent（内部表現）
# =========================

@dataclass(frozen=True)
class Intent:
    """
    生の入力解析結果（事実）。
    """

    is_emotional: bool = False   # 感情的な発言か
    is_metaphor: bool = False    # 比喩表現か
    is_question: bool = False    # 質問か
    is_casual: bool = False      # 軽い雑談か
    is_task: bool = False        # 作業・評価・解析リクエスト
    is_topic_shift: bool = False # ★ 話題・文脈の切替要求


# =========================
# IntentResult（外部制御用）
# =========================

IntentKind = Literal[
    "smalltalk",
    "consultation",
    "metaphor",
    "question",
    "task",
    "chat",
    "topic_shift",   # ★ NEW
]

TemporalAxis = Literal[
    "past",
    "present",
    "future",
    "if",
    "unknown",
]


@dataclass(frozen=True)
class IntentResult:
    kind: IntentKind
    temporal_axis: TemporalAxis


# =========================
# Temporal Axis Resolver
# =========================

PAST_PATTERNS = ["この前", "さっき", "昨日", "前に", "以前"]
FUTURE_PATTERNS = ["これから", "次", "今度", "明日", "そのうち"]
IF_PATTERNS = ["もし", "仮に", "たら", "なら"]


def resolve_temporal_axis(text: str) -> TemporalAxis:
    normalized = text.strip().lower()

    for pat in IF_PATTERNS:
        if re.search(pat, normalized):
            return "if"

    for pat in PAST_PATTERNS:
        if re.search(pat, normalized):
            return "past"

    for pat in FUTURE_PATTERNS:
        if re.search(pat, normalized):
            return "future"

    if normalized:
        return "present"

    return "unknown"


# =========================
# Intent Resolver
# =========================

CONSULTATION_HINTS = [
    "相談",
    "悩んで",
    "悩み",
    "聞いて",
    "話がある",
    "相談がある",
]

TOPIC_SHIFT_HINTS = [
    "話変わる",
    "話変える",
    "別の話",
    "ところで",
    "さて",
    "じゃあさ",
    "ちなみにだけど",
]


def resolve_intent(intent: Intent, *, text: str) -> IntentResult:
    normalized = text.strip().lower()
    temporal_axis = resolve_temporal_axis(text)

    # 0) ★ 文脈切替（最優先・内容は見ない）
    if intent.is_topic_shift:
        return IntentResult("topic_shift", temporal_axis)

    # 1) 比喩
    if intent.is_metaphor:
        return IntentResult("metaphor", temporal_axis)

    # 2) 感情（相談）
    if intent.is_emotional:
        return IntentResult("consultation", temporal_axis)

    for pat in CONSULTATION_HINTS:
        if re.search(pat, normalized):
            return IntentResult("consultation", temporal_axis)

    # 3) 作業・評価・解析
    if intent.is_task:
        return IntentResult("task", temporal_axis)

    # 4) 質問
    if intent.is_question:
        return IntentResult("question", temporal_axis)

    # 5) 雑談
    if intent.is_casual:
        return IntentResult("smalltalk", temporal_axis)

    # 6) 通常会話
    return IntentResult("chat", temporal_axis)


# =========================
# Intent Parser
# =========================

class IntentParser:
    """
    ユーザー入力を解析して Intent（boolean集合）を返す。
    """

    EMOTIONAL_PATTERNS = [
        "疲れ", "しんど", "つら", "無理", "限界", "死にそう",
    ]

    METAPHOR_HINTS = [
        "みたい", "っぽい", "感じ", "気分", "比喩",
    ]

    QUESTION_PATTERNS = [
        r"\?$", r"？$", "どう", "なに", "なんで", "なぜ", "どっち",
    ]

    CASUAL_PATTERNS = [
        "笑", r"w$", "だね", "かな", "なんとなく",
    ]

    TASK_PATTERNS = [
        "評価",
        "解析",
        "分析",
        "おかしい",
        "改善",
        "レビュー",
        "指摘",
        "設計",
        "問題点",
        "チェック",
    ]

    TOPIC_SHIFT_PATTERNS = [
        "話変わる",
        "話変える",
        "別の話",
        "ところで",
        "さて",
        "じゃあ",
        "ちなみに",
    ]

    @classmethod
    def parse(cls, text: str) -> Intent:
        normalized = text.strip().lower()
        intent = Intent()

        # ★ 文脈切替（最優先・他と独立）
        for pat in cls.TOPIC_SHIFT_PATTERNS:
            if re.search(pat, normalized):
                intent = Intent(
                    is_emotional=intent.is_emotional,
                    is_metaphor=intent.is_metaphor,
                    is_question=intent.is_question,
                    is_casual=intent.is_casual,
                    is_task=intent.is_task,
                    is_topic_shift=True,
                )
                break

        for pat in cls.EMOTIONAL_PATTERNS:
            if re.search(pat, normalized):
                intent = Intent(
                    is_emotional=True,
                    is_metaphor=intent.is_metaphor,
                    is_question=intent.is_question,
                    is_casual=intent.is_casual,
                    is_task=intent.is_task,
                    is_topic_shift=intent.is_topic_shift,
                )
                break

        for pat in cls.METAPHOR_HINTS:
            if re.search(pat, normalized):
                intent = Intent(
                    is_emotional=intent.is_emotional,
                    is_metaphor=True,
                    is_question=intent.is_question,
                    is_casual=intent.is_casual,
                    is_task=intent.is_task,
                    is_topic_shift=intent.is_topic_shift,
                )
                break

        for pat in cls.TASK_PATTERNS:
            if re.search(pat, normalized):
                intent = Intent(
                    is_emotional=intent.is_emotional,
                    is_metaphor=intent.is_metaphor,
                    is_question=intent.is_question,
                    is_casual=intent.is_casual,
                    is_task=True,
                    is_topic_shift=intent.is_topic_shift,
                )
                break

        for pat in cls.QUESTION_PATTERNS:
            if re.search(pat, normalized):
                intent = Intent(
                    is_emotional=intent.is_emotional,
                    is_metaphor=intent.is_metaphor,
                    is_question=True,
                    is_casual=intent.is_casual,
                    is_task=intent.is_task,
                    is_topic_shift=intent.is_topic_shift,
                )
                break

        for pat in cls.CASUAL_PATTERNS:
            if re.search(pat, normalized):
                intent = Intent(
                    is_emotional=intent.is_emotional,
                    is_metaphor=intent.is_metaphor,
                    is_question=intent.is_question,
                    is_casual=True,
                    is_task=intent.is_task,
                    is_topic_shift=intent.is_topic_shift,
                )
                break

        return intent