# core/guard_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.context_boundary import (
    ContextBoundaryManager,
    MemoryRef,
    RequestContext,
)
from core.drift_detector import DriftDetector
from core.llm_client import LLMClient
from core.logger import JSONLogger
from core.memory_control import (
    MemoryStore,
    MemorySelector,
    MemoryType,
)
from core.policy_gate import PolicyGate, PolicyDecision
from core.replay_engine import ReplayInput


class GuardEngineError(RuntimeError):
    """
    Raised when GuardEngine execution fails.
    """
    pass


@dataclass(frozen=True)
class GuardRequest:
    """
    Canonical input for GuardEngine v1.
    """
    user_id: str
    session_id: str
    scope: str
    intent: str
    prompt: str
    instructions: Optional[str] = None


@dataclass(frozen=True)
class GuardResult:
    """
    Canonical output of GuardEngine v1.
    """
    decision: PolicyDecision
    output_text: Optional[str]
    injected_memory_ids: List[str]
    replay_input: ReplayInput


class GuardEngine:
    """
    GuardEngine defines the canonical execution path of LLM-Guard v1.

    v1 guarantees:
    - Deterministic control flow
    - Explicit ALLOW / BLOCK decision
    - No hidden state
    - Replayable decision inputs
    """

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        drift_detector: DriftDetector,
        policy_gate: PolicyGate,
        memory_store: MemoryStore,
        logger: JSONLogger,
        boundary_manager: Optional[ContextBoundaryManager] = None,
        memory_selector: Optional[MemorySelector] = None,
        allowed_memory_types: Optional[List[MemoryType]] = None,
    ) -> None:
        self._llm = llm_client
        self._drift = drift_detector
        self._policy = policy_gate
        self._memory_store = memory_store
        self._logger = logger

        self._boundary = boundary_manager or ContextBoundaryManager()
        self._selector = memory_selector or MemorySelector()

        if allowed_memory_types is None:
            allowed_memory_types = [
                MemoryType.FACT,
                MemoryType.PREFERENCE,
                MemoryType.DECISION,
            ]
        self._allowed_memory_types = allowed_memory_types

    def run(
        self,
        *,
        request: GuardRequest,
        previous_output_text: Optional[str] = None,
        previous_response_id: Optional[str] = None,
    ) -> GuardResult:
        """
        Execute a single guarded LLM invocation.

        This method:
        - Validates context
        - Selects memory deterministically
        - Calls LLM (if allowed)
        - Detects drift (if previous output exists)
        - Evaluates policy
        - Logs everything
        - Returns replayable result
        """

        # -----------------------------
        # 1. Context validation
        # -----------------------------
        ctx = RequestContext(
            user_id=request.user_id,
            session_id=request.session_id,
            scope=request.scope,
            intent=request.intent,
        )
        ctx.validate()

        # -----------------------------
        # 2. Memory selection (store ≠ use)
        # -----------------------------
        all_memories = self._memory_store.list_all()

        selected_memories = self._selector.select(
            memories=all_memories,
            scope=request.scope,
            intent=request.intent,
            allowed_types=self._allowed_memory_types,
        )

        memory_refs: List[MemoryRef] = [
            MemoryRef(
                memory_id=m.memory_id,
                scope=m.scope,
                intent=m.intent,
                memory_type=m.memory_type.value,
                conflict=m.conflict,
            )
            for m in selected_memories
        ]

        allowed_memories = self._boundary.filter_memories(
            ctx=ctx,
            memories=memory_refs,
        )

        injected_memory_ids = [m.memory_id for m in allowed_memories]

        # -----------------------------
        # 3. LLM invocation
        # -----------------------------
        response = self._llm.generate_text(
            input_text=request.prompt,
            instructions=request.instructions,
        )

        output_text = response.output_text
        response_id = response.response_id

        # -----------------------------
        # 4. Drift detection (optional)
        # -----------------------------
        drift_status: Optional[str] = None
        drift_score: Optional[float] = None

        if previous_output_text and previous_response_id:
            drift = self._drift.compare(
                intent=request.intent,
                previous_text=previous_output_text,
                current_text=output_text,
                previous_response_id=previous_response_id,
                current_response_id=response_id,
            )
            drift_status = drift.status
            drift_score = drift.similarity

        # -----------------------------
        # 5. Policy evaluation
        # -----------------------------
        decision = self._policy.evaluate(
            drift_status=drift_status,
            drift_score=drift_score,
            injected_memory_ids=injected_memory_ids,
        )

        # -----------------------------
        # 6. Logging
        # -----------------------------
        self._logger.log(
            user_id=request.user_id,
            session_id=request.session_id,
            scope=request.scope,
            intent=request.intent,
            injected_memory_ids=injected_memory_ids,
            drift_score=drift_score,
            extra={
                "decision": decision.decision,
                "allowed": decision.allowed,
                "reason": decision.reason,
                "incident_flag": decision.incident_flag,
                "drift_status": drift_status,
                "response_id": response_id,
            },
        )

        # -----------------------------
        # 7. Replay input construction
        # -----------------------------
        replay_input = ReplayInput(
            user_id=request.user_id,
            session_id=request.session_id,
            scope=request.scope,
            intent=request.intent,
            injected_memory_ids=injected_memory_ids,
            drift_status=drift_status,
            drift_score=drift_score,
            drift_metrics=None,
        )

        return GuardResult(
            decision=decision,
            output_text=output_text if decision.allowed else None,
            injected_memory_ids=injected_memory_ids,
            replay_input=replay_input,
        )