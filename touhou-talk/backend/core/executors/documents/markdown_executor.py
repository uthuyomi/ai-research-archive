# core/input_pipeline/executors/documents/markdown_executor.py
"""
markdown_executor.py
=================================================
Markdown (.md) ファイル用 Executor（構造保持版）

【設計思想】
- Markdown は「文書構造」が意味を持つ
- ここでは「意味理解」や「再解釈」はしない
- LLM に渡したとき、構造が壊れない形で text を渡す

【やらないこと】
- HTML 変換
- AST 解析
- 見出しの意味付け
- コードブロックの実行 / 評価

【やること】
- txt_executor 相当の安全対策
- Markdown 特有の構造を壊さない
- 行単位での軽い正規化
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import DocumentExecutorBase


class MarkdownExecutor(DocumentExecutorBase):
    """
    Markdown (.md) 用 Executor
    """

    supported_extensions = (".md", ".markdown")
    filetype_label = "markdown"

    # ===== 安全制御 =====
    MAX_CHARS: int = 80_000
    MAX_BYTES: int = 5 * 1024 * 1024
    REJECT_IF_NUL_FOUND: bool = True

    def _extract_text(
        self,
        *,
        filename: str,
        raw_bytes: bytes,
        encoding: Optional[str],
    ) -> tuple[str, Dict[str, Any]]:
        """
        Markdown 抽出処理。

        戦略：
        1) サイズ制御
        2) バイナリ判定
        3) decode（txt とほぼ同じ戦略）
        4) Markdown 構造を壊さない正規化
        5) 行ベースでの最低限のクリーニング
        6) 長さ制限
        """

        if raw_bytes is None:
            raise ValueError("raw_bytes is None")

        original_size = len(raw_bytes)

        # 1) サイズ制御（bytes）
        truncated_bytes = raw_bytes
        truncated_by_bytes = False
        if original_size > self.MAX_BYTES:
            truncated_bytes = raw_bytes[: self.MAX_BYTES]
            truncated_by_bytes = True

        # 2) バイナリ判定
        if self.REJECT_IF_NUL_FOUND and b"\x00" in truncated_bytes:
            raise ValueError("seems_binary: contains NUL byte")

        # 3) decode
        used_encoding: Optional[str] = None
        text: Optional[str] = None

        if encoding:
            text = truncated_bytes.decode(encoding, errors="replace")
            used_encoding = encoding

        if text is None:
            candidates = ["utf-8", "utf-8-sig", "cp932", "latin-1"]
            last_error: Optional[Exception] = None
            for enc in candidates:
                try:
                    text = truncated_bytes.decode(enc, errors="replace")
                    used_encoding = enc
                    break
                except Exception as e:
                    last_error = e

            if text is None:
                raise ValueError(f"decode_failed: {last_error}")

        # 4) 改行正規化（Markdown 構造保持）
        # CRLF / CR を LF に統一
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # 5) 行ベースの最小正規化
        lines = normalized.split("\n")
        cleaned_lines = []

        for line in lines:
            # Markdown 構造を壊さないため：
            # - 行頭の #, -, *, >, ``` などはそのまま
            # - 行末の不要な制御文字だけ軽く掃除
            cleaned = "".join(
                ch if (ch == "\t" or ord(ch) >= 32) else " "
                for ch in line
            )
            cleaned_lines.append(cleaned)

        normalized = "\n".join(cleaned_lines)

        # 6) 長さ制限（chars）
        truncated_by_chars = False
        if len(normalized) > self.MAX_CHARS:
            normalized = normalized[: self.MAX_CHARS]
            truncated_by_chars = True

        # メタ情報（後段での制御・観測用）
        meta: Dict[str, Any] = {
            "encoding": used_encoding,
            "original_bytes": original_size,
            "truncated_by_bytes": truncated_by_bytes,
            "truncated_by_chars": truncated_by_chars,
            "char_count": len(normalized),
            "max_chars": self.MAX_CHARS,
            "max_bytes": self.MAX_BYTES,
            "structure_preserved": True,
            "markdown": True,
        }

        return normalized, meta