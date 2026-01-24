# core/llm_client.py
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI


@dataclass(frozen=True)
class LLMResponse:
    response_id: str
    output_text: str
    raw: Any


class LLMClientError(RuntimeError):
    pass


class LLMClient:
    """
    Minimal OpenAI client wrapper for LLM-Guard v0.

    v0 constraints:
    - No persona logic
    - No autonomy
    - No learning
    - Just: send prompt -> get text back
    """

    def __init__(
        self,
        model: str = "gpt-5-mini",
        api_key_env: str = "OPENAI_API_KEY",
        organization_env: str = "OPENAI_ORG_ID",
        project_env: str = "OPENAI_PROJECT_ID",
        timeout_seconds: Optional[float] = None,
    ) -> None:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise LLMClientError(
                f"Missing API key. Set environment variable {api_key_env}."
            )

        # Optional headers supported by the SDK (safe to pass even if unset)
        org_id = os.getenv(organization_env)
        project_id = os.getenv(project_env)

        # OpenAI SDK will read OPENAI_API_KEY by default, but we load explicitly for clarity.
        # If you use org/project scoping, set OPENAI_ORG_ID / OPENAI_PROJECT_ID.
        self._client = OpenAI(
            api_key=api_key,
            organization=org_id,
            project=project_id,
            timeout=timeout_seconds,
        )
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def generate_text(
        self,
        *,
        input_text: str,
        instructions: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Create a single response using the Responses API.

        Parameters
        - input_text: user input
        - instructions: system-style instruction (kept minimal in v0)
        - reasoning_effort: e.g. "low" | "medium" | "high" | "xhigh" (model-dependent)
        - extra: passthrough dict for future-proofing (v0 should rarely use this)

        Returns
        - LLMResponse with response_id + output_text
        """
        if not input_text or not input_text.strip():
            raise LLMClientError("input_text is empty.")

        payload: Dict[str, Any] = {
            "model": self._model,
            "input": input_text,
        }

        if instructions:
            payload["instructions"] = instructions

        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}

        if extra:
            # v0: allow explicit opt-in parameters without changing wrapper signature.
            payload.update(extra)

        try:
            resp = self._client.responses.create(**payload)
        except Exception as e:
            raise LLMClientError(f"OpenAI request failed: {e}") from e

        # SDK convenience: resp.output_text aggregates textual output
        output_text = getattr(resp, "output_text", None)
        if output_text is None:
            # Fallback: try to extract a reasonable string if SDK shape changes.
            output_text = str(resp)

        response_id = getattr(resp, "id", "") or ""
        return LLMResponse(response_id=response_id, output_text=output_text, raw=resp)