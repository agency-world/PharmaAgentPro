"""Clinical trial and safety analysis tools for Claude function calling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("tools.trial")


def _load_trials() -> list[dict[str, Any]]:
    path = Path(__file__).parent.parent / "datasets" / "clinical_trials.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_adverse_events() -> list[dict[str, Any]]:
    path = Path(__file__).parent.parent / "datasets" / "adverse_events.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TrialSearchTool:
    """Tool: Search clinical trials by compound, phase, status, or indication."""

    NAME = "trial_search"
    DESCRIPTION = (
        "Search the clinical trials database by compound name, trial ID, phase, "
        "status, or any keyword. Returns trial design, enrollment, endpoints, "
        "site information, and interim results when available."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term — compound name, trial ID (PCT-XXXX-XXXX), phase, or keyword",
            },
            "field": {
                "type": "string",
                "enum": ["any", "compound_name", "trial_id", "phase", "status"],
                "description": "Field to search. 'any' searches all fields.",
                "default": "any",
            },
        },
        "required": ["query"],
    }

    @staticmethod
    def execute(query: str, field: str = "any") -> str:
        trials = _load_trials()
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for trial in trials:
            if field == "any":
                if query_lower in json.dumps(trial).lower():
                    results.append(trial)
            else:
                if query_lower in str(trial.get(field, "")).lower():
                    results.append(trial)

        if not results:
            return json.dumps({"status": "no_results", "message": f"No trials found for '{query}'"})

        # Add enrollment progress
        for r in results:
            pop = r.get("population", {})
            target = pop.get("target_enrollment", 0)
            current = pop.get("current_enrollment", 0)
            if target > 0:
                r["enrollment_progress_pct"] = round(current / target * 100, 1)

        logger.info("Trial search: query='%s', results=%d", query, len(results))
        return json.dumps({"status": "success", "count": len(results), "trials": results}, indent=2, default=str)

    @classmethod
    def as_tool_definition(cls) -> dict[str, Any]:
        return {"name": cls.NAME, "description": cls.DESCRIPTION, "input_schema": cls.INPUT_SCHEMA}


class AdverseEventSearchTool:
    """Tool: Search and analyze adverse events from clinical trials."""

    NAME = "adverse_event_search"
    DESCRIPTION = (
        "Search the adverse events database by compound, trial, severity, "
        "seriousness, or event term. Returns detailed AE records including "
        "MedDRA coding, CTCAE grading, causality assessment, and SAE narratives."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "compound_name": {
                "type": "string",
                "description": "Filter by compound name (optional)",
            },
            "trial_id": {
                "type": "string",
                "description": "Filter by trial ID (optional)",
            },
            "serious_only": {
                "type": "boolean",
                "description": "Only return serious adverse events (SAEs)",
                "default": False,
            },
            "min_grade": {
                "type": "integer",
                "description": "Minimum CTCAE grade to include (1-5)",
                "default": 1,
            },
        },
    }

    @staticmethod
    def execute(
        compound_name: str = "",
        trial_id: str = "",
        serious_only: bool = False,
        min_grade: int = 1,
    ) -> str:
        events = _load_adverse_events()
        results: list[dict[str, Any]] = []

        for ae in events:
            if compound_name and compound_name.lower() not in ae.get("compound_name", "").lower():
                continue
            if trial_id and trial_id.lower() != ae.get("trial_id", "").lower():
                continue
            if serious_only and not ae.get("serious", False):
                continue
            if ae.get("ctcae_grade", 0) < min_grade:
                continue
            results.append(ae)

        if not results:
            return json.dumps({"status": "no_results", "message": "No adverse events match the criteria"})

        # Summary statistics
        summary = {
            "total_events": len(results),
            "serious_events": sum(1 for r in results if r.get("serious")),
            "by_severity": {},
            "by_soc": {},
            "by_causality": {},
        }
        for r in results:
            sev = r.get("severity", "Unknown")
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
            soc = r.get("meddra_soc", "Unknown")
            summary["by_soc"][soc] = summary["by_soc"].get(soc, 0) + 1
            caus = r.get("causality", "Unknown")
            summary["by_causality"][caus] = summary["by_causality"].get(caus, 0) + 1

        logger.info("AE search: %d events found", len(results))
        return json.dumps({"status": "success", "summary": summary, "events": results}, indent=2, default=str)

    @classmethod
    def as_tool_definition(cls) -> dict[str, Any]:
        return {"name": cls.NAME, "description": cls.DESCRIPTION, "input_schema": cls.INPUT_SCHEMA}


class SafetySignalTool:
    """Tool: Perform safety signal detection analysis."""

    NAME = "safety_signal_analysis"
    DESCRIPTION = (
        "Perform safety signal analysis for a compound by calculating adverse event "
        "rates, identifying disproportionate reporting, and flagging potential signals. "
        "Compares treatment arm AE rates to control/background rates."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "compound_name": {
                "type": "string",
                "description": "Compound name to analyze",
            },
        },
        "required": ["compound_name"],
    }

    @staticmethod
    def execute(compound_name: str) -> str:
        events = _load_adverse_events()
        trials = _load_trials()

        compound_events = [e for e in events if e.get("compound_name", "").lower() == compound_name.lower()]
        compound_trials = [t for t in trials if t.get("compound_name", "").lower() == compound_name.lower()]

        if not compound_events:
            return json.dumps({"status": "no_data", "message": f"No adverse event data for {compound_name}"})

        # Signal analysis
        signals: list[dict[str, Any]] = []
        sae_list = [e for e in compound_events if e.get("serious")]
        grade3_plus = [e for e in compound_events if e.get("ctcae_grade", 0) >= 3]

        # Group by MedDRA SOC
        soc_counts: dict[str, int] = {}
        for e in compound_events:
            soc = e.get("meddra_soc", "Unknown")
            soc_counts[soc] = soc_counts.get(soc, 0) + 1

        # Flag disproportionate signals
        total_events = len(compound_events)
        for soc, count in soc_counts.items():
            proportion = count / total_events if total_events > 0 else 0
            if proportion > 0.3 or count >= 3:
                signals.append({
                    "type": "disproportionate_reporting",
                    "soc": soc,
                    "count": count,
                    "proportion": round(proportion, 3),
                    "alert_level": "HIGH" if any(
                        e.get("meddra_soc") == soc and e.get("serious") for e in compound_events
                    ) else "MEDIUM",
                })

        # Check for dose-limiting toxicities
        dose_responses: list[dict[str, str]] = []
        for e in compound_events:
            if e.get("action_taken") in ["Drug permanently discontinued", "Dose reduced"]:
                dose_responses.append({
                    "event": e["event_term"],
                    "action": e["action_taken"],
                    "grade": str(e.get("ctcae_grade", "?")),
                })

        result = {
            "status": "success",
            "compound": compound_name,
            "total_events_analyzed": total_events,
            "serious_adverse_events": len(sae_list),
            "grade_3_plus_events": len(grade3_plus),
            "active_trials": len(compound_trials),
            "safety_signals": signals,
            "dose_limiting_toxicities": dose_responses,
            "overall_signal_status": (
                "ALERT — Action Required" if any(s["alert_level"] == "HIGH" for s in signals)
                else "MONITOR" if signals
                else "NO SIGNAL DETECTED"
            ),
            "recommendation": (
                "Immediate DSMB review recommended" if sae_list
                else "Continue routine monitoring"
            ),
        }

        logger.info("Safety signal analysis: %s → %s", compound_name, result["overall_signal_status"])
        return json.dumps(result, indent=2)

    @classmethod
    def as_tool_definition(cls) -> dict[str, Any]:
        return {"name": cls.NAME, "description": cls.DESCRIPTION, "input_schema": cls.INPUT_SCHEMA}
