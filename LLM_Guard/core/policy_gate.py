# core/policy_gate.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Any, List


class PolicyViolation(RuntimeError):
    """
    Raised when a policy explicitly blocks an action.

    v1:
    - This exception is optional to use.
    - Deterministic: same inputs -> same violation.
    """
    pass


@dataclass(frozen=True)
class PolicyDecision:
    """
    Canonical result of a policy evaluation.

    Fields are intentionally explicit to support:
    - observability
    - replay
    - audit
    """
    allowed: bool
    decision: str           # ALLOW | BLOCK
    reason: str             # human-readable, deterministic
    incident_flag: bool = False


class PolicyGate:
    """
    PolicyGate evaluates system-level rules for LLM behavior.

    v1 guarantees:
    - Declarative rules only
    - No learning
    - No inference
    - No internal state
    - Deterministic output for identical inputs
    """

    def __init__(self, *, policy_config: Dict[str, Any]) -> None:
        """
        policy_config example:

        {
            "block_on_drift": True,
            "incident_on_drift": True,
            "max_allowed_drift_score": 0.75
        }
        """
        if not isinstance(policy_config, dict):
            raise TypeError("policy_config must be a dict")

        # Defensive copy to avoid external mutation
        self._policy: Dict[str, Any] = dict(policy_config)

    def evaluate(
        self,
        *,
        drift_status: Optional[str],
        drift_score: Optional[float],
        injected_memory_ids: List[str],
    ) -> PolicyDecision:
        """
        Evaluate policy rules based on current system signals.

        This method:
        - does NOT mutate state
        - does NOT raise by default
        - returns a fully explained PolicyDecision
        """

        # -----------------------------
        # Rule 1: qualitative drift flag
        # -----------------------------
        if self._policy.get("block_on_drift", False):
            if drift_status == "drifting":
                return PolicyDecision(
                    allowed=False,
                    decision="BLOCK",
                    reason="Drift status flagged as 'drifting'",
                    incident_flag=bool(self._policy.get("incident_on_drift", True)),
                )

        # -----------------------------
        # Rule 2: numeric drift threshold
        # -----------------------------
        max_score = self._policy.get("max_allowed_drift_score")
        if max_score is not None:
            if drift_score is None:
                # Deterministic handling of missing signal
                return PolicyDecision(
                    allowed=False,
                    decision="BLOCK",
                    reason="Drift score missing while threshold is enforced",
                    incident_flag=True,
                )

            if drift_score < float(max_score):
                return PolicyDecision(
                    allowed=False,
                    decision="BLOCK",
                    reason=(
                        f"Drift score below threshold "
                        f"({drift_score:.3f} < {float(max_score):.3f})"
                    ),
                    incident_flag=True,
                )

        # -----------------------------
        # Rule 3: memory injection sanity
        # -----------------------------
        # v1 note:
        # Empty memory injection is NOT an error.
        # This rule exists to make the decision explicit and observable.
        if not injected_memory_ids:
            return PolicyDecision(
                allowed=True,
                decision="ALLOW",
                reason="No memory injected; policy allows continuation",
                incident_flag=False,
            )

        # -----------------------------
        # Default allow
        # -----------------------------
        return PolicyDecision(
            allowed=True,
            decision="ALLOW",
            reason="All policy checks passed",
            incident_flag=False,
        )

    def enforce(
        self,
        *,
        drift_status: Optional[str],
        drift_score: Optional[float],
        injected_memory_ids: List[str],
    ) -> PolicyDecision:
        """
        Evaluate and enforce policy.

        - Returns PolicyDecision if allowed
        - Raises PolicyViolation if blocked

        Intended usage:
        - runtime enforcement
        - optional hard-stop paths
        """
        decision = self.evaluate(
            drift_status=drift_status,
            drift_score=drift_score,
            injected_memory_ids=injected_memory_ids,
        )

        if not decision.allowed:
            raise PolicyViolation(decision.reason)

        return decision