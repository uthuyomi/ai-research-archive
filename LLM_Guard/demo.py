# demo.py
"""
LLM-Guard v1 demo (CLI).

This script demonstrates:
- Context boundary enforcement (rule-based)
- Memory store/use separation (store ≠ use)
- Deterministic memory injection (same ids -> same injected text)
- Drift detection (embedding cosine similarity)
- Policy evaluation (post-drift)
- Deterministic replay of policy decisions (no model calls)
- Observability via JSON logs

Execution:
  - Ensure OPENAI_API_KEY is available (env / .env depending on your setup)
  - Run:
      python demo.py
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Set

from core.context_boundary import ContextBoundaryManager, MemoryRef, RequestContext
from core.drift_detector import DriftDetector
from core.llm_client import LLMClient
from core.logger import JSONLogger
from core.memory_control import MemoryEntry, MemorySelector, MemoryStore, MemoryType
from core.policy_gate import PolicyGate
from core.replay_engine import ReplayEngine, ReplayInput


def _index_entries_by_id(entries: List[MemoryEntry]) -> Dict[str, str]:
    """
    Returns:
      memory_id -> memory content
    """
    return {e.memory_id: e.content for e in entries}


def _build_memory_refs(entries: List[MemoryEntry]) -> List[MemoryRef]:
    """
    Convert MemoryEntry -> MemoryRef for boundary checks.

    Notes:
    - memory_type may be deserialized as str depending on store shape.
    - conflict handling is represented by conflict_key in v1 (NOT boolean conflict).
    """
    refs: List[MemoryRef] = []
    for e in entries:
        mt = e.memory_type.value if isinstance(e.memory_type, MemoryType) else str(e.memory_type)
        refs.append(
            MemoryRef(
                memory_id=e.memory_id,
                scope=e.scope,
                intent=e.intent,
                memory_type=mt,  # "FACT" | "PREFERENCE" | "DECISION"
                conflict_key=getattr(e, "conflict_key", None),
            )
        )
    return refs


def _format_injected_memory(injected_ids: List[str], content_index: Dict[str, str]) -> str:
    """
    Deterministic formatting:
    - same ids -> same injected text
    - sorted for stable ordering
    """
    if not injected_ids:
        return ""

    lines: List[str] = []
    lines.append("### Injected Memory (system-provided; scope/intent verified)")
    for mid in sorted(injected_ids):
        content = content_index.get(mid, "")
        if content:
            lines.append(f"- [{mid}] {content}")
        else:
            lines.append(f"- [{mid}] (content missing)")
    return "\n".join(lines)


def _entries_by_ids(entries: List[MemoryEntry], allowed_ids: Set[str]) -> List[MemoryEntry]:
    """
    Deterministic mapping: keep original list order.
    """
    return [e for e in entries if e.memory_id in allowed_ids]


def main() -> None:
    # -----------------------------
    # Fixed demo parameters
    # -----------------------------
    user_id = "user_demo"
    scope = "policy_support"
    intent = "explain_policy"

    session_a = "session_001"
    session_b = "session_002"

    prompt = "Explain the refund policy in one short paragraph."

    # -----------------------------
    # Initialize core components
    # -----------------------------
    llm = LLMClient()
    drift_detector = DriftDetector()

    boundary = ContextBoundaryManager()
    logger = JSONLogger(log_path=Path("storage/logs/demo.log"))

    memory_store = MemoryStore(storage_path=Path("storage/memory.json"))
    memory_selector = MemorySelector()

    # v1 policy config (deterministic)
    policy_config = {
        "block_on_drift": True,
        "incident_on_drift": True,
        "max_allowed_drift_score": 0.75,  # similarity < 0.75 => BLOCK
    }
    policy_gate = PolicyGate(policy_config=policy_config)
    replay_engine = ReplayEngine(policy_gate=policy_gate)

    # -----------------------------
    # Store memory (store ≠ use)
    # -----------------------------
    stored_fact = memory_store.store(
        memory_type=MemoryType.FACT,
        scope=scope,
        intent=intent,
        content="Refunds are available within 30 days of purchase.",
        conflict_key="refund_policy_window_days",
    )

    # Load all memories and build references/index
    all_entries = memory_store.list_all()
    content_index = _index_entries_by_id(all_entries)
    memory_refs = _build_memory_refs(all_entries)

    # -----------------------------
    # First request (session A)
    # -----------------------------
    ctx_a = RequestContext(
        user_id=user_id,
        session_id=session_a,
        scope=scope,
        intent=intent,
    )

    # 1) boundary filtering (rule-based)
    allowed_refs_a = boundary.filter_memories(ctx=ctx_a, memories=memory_refs)
    allowed_ids_a = {m.memory_id for m in allowed_refs_a}

    # 2) selector gating (deterministic; conflict_key-based conflict detection)
    allowed_entries_a = _entries_by_ids(all_entries, allowed_ids_a)
    selection_a = memory_selector.select(
        memories=allowed_entries_a,
        scope=scope,
        intent=intent,
        allowed_types=[MemoryType.FACT, MemoryType.PREFERENCE, MemoryType.DECISION],
        policy_allows=True,
    )

    injected_ids_a = selection_a.injectable_memory_ids
    injected_text_a = _format_injected_memory(injected_ids_a, content_index)

    instructions_a = (
        "You are a support assistant. Answer clearly and concisely.\n"
        "If injected memory is present, you may use it as authoritative context.\n"
        "Do not invent additional policy details.\n"
    )
    if injected_text_a:
        instructions_a += "\n" + injected_text_a + "\n"

    response_a = llm.generate_text(
        input_text=prompt,
        instructions=instructions_a,
    )

    print("\n--- First response (session A) ---")
    print(response_a.output_text)

    # -----------------------------
    # Wait to simulate time gap
    # -----------------------------
    time.sleep(2)

    # -----------------------------
    # Second request (session B)
    # -----------------------------
    ctx_b = RequestContext(
        user_id=user_id,
        session_id=session_b,
        scope=scope,
        intent=intent,
    )

    allowed_refs_b = boundary.filter_memories(ctx=ctx_b, memories=memory_refs)
    allowed_ids_b = {m.memory_id for m in allowed_refs_b}

    allowed_entries_b = _entries_by_ids(all_entries, allowed_ids_b)
    selection_b = memory_selector.select(
        memories=allowed_entries_b,
        scope=scope,
        intent=intent,
        allowed_types=[MemoryType.FACT, MemoryType.PREFERENCE, MemoryType.DECISION],
        policy_allows=True,
    )

    injected_ids_b = selection_b.injectable_memory_ids
    injected_text_b = _format_injected_memory(injected_ids_b, content_index)

    instructions_b = (
        "You are a support assistant. Answer clearly and concisely.\n"
        "If injected memory is present, you may use it as authoritative context.\n"
        "Do not invent additional policy details.\n"
    )
    if injected_text_b:
        instructions_b += "\n" + injected_text_b + "\n"

    response_b = llm.generate_text(
        input_text=prompt,
        instructions=instructions_b,
    )

    print("\n--- Second response (session B) ---")
    print(response_b.output_text)

    # -----------------------------
    # Drift detection (numerical)
    # -----------------------------
    drift = drift_detector.compare(
        intent=intent,
        previous_text=response_a.output_text,
        current_text=response_b.output_text,
        previous_response_id=response_a.response_id,
        current_response_id=response_b.response_id,
    )

    print("\n--- Drift result ---")
    print(f"Similarity: {drift.similarity:.3f}")
    print(f"Status: {drift.status}")

    # -----------------------------
    # Policy decision (post-drift)
    # -----------------------------
    policy_decision = policy_gate.evaluate(
        drift_status=drift.status,
        drift_score=drift.similarity,
        injected_memory_ids=injected_ids_b,
    )

    print("\n--- Policy decision ---")
    print(f"Decision: {policy_decision.decision}")
    print(f"Allowed: {policy_decision.allowed}")
    print(f"Incident: {policy_decision.incident_flag}")
    print(f"Reason: {policy_decision.reason}")

    # -----------------------------
    # Deterministic replay (audit)
    # -----------------------------
    replay_input = ReplayInput(
        user_id=user_id,
        session_id=session_b,
        scope=scope,
        intent=intent,
        injected_memory_ids=injected_ids_b,
        drift_status=drift.status,
        drift_score=drift.similarity,
        drift_metrics={"cosine_similarity": drift.similarity},
    )
    replay_result = replay_engine.replay(replay_input)

    print("\n--- Replay result (deterministic) ---")
    print(f"Decision: {replay_result.decision}")
    print(f"Allowed: {replay_result.allowed}")
    print(f"Incident: {replay_result.incident_flag}")
    print(f"Reason: {replay_result.reason}")

    # -----------------------------
    # Logging (canonical log line)
    # -----------------------------
    logger.log(
        user_id=user_id,
        session_id=session_b,
        scope=scope,
        intent=intent,
        injected_memory_ids=injected_ids_b,
        drift_score=drift.similarity,
        extra={
            "stored_memory_id": stored_fact.memory_id,
            "memory_selection_reason_a": selection_a.reason,
            "memory_selection_reason_b": selection_b.reason,
            "memory_blocked_ids_a": selection_a.blocked_memory_ids,
            "memory_blocked_ids_b": selection_b.blocked_memory_ids,
            "memory_conflict_detected_a": selection_a.conflict_detected,
            "memory_conflict_detected_b": selection_b.conflict_detected,
            "previous_response_id": drift.previous_response_id,
            "current_response_id": drift.current_response_id,
            "drift_status": drift.status,
            "policy_decision": policy_decision.decision,
            "policy_allowed": policy_decision.allowed,
            "policy_incident": policy_decision.incident_flag,
            "policy_reason": policy_decision.reason,
            "replay_decision": replay_result.decision,
            "replay_allowed": replay_result.allowed,
            "replay_incident": replay_result.incident_flag,
        },
    )

    print("\nDemo completed.")


if __name__ == "__main__":
    main()