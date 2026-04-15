"""Regulatory document generation tool for Claude function calling."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("tools.document")


def _load_templates() -> dict[str, Any]:
    path = Path(__file__).parent.parent / "datasets" / "regulatory_templates.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class DocumentGeneratorTool:
    """Tool: Generate regulatory document scaffolds with compliance metadata."""

    NAME = "generate_document"
    DESCRIPTION = (
        "Generate a regulatory document scaffold based on the specified template type. "
        "Supported types: ind_annual_report, clinical_study_report, safety_report_cioms, "
        "investigator_brochure, dsur, protocol_synopsis. Returns a structured document "
        "with all required sections, compliance headers, and placeholders."
    )
    INPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "document_type": {
                "type": "string",
                "enum": [
                    "ind_annual_report",
                    "clinical_study_report",
                    "safety_report_cioms",
                    "investigator_brochure",
                    "dsur",
                    "protocol_synopsis",
                ],
                "description": "Type of regulatory document to generate",
            },
            "compound_name": {
                "type": "string",
                "description": "Name of the compound/drug",
            },
            "additional_fields": {
                "type": "object",
                "description": "Additional fields specific to the document type (e.g., trial_id, ind_number)",
            },
        },
        "required": ["document_type", "compound_name"],
    }

    @staticmethod
    def execute(
        document_type: str,
        compound_name: str,
        additional_fields: dict[str, Any] | None = None,
    ) -> str:
        templates = _load_templates()
        template = templates.get("templates", {}).get(document_type)

        if not template:
            return json.dumps({
                "status": "error",
                "message": f"Unknown document type: {document_type}",
                "available_types": list(templates.get("templates", {}).keys()),
            })

        fields = additional_fields or {}
        fields["compound_name"] = compound_name
        now = datetime.now(timezone.utc)

        # Build document header
        doc_lines = [
            f"# {template['name']}",
            "",
            "---",
            "**CONFIDENTIAL — For Regulatory Use Only**",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Document Type | {template['name']} |",
            f"| Compliance Standard | {template['compliance_standard']} |",
            f"| Compound | {compound_name} |",
            f"| Generated Date | {now.strftime('%Y-%m-%d')} |",
            f"| Version | DRAFT v0.1 |",
            f"| Status | Pending Review |",
        ]

        # Add additional fields to header
        for key, value in fields.items():
            if key != "compound_name":
                doc_lines.append(f"| {key.replace('_', ' ').title()} | {value} |")

        doc_lines.append("")
        doc_lines.append("---")
        doc_lines.append("")

        # Required fields checklist
        doc_lines.append("## Required Fields Checklist")
        doc_lines.append("")
        for req_field in template.get("required_fields", []):
            status = "x" if req_field in fields else " "
            doc_lines.append(f"- [{status}] {req_field}: {fields.get(req_field, '*[REQUIRED — NOT PROVIDED]*')}")
        doc_lines.append("")

        # Generate sections
        doc_lines.append("---")
        doc_lines.append("")
        for i, section in enumerate(template.get("sections", []), 1):
            doc_lines.append(f"## {i}. {section}")
            doc_lines.append("")
            doc_lines.append(f"*[Content for \"{section}\" to be completed per {template['compliance_standard']}]*")
            doc_lines.append("")

        # Compliance footer
        doc_lines.extend([
            "---",
            "",
            "## Document Control",
            "",
            "| Role | Name | Date | Signature |",
            "|------|------|------|-----------|",
            "| Author | *[Name]* | *[Date]* | *[Pending]* |",
            "| Medical Reviewer | *[Name]* | *[Date]* | *[Pending]* |",
            "| Regulatory Lead | *[Name]* | *[Date]* | *[Pending]* |",
            "| Quality Assurance | *[Name]* | *[Date]* | *[Pending]* |",
            "",
            "---",
            "",
            f"*This document was generated in compliance with {template['compliance_standard']}. "
            "All content must be reviewed and approved by qualified personnel before regulatory submission.*",
        ])

        document_text = "\n".join(doc_lines)

        result = {
            "status": "success",
            "document_type": document_type,
            "compliance_standard": template["compliance_standard"],
            "compound_name": compound_name,
            "sections_count": len(template.get("sections", [])),
            "required_fields_provided": sum(1 for f in template.get("required_fields", []) if f in fields),
            "required_fields_total": len(template.get("required_fields", [])),
            "document": document_text,
        }

        logger.info("Document generated: %s for %s (%s)",
                     document_type, compound_name, template["compliance_standard"])
        return json.dumps(result, indent=2)

    @classmethod
    def as_tool_definition(cls) -> dict[str, Any]:
        return {"name": cls.NAME, "description": cls.DESCRIPTION, "input_schema": cls.INPUT_SCHEMA}
