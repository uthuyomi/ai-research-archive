"""
documents/__init__.py
=====================

documents 系 executor の登録・ルーティングを行うモジュール。
"""

from __future__ import annotations

from typing import Dict, Optional, Type
import os
import logging

from .base import DocumentExecutorBase

# --- executor 実装 ---
from .text_executor import TextExecutor
from .markdown_executor import MarkdownExecutor
from .pdf_executor import PDFExecutor
from .docx_executor import DOCXExecutor

logger = logging.getLogger(__name__)

# ==================================================
# Executor Registry
# ==================================================

_EXECUTOR_REGISTRY: Dict[str, Type[DocumentExecutorBase]] = {}


def register_executor(
    extensions: list[str],
    executor_cls: Type[DocumentExecutorBase],
) -> None:
    for ext in extensions:
        _EXECUTOR_REGISTRY[ext.lower()] = executor_cls


# ==================================================
# 初期登録
# ==================================================

register_executor([".txt"], TextExecutor)
register_executor([".md", ".markdown"], MarkdownExecutor)
register_executor([".pdf"], PDFExecutor)
register_executor([".docx"], DOCXExecutor)


# ==================================================
# Dispatcher
# ==================================================

def dispatch_executor(
    *,
    filename: str,
) -> Optional[Type[DocumentExecutorBase]]:
    if not filename:
        return None

    _, ext = os.path.splitext(filename)
    if not ext:
        return None

    return _EXECUTOR_REGISTRY.get(ext.lower())


def execute_document(
    *,
    filename: str,
    data: bytes,
    encoding: Optional[str] = None,
):
    """
    documents executor を実行する共通エントリ。
    """
    executor_cls = dispatch_executor(filename=filename)
    if executor_cls is None:
        logger.debug("No document executor for file: %s", filename)
        return None

    try:
        executor = executor_cls()

        # ★ 契約どおり渡す（これが唯一の正解）
        return executor.execute(
            filename=filename,
            raw_bytes=data,
            encoding=encoding,
        )

    except Exception:
        logger.exception(
            "Document executor failed: %s (%s)",
            filename,
            executor_cls.__name__,
        )
        return None


__all__ = [
    "dispatch_executor",
    "execute_document",
    "register_executor",
]