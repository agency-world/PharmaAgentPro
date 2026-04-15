"""Base agent with shared infrastructure — Claude API, guardrails, memory, audit."""

from __future__ import annotations

import json
import time
from typing import Any

import anthropic

from src.utils.config import Config
from src.utils.audit import AuditLogger
from src.utils.usage_tracker import UsageTracker
from src.utils.logger import get_logger
from src.guardrails.input_validator import InputValidator
from src.guardrails.output_filter import OutputFilter
from src.guardrails.rate_limiter import RateLimiter
from src.memory.memory_store import MemoryStore

logger = get_logger("agent.base")


class BaseAgent:
    """Foundation for all PharmaAgent Pro agents.

    Provides:
    - Claude API client with prompt caching
    - Extended thinking for complex reasoning
    - Guardrails (input validation, output filtering, rate limiting)
    - Persistent memory store
    - Audit logging
    - LLM usage tracking
    """

    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        config: Config | None = None,
        model_override: str | None = None,
    ):
        self.name = agent_name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.config = config or Config.load()

        # Model selection
        self.model = model_override or self.config.models.primary_model

        # Claude API client
        self.client = anthropic.Anthropic(
            api_key=self.config.api_key,
            max_retries=3,
            timeout=120.0,
        )

        # Shared infrastructure
        self.audit = AuditLogger(self.config.audit_log_path)
        self.usage_tracker = UsageTracker()
        self.memory = MemoryStore(self.config.memory_store_path)
        self.input_validator = InputValidator()
        self.output_filter = OutputFilter()
        self.rate_limiter = RateLimiter(self.config.rate_limit.requests_per_minute)

        # Conversation state
        self.messages: list[dict[str, Any]] = []
        self.session_id: str = ""

        logger.info("Agent '%s' initialized (model=%s)", self.name, self.model)

    def _build_system_prompt(self) -> list[dict[str, Any]]:
        """Build system prompt with memory context and caching."""
        parts: list[dict[str, Any]] = []

        # Core system prompt (cached)
        parts.append({
            "type": "text",
            "text": self.system_prompt,
            "cache_control": {"type": "ephemeral"},
        })

        # Inject relevant memory context
        memory_context = self.memory.get_context_for_agent(self.name)
        if memory_context:
            parts.append({
                "type": "text",
                "text": f"\n\n{memory_context}",
            })

        return parts

    def _execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool by name and return the result string."""
        # Import tools dynamically to avoid circular imports
        from src.tools.drug_tools import DrugLookupTool, DrugInteractionTool
        from src.tools.trial_tools import TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
        from src.tools.document_tools import DocumentGeneratorTool

        tool_map = {
            DrugLookupTool.NAME: DrugLookupTool.execute,
            DrugInteractionTool.NAME: DrugInteractionTool.execute,
            TrialSearchTool.NAME: TrialSearchTool.execute,
            AdverseEventSearchTool.NAME: AdverseEventSearchTool.execute,
            SafetySignalTool.NAME: SafetySignalTool.execute,
            DocumentGeneratorTool.NAME: DocumentGeneratorTool.execute,
        }

        executor = tool_map.get(tool_name)
        if not executor:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        self.audit.log(
            event_type="tool_use",
            agent=self.name,
            action=f"Calling tool: {tool_name}",
            details={"tool_name": tool_name, "input": tool_input},
            session_id=self.session_id,
        )

        try:
            result = executor(**tool_input)
            return result
        except Exception as e:
            logger.error("Tool '%s' failed: %s", tool_name, e)
            return json.dumps({"error": str(e)})

    def chat(
        self,
        user_message: str,
        session_id: str = "",
        user_id: str = "default",
        use_thinking: bool = False,
    ) -> dict[str, Any]:
        """Process a single user message through the full agent pipeline.

        Returns:
            Dict with keys: response, thinking, tool_calls, usage, warnings
        """
        self.session_id = session_id

        # --- Guardrails: Rate limiting ---
        rate_check = self.rate_limiter.check(user_id)
        if not rate_check.allowed:
            return {
                "response": rate_check.message,
                "thinking": None,
                "tool_calls": [],
                "usage": {},
                "warnings": ["Rate limit exceeded"],
            }

        # --- Guardrails: Input validation ---
        validation = self.input_validator.validate(user_message)
        if not validation.is_valid:
            self.audit.log(
                event_type="input_rejected",
                agent=self.name,
                action="Input validation failed",
                details={"reason": validation.message},
                user_id=user_id,
                session_id=session_id,
            )
            return {
                "response": validation.message,
                "thinking": None,
                "tool_calls": [],
                "usage": {},
                "warnings": [validation.message],
            }

        # Use sanitized input (PII redacted)
        safe_input = validation.sanitized_input or user_message

        # Log the query
        self.audit.log(
            event_type="query",
            agent=self.name,
            action="Processing user query",
            details={
                "pii_detected": validation.pii_detected,
                "has_thinking": use_thinking,
            },
            user_id=user_id,
            session_id=session_id,
        )

        # Add user message to conversation
        self.messages.append({"role": "user", "content": safe_input})

        # --- LLM Call with tool loop ---
        all_tool_calls: list[dict[str, Any]] = []
        thinking_text = ""
        final_response = ""
        total_usage: dict[str, Any] = {
            "input_tokens": 0, "output_tokens": 0,
            "cache_creation_tokens": 0, "cache_read_tokens": 0,
        }

        max_iterations = 10  # prevent infinite tool loops
        for iteration in range(max_iterations):
            start_time = time.perf_counter()

            # Build request parameters
            request_params: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.config.models.max_tokens,
                "system": self._build_system_prompt(),
                "messages": self.messages,
            }

            if self.tools:
                request_params["tools"] = self.tools

            if use_thinking:
                request_params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self.config.models.thinking_budget_tokens,
                }

            # Make API call
            try:
                response = self.client.messages.create(**request_params)
            except anthropic.APIError as e:
                logger.error("API call failed: %s", e)
                return {
                    "response": f"I encountered an error processing your request: {e}",
                    "thinking": None,
                    "tool_calls": all_tool_calls,
                    "usage": total_usage,
                    "warnings": [f"API error: {e}"],
                }

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Track usage
            usage = response.usage
            total_usage["input_tokens"] += usage.input_tokens
            total_usage["output_tokens"] += usage.output_tokens
            total_usage["cache_creation_tokens"] += getattr(usage, "cache_creation_input_tokens", 0) or 0
            total_usage["cache_read_tokens"] += getattr(usage, "cache_read_input_tokens", 0) or 0

            self.usage_tracker.record_from_response(
                response, self.model, self.name, session_id, latency_ms
            )

            # Process response content blocks
            tool_uses: list[dict[str, Any]] = []
            for block in response.content:
                if block.type == "thinking":
                    thinking_text += block.thinking + "\n"
                elif block.type == "text":
                    final_response = block.text
                elif block.type == "tool_use":
                    tool_uses.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            # If no tool calls, we're done
            if response.stop_reason != "tool_use" or not tool_uses:
                self.messages.append({"role": "assistant", "content": response.content})
                break

            # Execute tools and continue
            self.messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tool_call in tool_uses:
                result_str = self._execute_tool(tool_call["name"], tool_call["input"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call["id"],
                    "content": result_str,
                })
                all_tool_calls.append({
                    "tool": tool_call["name"],
                    "input": tool_call["input"],
                    "result_preview": result_str[:200],
                })

            self.messages.append({"role": "user", "content": tool_results})

        # --- Guardrails: Output filtering ---
        filter_result = self.output_filter.filter(final_response)
        warnings = filter_result.warnings.copy()
        if validation.pii_detected:
            warnings.append(f"PII was detected and redacted from input: {', '.join(validation.pii_detected)}")

        # Add compliance footer if generating documents
        if any(tc.get("tool") == "generate_document" for tc in all_tool_calls):
            filter_result.filtered_text = self.output_filter.add_compliance_footer(
                filter_result.filtered_text, "regulatory"
            )

        # Audit the response
        self.audit.log(
            event_type="response",
            agent=self.name,
            action="Generated response",
            details={
                "tool_calls": len(all_tool_calls),
                "tokens": total_usage,
                "redactions": filter_result.redactions_applied,
                "warnings": warnings,
            },
            user_id=user_id,
            session_id=session_id,
        )

        return {
            "response": filter_result.filtered_text,
            "thinking": thinking_text if thinking_text else None,
            "tool_calls": all_tool_calls,
            "usage": total_usage,
            "warnings": warnings,
        }

    def reset_conversation(self) -> None:
        """Clear conversation history for a fresh start."""
        self.messages = []
        logger.info("Conversation reset for agent '%s'", self.name)
