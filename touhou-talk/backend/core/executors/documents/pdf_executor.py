# core/input_pipeline/executors/documents/pdf_executor.py
"""
pdf_executor.py
=================================================
PDF (.pdf) ファイル用 Executor（テキスト抽出版）

【設計思想】
- PDF は「見た目重視・構造破壊済み」のフォーマット
- ここでは意味解析・段組推定・レイアウト復元は行わない
- 抽出できたテキストのみを安全に LLM へ渡す

【前提ライブラリ】
- PyPDF2
  pip install PyPDF2

【やらないこと】
- OCR（画像PDFは対象外）
- レイアウト復元
- 表構造の推定
- 注釈・リンク解析

【やること】
- ページ単位でテキスト抽出
- サイズ・ページ数制限
- 失敗しても例外を握り潰さず Executor 側で制御
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List

from .base import DocumentExecutorBase

try:
    from PyPDF2 import PdfReader
except Exception as e:  # import 時点で落ちるのを防ぐ
    PdfReader = None


class PDFExecutor(DocumentExecutorBase):
    """
    PDF 用 Executor
    """

    supported_extensions = (".pdf",)
    filetype_label = "pdf"

    # ===== 安全制御 =====
    MAX_BYTES: int = 10 * 1024 * 1024      # 10MB
    MAX_CHARS: int = 120_000               # 抽出後の最大文字数
    MAX_PAGES: int = 50                    # 読み取る最大ページ数

    def _extract_text(
        self,
        *,
        filename: str,
        raw_bytes: bytes,
        encoding: Optional[str],
    ) -> tuple[str, Dict[str, Any]]:
        """
        PDF からテキストを抽出する。

        戦略：
        1) ライブラリ存在確認
        2) サイズ制限
        3) PdfReader 初期化
        4) ページ単位で抽出
        5) 正規化
        6) 長さ制限
        """

        if PdfReader is None:
            raise RuntimeError(
                "PyPDF2 is not installed. "
                "Install with: pip install PyPDF2"
            )

        if raw_bytes is None:
            raise ValueError("raw_bytes is None")

        original_size = len(raw_bytes)

        # 1) サイズ制限（bytes）
        truncated_bytes = raw_bytes
        truncated_by_bytes = False
        if original_size > self.MAX_BYTES:
            truncated_bytes = raw_bytes[: self.MAX_BYTES]
            truncated_by_bytes = True

        # 2) PdfReader 初期化
        try:
            from io import BytesIO
            reader = PdfReader(BytesIO(truncated_bytes))
        except Exception as e:
            raise ValueError(f"pdf_open_failed: {e}")

        # 3) ページ数制御
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, self.MAX_PAGES)

        extracted_pages: List[str] = []
        page_errors: List[int] = []

        # 4) ページ単位で抽出
        for idx in range(pages_to_read):
            try:
                page = reader.pages[idx]
                text = page.extract_text() or ""
                extracted_pages.append(text)
            except Exception:
                # 特定ページだけ壊れているケースは多い
                page_errors.append(idx)
                continue

        # 5) 結合・正規化
        combined = "\n\n".join(
            f"[Page {i + 1}]\n{txt}"
            for i, txt in enumerate(extracted_pages)
            if txt.strip()
        )

        normalized = (
            combined
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )

        # 6) 長さ制限（chars）
        truncated_by_chars = False
        if len(normalized) > self.MAX_CHARS:
            normalized = normalized[: self.MAX_CHARS]
            truncated_by_chars = True

        meta: Dict[str, Any] = {
            "original_bytes": original_size,
            "truncated_by_bytes": truncated_by_bytes,
            "truncated_by_chars": truncated_by_chars,
            "char_count": len(normalized),
            "pages_total": total_pages,
            "pages_read": pages_to_read,
            "page_errors": page_errors,
            "max_pages": self.MAX_PAGES,
            "max_chars": self.MAX_CHARS,
            "pdf_text_extracted": True,
            "ocr_used": False,
        }

        return normalized, meta