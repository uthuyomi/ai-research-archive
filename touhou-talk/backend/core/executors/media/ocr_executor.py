"""
ocr_executor.py

画像添付に対する OCR 実行層。

役割：
- vision_executor が「画像を扱うべき」と判断した場合のみ起動
- 画像から文字を抽出する
- 意味理解・要約・評価は一切行わない

重要思想：
- ChatGPT互換（勝手にOCRしない）
- OCRは素材生成であり、判断は上位層
- 失敗しても全体を壊さない
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.input_pipeline.envelope import InputEnvelope, AttachmentKind
from core.executors.media.vision_executor import VisionResult
from core.input_pipeline.detector import DetectionResult, PrimaryMode
from core.input_pipeline.intent_score import IntentScoreResult, Intent

# AttachmentSource は memory / path 判定に使用
from core.input_pipeline.envelope import AttachmentSource


# =========================
# optional OCR backend
# =========================

try:
    import pytesseract
    from PIL import Image

    # ★ Windows 環境向け：tesseract.exe 明示指定
    # PowerShell で `where tesseract` して出たパスを使う
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

except Exception:  # pragma: no cover
    pytesseract = None
    Image = None

# =========================
# 出力構造
# =========================

@dataclass(frozen=True)
class OCRResult:
    """
    OCR の出力。

    executed:
        - True  : OCR を実行した
        - False : 実行しなかった
    """
    executed: bool
    texts: List[Dict[str, Any]]
    skipped: bool
    reasons: List[str]


# =========================
# 内部設定（保守的）
# =========================

MIN_CHAR_COUNT = 5          # これ未満はノイズ扱い
MAX_TEXT_LENGTH = 10_000    # OCR暴走防止
DEFAULT_LANG = "jpn+eng"    # 日本語＋英語


# =========================
# 内部ユーティリティ
# =========================

def _write_temp_image(data: bytes, suffix: str | None) -> Path:
    """
    memory 添付（bytes）を一時ファイルに書き出す。
    OCR 用途限定なので delete=False で明示管理。
    """
    sfx = f".{suffix.lstrip('.')}" if suffix else ".img"

    tmp = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=sfx,
        delete=False,
    )
    tmp.write(data)
    tmp.flush()
    tmp.close()

    return Path(tmp.name)


# =========================
# メイン関数
# =========================

def execute_ocr(
    envelope: InputEnvelope,
    vision: VisionResult,
    detection: DetectionResult,
    intent: IntentScoreResult,
) -> OCRResult:
    """
    OCR 実行エントリポイント。
    """

    reasons: List[str] = []

    # -------------------------
    # 実行条件チェック
    # -------------------------
    if not vision.analyzed:
        return OCRResult(
            executed=False,
            texts=[],
            skipped=True,
            reasons=["vision_not_analyzed"],
        )

    if pytesseract is None or Image is None:
        return OCRResult(
            executed=False,
            texts=[],
            skipped=True,
            reasons=["ocr_backend_not_available"],
        )

    # ChatGPT互換ルール：
    # 明示的に「解析寄り」の intent のみ OCR 許可
    if intent.primary not in (Intent.DEBUG, Intent.EXPLAIN, Intent.REVIEW):
        return OCRResult(
            executed=False,
            texts=[],
            skipped=True,
            reasons=[f"intent_not_allowed:{intent.primary.value}"],
        )

    # ANALYSIS 以外では OCR を抑制
    if detection.primary_mode != PrimaryMode.ANALYSIS:
        return OCRResult(
            executed=False,
            texts=[],
            skipped=True,
            reasons=["primary_mode_not_analysis"],
        )

    # -------------------------
    # OCR 対象抽出
    # -------------------------
    image_attachments = [
        att for att in envelope.attachments
        if att.meta.kind == AttachmentKind.image
    ]

    if not image_attachments:
        return OCRResult(
            executed=False,
            texts=[],
            skipped=True,
            reasons=["no_image_attachments"],
        )

    # -------------------------
    # OCR 実行
    # -------------------------
    results: List[Dict[str, Any]] = []

    for att in image_attachments:
        meta = att.meta
        ref = att.ref

        image_path: Path | None = None
        temp_created = False

        # ---- path 添付（従来）
        if ref.source == AttachmentSource.path and ref.file_path:
            image_path = Path(ref.file_path)

            if not image_path.exists():
                reasons.append(f"image_file_not_found:{meta.filename}")
                continue

        # ---- memory 添付（今回対応）
        elif ref.source == AttachmentSource.memory and ref.bytes_data:
            try:
                image_path = _write_temp_image(
                    data=ref.bytes_data,
                    suffix=meta.ext,
                )
                temp_created = True
                reasons.append(f"temp_image_created:{meta.filename}")
            except Exception as e:
                reasons.append(f"temp_image_failed:{meta.filename}:{e}")
                continue

        else:
            reasons.append(f"skip_image_no_source:{meta.filename}")
            continue

        try:
            img = Image.open(str(image_path))

            raw_text = pytesseract.image_to_string(
                img,
                lang=DEFAULT_LANG,
            )

            if not raw_text:
                reasons.append(f"empty_ocr_result:{meta.filename}")
                continue

            text = raw_text.strip()

            if len(text) < MIN_CHAR_COUNT:
                reasons.append(f"ocr_text_too_short:{meta.filename}")
                continue

            if len(text) > MAX_TEXT_LENGTH:
                text = text[:MAX_TEXT_LENGTH]
                reasons.append(f"ocr_text_truncated:{meta.filename}")

            results.append({
                "filename": meta.filename,
                "char_count": len(text),
                "language_hint": DEFAULT_LANG,
                "text": text,
            })

            reasons.append(f"ocr_executed:{meta.filename}")

        except Exception as e:
            reasons.append(f"ocr_failed:{meta.filename}:{e}")

        finally:
            # 一時ファイルは必ず削除
            if temp_created and image_path:
                try:
                    image_path.unlink(missing_ok=True)
                except Exception:
                    reasons.append(f"temp_cleanup_failed:{meta.filename}")

    # -------------------------
    # 結果整理
    # -------------------------
    if not results:
        return OCRResult(
            executed=False,
            texts=[],
            skipped=True,
            reasons=reasons + ["no_valid_ocr_text"],
        )

    return OCRResult(
        executed=True,
        texts=results,
        skipped=False,
        reasons=reasons,
    )