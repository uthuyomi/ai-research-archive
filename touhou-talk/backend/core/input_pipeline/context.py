"""
context.py

input_pipeline の最終統合層。

役割：
- envelope / detector / preprocess / intent_score / ocr を統合
- LLM に渡す「生成用コンテキスト」を明示的に構築
- 生成トーン・詳細度・断言強度・禁止事項を決定

方針：
- 意味理解はしない
- 判断は upstream（detector / intent_score / vision / ocr）で完結
- ここでは「生成の枠組み」だけを作る
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from core.input_pipeline.envelope import InputEnvelope, EnvelopeReliability
from core.input_pipeline.detector import DetectionResult, PrimaryMode, AttachmentRole
from core.input_pipeline.intent_score import IntentScoreResult, Intent
from core.input_pipeline.preprocess import PreprocessResult


# =========================
# 生成トーン定義
# =========================

class GenerationTone(str, Enum):
    CASUAL = "casual"            # 雑談寄り
    NEUTRAL = "neutral"          # 標準
    EXPLANATORY = "explanatory"  # 解説重視
    ANALYTICAL = "analytical"    # 分析・レビュー寄り
    CAUTIOUS = "cautious"        # 断定回避・慎重


# =========================
# 禁止アクション（安全弁）
# =========================

FORBIDDEN_ACTIONS_BASE = [
    "numerical_validation",
    "business_decision",
    "legal_judgement",
    "medical_judgement",
    "financial_advice",
]


# =========================
# 出力構造
# =========================

@dataclass(frozen=True)
class GenerationContext:
    # 入力事実
    text: str
    attachments_info: List[Dict[str, Any]]

    # 判定結果
    primary_mode: PrimaryMode
    attachment_role: AttachmentRole
    primary_intent: Intent

    # 生成制御
    tone: GenerationTone
    detail_level: float          # 0.0〜1.0
    confidence: float            # 0.0〜1.0（断言上限）

    # 安全制御
    forbid_actions: List[str]
    reliability: EnvelopeReliability

    # OCR / Vision 由来の素材（判断しない）
    ocr: Optional[Any]

    # ★追加：link 素材（未解決 / 解決済）
    links: List[Dict[str, Any]]
    links_resolved: List[Dict[str, Any]]

    # デバッグ・説明用
    meta: Dict[str, Any]


# =========================
# メインビルダー
# =========================

def build_generation_context(
    *,
    envelope: InputEnvelope,
    detected: DetectionResult,
    intent_score: IntentScoreResult,
    preprocess: PreprocessResult,
    ocr: Optional[Any] = None,
) -> GenerationContext:
    """
    input_pipeline の最終出口。
    server.py から直接呼ばれる前提。
    """

    # -------------------------
    # トーン決定
    # -------------------------
    if detected.primary_mode == PrimaryMode.CHAT:
        tone = GenerationTone.CASUAL
    elif intent_score.primary == Intent.EXPLAIN:
        tone = GenerationTone.EXPLANATORY
    elif intent_score.primary in (Intent.REVIEW, Intent.DEBUG):
        tone = GenerationTone.ANALYTICAL
    else:
        tone = GenerationTone.NEUTRAL

    # reliability が LOW の場合は慎重寄り
    if envelope.reliability == EnvelopeReliability.LOW:
        tone = GenerationTone.CAUTIOUS

    # -------------------------
    # 詳細度（説明の粒度）
    # -------------------------
    if intent_score.primary == Intent.CHAT:
        detail_level = 0.3
    elif intent_score.primary == Intent.EXPLAIN:
        detail_level = 0.7
    elif intent_score.primary == Intent.DEBUG:
        detail_level = 0.8
    elif intent_score.primary == Intent.REVIEW:
        detail_level = 0.7
    else:
        detail_level = 0.5

    # -------------------------
    # 断言強度（confidence cap）
    # -------------------------
    confidence = intent_score.confidence

    if envelope.reliability == EnvelopeReliability.MEDIUM:
        confidence = min(confidence, 0.75)
    elif envelope.reliability == EnvelopeReliability.LOW:
        confidence = min(confidence, 0.6)

    # -------------------------
    # 添付情報（生成用の軽量要約）
    # -------------------------
    attachments_info: List[Dict[str, Any]] = []

    for att in preprocess.attachments_summary:
        info = {
            "filename": att.get("filename"),
            "kind": att.get("kind"),
            "skipped": att.get("skipped", False),
        }

        # 生成に使ってよい軽量メタのみ
        for key in (
            "line_count",
            "char_count",
            "paragraph_count",
            "heading_count",
            "sheet_count",
            "sheets",
            "page_estimate",
        ):
            if key in att:
                info[key] = att[key]

        attachments_info.append(info)

    # -------------------------
    # ★ documents executor meta
    # -------------------------
    documents_meta: List[Dict[str, Any]] = []

    for att in preprocess.attachments_summary:
        if "document_meta" in att:
            documents_meta.append({
                "filename": att.get("filename"),
                "skipped": att.get("skipped", False),
                "document_meta": att.get("document_meta"),
            })

    # -------------------------
    # 禁止アクション決定
    # -------------------------
    forbid_actions = list(FORBIDDEN_ACTIONS_BASE)

    if intent_score.primary == Intent.DECIDE:
        forbid_actions.append("final_decision")

    if confidence < 0.6:
        forbid_actions.append("strong_assertion")

    # -------------------------
    # meta（説明責任・デバッグ用）
    # -------------------------
    meta: Dict[str, Any] = {
        "detector_reasons": detected.reasons,
        "intent_reasons": intent_score.reasons,
        "preprocess_reasons": preprocess.reasons,
        "detail_level": detail_level,
        "tone": tone.value,
    }

    if documents_meta:
        meta["documents_meta"] = documents_meta

    # OCR は「実行されたかどうか」だけを明示
    if ocr is not None:
        meta["ocr_executed"] = bool(getattr(ocr, "executed", False))
        meta["ocr_reasons"] = getattr(ocr, "reasons", [])

    # -------------------------
    # ★ link 情報の正式統合
    # -------------------------
    links: List[Dict[str, Any]] = getattr(preprocess, "links", []) or []

    links_resolved: List[Dict[str, Any]] = []
    if "links_resolved" in meta:
        links_resolved = meta.get("links_resolved", []) or []

    return GenerationContext(
        text=envelope.text,
        attachments_info=attachments_info,
        primary_mode=detected.primary_mode,
        attachment_role=detected.attachment_role,
        primary_intent=intent_score.primary,
        tone=tone,
        detail_level=detail_level,
        confidence=confidence,
        forbid_actions=forbid_actions,
        reliability=envelope.reliability,

        # OCR / Vision 素材（意味解釈しない）
        ocr=ocr,

        # ★正式フィールド
        links=links,
        links_resolved=links_resolved,

        meta=meta,
    )