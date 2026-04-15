"""Main orchestrator agent — routes queries to specialized sub-agents."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from src.agents.base_agent import BaseAgent
from src.tools.drug_tools import DrugLookupTool, DrugInteractionTool
from src.tools.trial_tools import TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
from src.tools.document_tools import DocumentGeneratorTool
from src.utils.config import Config
from src.utils.logger import get_logger

logger = get_logger("agent.orchestrator")

# All available tools
ALL_TOOLS = [
    DrugLookupTool.as_tool_definition(),
    DrugInteractionTool.as_tool_definition(),
    TrialSearchTool.as_tool_definition(),
    AdverseEventSearchTool.as_tool_definition(),
    SafetySignalTool.as_tool_definition(),
    DocumentGeneratorTool.as_tool_definition(),
]

# Domain-specific agent configurations
AGENT_CONFIGS = {
    "drug_discovery": {
        "name": "drug_discovery",
        "system_prompt": (
            "You are PharmaAgent Pro's Drug Discovery Specialist. "
            "You have deep expertise in medicinal chemistry, pharmacology, ADMET assessment, "
            "and computational drug design. You help researchers analyze compounds, evaluate "
            "drug-likeness, check interactions, and optimize lead candidates.\n\n"
            "RULES:\n"
            "- Always use the drug_lookup tool to retrieve compound data before analysis\n"
            "- Use the drug_interaction_check tool when comparing multiple compounds\n"
            "- Include Lipinski Rule of Five assessment in compound reviews\n"
            "- Flag CYP interaction liabilities prominently\n"
            "- Never fabricate data — only use what the tools return\n"
            "- Use extended thinking for complex SAR analysis"
        ),
        "tools": [
            DrugLookupTool.as_tool_definition(),
            DrugInteractionTool.as_tool_definition(),
        ],
        "use_thinking": True,
    },
    "clinical_trials": {
        "name": "clinical_trials",
        "system_prompt": (
            "You are PharmaAgent Pro's Clinical Trials Research Specialist. "
            "You have expertise in trial design, biostatistics, clinical operations, "
            "and safety monitoring. You help teams analyze trial data, track enrollment, "
            "evaluate endpoints, and assess adverse event profiles.\n\n"
            "RULES:\n"
            "- Always use the trial_search tool to retrieve trial data\n"
            "- Use the adverse_event_search tool for safety analysis\n"
            "- Include enrollment progress percentages in trial summaries\n"
            "- Present efficacy data with hazard ratios and confidence intervals\n"
            "- Highlight SAEs and safety signals prominently\n"
            "- Never extrapolate beyond available data"
        ),
        "tools": [
            TrialSearchTool.as_tool_definition(),
            AdverseEventSearchTool.as_tool_definition(),
            SafetySignalTool.as_tool_definition(),
        ],
        "use_thinking": True,
    },
    "regulatory": {
        "name": "regulatory",
        "system_prompt": (
            "You are PharmaAgent Pro's Regulatory Affairs Specialist. "
            "You have deep knowledge of FDA regulations, ICH guidelines, and global "
            "submission requirements. You generate compliant regulatory documents, "
            "advise on submission strategy, and validate document completeness.\n\n"
            "RULES:\n"
            "- Use the generate_document tool to create regulatory document scaffolds\n"
            "- Always cite specific regulatory standards (e.g., 21 CFR 312.33)\n"
            "- Include compliance checklists in all generated documents\n"
            "- Flag any data gaps that would prevent submission\n"
            "- Use formal regulatory language appropriate for FDA/EMA\n"
            "- All documents must include confidentiality notices"
        ),
        "tools": [
            DocumentGeneratorTool.as_tool_definition(),
            TrialSearchTool.as_tool_definition(),
            AdverseEventSearchTool.as_tool_definition(),
            DrugLookupTool.as_tool_definition(),
        ],
        "use_thinking": False,
    },
    "safety": {
        "name": "safety",
        "system_prompt": (
            "You are PharmaAgent Pro's Safety & Pharmacovigilance Specialist. "
            "You have expertise in signal detection, risk assessment, benefit-risk analysis, "
            "and regulatory safety reporting. You monitor adverse events, detect safety signals, "
            "and recommend risk mitigation strategies.\n\n"
            "RULES:\n"
            "- Use the safety_signal_analysis tool for signal detection\n"
            "- Use the adverse_event_search tool to retrieve safety data\n"
            "- ALWAYS lead with the most serious safety findings\n"
            "- Use CTCAE v5.0 grading for all adverse event assessments\n"
            "- Include causality assessment for every AE discussed\n"
            "- Flag any SAE requiring expedited reporting (15-day / 7-day)\n"
            "- Use extended thinking for complex benefit-risk analyses\n"
            "- Never downplay or minimize serious safety signals"
        ),
        "tools": [
            SafetySignalTool.as_tool_definition(),
            AdverseEventSearchTool.as_tool_definition(),
            TrialSearchTool.as_tool_definition(),
            DrugLookupTool.as_tool_definition(),
        ],
        "use_thinking": True,
    },
}

ORCHESTRATOR_SYSTEM_PROMPT = """\
You are **PharmaAgent Pro**, an advanced pharmaceutical intelligence assistant powered by \
Claude's Managed Agent architecture. You orchestrate a team of specialized sub-agents to \
help pharmaceutical researchers, clinicians, and regulatory professionals.

