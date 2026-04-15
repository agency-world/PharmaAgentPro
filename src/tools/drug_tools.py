"""Drug discovery and compound analysis tools for Claude function calling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("tools.drug")


def _load_compounds() -> list[dict[str, Any]]:
    """Load the compound library dataset."""
    path = Path(__file__).parent.parent / "datasets" / "drugs_compound_library.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class DrugLookupTool:
    """Tool: Search and retrieve compound data from the drug library."""

    NAME = "drug_lookup"
    DESCRIPTION = (
        "Search the pharmaceutical compound library by name, compound ID, drug class, "
        "target, indication, or phase. Returns detailed compound profiles including "
        "molecular properties, pharmacokinetics, and development status."
    )
    INPUT_SCHEMA = {
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
                "default": "any",
            },
        },
        "required": ["query"],
    }

    @staticmethod
    def execute(query: str, field: str = "any") -> str:
        """Execute the drug lookup tool."""
        compounds = _load_compounds()
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for compound in compounds:
            if field == "any":
                searchable = json.dumps(compound).lower()
                if query_lower in searchable:
                    results.append(compound)
            else:
                value = str(compound.get(field, "")).lower()
                if query_lower in value:
                    results.append(compound)

        if not results:
            return json.dumps({"status": "no_results", "message": f"No compounds found matching '{query}' in field '{field}'"})

        # Add Lipinski assessment
        for r in results:
            if r.get("lipinski_violations") is not None:
                r["lipinski_compliant"] = r["lipinski_violations"] == 0
                r["drug_likeness"] = "Good" if r["lipinski_violations"] == 0 else f"Marginal ({r['lipinski_violations']} violation(s))"

        logger.info("Drug lookup: query='%s', field='%s', results=%d", query, field, len(results))
        return json.dumps({"status": "success", "count": len(results), "compounds": results}, indent=2, default=str)

    @classmethod
    def as_tool_definition(cls) -> dict[str, Any]:
        """Return the tool definition for Claude API."""
        return {
            "name": cls.NAME,
            "description": cls.DESCRIPTION,
            "input_schema": cls.INPUT_SCHEMA,
        }


class DrugInteractionTool:
    """Tool: Check potential drug-drug interactions based on CYP enzyme profiles."""

    NAME = "drug_interaction_check"
    DESCRIPTION = (
        "Check for potential drug-drug interactions between two or more compounds "
        "based on their CYP enzyme inhibition and substrate profiles. "
        "Returns interaction risk level and clinical recommendations."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "compound_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of compound names to check for interactions",
                "minItems": 2,
            },
        },
        "required": ["compound_names"],
    }

    @staticmethod
    def execute(compound_names: list[str]) -> str:
        """Check CYP-mediated drug-drug interactions."""
        compounds = _load_compounds()
        name_lower = {c["name"].lower(): c for c in compounds}

        found: list[dict[str, Any]] = []
        not_found: list[str] = []
        for name in compound_names:
            c = name_lower.get(name.lower())
            if c:
                found.append(c)
            else:
                not_found.append(name)

        if not_found:
            return json.dumps({
                "status": "partial",
                "message": f"Compounds not found in library: {', '.join(not_found)}",
                "found": [c["name"] for c in found],
            })

        # Analyze CYP interactions
        interactions: list[dict[str, str]] = []
        for i, c1 in enumerate(found):
            for c2 in found[i + 1:]:
                cyp1 = c1.get("cyp_interactions", [])
                cyp2 = c2.get("cyp_interactions", [])

                for interaction1 in cyp1:
                    enzyme1 = interaction1.split()[0]
                    role1 = " ".join(interaction1.split()[1:])
                    for interaction2 in cyp2:
                        enzyme2 = interaction2.split()[0]
                        role2 = " ".join(interaction2.split()[1:])

                        if enzyme1 == enzyme2:
                            # Substrate + inhibitor = potential interaction
                            risk = "LOW"
                            if "substrate" in role1 and "inhibitor" in role2:
                                risk = "MODERATE" if "weak" in role2 else "HIGH"
                            elif "substrate" in role2 and "inhibitor" in role1:
                                risk = "MODERATE" if "weak" in role1 else "HIGH"
                            elif "substrate" in role1 and "substrate" in role2:
                                risk = "LOW"

                            if risk != "LOW":
                                interactions.append({
                                    "compound_a": c1["name"],
                                    "compound_b": c2["name"],
                                    "enzyme": enzyme1,
                                    "mechanism": f"{c1['name']} ({interaction1}) + {c2['name']} ({interaction2})",
                                    "risk_level": risk,
                                    "recommendation": (
                                        "Monitor closely and consider dose adjustment"
                                        if risk == "MODERATE"
                                        else "Avoid co-administration or use alternative agent"
                                    ),
                                })

        result = {
            "status": "success",
            "compounds_checked": [c["name"] for c in found],
            "interaction_count": len(interactions),
            "interactions": interactions,
            "overall_risk": (
                "HIGH" if any(i["risk_level"] == "HIGH" for i in interactions)
                else "MODERATE" if interactions
                else "LOW"
            ),
        }

        logger.info("Drug interaction check: %s → %d interactions found",
                     ", ".join(compound_names), len(interactions))
        return json.dumps(result, indent=2)

    @classmethod
    def as_tool_definition(cls) -> dict[str, Any]:
        return {
            "name": cls.NAME,
            "description": cls.DESCRIPTION,
            "input_schema": cls.INPUT_SCHEMA,
        }
