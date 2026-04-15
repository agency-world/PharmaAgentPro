"""Input validation guardrails for pharma agent queries."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger("guardrails.input")

# Patterns that may indicate prompt injection or jailbreak attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"forget\s+(everything|all|your)\s+(instructions|rules|guidelines)",
    r"you\s+are\s+now\s+(?:a\s+)?(?:different|new|unrestricted)",
    r"act\s+as\s+(?:if|though)\s+you\s+(?:have\s+)?no\s+(?:rules|restrictions)",
    r"pretend\s+(?:you\s+are|to\s+be)\s+(?:a\s+)?(?:different|unrestricted)",
    r"override\s+(?:your\s+)?(?:safety|system|guardrail)",
    r"disable\s+(?:your\s+)?(?:safety|filters|guardrails)",
]

# Patterns indicating patient-identifiable information in input
_PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b\d{9}\b", "potential SSN without dashes"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email address"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone number"),
    (r"\b(?:MRN|medical\s+record)\s*[:#]?\s*\d{6,}\b", "medical record number"),
    (r"\bDOB\s*[:#]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "date of birth"),
]

# Topics that should be refused outright
_PROHIBITED_TOPICS = [
    r"(?:how\s+to\s+)?(?:synthesize|manufacture|make|produce)\s+(?:illegal|illicit|controlled)\s+(?:drugs|substances|narcotics)",
    r"(?:bypass|circumvent|evade)\s+(?:FDA|regulatory|safety)\s+(?:approval|review|oversight)",
    r"(?:falsify|fabricate|forge)\s+(?:clinical|trial|safety|regulatory)\s+(?:data|results|reports)",
]


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    message: str = ""
    pii_detected: list[str] | None = None
    sanitized_input: str = ""


class InputValidator:
    """Validate and sanitize user inputs before processing."""

    def __init__(self, max_input_length: int = 50000):
        self.max_input_length = max_input_length
        self._injection_re = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
        self._pii_re = [(re.compile(p), label) for p, label in _PII_PATTERNS]
        self._prohibited_re = [re.compile(p, re.IGNORECASE) for p in _PROHIBITED_TOPICS]

    def validate(self, user_input: str) -> ValidationResult:
        """Run all validation checks on user input."""
        if not user_input or not user_input.strip():
            return ValidationResult(is_valid=False, message="Input cannot be empty")

        if len(user_input) > self.max_input_length:
            return ValidationResult(
                is_valid=False,
                message=f"Input exceeds maximum length of {self.max_input_length} characters",
            )

        # Check for prohibited topics
        for pattern in self._prohibited_re:
            if pattern.search(user_input):
                logger.warning("Prohibited topic detected in input")
                return ValidationResult(
                    is_valid=False,
                    message="This request involves a prohibited topic and cannot be processed.",
                )

        # Check for prompt injection attempts
        for pattern in self._injection_re:
            if pattern.search(user_input):
                logger.warning("Potential prompt injection detected")
                return ValidationResult(
                    is_valid=False,
                    message="Input contains patterns that may indicate a prompt injection attempt.",
                )

        # Check for PII and sanitize
        pii_found: list[str] = []
        sanitized = user_input
        for pattern, label in self._pii_re:
            matches = pattern.findall(sanitized)
            if matches:
                pii_found.append(f"{label} ({len(matches)} instance(s))")
                sanitized = pattern.sub(f"[REDACTED_{label.upper().replace(' ', '_')}]", sanitized)

        if pii_found:
            logger.info("PII detected and redacted: %s", ", ".join(pii_found))

        return ValidationResult(
            is_valid=True,
            pii_detected=pii_found if pii_found else None,
            sanitized_input=sanitized,
        )
