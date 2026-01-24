# core/input_pipeline/envelope.py
"""
InputEnvelope: API層から渡される入力（text / attachments / recent messages）を
「後段が扱いやすい形」に正規化して束ねるモジュール。

ここは “生成” をしない。
- 入力をまとめる
- 添付のメタ情報を確定する
- サイズ制限・形式制限を適用する
- 後段（detector / preprocess / intent_score）に渡すための土台を作る

依存：pydantic（FastAPI前提）
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator


# =========================
# Errors
# =========================

class InputPipelineError(Exception):
    """input_pipeline 全体の基底例外（API層で捕まえて整形応答にする用）。"""


class AttachmentTooLargeError(InputPipelineError):
    """添付が大きすぎる（または読み込み上限を超える）。"""


class UnsupportedAttachmentError(InputPipelineError):
    """対応外の添付形式。"""


class InvalidEnvelopeError(InputPipelineError):
    """Envelope構造が不正。"""


# =========================
# Attachment Types / Rules
# =========================

class AttachmentKind(str, Enum):
    image = "image"
    document = "document"
    code = "code"
    spreadsheet = "spreadsheet"
    unknown = "unknown"


class InputType(str, Enum):
    CHAT = "chat"
    DOCUMENT = "document"
    CODE = "code"
    SPREADSHEET = "spreadsheet"
    MIXED = "mixed"


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
DOC_TEXT_EXTS = {".md", ".txt"}
DOC_RICH_EXTS = {".pdf", ".docx"}
SHEET_EXTS = {".xlsx"}
CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".json", ".yml", ".yaml", ".css", ".scss"}

SUPPORTED_EXTS = IMAGE_EXTS | DOC_TEXT_EXTS | DOC_RICH_EXTS | SHEET_EXTS | CODE_EXTS


class EnvelopeReliability(str, Enum):
    """
    InputEnvelope 全体の信頼度。
    generation/context 側がそのまま参照する。
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def infer_kind_from_ext(ext: str) -> AttachmentKind:
    ext = ext.lower()
    if ext in IMAGE_EXTS:
        return AttachmentKind.image
    if ext in SHEET_EXTS:
        return AttachmentKind.spreadsheet
    if ext in CODE_EXTS:
        return AttachmentKind.code
    if ext in DOC_TEXT_EXTS or ext in DOC_RICH_EXTS:
        return AttachmentKind.document
    return AttachmentKind.unknown


def normalize_ext(filename: str) -> str:
    p = Path(filename)
    return p.suffix.lower().strip() if p.suffix else ""


def normalize_text(text: Optional[str], *, max_chars: int) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(t) > max_chars:
        t = t[:max_chars]
    return t


def sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


# =========================
# Config / Options
# =========================

@dataclass(frozen=True)
class EnvelopeLimits:
    max_text_chars: int = 50_000
    max_attachments: int = 5
    max_attachment_bytes: int = 8 * 1024 * 1024
    max_richdoc_bytes: int = 12 * 1024 * 1024
    max_image_bytes: int = 6 * 1024 * 1024


@dataclass(frozen=True)
class EnvelopePolicy:
    supported_exts: frozenset[str] = frozenset(SUPPORTED_EXTS)
    allow_unknown_extension: bool = False


# =========================
# Models
# =========================

class MessageLite(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "assistant", "system"] = Field(...)
    content: str = Field(default="")
    name: Optional[str] = Field(default=None)


class AttachmentSource(str, Enum):
    memory = "memory"
    path = "path"


class AttachmentRef(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: AttachmentSource = Field(...)
    bytes_data: Optional[bytes] = Field(default=None, repr=False)
    file_path: Optional[str] = Field(default=None)

    @field_validator("file_path")
    @classmethod
    def _validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return str(Path(v))

    def read_bytes(self, *, max_bytes: int) -> bytes:
        if self.source == AttachmentSource.memory:
            if self.bytes_data is None:
                raise InvalidEnvelopeError("AttachmentRef(memory) but bytes_data is None")
            if len(self.bytes_data) > max_bytes:
                raise AttachmentTooLargeError
            return self.bytes_data

        if self.source == AttachmentSource.path:
            if not self.file_path:
                raise InvalidEnvelopeError("AttachmentRef(path) but file_path is None")
            p = Path(self.file_path)
            if not p.exists() or not p.is_file():
                raise InvalidEnvelopeError(f"path not found: {self.file_path}")
            size = p.stat().st_size
            if size > max_bytes:
                raise AttachmentTooLargeError
            return p.read_bytes()

        raise InvalidEnvelopeError(f"unknown source: {self.source}")


class AttachmentMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    filename: str = Field(...)
    ext: str = Field(default="")
    kind: AttachmentKind = Field(default=AttachmentKind.unknown)
    mime: Optional[str] = Field(default=None)
    size_bytes: Optional[int] = Field(default=None)
    sha256: Optional[str] = Field(default=None)

    @field_validator("ext")
    @classmethod
    def _normalize_ext(cls, v: str) -> str:
        return v.lower().strip() if v else ""

    @field_validator("filename")
    @classmethod
    def _sanitize_filename(cls, v: str) -> str:
        return Path(v).name


class Attachment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    meta: AttachmentMeta = Field(...)
    ref: AttachmentRef = Field(...)


class InputEnvelope(BaseModel):
    """
    入力の正規化済みパッケージ。
    """
    model_config = ConfigDict(extra="ignore")

    text: str = Field(default="")
    attachments: List[Attachment] = Field(default_factory=list)
    recent_messages: List[MessageLite] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)

    # ★追加：generation/context が直接参照する
    reliability: EnvelopeReliability = Field(
        default=EnvelopeReliability.MEDIUM
    )


