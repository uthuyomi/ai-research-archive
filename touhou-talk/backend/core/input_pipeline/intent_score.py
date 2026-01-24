"""
intent_score.py

detector が決めた「扱い方（離散）」に対して、
intent_score は「何を求めているかの濃度（連続）」を推定する。

重要方針：
- 意味理解はしない
- LLMは使わない
- ルールベース・説明可能
- 複数intentに同時スコアを与える（どれか一つに決めない）

この結果は context_builder / executor 選択で
・生成トーン
・説明の粒度
・踏み込み度
・Phase3（画像解析など）起動判定
に使われる。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from core.input_pipeline.envelope import InputEnvelope, AttachmentKind
from core.input_pipeline.detector import DetectionResult, PrimaryMode


# =========================
# Intent 定義
# =========================

class Intent(str, Enum):
    CHAT = "chat"          # 雑談・感想
    EXPLAIN = "explain"    # 仕組み・内容の説明
    REVIEW = "review"      # 評価・レビュー
    DECIDE = "decide"      # 判断材料が欲しい
    DEBUG = "debug"        # 問題解決・原因特定


# =========================
# 出力構造
# =========================

@dataclass(frozen=True)
class IntentScoreResult:
    scores: Dict[Intent, float]
    primary: Intent
    confidence: float
    reasons: List[str]


# =========================
# メイン関数
# =========================

def score_intent(
    envelope: InputEnvelope,
    detection: DetectionResult,
) -> IntentScoreResult:
    """
    InputEnvelope + DetectionResult を元に intent スコアを算出する。
    """

    # -------------------------
    # 初期スコア
    # -------------------------
    scores: Dict[Intent, float] = {
        Intent.CHAT: 0.0,
        Intent.EXPLAIN: 0.0,
        Intent.REVIEW: 0.0,
        Intent.DECIDE: 0.0,
        Intent.DEBUG: 0.0,
    }

    reasons: List[str] = []

    text = envelope.text or ""
    text_len = len(text.strip())
    has_text = text_len > 0
    has_attachments = len(envelope.attachments) > 0

    # 添付の性質
    image_count = 0
    code_like = False
    doc_like = False

    for att in envelope.attachments:
        kind = att.meta.kind
        ext = att.meta.ext

        if kind == AttachmentKind.image:
            image_count += 1
        else:
            if ext in (".py", ".js", ".ts", ".tsx", ".json", ".yml", ".yaml", ".css", ".scss"):
                code_like = True
            else:
                doc_like = True

    # -------------------------
    # detector 結果によるベース配分
    # -------------------------
    if detection.primary_mode == PrimaryMode.CHAT:
        scores[Intent.CHAT] += 0.6
        reasons.append("primary_mode_chat")

    elif detection.primary_mode == PrimaryMode.ANALYSIS:
        scores[Intent.EXPLAIN] += 0.4
        scores[Intent.REVIEW] += 0.4
        reasons.append("primary_mode_analysis")

    elif detection.primary_mode == PrimaryMode.TASK:
        scores[Intent.DECIDE] += 0.4
        scores[Intent.DEBUG] += 0.3
        reasons.append("primary_mode_task")

    # -------------------------
    # テキスト量による補正
    # -------------------------
    if has_text:
        if text_len < 80:
            scores[Intent.CHAT] += 0.2
            reasons.append("short_text_bias_chat")

        elif text_len < 300:
            scores[Intent.EXPLAIN] += 0.2
            reasons.append("medium_text_bias_explain")

        else:
            scores[Intent.REVIEW] += 0.2
            scores[Intent.DECIDE] += 0.2
            reasons.append("long_text_bias_review_decide")

    # -------------------------
    # 添付による補正
    # -------------------------
    if has_attachments:
        if image_count > 0:
            scores[Intent.EXPLAIN] += 0.25
            scores[Intent.REVIEW] += 0.25
            reasons.append("image_present")

        if code_like:
            scores[Intent.DEBUG] += 0.4
            scores[Intent.REVIEW] += 0.2
            reasons.append("code_attachment_present")

        if doc_like:
            scores[Intent.EXPLAIN] += 0.3
            scores[Intent.REVIEW] += 0.3
            reasons.append("document_attachment_present")

    # -------------------------
    # スコア正規化
    # -------------------------
    for k in scores:
        scores[k] = max(0.0, min(scores[k], 1.0))

    # -------------------------
    # primary intent 決定
    # -------------------------
    primary = max(scores.items(), key=lambda x: x[1])[0]
    reasons.append(f"primary_intent={primary.value}")

    # -------------------------
    # confidence 算出
    # -------------------------
    sorted_vals = sorted(scores.values(), reverse=True)
    gap = sorted_vals[0] - sorted_vals[1] if len(sorted_vals) > 1 else sorted_vals[0]

    confidence = 0.6 + min(gap, 0.3)
    confidence = max(0.5, min(confidence, 0.9))

    return IntentScoreResult(
        scores=scores,
        primary=primary,
        confidence=confidence,
        reasons=reasons,
    )