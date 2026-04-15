"""Tests for utility modules."""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from dataclasses import asdict

from src.utils.config import Config, ModelConfig
from src.utils.audit import AuditLogger
from src.utils.usage_tracker import UsageTracker, RequestMetrics


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.models.primary_model == "claude-opus-4-6"
        assert config.models.fast_model == "claude-sonnet-4-6"
        assert config.env == "development"

    def test_validate_missing_key(self):
        config = Config(api_key="")
        errors = config.validate()
        assert any("ANTHROPIC_API_KEY" in e for e in errors)

    def test_validate_with_key(self):
        config = Config(api_key="sk-ant-test")
        errors = config.validate()
        assert not any("ANTHROPIC_API_KEY" in e for e in errors)

    def test_resolve_path(self):
        config = Config()
        path = config.resolve_path("src/datasets")
        assert path.name == "datasets"


class TestAuditLogger:
    def test_log_and_query(self, tmp_path):
        audit = AuditLogger(log_path=str(tmp_path / "test_audit.jsonl"))
        audit.log(
            event_type="query",
            agent="test_agent",
            action="Test action",
            details={"key": "value"},
        )
        records = audit.query_logs()
        assert len(records) == 1
        assert records[0]["event_type"] == "query"
        assert records[0]["agent"] == "test_agent"

    def test_filter_by_event_type(self, tmp_path):
        audit = AuditLogger(log_path=str(tmp_path / "test_audit.jsonl"))
        audit.log(event_type="query", agent="a", action="query1")
        audit.log(event_type="tool_use", agent="a", action="tool1")
        audit.log(event_type="query", agent="a", action="query2")
        records = audit.query_logs(event_type="query")
        assert len(records) == 2

    def test_filter_by_agent(self, tmp_path):
        audit = AuditLogger(log_path=str(tmp_path / "test_audit.jsonl"))
        audit.log(event_type="query", agent="agent_a", action="a1")
        audit.log(event_type="query", agent="agent_b", action="b1")
        records = audit.query_logs(agent="agent_a")
        assert len(records) == 1

    def test_summary(self, tmp_path):
        audit = AuditLogger(log_path=str(tmp_path / "test_audit.jsonl"))
        audit.log(event_type="query", agent="a", action="a1")
        audit.log(event_type="tool_use", agent="b", action="b1")
        summary = audit.get_summary()
        assert summary["total_records"] == 2
        assert summary["event_types"]["query"] == 1
        assert summary["agents"]["a"] == 1


class TestUsageTracker:
    def test_record_metrics(self, tmp_path):
        tracker = UsageTracker(log_path=str(tmp_path / "test_usage.jsonl"))

        # Create mock response
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.usage.cache_creation_input_tokens = 10
        mock_response.usage.cache_read_input_tokens = 5

        metrics = tracker.record_from_response(
            mock_response, "claude-opus-4-6", "test_agent", "session1"
        )
        assert metrics.input_tokens == 100
        assert metrics.output_tokens == 50
        assert metrics.estimated_cost_usd > 0

    def test_session_summary(self, tmp_path):
        tracker = UsageTracker(log_path=str(tmp_path / "test_usage.jsonl"))

        mock = MagicMock()
        mock.usage.input_tokens = 100
        mock.usage.output_tokens = 50
        mock.usage.cache_creation_input_tokens = 0
        mock.usage.cache_read_input_tokens = 0

        tracker.record_from_response(mock, "claude-opus-4-6", "a", "s1")
        tracker.record_from_response(mock, "claude-opus-4-6", "a", "s1")

        summary = tracker.get_session_summary("s1")
        assert summary["request_count"] == 2
        assert summary["total_input_tokens"] == 200

    def test_global_summary(self, tmp_path):
        tracker = UsageTracker(log_path=str(tmp_path / "test_usage.jsonl"))

        mock = MagicMock()
        mock.usage.input_tokens = 100
        mock.usage.output_tokens = 50
        mock.usage.cache_creation_input_tokens = 0
        mock.usage.cache_read_input_tokens = 0

        tracker.record_from_response(mock, "claude-opus-4-6", "a", "s1")
        tracker.record_from_response(mock, "claude-opus-4-6", "b", "s2")

        summary = tracker.get_global_summary()
        assert summary["sessions"] == 2
        assert summary["total_requests"] == 2

    def test_cost_calculation(self, tmp_path):
        tracker = UsageTracker(log_path=str(tmp_path / "test_usage.jsonl"))
        metrics = RequestMetrics(
            model="claude-opus-4-6",
            input_tokens=1_000_000,
            output_tokens=100_000,
        )
        cost = tracker._calculate_cost(metrics)
        # Opus: $15/MTok input + $75/MTok output
        expected = (1_000_000 * 15 / 1_000_000) + (100_000 * 75 / 1_000_000)
        assert cost == expected
