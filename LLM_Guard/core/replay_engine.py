# core/replay_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ReplayError(RuntimeError):
    """
    Raised when replay execution fails or input is invalid.

    v1:
    - Deterministic failure only
    - No partial success
    """
    pass


@dataclass(frozen=True)
class ReplayInput:
    """
    Immutable snapshot of inputs required to reproduce a policy decision.

    v1 guarantees:
    - No model output included
    - No timestamps
    - Only system-level signals
    """
    user_id: str
    session_id: str
    scope: str
    intent: str
    injected_memory_ids: List[str]
    drift_status: Optional[str]
    drift_score: Optional[float]
    drift_metrics: Optional[Dict[str, float]] = None


@dataclass(frozen=True)
class ReplayResult:
    """
    Deterministic result of a replay execution.
    """
    decision: str           # ALLOW | BLOCK
    allowed: bool
    incident_flag: bool
    reason: str


class ReplayEngine:
    """
    ReplayEngine reproduces policy decisions deterministically.

    v1 guarantees:
    - No model calls
    - No time dependency
    - No randomness
    - Identical input => identical output
    """

    def __init__(self, *, policy_gate: Any) -> None:
        """
        policy_gate must expose:
        - evaluate(drift_status, drift_score, injected_memory_ids)
        """
        if not hasattr(policy_gate, "evaluate"):
            raise ReplayError("policy_gate must provide an evaluate() method")

        self._policy_gate = policy_gate

    def replay(self, replay_input: ReplayInput) -> ReplayResult:
        """
        Re-run policy evaluation using historical inputs.

        This method:
        - does NOT mutate state
        - does NOT catch PolicyViolation
        - always returns an explicit ReplayResult
        """

        if replay_input is None:
            raise ReplayError("ReplayInput must not be None")

        decision = self._policy_gate.evaluate(
            drift_status=replay_input.drift_status,
            drift_score=replay_input.drift_score,
            injected_memory_ids=replay_input.injected_memory_ids,
        )

        return ReplayResult(
            decision=decision.decision,
            allowed=decision.allowed,
            incident_flag=decision.incident_flag,
            reason=decision.reason,
        )

    def replay_many(self, inputs: List[ReplayInput]) -> List[ReplayResult]:
        """
        Replay multiple inputs sequentially.

        Intended for:
        - audits
        - regression verification
        - compliance checks
        """
        if inputs is None:
            raise ReplayError("inputs must not be None")

        results: List[ReplayResult] = []

        for idx, replay_input in enumerate(inputs):
            try:
                result = self.replay(replay_input)
            except Exception as e:
                raise ReplayError(
                    f"Replay failed at index {idx}: {e}"
                ) from e
            results.append(result)

        return results