# =========================
# Builder
# =========================

class EnvelopeBuilder:
    def __init__(
        self,
        *,
        limits: EnvelopeLimits = EnvelopeLimits(),
        policy: EnvelopePolicy = EnvelopePolicy(),
    ) -> None:
        self._limits = limits
        self._policy = policy

    def build(
        self,
        *,
        text: Optional[str],
        attachments: Optional[List[Tuple[str, AttachmentRef]]] = None,
        recent_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> InputEnvelope:
        t = normalize_text(text, max_chars=self._limits.max_text_chars)

        msgs: List[MessageLite] = []
        if recent_messages:
            for m in recent_messages:
                msgs.append(MessageLite(**m))

        att_list: List[Attachment] = []
        warnings: List[str] = []

        if attachments:
            if len(attachments) > self._limits.max_attachments:
                raise InvalidEnvelopeError("too many attachments")

            for (filename, ref) in attachments:
                meta, warn = self._build_attachment_meta(filename=filename, ref=ref)
                if warn:
                    warnings.append(warn)
                att_list.append(Attachment(meta=meta, ref=ref))

        # ★信頼度の最終確定（ここが責務）
        if warnings:
            reliability = EnvelopeReliability.LOW
        elif att_list:
            reliability = EnvelopeReliability.HIGH
        else:
            reliability = EnvelopeReliability.MEDIUM

        return InputEnvelope(
            text=t,
            attachments=att_list,
            recent_messages=msgs,
            warnings=warnings,
            reliability=reliability,
        )

    def _build_attachment_meta(
        self, *, filename: str, ref: AttachmentRef
    ) -> Tuple[AttachmentMeta, Optional[str]]:
        ext = normalize_ext(filename)

        if not ext and not self._policy.allow_unknown_extension:
            raise UnsupportedAttachmentError(f"missing extension: {filename}")

        if ext and ext not in self._policy.supported_exts and not self._policy.allow_unknown_extension:
            raise UnsupportedAttachmentError(f"unsupported extension: {ext}")

        kind = infer_kind_from_ext(ext) if ext else AttachmentKind.unknown

        size_bytes: Optional[int] = None
        warning: Optional[str] = None

        if ref.source == AttachmentSource.memory:
            if ref.bytes_data is None:
                raise InvalidEnvelopeError
            size_bytes = len(ref.bytes_data)

        elif ref.source == AttachmentSource.path:
            if not ref.file_path:
                raise InvalidEnvelopeError
            p = Path(ref.file_path)
            if p.exists() and p.is_file():
                size_bytes = p.stat().st_size
            else:
                warning = f"path not found at build time: {ref.file_path}"

        max_bytes = self._pick_limit_for(ext=ext, kind=kind)
        if size_bytes is not None and size_bytes > max_bytes:
            raise AttachmentTooLargeError

        digest: Optional[str] = None
        if ref.source == AttachmentSource.memory and ref.bytes_data is not None:
            digest = sha256_hex(ref.bytes_data)

        meta = AttachmentMeta(
            filename=filename,
            ext=ext,
            kind=kind,
            size_bytes=size_bytes,
            sha256=digest,
        )
        return meta, warning

    def _pick_limit_for(self, *, ext: str, kind: AttachmentKind) -> int:
        if ext in DOC_RICH_EXTS or ext in SHEET_EXTS:
            return self._limits.max_richdoc_bytes
        if ext in IMAGE_EXTS:
            return self._limits.max_image_bytes
        return self._limits.max_attachment_bytes


# =========================
# Convenience helpers
# =========================

def build_envelope(
    *,
    text: Optional[str],
    attachments: Optional[List[Tuple[str, AttachmentRef]]] = None,
    recent_messages: Optional[List[Dict[str, Any]]] = None,
    limits: EnvelopeLimits = EnvelopeLimits(),
    policy: EnvelopePolicy = EnvelopePolicy(),
) -> InputEnvelope:
    return EnvelopeBuilder(limits=limits, policy=policy).build(
        text=text,
        attachments=attachments,
        recent_messages=recent_messages,
    )


def infer_input_type_from_envelope(envelope: InputEnvelope) -> InputType:
    attachments = envelope.attachments

    if not attachments:
        return InputType.CHAT

    kinds = {att.meta.kind for att in attachments}

    if len(kinds) == 1:
        kind = next(iter(kinds))
        if kind == AttachmentKind.document:
            return InputType.DOCUMENT
        if kind == AttachmentKind.code:
            return InputType.CODE
        if kind == AttachmentKind.spreadsheet:
            return InputType.SPREADSHEET
        return InputType.MIXED

    return InputType.MIXED