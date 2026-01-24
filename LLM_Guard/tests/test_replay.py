# tests/test_replay.py
"""
Unit tests for ReplayEngine (LLM-Guard v1).

Purpose:
- Verify deterministic replay behavior
- Ensure identical input yields identical output
- Ensure replay is independent of runtime state

v1 guarantees:
- No randomness
- No mutation
- No model calls
"""

import pytest

from core.policy_gate import PolicyGate
from core.replay_engine import (
    ReplayEngine,
    ReplayInput,
    ReplayResult,
)


@pytest.fixture
def policy_gate() -> PolicyGate:
    policy_config = {
        "block_on_drift": True,
        "incident_on_drift": True,
        "max_allowed_drift_score": 0.75,
    }
    return PolicyGate(policy_config=policy_config)


@pytest.fixture
def replay_engine(policy_gate: PolicyGate) -> ReplayEngine:
    return ReplayEngine(policy_gate=policy_gate)


def test_replay_returns_same_decision_for_same_input(
    replay_engine: ReplayEngine,
) -> None:
    replay_input = ReplayInput(
        user_id="user_1",
        session_id="sess_1",
        scope="test",
        intent="explain_policy",
        injected_memory_ids=["MEM_01"],
        drift_status="stable",
        drift_score=0.9,
        drift_metrics={"cosine": 0.9},
    )

    result_1 = replay_engine.replay(replay_input)
    result_2 = replay_engine.replay(replay_input)

    assert isinstance(result_1, ReplayResult)
    assert result_1 == result_2


def test_replay_blocks_on_drift(
    replay_engine: ReplayEngine,
) -> None:
    replay_input = ReplayInput(
        user_id="user_2",
        session_id="sess_2",
        scope="test",
        intent="answer_question",
        injected_memory_ids=["MEM_02"],
        drift_status="drifting",
        drift_score=0.6,
        drift_metrics={"cosine": 0.6},
    )

    result = replay_engine.replay(replay_input)

    assert result.allowed is False
    assert result.decision == "BLOCK"
    assert result.incident_flag is True
    assert "drift" in result.reason.lower()


def test_replay_blocks_on_low_score_even_if_status_stable(
    replay_engine: ReplayEngine,
) -> None:
    replay_input = ReplayInput(
        user_id="user_3",
        session_id="sess_3",
        scope="test",
        intent="answer_question",
        injected_memory_ids=["MEM_03"],
        drift_status="stable",
        drift_score=0.5,
        drift_metrics={"cosine": 0.5},
    )

    result = replay_engine.replay(replay_input)

    assert result.allowed is False
    assert result.decision == "BLOCK"
    assert "threshold" in result.reason.lower()


def test_replay_allows_when_conditions_pass(
    replay_engine: ReplayEngine,
) -> None:
    replay_input = ReplayInput(
        user_id="user_4",
        session_id="sess_4",
        scope="test",
        intent="answer_question",
        injected_memory_ids=["MEM_OK"],
        drift_status="stable",
        drift_score=0.95,
        drift_metrics={"cosine": 0.95},
    )

    result = replay_engine.replay(replay_input)

    assert result.allowed is True
    assert result.decision == "ALLOW"
    assert result.incident_flag is False