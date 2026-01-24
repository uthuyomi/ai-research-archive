# tests/test_policy.py
"""
Unit tests for PolicyGate (LLM-Guard v1).

Purpose:
- Verify deterministic policy decisions
- Ensure drift-based blocking works
- Ensure threshold-based blocking works
- Ensure default allow behavior is stable

v1 guarantees:
- No learning
- No randomness
- Same input → same output
"""

import pytest

from core.policy_gate import PolicyGate, PolicyViolation


@pytest.fixture
def default_policy_config() -> dict:
    return {
        "block_on_drift": True,
        "incident_on_drift": True,
        "max_allowed_drift_score": 0.75,
    }


def test_block_when_drift_detected(default_policy_config: dict) -> None:
    gate = PolicyGate(policy_config=default_policy_config)

    decision = gate.evaluate(
        drift_status="drifting",
        drift_score=0.6,
        injected_memory_ids=["MEM_01"],
    )

    assert decision.allowed is False
    assert decision.decision == "BLOCK"
    assert "drift" in decision.reason.lower()
    assert decision.incident_flag is True


def test_block_when_drift_score_below_threshold(default_policy_config: dict) -> None:
    gate = PolicyGate(policy_config=default_policy_config)

    decision = gate.evaluate(
        drift_status="stable",
        drift_score=0.5,
        injected_memory_ids=["MEM_02"],
    )

    assert decision.allowed is False
    assert decision.decision == "BLOCK"
    assert "threshold" in decision.reason.lower()
    assert decision.incident_flag is True


def test_allow_when_drift_score_above_threshold(default_policy_config: dict) -> None:
    gate = PolicyGate(policy_config=default_policy_config)

    decision = gate.evaluate(
        drift_status="stable",
        drift_score=0.9,
        injected_memory_ids=["MEM_03"],
    )

    assert decision.allowed is True
    assert decision.decision == "ALLOW"
    assert decision.incident_flag is False


def test_allow_when_no_memory_injected(default_policy_config: dict) -> None:
    gate = PolicyGate(policy_config=default_policy_config)

    decision = gate.evaluate(
        drift_status="stable",
        drift_score=0.9,
        injected_memory_ids=[],
    )

    assert decision.allowed is True
    assert decision.decision == "ALLOW"
    assert "no memory" in decision.reason.lower()


def test_enforce_raises_on_block(default_policy_config: dict) -> None:
    gate = PolicyGate(policy_config=default_policy_config)

    with pytest.raises(PolicyViolation):
        gate.enforce(
            drift_status="drifting",
            drift_score=0.6,
            injected_memory_ids=["MEM_99"],
        )


def test_enforce_returns_decision_on_allow(default_policy_config: dict) -> None:
    gate = PolicyGate(policy_config=default_policy_config)

    decision = gate.enforce(
        drift_status="stable",
        drift_score=0.95,
        injected_memory_ids=["MEM_OK"],
    )

    assert decision.allowed is True
    assert decision.decision == "ALLOW"