# tests/test_drift.py
"""
Minimal tests for DriftDetector (LLM-Guard v0).

Purpose:
- Verify cosine similarity logic
- Verify threshold-based status classification
- Avoid network calls by mocking embeddings

v0 policy:
- No learning
- No adaptive thresholds
- Deterministic behavior only
"""

from __future__ import annotations

import numpy as np
import pytest

from core.drift_detector import DriftDetector, DriftResult


class DummyDriftDetector(DriftDetector):
    """
    DriftDetector override for testing.

    This bypasses OpenAI embeddings and returns
    deterministic vectors instead.
    """

    def __init__(self, *, threshold: float = 0.75) -> None:
        # Do not call super().__init__ (avoids API key / network)
        self._threshold = threshold

    def _embed(self, text: str) -> np.ndarray:
        # Deterministic fake embeddings based on input
        if text == "same":
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if text == "similar":
            return np.array([0.9, 0.1, 0.0], dtype=np.float32)
        if text == "different":
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)


def test_identical_text_is_stable() -> None:
    detector = DummyDriftDetector(threshold=0.8)

    result: DriftResult = detector.compare(
        intent="test_intent",
        previous_text="same",
        current_text="same",
        previous_response_id="r1",
        current_response_id="r2",
    )

    assert result.status == "stable"
    assert result.similarity == pytest.approx(1.0, rel=1e-5)


def test_similar_text_is_stable_above_threshold() -> None:
    detector = DummyDriftDetector(threshold=0.7)

    result: DriftResult = detector.compare(
        intent="test_intent",
        previous_text="same",
        current_text="similar",
        previous_response_id="r1",
        current_response_id="r2",
    )

    assert result.status == "stable"
    assert result.similarity > 0.7


def test_different_text_is_drifting() -> None:
    detector = DummyDriftDetector(threshold=0.8)

    result: DriftResult = detector.compare(
        intent="test_intent",
        previous_text="same",
        current_text="different",
        previous_response_id="r1",
        current_response_id="r2",
    )

    assert result.status == "drifting"
    assert result.similarity < 0.8


def test_empty_text_raises_error() -> None:
    detector = DummyDriftDetector()

    with pytest.raises(Exception):
        detector.compare(
            intent="test_intent",
            previous_text="",
            current_text="same",
        )