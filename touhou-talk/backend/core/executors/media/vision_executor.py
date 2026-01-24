"""
vision_executor.py

画像添付に対する最小限・安全な処理層。

役割：
- 画像が存在するかを検出
- 枚数・拡張子・サイズなど「事実情報」のみ整理
- OCR / CV / 意味理解は一切しない
- Phase3（画像解析）に進むかどうかの判断材料を作る

重要：
- ChatGPT 互換思想
- 将来 OCR / Vision モデルを差し替え可能
- 今は「やらない判断」を正しくすることが目的
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.input_pipeline.envelope import InputEnvelope, AttachmentKind
from core.input_pipeline.detector import DetectionResult, PrimaryMode
from core.input_pipeline.intent_score import IntentScoreResult, Intent


# =========================
# 出力構造
# =========================

@dataclass(frozen=True)
class VisionResult:
    """
    vision_executor の出力。

    analyzed:
        - True  : Phase3 に進んでよいと判断された
        - False : 画像は検出したが解析は行わない

    skipped:
        - True  : 処理自体をスキップ
        - False : 最低限の整理は行った
    """
    analyzed: bool
    image_count: int
    images: List[Dict[str, Any]]
    skipped: bool
    reasons: List[str]


# =========================
# メイン関数
# =========================

def execute_vision(
    envelope: InputEnvelope,
    detection: DetectionResult,
    intent: IntentScoreResult,
) -> VisionResult:
    """
    画像添付がある場合の最小限処理。
    """

    reasons: List[str] = []

    # -------------------------
    # 画像抽出（事実）
    # -------------------------
    image_attachments = [
        att for att in envelope.attachments
        if att.meta.kind == AttachmentKind.image
    ]

    image_count = len(image_attachments)

    if image_count == 0:
        return VisionResult(
            analyzed=False,
            image_count=0,
            images=[],
            skipped=True,
            reasons=["no_image_attachments"],
        )

    reasons.append(f"image_count={image_count}")

    # -------------------------
    # 画像メタ情報整理（軽量・安全）
    # -------------------------
    images_info: List[Dict[str, Any]] = []

    for att in image_attachments:
        meta = att.meta
        images_info.append({
            "filename": meta.filename,
            "ext": meta.ext,
            "size_bytes": meta.size_bytes,
            "sha256": meta.sha256,
        })

    # -------------------------
    # Phase3 に進むかの判断
    # -------------------------
    # 原則：
    # - 勝手に解析しない
    # - detector と intent の両方を見る
    #
    # 明示条件（ChatGPT互換）：
    # 1. primary_mode == ANALYSIS
    # 2. intent が「画像を扱いそう」なもの
    #
    # どちらも満たさなければ Phase3 は false
    needs_phase3 = False

    if detection.primary_mode == PrimaryMode.ANALYSIS:
        reasons.append("analysis_mode_detected")
        needs_phase3 = True

    if intent.primary in (Intent.EXPLAIN, Intent.REVIEW, Intent.DEBUG):
        reasons.append(f"intent_allows_image_handling:{intent.primary.value}")
        needs_phase3 = True

    # -------------------------
    # スキップ判定
    # -------------------------
    if not needs_phase3:
        return VisionResult(
            analyzed=False,
            image_count=image_count,
            images=images_info,
            skipped=True,
            reasons=reasons + ["vision_phase3_not_required"],
        )

    # -------------------------
    # Phase3 stub（現時点では中身なし）
    # -------------------------
    # ここでは「進んでよい」という事実だけを返す
    reasons.append("vision_phase3_enabled_stub")

    return VisionResult(
        analyzed=True,
        image_count=image_count,
        images=images_info,
        skipped=False,
        reasons=reasons,
    )