## Your Capabilities
1. **Drug Discovery** — Compound analysis, drug-likeness, interactions, lead optimization
2. **Clinical Trials** — Trial design analysis, enrollment tracking, endpoint evaluation
3. **Regulatory Affairs** — Compliant document generation (IND reports, CSRs, CIOMS, DSURs)
4. **Safety Monitoring** — Adverse event analysis, signal detection, benefit-risk assessment

## Available Tools
You have direct access to these tools:
- `drug_lookup` — Search the compound library
- `drug_interaction_check` — Analyze drug-drug interactions
- `trial_search` — Search clinical trials database
- `adverse_event_search` — Query adverse event records
- `safety_signal_analysis` — Run signal detection analysis
- `generate_document` — Create regulatory document scaffolds

## Response Guidelines
1. Use tools proactively to retrieve data before responding
2. Provide evidence-based answers grounded in the dataset
3. Flag safety concerns with appropriate severity levels
4. Include data citations (compound IDs, trial IDs, AE IDs)
5. For complex analyses, leverage extended thinking
6. Add appropriate disclaimers for medical/regulatory content
7. Remember user preferences and context across the conversation

## Important
- Never fabricate data — use only tool results
- Anonymize all patient identifiers
- Flag any PII in inputs for redaction
- All regulatory documents require human review before submission\
"""


class PharmaOrchestrator:
    """Main orchestrator that handles multi-turn conversations and routes to sub-agents.

    The orchestrator first tries to handle queries directly using all available tools.
    For specialized deep-dive requests, it delegates to the appropriate sub-agent.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()

        # Main orchestrator agent with all tools
        self.main_agent = BaseAgent(
            agent_name="orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            tools=ALL_TOOLS,
            config=self.config,
        )

        # Classifier for routing (uses fast model)
        self.classifier_client = anthropic.Anthropic(
            api_key=self.config.api_key,
            max_retries=2,
            timeout=30.0,
        )

        # Lazy-loaded sub-agents
        self._sub_agents: dict[str, BaseAgent] = {}

        logger.info("PharmaOrchestrator initialized with %d tool(s)", len(ALL_TOOLS))

    def _get_sub_agent(self, domain: str) -> BaseAgent:
        """Get or create a sub-agent for a specific domain."""
        if domain not in self._sub_agents:
            agent_config = AGENT_CONFIGS.get(domain)
            if not agent_config:
                raise ValueError(f"Unknown domain: {domain}")

            self._sub_agents[domain] = BaseAgent(
                agent_name=agent_config["name"],
                system_prompt=agent_config["system_prompt"],
                tools=agent_config["tools"],
                config=self.config,
            )
        return self._sub_agents[domain]

    def classify_query(self, user_message: str) -> dict[str, Any]:
        """Classify user query to determine routing — uses the fast classifier model.

        Returns:
            Dict with 'domain', 'use_thinking', 'confidence'
        """
        classification_prompt = f"""\
Classify this pharmaceutical query into exactly one domain.

Query: "{user_message}"

Domains:
- drug_discovery: compound analysis, molecular properties, drug-likeness, interactions, SAR
- clinical_trials: trial design, enrollment, endpoints, efficacy data, trial search
- regulatory: document generation, FDA compliance, ICH guidelines, submissions
- safety: adverse events, signal detection, benefit-risk, pharmacovigilance
- general: greetings, help requests, multi-domain, or unclear

Respond with ONLY a JSON object:
{{"domain": "<domain>", "confidence": <0.0-1.0>, "reasoning": "<brief>"}}"""

        try:
            response = self.classifier_client.messages.create(
                model=self.config.models.classifier_model,
                max_tokens=200,
                messages=[{"role": "user", "content": classification_prompt}],
            )
            text = response.content[0].text.strip()

            # Track classifier usage
            self.main_agent.usage_tracker.record_from_response(
                response, self.config.models.classifier_model, "classifier"
            )

            # Parse JSON response
            result = json.loads(text)
            result.setdefault("domain", "general")
            result.setdefault("confidence", 0.5)
            logger.info("Query classified: domain=%s, confidence=%.2f",
                        result["domain"], result["confidence"])
            return result

        except (json.JSONDecodeError, anthropic.APIError) as e:
            logger.warning("Classification failed, defaulting to orchestrator: %s", e)
            return {"domain": "general", "confidence": 0.0, "reasoning": "Classification failed"}

    def chat(
        self,
        user_message: str,
        session_id: str = "",
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Process a user message through the orchestration pipeline.

        Pipeline:
        1. Classify query domain
        2. Route to appropriate agent
        3. Apply guardrails
        4. Return response with metadata
        """
        # Classify the query
        classification = self.classify_query(user_message)
        domain = classification["domain"]
        confidence = classification.get("confidence", 0)

        # Determine routing
        use_sub_agent = domain in AGENT_CONFIGS and confidence >= 0.7

        if use_sub_agent:
            agent = self._get_sub_agent(domain)
            agent_config = AGENT_CONFIGS[domain]
            use_thinking = agent_config.get("use_thinking", False)
            logger.info("Routing to sub-agent: %s (confidence=%.2f)", domain, confidence)
        else:
            agent = self.main_agent
            use_thinking = domain in ("drug_discovery", "safety", "clinical_trials")
            logger.info("Handling with orchestrator (domain=%s, confidence=%.2f)", domain, confidence)

        # Process through the selected agent
        result = agent.chat(
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            use_thinking=use_thinking,
        )

        # Add routing metadata
        result["routing"] = {
            "domain": domain,
            "confidence": confidence,
            "agent": agent.name,
            "used_thinking": use_thinking,
        }

        return result

    def get_status(self) -> dict[str, Any]:
        """Get system status including usage, memory, and audit stats."""
        return {
            "agents_active": ["orchestrator"] + list(self._sub_agents.keys()),
            "usage": self.main_agent.usage_tracker.get_global_summary(),
            "audit": self.main_agent.audit.get_summary(),
            "memory_count": len(self.main_agent.memory._index.get("memories", {})),
            "rate_limit": self.main_agent.rate_limiter.get_usage(),
        }

    def save_memory(self, path: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        """Save information to the persistent memory store."""
        return self.main_agent.memory.write(path, content, tags)

    def search_memory(self, query: str) -> list[dict[str, Any]]:
        """Search the persistent memory store."""
        return self.main_agent.memory.search(query)

    def reset(self) -> None:
        """Reset all agent conversations."""
        self.main_agent.reset_conversation()
        for agent in self._sub_agents.values():
            agent.reset_conversation()
        logger.info("All agents reset")
