"""Centralized configuration management for PharmaAgent Pro."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class ModelConfig:
    """Model selection and parameters."""
    primary_model: str = "claude-opus-4-6"
    fast_model: str = "claude-sonnet-4-6"
    classifier_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 8192
    thinking_budget_tokens: int = 10000
    temperature: float = 0.0


@dataclass
class CacheConfig:
    """Prompt caching settings."""
    enabled: bool = True
    ttl_minutes: int = 5
    min_tokens_for_cache: int = 2048


@dataclass
class RateLimitConfig:
    """Rate limiting settings."""
    requests_per_minute: int = 30
    max_tokens_per_minute: int = 400000
    max_concurrent_requests: int = 5


@dataclass
class Config:
    """Root configuration for PharmaAgent Pro."""
    api_key: str = ""
    env: str = "development"
    log_level: str = "INFO"
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    models: ModelConfig = field(default_factory=ModelConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    audit_log_path: str = "logs/audit.jsonl"
    memory_store_path: str = "src/memory/store"
    datasets_path: str = "src/datasets"

    @classmethod
    def load(cls) -> Config:
        """Load configuration from environment variables and .env file."""
        load_dotenv()
        project_root = Path(__file__).parent.parent.parent

        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            env=os.getenv("PHARMA_AGENT_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            project_root=project_root,
            models=ModelConfig(
                max_tokens=int(os.getenv("MAX_TOKENS_PER_REQUEST", "8192")),
                thinking_budget_tokens=int(os.getenv("THINKING_BUDGET_TOKENS", "10000")),
            ),
            cache=CacheConfig(
                ttl_minutes=int(os.getenv("CACHE_TTL_MINUTES", "5")),
            ),
            rate_limit=RateLimitConfig(
                requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")),
            ),
            audit_log_path=os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl"),
            memory_store_path=os.getenv("MEMORY_STORE_PATH", "src/memory/store"),
            datasets_path=os.getenv("DATASETS_PATH", "src/datasets"),
        )

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path against the project root."""
        return self.project_root / relative_path

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.api_key:
            errors.append("ANTHROPIC_API_KEY is not set")
        datasets = self.resolve_path(self.datasets_path)
        if not datasets.exists():
            errors.append(f"Datasets directory not found: {datasets}")
        return errors
