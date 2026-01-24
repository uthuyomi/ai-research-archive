# core/drift_detector.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from openai import OpenAI


class DriftDetectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DriftResult:
    """
    Result of a drift comparison between two responses.
    """
    intent: str
    previous_response_id: str
    current_response_id: str
    similarity: float
    status: str  # "stable" | "drifting"


class DriftDetector:
    """
    Minimal drift detector for LLM-Guard v0.

    v0 constraints:
    - Single metric (cosine similarity)
    - No adaptive thresholds
    - Explainability over precision
    """

    def __init__(
        self,
        *,
        embedding_model: str = "text-embedding-3-small",
        threshold: float = 0.75,
        api_key_env: str = "OPENAI_API_KEY",
    ) -> None:
        self._threshold = threshold

        api_key = __import__("os").getenv(api_key_env)
        if not api_key:
            raise DriftDetectionError(
                f"Missing API key. Set environment variable {api_key_env}."
            )

        self._client = OpenAI(api_key=api_key)
        self._embedding_model = embedding_model

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        if a.size == 0 or b.size == 0:
            return 0.0
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def _embed(self, text: str) -> np.ndarray:
        try:
            resp = self._client.embeddings.create(
                model=self._embedding_model,
                input=text,
            )
        except Exception as e:
            raise DriftDetectionError(f"Embedding request failed: {e}") from e

        try:
            vector = resp.data[0].embedding
        except Exception as e:
            raise DriftDetectionError(f"Invalid embedding response: {e}") from e

        return np.array(vector, dtype=np.float32)

    def compare(
        self,
        *,
        intent: str,
        previous_text: str,
        current_text: str,
        previous_response_id: Optional[str] = "",
        current_response_id: Optional[str] = "",
    ) -> DriftResult:
        if not previous_text or not current_text:
            raise DriftDetectionError("Both texts must be non-empty for drift detection.")

        v_prev = self._embed(previous_text)
        v_curr = self._embed(current_text)

        similarity = self._cosine_similarity(v_prev, v_curr)
        status = "stable" if similarity >= self._threshold else "drifting"

        return DriftResult(
            intent=intent,
            previous_response_id=previous_response_id or "",
            current_response_id=current_response_id or "",
            similarity=similarity,
            status=status,
        )