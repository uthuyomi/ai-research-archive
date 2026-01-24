"""
preprocess.py

input_pipeline における「軽量前処理」層。

目的：
- detector の結果を踏まえ、
  “必要な場合のみ” 添付やテキストに軽く触る
- 内容の意味理解はしない
- 構造・規模・性質など「事実＋準事実」のみ抽出する

重要原則：
- 重い処理はしない
- 断定しない
- 失敗しても全体を壊さない
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.input_pipeline.envelope import (
    InputEnvelope,
    AttachmentKind,
)

from core.input_pipeline.detector import DetectionResult
from core.executors.documents import execute_document

# ★追加：link 検出（解析はしない）


# --- optional deps（存在しない環境でも落とさない） ---
try:
    from pdfminer.high_level import extract_text as pdf_extract_text
except Exception:  # pragma: no cover
    pdf_extract_text = None

try:
    import docx  # python-docx
except Exception:  # pragma: no cover
    docx = None

try:
    import openpyxl
except Exception:  # pragma: no cover
    openpyxl = None


# =========================
# 出力構造
# =========================

@dataclass(frozen=True)
class PreprocessResult:
    """
    preprocess の最終出力。
    context_builder / generation_context が
    そのまま使える形にする。
    """
    text_summary: Optional[Dict[str, Any]]
    attachments_summary: List[Dict[str, Any]]
    documents_meta: List[Dict[str, Any]]

    # ★追加：検出されたリンク（未解決・未解析）
    links: List[Dict[str, Any]]

    skipped: bool
    reasons: List[str]


# =========================
# メイン関数
# =========================

def preprocess_input(
    envelope: InputEnvelope,
    detection: DetectionResult,
) -> PreprocessResult:
    """
    前処理のエントリポイント。

    ※ intent は扱わない（score_intent の責務）
    """

    reasons: List[str] = []

    # -------------------------
    # preprocess を走らせるか？
    # -------------------------
    if not detection.needs_preprocess:
        return PreprocessResult(
            text_summary=None,
            attachments_summary=[],
            documents_meta=[],
            links=[],
            skipped=True,
            reasons=["detector_decided_skip_preprocess"],
        )

    # -------------------------
    # テキスト側の軽量処理
    # -------------------------
    text_summary: Optional[Dict[str, Any]] = None
    links: List[Dict[str, Any]] = []

    if envelope.text:
        text = envelope.text
        lines = text.splitlines()

        text_summary = {
            "text_length": len(text),
            "line_count": len(lines),
            "has_code_block": "```" in text,
        }
        reasons.append("text_summary_generated")
    # -------------------------
    # 添付の前処理
    # -------------------------
    attachments_summary: List[Dict[str, Any]] = []

    for att in envelope.attachments:
        summary = _preprocess_attachment(att)
        attachments_summary.append(summary)
        reasons.append(f"processed_attachment:{att.meta.filename}")

    # -------------------------
    # documents_meta 抽出
    # -------------------------
    documents_meta: List[Dict[str, Any]] = []

    for item in attachments_summary:
        if not item.get("skipped") and "document_meta" in item:
            documents_meta.append(
                {
                    "filename": item.get("filename"),
                    "document_meta": item.get("document_meta"),
                }
            )

    return PreprocessResult(
        text_summary=text_summary,
        attachments_summary=attachments_summary,
        documents_meta=documents_meta,
        links=links,
        skipped=False,
        reasons=reasons,
    )


# =========================
# 添付別処理
# =========================

def _preprocess_attachment(att) -> Dict[str, Any]:
    """
    添付1件分の前処理。

    重要：
    - path 添付（filesystem）
    - memory 添付（UploadFile / bytes）
    の両方を正しく扱う
    """
    meta = att.meta
    ref = att.ref

    base: Dict[str, Any] = {
        "filename": meta.filename,
        "kind": meta.kind.value,
        "size_bytes": meta.size_bytes,
        "skipped": False,
    }

    # -------------------------
    # IMAGE
    # -------------------------
    if meta.kind == AttachmentKind.image:
        base.update(
            {
                "image_hint": True,
                "analysis_note": "image_present_no_ocr",
            }
        )
        return base

    # -------------------------
    # DOCUMENT / CODE / SHEET
    # -------------------------
    try:
        data: Optional[bytes] = None

        # ===== memory 添付（UploadFile 経由）=====
        if ref.source == ref.source.memory and ref.bytes_data:
            data = ref.bytes_data

        # ===== path 添付（filesystem）=====
        elif ref.source == ref.source.path and ref.file_path:
            path = Path(ref.file_path)
            if path.exists():
                data = path.read_bytes()

        # どちらでも data を取得できなかった場合
        if not data:
            base["skipped"] = True
            base["reason"] = "file_not_found"
            return base

        # documents executor に委譲
        result = execute_document(
            filename=meta.filename,
            data=data,
        )

        if result is None:
            base["skipped"] = True
            base["reason"] = "no_document_executor"
            return base

        # 解釈しない・評価しない・そのまま載せる
        base["document_meta"] = result
        return base

    except Exception as e:
        base["skipped"] = True
        base["error"] = str(e)
        return base