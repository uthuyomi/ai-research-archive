"""
detector.py

InputEnvelope を受け取り、
「この入力をどう扱うべきか」を判断する層。

責務（重要）:
- 内容の意味理解はしない
- 解析はしない
- あくまで「扱い方の分類」と「処理の要否」を決める

ここでの判断は:
- preprocess を走らせるか
- 生成トーンをどう寄せるか
- attachment が主役か補足か
を決めるための“交通整理”。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List

from core.input_pipeline.envelope import (
    InputEnvelope,
    AttachmentKind,
    InputType,
    infer_input_type_from_envelope,
)


# =========================
# URL検出（軽量・副作用なし）
# =========================

_URL_RE = re.compile(r"https?://", re.IGNORECASE)


def _text_contains_url(text: str) -> bool:
    """
    detector 層での最低限の URL 判定。
    厳密な解析は preprocess / link pipeline に委ねる。
    """
    if not text:
        return False
    return bool(_URL_RE.search(text))


# =========================
# 判定結果の定義
# =========================

class PrimaryMode(str, Enum):
    """
    この入力の主目的。
    """
    CHAT = "chat"          # 雑談・軽い会話
    ANALYSIS = "analysis"  # 説明・レビュー・構造把握
    TASK = "task"          # 判断・作業・次の一手


class AttachmentRole(str, Enum):
    """
    添付の役割。
    """
    NONE = "none"          # 添付なし
    SUPPORT = "support"    # 会話の補助
    PRIMARY = "primary"    # 添付が主役


@dataclass(frozen=True)
class DetectionResult:
    """
    detector の最終出力。
    """
    primary_mode: PrimaryMode
    attachment_role: AttachmentRole
    needs_preprocess: bool
    confidence: float
    reasons: List[str]


# =========================
# メイン判定関数
# =========================

def detect_input(envelope: InputEnvelope) -> DetectionResult:
    """
    InputEnvelope から入力の性質を判定する。

    判定はスコアリングではなく、
    説明可能なルールベースのみを用いる。
    """

    reasons: List[str] = []

    # -------------------------
    # 入力タイプの事実ベース推定
    # -------------------------
    input_type: InputType = infer_input_type_from_envelope(envelope)
    reasons.append(f"inferred_input_type={input_type.value}")

    text: str = envelope.text.strip()
    has_text: bool = bool(text)
    has_attachments: bool = len(envelope.attachments) > 0
    text_len: int = len(text)

    contains_url: bool = _text_contains_url(text)
    if contains_url:
        reasons.append("text_contains_url=true")

    # -------------------------
    # 添付の内訳を把握
    # -------------------------
    image_count = 0
    non_image_count = 0

    for att in envelope.attachments:
        if att.meta.kind == AttachmentKind.image:
            image_count += 1
        else:
            non_image_count += 1

    if image_count:
        reasons.append(f"image_count={image_count}")
    if non_image_count:
        reasons.append(f"file_count={non_image_count}")

    # -------------------------
    # 添付の役割判定
    # -------------------------
    if not has_attachments:
        attachment_role = AttachmentRole.NONE
        reasons.append("attachment_role=none")

    else:
        # テキストがほぼ無い → 添付が主役
        if not has_text or text_len < 20:
            attachment_role = AttachmentRole.PRIMARY
            reasons.append("attachment_role=primary_due_to_no_text")

        else:
            attachment_role = AttachmentRole.SUPPORT
            reasons.append("attachment_role=support_with_text")

    # -------------------------
    # primary_mode 判定
    # -------------------------
    # 優先度：
    # 1. 添付が主役 → ANALYSIS
    # 2. 添付あり → ANALYSIS
    # 3. テキストのみ → CHAT / TASK
    if attachment_role == AttachmentRole.PRIMARY:
        primary_mode = PrimaryMode.ANALYSIS
        reasons.append("primary_mode=analysis_primary_attachment")

    elif has_attachments:
        primary_mode = PrimaryMode.ANALYSIS
        reasons.append("primary_mode=analysis_with_attachments")

    else:
        # テキストのみ
        reasons.append(f"text_length={text_len}")

        if text_len < 200:
            primary_mode = PrimaryMode.CHAT
            reasons.append("primary_mode=chat_short_text")

        else:
            primary_mode = PrimaryMode.TASK
            reasons.append("primary_mode=task_long_text")

    # -------------------------
    # preprocess 要否判定
    # -------------------------
    # 原則：
    # - ANALYSIS → preprocess
    # - 例外：短文CHATでも URL が含まれていれば preprocess
    needs_preprocess = False

    if primary_mode == PrimaryMode.ANALYSIS:
        needs_preprocess = True
        reasons.append("needs_preprocess=true_by_analysis")

    elif primary_mode == PrimaryMode.CHAT and contains_url:
        needs_preprocess = True
        reasons.append("needs_preprocess=true_by_url_in_chat")

    else:
        reasons.append("needs_preprocess=false")

    # -------------------------
    # confidence 算出
    # -------------------------
    confidence = 0.85

    # 短文のみは揺らぎやすい
    if not has_attachments and text_len < 50:
        confidence -= 0.1
        reasons.append("confidence_down_short_text_only")

    confidence = max(0.4, min(confidence, 0.95))

    return DetectionResult(
        primary_mode=primary_mode,
        attachment_role=attachment_role,
        needs_preprocess=needs_preprocess,
        confidence=confidence,
        reasons=reasons,
    )