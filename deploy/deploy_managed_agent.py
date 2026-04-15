"""Deploy PharmaAgent Pro to Claude Managed Agents Platform.

This script creates all resources on platform.claude.com:
1. Agent with pharma system prompt, custom tools, and full toolset
2. Cloud environment with required packages
3. Memory store seeded with pharma context
4. Interactive session ready for chatbot

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python deploy/deploy_managed_agent.py

    # Or with .env file
    python deploy/deploy_managed_agent.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import anthropic

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

AGENT_NAME = "PharmaAgent Pro"
AGENT_MODEL = "claude-sonnet-4-6"
DEPLOY_STATE_FILE = Path(__file__).parent / "deploy_state.json"

SYSTEM_PROMPT = """\
You are **PharmaAgent Pro**, an advanced pharmaceutical intelligence assistant \
built on Claude's Managed Agent platform. You help pharmaceutical researchers, \
clinicians, and regulatory professionals with:

1. **Drug Discovery** — Compound analysis, drug-likeness (Lipinski), ADMET, \
   CYP interactions, SAR, lead optimization
2. **Clinical Trials** — Trial design analysis, enrollment tracking, \
   endpoint evaluation, safety monitoring
3. **Regulatory Affairs** — Compliant document generation (IND reports, CSRs, \
   CIOMS, DSURs, IBs), FDA/ICH guideline compliance
4. **Safety & Pharmacovigilance** — Adverse event analysis, signal detection, \
   benefit-risk assessment, expedited reporting

## Rules
- Use tools proactively to retrieve data before responding
- Never fabricate data — use only tool results and verified information
- Flag safety concerns prominently with severity levels
- Include compound/trial/AE identifiers in all responses
- Anonymize patient identifiers (use subject IDs only)
- Add compliance disclaimers to regulatory documents
- For complex analyses (drug interactions, benefit-risk), think step by step
- All regulatory documents must include confidentiality notices
- Use CTCAE v5.0 grading for adverse event severity
- SAE reporting: 7 days (fatal/life-threatening), 15 days (other serious)

## Available Data
- 8 pharmaceutical compounds in development (small molecules, biologics, \
  oligonucleotides, peptides)
- 5 active clinical trials (Phase I–III) across oncology, neurology, \
  immunology, cardiology, rheumatology
- 10 adverse event records including 4 serious adverse events with narratives
- 6 regulatory document templates (IND report, CSR, CIOMS, DSUR, IB, protocol)

