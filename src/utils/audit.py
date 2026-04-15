"""Audit logging for compliance tracking and regulatory traceability."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("audit")


class AuditLogger:
    """Append-only audit log for all agent actions — regulatory compliance trail."""

    def __init__(self, log_path: str = "logs/audit.jsonl"):
        self._path = Path(__file__).parent.parent.parent / log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        logger.info("Audit logger initialized: %s", self._path)

    def log(
        self,
        event_type: str,
        agent: str,
        action: str,
        details: dict[str, Any] | None = None,
        user_id: str = "system",
        session_id: str = "",
    ) -> dict[str, Any]:
        """Write an immutable audit record.

        Args:
            event_type: Category — query, tool_use, document_generation, safety_alert, etc.
            agent: Which agent performed the action.
            action: Human-readable description of what happened.
            details: Arbitrary payload with additional context.
            user_id: Who triggered the action.
            session_id: Conversation session identifier.

        Returns:
            The audit record that was written.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent": agent,
            "action": action,
            "user_id": user_id,
            "session_id": session_id,
            "details": details or {},
        }

        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")

        logger.debug("AUDIT | %s | %s | %s", event_type, agent, action)
        return record

    def query_logs(
        self,
        event_type: str | None = None,
        agent: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read audit logs with optional filters."""
        if not self._path.exists():
            return []

        results: list[dict[str, Any]] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if event_type and record.get("event_type") != event_type:
                    continue
                if agent and record.get("agent") != agent:
                    continue
                if since:
                    record_time = datetime.fromisoformat(record["timestamp"])
                    if record_time < since:
                        continue
                results.append(record)
                if len(results) >= limit:
                    break
        return results

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of audit log statistics."""
        if not self._path.exists():
            return {"total_records": 0, "event_types": {}, "agents": {}}

        total = 0
        event_types: dict[str, int] = {}
        agents: dict[str, int] = {}

        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                total += 1
                et = record.get("event_type", "unknown")
                event_types[et] = event_types.get(et, 0) + 1
                ag = record.get("agent", "unknown")
                agents[ag] = agents.get(ag, 0) + 1

        return {"total_records": total, "event_types": event_types, "agents": agents}
