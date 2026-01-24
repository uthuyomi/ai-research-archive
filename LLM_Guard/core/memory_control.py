from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any


class MemoryControlError(RuntimeError):
    pass


class MemoryType(str, Enum):
    FACT = "FACT"
    PREFERENCE = "PREFERENCE"
    DECISION = "DECISION"


# ============================================================
# Memory Entry (canonical, immutable)
# ============================================================

@dataclass(frozen=True)
class MemoryEntry:
    """
    Canonical memory record for LLM-Guard v1.

    Guarantees:
    - Immutable after creation
    - Storage != Usage
    - No implicit conflict resolution
    """
    memory_id: str
    memory_type: MemoryType | str
    scope: str
    intent: str
    content: str
    conflict_key: Optional[str] = None  # explicit conflict axis (optional)


# ============================================================
# Memory Store
# ============================================================

class MemoryStore:
    """
    File-backed memory store (JSON).

    Constraints:
    - Append-only semantics
    - No automatic reuse
    - No mutation
    """

    def __init__(self, storage_path: str | Path) -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_all([])

    def _read_all(self) -> List[dict]:
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise MemoryControlError("Memory store must contain a list.")
            return data
        except Exception as e:
            raise MemoryControlError(f"Failed to read memory store: {e}") from e

    def _write_all(self, data: List[dict]) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise MemoryControlError(f"Failed to write memory store: {e}") from e

    def store(
        self,
        *,
        memory_type: MemoryType,
        scope: str,
        intent: str,
        content: str,
        conflict_key: Optional[str] = None,
    ) -> MemoryEntry:
        if not content or not content.strip():
            raise MemoryControlError("Memory content must be non-empty.")
        if not scope or not scope.strip():
            raise MemoryControlError("scope is required.")
        if not intent or not intent.strip():
            raise MemoryControlError("intent is required.")

        entry = MemoryEntry(
            memory_id=str(uuid.uuid4()),
            memory_type=memory_type.value,  # JSON には str で保存
            scope=scope,
            intent=intent,
            content=content,
            conflict_key=conflict_key,
        )

        data = self._read_all()
        data.append(asdict(entry))
        self._write_all(data)

        return entry

    def list_all(self) -> List[MemoryEntry]:
        raw = self._read_all()
        entries: List[MemoryEntry] = []

        for item in raw:
            try:
                mt_raw = item.get("memory_type")
                # 正規化：str → MemoryType
                if isinstance(mt_raw, str):
                    mt = MemoryType(mt_raw)
                elif isinstance(mt_raw, MemoryType):
                    mt = mt_raw
                else:
                    raise MemoryControlError(f"Invalid memory_type: {mt_raw}")

                entries.append(
                    MemoryEntry(
                        memory_id=item["memory_id"],
                        memory_type=mt,
                        scope=item["scope"],
                        intent=item["intent"],
                        content=item["content"],
                        conflict_key=item.get("conflict_key"),
                    )
                )
            except Exception as e:
                raise MemoryControlError(f"Invalid memory entry format: {e}") from e

        return entries


# ============================================================
# Memory Selection & Conflict Detection
# ============================================================

@dataclass(frozen=True)
class MemorySelectionResult:
    injectable_memory_ids: List[str]
    blocked_memory_ids: List[str]
    conflict_detected: bool
    reason: str


class MemorySelector:
    """
    Explicit memory usage gate.

    Guarantees:
    - Deterministic
    - Rule-based only
    - Conflicts block injection entirely
    """

    # -------------------------
    # Utility
    # -------------------------

    @staticmethod
    def _normalize_memory_type(value: Any) -> str:
        """
        Normalize memory_type to string.
        Accepts Enum or str.
        """
        if value is None:
            return ""
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    # -------------------------
    # Conflict detection
    # -------------------------

    @staticmethod
    def _detect_conflicts(
        memories: List[MemoryEntry],
    ) -> Tuple[bool, List[str]]:
        """
        Detect conflicts using conflict_key.

        If two or more memories share the same conflict_key,
        all of them are considered conflicting.
        """
        seen: Dict[str, str] = {}
        conflicts: List[str] = []

        for mem in memories:
            if not mem.conflict_key:
                continue

            if mem.conflict_key in seen:
                conflicts.append(mem.memory_id)
                conflicts.append(seen[mem.conflict_key])
            else:
                seen[mem.conflict_key] = mem.memory_id

        return bool(conflicts), sorted(set(conflicts))

    # -------------------------
    # Selection
    # -------------------------

    def select(
        self,
        *,
        memories: Iterable[MemoryEntry],
        scope: str,
        intent: str,
        allowed_types: Iterable[MemoryType],
        policy_allows: bool,
    ) -> MemorySelectionResult:
        """
        v1 selection rules:
        - Policy gate must allow
        - Scope must match
        - Intent must match
        - MemoryType must be allowed
        - Any conflict blocks injection
        """

        all_memories = list(memories)

        if not policy_allows:
            return MemorySelectionResult(
                injectable_memory_ids=[],
                blocked_memory_ids=[m.memory_id for m in all_memories],
                conflict_detected=False,
                reason="Policy gate blocked memory injection",
            )

        allowed_type_set = {t.value for t in allowed_types}

        candidates: List[MemoryEntry] = []
        for m in all_memories:
            mem_type = self._normalize_memory_type(m.memory_type)
            if (
                m.scope == scope
                and m.intent == intent
                and mem_type in allowed_type_set
            ):
                candidates.append(m)

        if not candidates:
            return MemorySelectionResult(
                injectable_memory_ids=[],
                blocked_memory_ids=[],
                conflict_detected=False,
                reason="No eligible memory candidates",
            )

        conflict_detected, conflicting_ids = self._detect_conflicts(candidates)

        if conflict_detected:
            return MemorySelectionResult(
                injectable_memory_ids=[],
                blocked_memory_ids=conflicting_ids,
                conflict_detected=True,
                reason="Memory conflict detected; injection blocked",
            )

        return MemorySelectionResult(
            injectable_memory_ids=[m.memory_id for m in candidates],
            blocked_memory_ids=[],
            conflict_detected=False,
            reason="Memory injection allowed",
        )