## Compliance Standards
- 21 CFR 312 (IND), 21 CFR 314 (NDA)
- ICH E2A (expedited reporting), ICH E2F (DSUR), ICH E3 (CSR)
- ICH E6 R2 (GCP), ICH E8 R1, ICH E9 R1
- MedDRA coding, CTCAE v5.0 grading
"""

CUSTOM_TOOLS = [
    {
        "type": "custom",
        "name": "drug_lookup",
        "description": (
            "Search the pharmaceutical compound library by name, compound ID, "
            "drug class, target, indication, or phase. Returns detailed compound "
            "profiles including molecular properties, pharmacokinetics, Lipinski "
            "assessment, and development status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term — compound name, ID (PHA-XXX), class, target, or indication",
                },
                "field": {
                    "type": "string",
                    "enum": ["any", "name", "compound_id", "class", "target", "indication", "phase"],
                    "description": "Which field to search. 'any' searches all fields.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "type": "custom",
        "name": "drug_interaction_check",
        "description": (
            "Check for potential drug-drug interactions between compounds based on "
            "CYP enzyme inhibition and substrate profiles. Returns interaction risk "
            "level and clinical recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "compound_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of compound names to check for interactions",
                },
            },
            "required": ["compound_names"],
        },
    },
    {
        "type": "custom",
        "name": "trial_search",
        "description": (
            "Search clinical trials database by compound name, trial ID, phase, or status. "
            "Returns trial design, enrollment, endpoints, site information, and interim results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term — compound name, trial ID (PCT-XXXX-XXXX), phase, or keyword",
                },
                "field": {
                    "type": "string",
                    "enum": ["any", "compound_name", "trial_id", "phase", "status"],
                    "description": "Field to search.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "type": "custom",
        "name": "adverse_event_search",
        "description": (
            "Search adverse events database by compound, trial, severity, or seriousness. "
            "Returns AE records with MedDRA coding, CTCAE grading, causality, and SAE narratives."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "compound_name": {"type": "string", "description": "Filter by compound name"},
                "trial_id": {"type": "string", "description": "Filter by trial ID"},
                "serious_only": {"type": "boolean", "description": "Only return SAEs"},
                "min_grade": {"type": "integer", "description": "Minimum CTCAE grade (1-5)"},
            },
        },
    },
    {
        "type": "custom",
        "name": "safety_signal_analysis",
        "description": (
            "Perform safety signal detection for a compound. Calculates AE rates, "
            "identifies disproportionate reporting, flags dose-limiting toxicities, "
            "and provides overall signal status with recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "compound_name": {"type": "string", "description": "Compound to analyze"},
            },
            "required": ["compound_name"],
        },
    },
    {
        "type": "custom",
        "name": "generate_document",
        "description": (
            "Generate a regulatory document scaffold. Types: ind_annual_report, "
            "clinical_study_report, safety_report_cioms, investigator_brochure, dsur, "
            "protocol_synopsis. Returns structured document with compliance headers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "document_type": {
                    "type": "string",
                    "enum": [
                        "ind_annual_report", "clinical_study_report",
                        "safety_report_cioms", "investigator_brochure",
                        "dsur", "protocol_synopsis",
                    ],
                    "description": "Type of regulatory document",
                },
                "compound_name": {"type": "string", "description": "Compound name"},
                "additional_fields": {
                    "type": "object",
                    "description": "Extra fields (e.g., ind_number, trial_id)",
                },
            },
            "required": ["document_type", "compound_name"],
        },
    },
]

# ──────────────────────────────────────────────────────────────
# Data loading helpers
# ──────────────────────────────────────────────────────────────

def _load_dataset(name: str) -> str:
    path = Path(__file__).parent.parent / "src" / "datasets" / name
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _build_memory_content() -> dict[str, str]:
    """Build memory entries from datasets."""
    return {
        "/pharma/compounds.md": (
            "# Compound Library\n\n"
            "PharmaAgent Pro has 8 compounds in development:\n"
            "- PHA-001 Nexavirin (Antiviral, Phase II) — COVID-19\n"
            "- PHA-002 Oncolytin-B (Kinase Inhibitor, Phase III) — NSCLC\n"
            "- PHA-003 Immunex-340 (mAb, Phase I) — Melanoma\n"
            "- PHA-004 Neuragen-X (Small Molecule, Phase I) — Alzheimer's\n"
            "- PHA-005 Cardiofix-200 (PCSK9 siRNA, Phase II) — Hypercholesterolemia\n"
            "- PHA-006 Inflammablock (JAK Inhibitor, Phase III) — RA\n"
            "- PHA-007 GlucoSense-Pro (GLP-1 Agonist, Phase II) — T2D+Obesity\n"
            "- PHA-008 Pulmorest-XR (PDE4 Inhibitor, Phase I) — IPF\n"
        ),
        "/pharma/trials.md": (
            "# Active Clinical Trials\n\n"
            "- PCT-2024-0147: Nexavirin Phase II (COVID-19) — 287/420 enrolled\n"
            "- PCT-2023-0089: ONCOLYZE-3 Phase III (NSCLC) — 598/600, BTD granted\n"
            "- PCT-2025-0201: IMMUNEX-FIRST Phase I (Solid Tumors) — 34/90\n"
            "- PCT-2025-0178: NEURA-CLEAR Phase I (Alzheimer's) — 18/72\n"
            "- PCT-2024-0156: INFLAM-RESOLVE Phase III (RA) — 748/750\n"
        ),
        "/pharma/safety_alerts.md": (
            "# Active Safety Signals\n\n"
            "## Oncolytin-B\n"
            "- SAE: Interstitial Lung Disease (Grade 3, drug discontinued)\n"
            "- SAE: QTc Prolongation (Grade 2, dose reduced)\n\n"
            "## Immunex-340\n"
            "- SAE: Immune-mediated Hepatitis (Grade 3, at 3.0 mg/kg dose)\n\n"
            "## Inflammablock\n"
            "- SAE: Deep Vein Thrombosis (Grade 3, per VTE stopping rule)\n"
            "- Herpes Zoster reactivation signal (JAK-class effect)\n"
        ),
        "/pharma/regulatory_standards.md": (
            "# Regulatory Compliance Standards\n\n"
            "All documents must comply with:\n"
            "- 21 CFR 312 (IND regulations)\n"
            "- ICH E2A (expedited safety reporting)\n"
            "- ICH E2F (DSUR format)\n"
            "- ICH E3 (CSR structure)\n"
            "- ICH E6 R2 (Good Clinical Practice)\n"
            "- MedDRA preferred terms for AE coding\n"
            "- CTCAE v5.0 for severity grading\n"
            "- ISO 8601 date format\n"
        ),
    }


# ──────────────────────────────────────────────────────────────
# Deployment functions
# ──────────────────────────────────────────────────────────────

def save_state(state: dict) -> None:
    """Persist deployment state to file."""
    with open(DEPLOY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"  State saved to {DEPLOY_STATE_FILE}")


def load_state() -> dict:
    """Load deployment state from file."""
    if DEPLOY_STATE_FILE.exists():
        with open(DEPLOY_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def deploy() -> dict:
    """Deploy PharmaAgent Pro to Claude Managed Agents Platform.

    Returns:
        Deployment state with all resource IDs.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        print("  Or create a .env file with the key.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    state = load_state()

    print("=" * 60)
    print("  PharmaAgent Pro — Managed Agent Deployment")
    print("=" * 60)

    # ── Step 1: Create Agent ──────────────────────────────────
    if "agent_id" not in state:
        print("\n[1/4] Creating Agent...")
        agent = client.beta.agents.create(
            name=AGENT_NAME,
            model=AGENT_MODEL,
            system=SYSTEM_PROMPT,
            tools=[
                {
                    "type": "agent_toolset_20260401",
                    "configs": [
                        {"name": "web_fetch", "enabled": True},
                        {"name": "web_search", "enabled": True},
                        {"name": "bash", "enabled": True},
                        {"name": "read", "enabled": True},
                        {"name": "write", "enabled": True},
                        {"name": "edit", "enabled": True},
                        {"name": "glob", "enabled": True},
                        {"name": "grep", "enabled": True},
                    ],
                },
                *CUSTOM_TOOLS,
            ],
        )
        state["agent_id"] = agent.id
        state["agent_version"] = agent.version
        save_state(state)
        print(f"  Agent created: {agent.id} (v{agent.version})")
    else:
        print(f"\n[1/4] Agent exists: {state['agent_id']}")

    # ── Step 2: Create Environment ────────────────────────────
    if "environment_id" not in state:
        print("\n[2/4] Creating Cloud Environment...")
        environment = client.beta.environments.create(
            name="pharma-agent-env",
            config={
                "type": "cloud",
                "packages": {
                    "pip": ["pandas", "jinja2", "rich"],
                },
                "networking": {"type": "unrestricted"},
            },
        )
        state["environment_id"] = environment.id
        save_state(state)
        print(f"  Environment created: {environment.id}")
    else:
        print(f"\n[2/4] Environment exists: {state['environment_id']}")

    # ── Step 3: Create Memory Store & Seed ────────────────────
    if "memory_store_id" not in state:
        print("\n[3/4] Creating Memory Store...")
        try:
            store = client.beta.memory_stores.create(
                name="PharmaAgent Pro Context",
                description=(
                    "Pharmaceutical compound library, clinical trial data, "
                    "safety alerts, and regulatory standards for PharmaAgent Pro."
                ),
            )
            state["memory_store_id"] = store.id
            save_state(state)
            print(f"  Memory store created: {store.id}")

            # Seed with pharma context
            print("  Seeding memory with pharma data...")
            for path, content in _build_memory_content().items():
                client.beta.memory_stores.memories.write(
                    memory_store_id=store.id,
                    path=path,
                    content=content,
                )
                print(f"    Written: {path}")

            # Upload full datasets as memory entries
            for dataset_name, mem_path in [
                ("drugs_compound_library.json", "/data/compounds.json"),
                ("clinical_trials.json", "/data/trials.json"),
                ("adverse_events.json", "/data/adverse_events.json"),
                ("regulatory_templates.json", "/data/regulatory_templates.json"),
            ]:
                dataset_content = _load_dataset(dataset_name)
                if len(dataset_content.encode("utf-8")) <= 100 * 1024:
                    client.beta.memory_stores.memories.write(
                        memory_store_id=store.id,
                        path=mem_path,
                        content=dataset_content,
                    )
                    print(f"    Uploaded dataset: {mem_path}")
                else:
                    print(f"    Skipped (>100KB): {mem_path}")

            print("  Memory seeding complete.")
        except (AttributeError, Exception) as e:
            print(f"  Memory Store API not available yet (research preview): {e}")
            print("  Skipping memory store — agent will use local memory + system prompt context.")
            state["memory_store_id"] = None
            save_state(state)
    else:
        if state["memory_store_id"]:
            print(f"\n[3/4] Memory store exists: {state['memory_store_id']}")
        else:
            print("\n[3/4] Memory store: skipped (using local memory)")

    # ── Step 4: Create Session ────────────────────────────────
    print("\n[4/4] Creating Session...")
    session_kwargs = {
        "agent": state["agent_id"],
        "environment_id": state["environment_id"],
        "title": "PharmaAgent Pro — Agentic Chatbot",
    }

    # Attach memory store if available
    if state.get("memory_store_id"):
        session_kwargs["resources"] = [
            {
                "type": "memory_store",
                "memory_store_id": state["memory_store_id"],
                "access": "read_write",
                "prompt": (
                    "This memory contains the pharmaceutical compound library, "
                    "clinical trial database, adverse event records, and regulatory "
                    "templates. Check /pharma/ for summaries and /data/ for full datasets. "
                    "Use this data to answer pharma queries accurately."
                ),
            },
        ]

    session = client.beta.sessions.create(**session_kwargs)
    state["session_id"] = session.id
    state["session_status"] = "idle"
    save_state(state)
    print(f"  Session created: {session.id}")

    # ── Summary ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE")
    print("=" * 60)
    mem_info = state.get('memory_store_id') or 'local (SDK memory API in research preview)'
    print(f"""
  Agent ID:       {state['agent_id']}
  Environment ID: {state['environment_id']}
  Memory Store:   {mem_info}
  Session ID:     {state['session_id']}

  Dashboard:
    https://platform.claude.com/workspaces/default/agents

  Next steps:
    1. Run the chatbot:
       python deploy/chatbot.py

    2. Or use the web UI:
       python deploy/chatbot_server.py
       Open http://localhost:3000

    3. Or interact via API:
       curl -X POST http://localhost:8000/chat \\
         -H 'Content-Type: application/json' \\
         -d '{{"message": "Analyze Nexavirin drug-likeness"}}'
""")

    return state


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    deploy()
