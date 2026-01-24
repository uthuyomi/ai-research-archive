# core/input_pipeline/executors/documents/base.py
"""
base.py
=================================================
Documents 系 Executor の基底クラス。

【このファイルの役割】
- txt / md / pdf / docx など「文書ファイル」を扱う Executor の共通基盤
- 各フォーマット固有の処理は派生クラスに任せる
- input_pipeline の一部として「一時的な読解結果」を生成する
- DB・人格・長期記憶には一切触れない（重要）

【設計上の前提】
- Documents は「知識」ではなく「参照入力」
- この層で扱う情報は request-scope（1リクエスト限り）
- 保存・記憶・要約などは上位レイヤの責務

この base.py は以下を保証する：
- インターフェースの統一
- 実行結果フォーマットの統一
- 失敗時の安全なフォールバック
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class DocumentResult:
    """
    Documents Executor の実行結果を表す共通データ構造。

    ※ OCR や Vision と同様、
      generation_context にそのまま載せられる前提の構造。

    属性は「LLM に渡しても問題ない粒度」に留める。
    """

    def __init__(
        self,
        *,
        executed: bool,
        filename: str,
        filetype: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ):
        # Executor が実行されたかどうか
        self.executed = executed

        # 元ファイル名（例: sample.txt）
        self.filename = filename

        # ファイル種別（txt / md / pdf / docx など）
        self.filetype = filetype

        # 抽出された本文テキスト（失敗時は None）
        self.text = text

        # ページ数・文字数・推定構造などの補助情報
        self.metadata = metadata or {}

        # 実行理由・失敗理由など（デバッグ・ログ用途）
        self.reason = reason

    def to_prompt_fragment(self) -> str:
        """
        PromptBuilder が使うためのテキスト断片を生成する。

        ※ system prompt 側に載せる想定。
        ※ user prompt には直接流さない前提。
        """
        if not self.executed or not self.text:
            return ""

        lines = []
        lines.append(f"（{self.filename} / {self.filetype}）")
        lines.append(self.text)

        return "\n".join(lines)


class DocumentExecutorBase(ABC):
    """
    Documents Executor の抽象基底クラス。

    各フォーマット（txt / md / pdf / docx）は
    必ずこのクラスを継承する。

    【このクラスがやること】
    - 実行条件のチェック
    - 共通エラーハンドリング
    - 実行結果（DocumentResult）の統一生成

    【やらないこと】
    - DB 保存
    - 要約
    - 意味理解
    - 会話制御
    """

    # 対応するファイル拡張子（派生クラスで上書き必須）
    supported_extensions: tuple[str, ...] = ()

    # filetype 表示名（例: "txt", "pdf"）
    filetype_label: str = "unknown"

    def __init__(self) -> None:
        # 将来的に設定値や制限を持たせる余地を残す
        pass

    def can_handle(self, filename: str) -> bool:
        """
        この Executor が filename を扱えるかどうかを判定する。

        input_pipeline 側で Executor 選択に使われる。
        """
        lower = filename.lower()
        return any(lower.endswith(ext) for ext in self.supported_extensions)

    def execute(
        self,
        *,
        filename: str,
        raw_bytes: bytes,
        encoding: Optional[str] = None,
    ) -> DocumentResult:
        """
        Documents Executor の共通エントリポイント。

        - try / except をここで一元管理
        - 派生クラスは _extract_text のみ実装すればよい
        """

        try:
            text, metadata = self._extract_text(
                filename=filename,
                raw_bytes=raw_bytes,
                encoding=encoding,
            )

            return DocumentResult(
                executed=True,
                filename=filename,
                filetype=self.filetype_label,
                text=text,
                metadata=metadata,
                reason="document_extracted",
            )

        except Exception as e:
            # 失敗しても会話自体は止めない
            return DocumentResult(
                executed=False,
                filename=filename,
                filetype=self.filetype_label,
                text=None,
                metadata={},
                reason=f"document_extract_failed: {e}",
            )

    @abstractmethod
    def _extract_text(
        self,
        *,
        filename: str,
        raw_bytes: bytes,
        encoding: Optional[str],
    ) -> tuple[str, Dict[str, Any]]:
        """
        実際のテキスト抽出処理（派生クラスで実装）。

        戻り値：
        - text: 抽出された本文
        - metadata: 補助情報（文字数・ページ数など）

        ※ 例外はここで握り潰さず、上位 execute に投げる
        """
        raise NotImplementedError