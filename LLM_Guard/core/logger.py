# core/logger.py
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class LoggerError(RuntimeError):
    pass


@dataclass(frozen=True)
class LogRecord:
    """
    Canonical log record for LLM-Guard.

    v1 guarantees:
    - JSON only
    - Append-only
    - Deterministic fields
    - Incident-grade explainability
    """

    # Core identity
    timestamp: str
    user_id: str
    session_id: str
    scope: str
    intent: str

    # Memory
    injected_memory_ids: List[str]

    # Drift (v1: multi-metric capable)
    drift_score: Optional[float] = None
    drift_metrics: Optional[Dict[str, float]] = None
    drift_status: Optional[str] = None  # "stable" | "drifting"

    # Policy / decision layer (v1)
    policy_decision: Optional[str] = None
    policy_reason: Optional[str] = None

    # Incident semantics (v1)
    incident_flag: bool = False

    # Extension slot (explicitly non-semantic)
    extra: Optional[Dict[str, Any]] = None


class JSONLogger:
    """
    JSON logger for LLM-Guard.

    Supports:
    - stdout logging
    - file logging (append-only)
    """

    def __init__(self, *, log_path: Optional[str | Path] = None) -> None:
        self._log_path: Optional[Path] = None
        if log_path:
            self._log_path = Path(log_path)
            self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def emit(self, record: LogRecord) -> None:
        payload = asdict(record)

        # Ensure timestamp exists / override if missing
        payload["timestamp"] = payload.get("timestamp") or self._now_iso()

        try:
            line = json.dumps(payload, ensure_ascii=False)
        except Exception as e:
            raise LoggerError(f"Failed to serialize log record: {e}") from e

        # stdout
        print(line, file=sys.stdout)

        # file (append)
        if self._log_path:
            try:
                with self._log_path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception as e:
                raise LoggerError(f"Failed to write log file: {e}") from e

    def log(
        self,
        *,
        user_id: str,
        session_id: str,
        scope: str,
        intent: str,
        injected_memory_ids: List[str],
        drift_score: Optional[float] = None,
        drift_metrics: Optional[Dict[str, float]] = None,
        drift_status: Optional[str] = None,
        policy_decision: Optional[str] = None,
        policy_reason: Optional[str] = None,
        incident_flag: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a single structured log entry.

        v1 rules:
        - All decisions must be explicit
        - Incident flag must be intentional
        - No implicit inference inside logger
        """
        record = LogRecord(
            timestamp=self._now_iso(),
            user_id=user_id,
            session_id=session_id,
            scope=scope,
            intent=intent,
            injected_memory_ids=injected_memory_ids,
            drift_score=drift_score,
            drift_metrics=drift_metrics,
            drift_status=drift_status,
            policy_decision=policy_decision,
            policy_reason=policy_reason,
            incident_flag=incident_flag,
            extra=extra,
        )
        self.emit(record)