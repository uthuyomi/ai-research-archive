# core/input_pipeline/executors/documents/text_executor.py
"""
text_executor.py
=================================================
txt / text 系ファイルの抽出 Executor（最小・安全版）

【狙い】
- txt を「確実に」読めるようにする
- 失敗しても会話・パイプラインが落ちない
- 文字化けやバイナリ誤判定を最小化する

【注意】
- ここでは「整形」や「意味理解」はしない
- 抽出した文字列は prompt に混ぜられる前提なので、
  異常に巨大なテキストは切り詰める（防御）
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import DocumentExecutorBase


class TextExecutor(DocumentExecutorBase):
    """
    .txt (plain text) を扱う Executor。

    - supported_extensions / filetype_label を定義
    - _extract_text を実装
    """

    supported_extensions = (".txt",)
    filetype_label = "txt"

    # ===== 安全制御（必要なら後から設定化できる） =====
    # どれくらいまでを prompt に流して良いか（超えたら切る）
    MAX_CHARS: int = 50_000

    # 生 bytes の時点でサイズが極端に大きい場合に切る（目安）
    # ※ 例えば 5MB 超など。必要なら調整。
    MAX_BYTES: int = 5 * 1024 * 1024

    # バイナリっぽさの検出で使う NUL バイトの閾値
    # 0x00 が含まれるテキストは大抵バイナリ扱いで良い
    REJECT_IF_NUL_FOUND: bool = True

    def _extract_text(
        self,
        *,
        filename: str,
        raw_bytes: bytes,
        encoding: Optional[str],
    ) -> tuple[str, Dict[str, Any]]:
        """
        txt の抽出処理。

        戦略：
        1) サイズ防御
        2) バイナリ判定（NUL含有）
        3) decode（優先順位：指定encoding → utf-8 → utf-8-sig → cp932 → latin-1）
           - cp932 は日本語環境の現実対応
           - latin-1 は「絶対に落ちない」最後の手段（ただし文字化けしやすい）
        4) 正規化（改行）
        5) 長さ制限で切り詰め
        """

        if raw_bytes is None:
            raise ValueError("raw_bytes is None")

        original_size = len(raw_bytes)

        # 1) サイズ防御：極端に大きいファイルをそのまま扱わない
        #    ここで bytes を切ると UTF-8 の途中切れ等の可能性があるが、
        #    「落ちないこと」を優先し、後段で replace decode を使う。
        truncated_bytes = raw_bytes
        truncated_by_bytes = False
        if original_size > self.MAX_BYTES:
            truncated_bytes = raw_bytes[: self.MAX_BYTES]
            truncated_by_bytes = True

        # 2) バイナリ判定（最小）
        if self.REJECT_IF_NUL_FOUND and b"\x00" in truncated_bytes:
            raise ValueError("seems_binary: contains NUL byte")

        # 3) decode
        used_encoding: Optional[str] = None
        text: Optional[str] = None

        # 指定 encoding があれば最優先で試す
        # ※ 指定が間違ってても落ちるだけでパイプラインは止まらない（上位で握る）
        if encoding:
            text = truncated_bytes.decode(encoding, errors="replace")
            used_encoding = encoding

        if text is None:
            # 優先順：utf-8 → utf-8-sig → cp932 → latin-1
            candidates = ["utf-8", "utf-8-sig", "cp932", "latin-1"]
            last_error: Optional[Exception] = None
            for enc in candidates:
                try:
                    text = truncated_bytes.decode(enc, errors="replace")
                    used_encoding = enc
                    break
                except Exception as e:
                    last_error = e
                    continue

            if text is None:
                # ここに来るのはほぼないが、念のため
                raise ValueError(f"decode_failed: {last_error}")

        # 4) 軽い正規化
        # - Windows 改行などを統一
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # 目に見えない制御文字だらけを軽減（最小）
        # ただしタブは残す（コードっぽいテキストもあり得る）
        normalized = "".join(
            ch if (ch == "\n" or ch == "\t" or ord(ch) >= 32) else " "
            for ch in normalized
        )

        # 5) 長さ制限（prompt 汚染 / コスト防御）
        truncated_by_chars = False
        if len(normalized) > self.MAX_CHARS:
            normalized = normalized[: self.MAX_CHARS]
            truncated_by_chars = True

        # メタデータ（後段の制御・デバッグ用）
        meta: Dict[str, Any] = {
            "encoding": used_encoding,
            "original_bytes": original_size,
            "truncated_by_bytes": truncated_by_bytes,
            "truncated_by_chars": truncated_by_chars,
            "char_count": len(normalized),
            "max_chars": self.MAX_CHARS,
            "max_bytes": self.MAX_BYTES,
        }

        return normalized, meta