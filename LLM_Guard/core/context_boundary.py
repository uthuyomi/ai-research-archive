# core/context_boundary.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


class ContextBoundaryError(RuntimeError):
    pass


@dataclass(frozen=True)
class RequestContext:
    """
    Immutable request context for LLM-Guard.

    Rules:
    - All fields are required
    - No inference, no AI judgment
    - Ambiguity => exclusion
    """
    user_id: str
    session_id: str
    scope: str
    intent: str

    def validate(self) -> None:
        if not self.user_id or not self.user_id.strip():
            raise ContextBoundaryError("user_id is required.")
        if not self.session_id or not self.session_id.strip():
            raise ContextBoundaryError("session_id is required.")
        if not self.scope or not self.scope.strip():
            raise ContextBoundaryError("scope is required.")
        if not self.intent or not self.intent.strip():
            raise ContextBoundaryError("intent is required.")


@dataclass(frozen=True)
class MemoryRef:
    """
    Lightweight reference to a memory entry.

    v1 alignment:
    - Contains only metadata required for boundary checks.
    - Conflict is not resolved here; conflict_key is metadata only.
    - memory_type is kept as str for compatibility (FACT|PREFERENCE|DECISION).
    """
    memory_id: str
    scope: str
    intent: str
    memory_type: str  # FACT | PREFERENCE | DECISION
    conflict_key: Optional[str] = None  # boundary does not resolve conflicts


@dataclass(frozen=True)
class BoundaryFilterResult:
    """
    Explainable result for boundary filtering (coarse-grained).
    """
    allowed: List[MemoryRef]
    blocked: List[MemoryRef]
    reason: str


class ContextBoundaryManager:
    """
    Enforces hard boundaries for context and memory usage.

    Guarantees:
    - Rule-based only
    - No heuristics
    - No learning
    - Exclude on mismatch
    """

    def __init__(self, *, allowed_memory_types: Optional[Iterable[str]] = None) -> None:
        if allowed_memory_types is None:
            allowed_memory_types = ("FACT", "PREFERENCE", "DECISION")
        self._allowed_memory_types = {str(x) for x in allowed_memory_types}

    @property
    def allowed_memory_types(self) -> List[str]:
        return sorted(self._allowed_memory_types)

    @staticmethod
    def _normalize_memory_type(value: Any) -> str:
        """
        Normalize memory_type to string without importing MemoryType here.
        Accepts Enum-like objects with .value.
        """
        if value is None:
            return ""
        if hasattr(value, "value"):
            return str(getattr(value, "value"))
        return str(value)

    def filter_memories(
        self,
        *,
        ctx: RequestContext,
        memories: Iterable[MemoryRef],
    ) -> List[MemoryRef]:
        """
        Backward-compatible API: returns only memories allowed for the context.

        Exclusion rules (any => excluded):
        - missing/blank memory_id
        - scope mismatch
        - intent mismatch
        - memory_type not allowed
        """
        ctx.validate()

        allowed: List[MemoryRef] = []
        for mem in memories:
            if not mem.memory_id or not str(mem.memory_id).strip():
                continue

            mem_type = self._normalize_memory_type(mem.memory_type)
            if mem_type not in self._allowed_memory_types:
                continue
            if mem.scope != ctx.scope:
                continue
            if mem.intent != ctx.intent:
                continue

            allowed.append(mem)

        return allowed

    def filter_memories_with_reason(
        self,
        *,
        ctx: RequestContext,
        memories: Iterable[MemoryRef],
    ) -> BoundaryFilterResult:
        """
        v1-friendly API: returns allowed + blocked + a coarse reason.

        This does not attempt per-item explanations.
        Caller can log blocked ids/types for traceability.
        """
        ctx.validate()

        allowed: List[MemoryRef] = []
        blocked: List[MemoryRef] = []

        for mem in memories:
            if not mem.memory_id or not str(mem.memory_id).strip():
                blocked.append(mem)
                continue

            mem_type = self._normalize_memory_type(mem.memory_type)
            if mem_type not in self._allowed_memory_types:
                blocked.append(mem)
                continue
            if mem.scope != ctx.scope:
                blocked.append(mem)
                continue
            if mem.intent != ctx.intent:
                blocked.append(mem)
                continue

            allowed.append(mem)

        reason = "Boundary filtering applied (scope/intent/type)"
        return BoundaryFilterResult(allowed=allowed, blocked=blocked, reason=reason)

    def assert_context_compatible(
        self,
        *,
        ctx: RequestContext,
        expected: Dict[str, str],
    ) -> None:
        """
        Hard assertion for context compatibility.

        expected keys can include:
        - user_id
        - session_id
        - scope
        - intent

        Any mismatch raises an error.
        """
        ctx.validate()

        for key, expected_value in expected.items():
            if not hasattr(ctx, key):
                raise ContextBoundaryError(f"Unknown context key: '{key}'")

            actual_value = getattr(ctx, key)
            if actual_value != expected_value:
                raise ContextBoundaryError(
                    f"Context mismatch on '{key}': expected='{expected_value}', actual='{actual_value}'"
                )

    def is_context_compatible(
        self,
        *,
        ctx: RequestContext,
        expected: Dict[str, str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Non-throwing compatibility check.

        Returns:
        - (True, None) if compatible
        - (False, reason) if mismatch
        """
        try:
            self.assert_context_compatible(ctx=ctx, expected=expected)
        except ContextBoundaryError as e:
            return False, str(e)
        return True, None