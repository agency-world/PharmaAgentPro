"""LLM usage tracking — token counts, costs, latency, and cache performance."""

from __future__ import annotations

import json
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from src.utils.logger import get_logger

logger = get_logger("usage")

# Pricing per million tokens (as of April 2026)
MODEL_PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0, "cache_write": 1.0, "cache_read": 0.08},
}


@dataclass
class RequestMetrics:
    """Metrics for a single LLM request."""
    timestamp: str = ""
    model: str = ""
    agent: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    thinking_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    session_id: str = ""
    success: bool = True
    error: str = ""


class UsageTracker:
    """Track and persist LLM usage metrics across all agents."""

    def __init__(self, log_path: str = "logs/usage.jsonl"):
        self._path = Path(__file__).parent.parent.parent / log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._session_totals: dict[str, dict[str, Any]] = {}
        logger.info("Usage tracker initialized: %s", self._path)

    @contextmanager
    def track_request(
        self, model: str, agent: str, session_id: str = ""
    ) -> Generator[RequestMetrics, None, None]:
        """Context manager to time and record an LLM request.

        Usage:
            with tracker.track_request("claude-opus-4-6", "drug_discovery") as metrics:
                response = client.messages.create(...)
                metrics.input_tokens = response.usage.input_tokens
                metrics.output_tokens = response.usage.output_tokens
                # ... etc
        """
        metrics = RequestMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            agent=agent,
            session_id=session_id,
        )
        start = time.perf_counter()
        try:
            yield metrics
        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            raise
        finally:
            metrics.latency_ms = (time.perf_counter() - start) * 1000
            metrics.estimated_cost_usd = self._calculate_cost(metrics)
            self._persist(metrics)
            self._update_session_totals(metrics)

    def record_from_response(
        self, response: Any, model: str, agent: str, session_id: str = "", latency_ms: float = 0.0
    ) -> RequestMetrics:
        """Record metrics directly from an Anthropic API response object."""
        usage = response.usage
        metrics = RequestMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            agent=agent,
            session_id=session_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            latency_ms=latency_ms,
        )
        metrics.estimated_cost_usd = self._calculate_cost(metrics)
        self._persist(metrics)
        self._update_session_totals(metrics)
        return metrics

    def _calculate_cost(self, m: RequestMetrics) -> float:
        """Calculate estimated USD cost for a request."""
        pricing = MODEL_PRICING.get(m.model)
        if not pricing:
            return 0.0
        cost = (
            (m.input_tokens * pricing["input"] / 1_000_000)
            + (m.output_tokens * pricing["output"] / 1_000_000)
            + (m.cache_creation_tokens * pricing["cache_write"] / 1_000_000)
            + (m.cache_read_tokens * pricing["cache_read"] / 1_000_000)
        )
        return round(cost, 6)

    def _persist(self, metrics: RequestMetrics) -> None:
        """Append metrics to the JSONL log."""
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(metrics)) + "\n")

    def _update_session_totals(self, m: RequestMetrics) -> None:
        """Accumulate session-level totals in memory."""
        sid = m.session_id or "default"
        if sid not in self._session_totals:
            self._session_totals[sid] = {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cache_read_tokens": 0,
                "total_cache_creation_tokens": 0,
                "total_cost_usd": 0.0,
                "request_count": 0,
                "total_latency_ms": 0.0,
            }
        t = self._session_totals[sid]
        t["total_input_tokens"] += m.input_tokens
        t["total_output_tokens"] += m.output_tokens
        t["total_cache_read_tokens"] += m.cache_read_tokens
        t["total_cache_creation_tokens"] += m.cache_creation_tokens
        t["total_cost_usd"] = round(t["total_cost_usd"] + m.estimated_cost_usd, 6)
        t["request_count"] += 1
        t["total_latency_ms"] += m.latency_ms

    def get_session_summary(self, session_id: str = "default") -> dict[str, Any]:
        """Get accumulated usage for a session."""
        totals = self._session_totals.get(session_id, {})
        if totals and totals["request_count"] > 0:
            totals["avg_latency_ms"] = round(
                totals["total_latency_ms"] / totals["request_count"], 1
            )
            cache_total = totals["total_cache_read_tokens"] + totals["total_cache_creation_tokens"]
            input_total = totals["total_input_tokens"] + cache_total
            totals["cache_hit_rate"] = (
                round(totals["total_cache_read_tokens"] / input_total, 3) if input_total > 0 else 0
            )
        return totals

    def get_global_summary(self) -> dict[str, Any]:
        """Get aggregated usage across all sessions."""
        global_totals = {
            "sessions": len(self._session_totals),
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "total_requests": 0,
        }
        for t in self._session_totals.values():
            global_totals["total_input_tokens"] += t["total_input_tokens"]
            global_totals["total_output_tokens"] += t["total_output_tokens"]
            global_totals["total_cost_usd"] = round(
                global_totals["total_cost_usd"] + t["total_cost_usd"], 6
            )
            global_totals["total_requests"] += t["request_count"]
        return global_totals
