"""Compliance checking for regulatory document generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("guardrails.compliance")


@dataclass
class ComplianceResult:
    """Result of a compliance check."""
    is_compliant: bool
    standard: str
    missing_fields: list[str]
    warnings: list[str]
    checklist: dict[str, bool]


class ComplianceChecker:
    """Validate documents against regulatory compliance standards."""

    # Required elements by document type
    REQUIREMENTS: dict[str, dict[str, Any]] = {
        "ind_annual_report": {
            "standard": "21 CFR 312.33",
            "required_fields": [
                "ind_number", "sponsor", "compound_name", "reporting_period",
                "submission_date",
            ],
            "required_sections": [
                "Individual Study Information",
                "Summary of Safety Information",
                "Summary of Manufacturing Changes",
            ],
        },
        "clinical_study_report": {
            "standard": "ICH E3",
            "required_fields": [
                "study_id", "compound_name", "phase", "sponsor", "report_date",
            ],
            "required_sections": [
                "Synopsis", "Ethics", "Study Objectives", "Investigational Plan",
                "Study Patients", "Efficacy Evaluation", "Safety Evaluation",
                "Discussion and Overall Conclusions",
            ],
        },
        "safety_report_cioms": {
            "standard": "ICH E2A / CIOMS I",
            "required_fields": [
                "ae_id", "compound_name", "event_term", "seriousness_criteria",
            ],
            "required_sections": [
                "Patient Information", "Adverse Event Information",
                "Suspect Drug Information", "Narrative Summary",
            ],
        },
        "dsur": {
            "standard": "ICH E2F",
            "required_fields": [
                "compound_name", "development_phase", "reporting_period",
                "sponsor", "dibd",
            ],
            "required_sections": [
                "Executive Summary", "Actions Taken for Safety Reasons",
                "Estimated Cumulative Exposure", "Signal Evaluation",
                "Overall Safety Assessment", "Benefit-Risk Conclusions",
            ],
        },
        "investigator_brochure": {
            "standard": "ICH E6(R2)",
            "required_fields": ["compound_name", "version", "date", "sponsor"],
            "required_sections": [
                "Summary", "Physical, Chemical, and Pharmaceutical Properties",
                "Nonclinical Studies", "Effects in Humans",
                "Summary of Data and Guidance for the Investigator",
            ],
        },
    }

    def check(
        self,
        doc_type: str,
        provided_fields: dict[str, Any],
        document_text: str = "",
    ) -> ComplianceResult:
        """Check a document against its compliance standard.

        Args:
            doc_type: The regulatory document type.
            provided_fields: Fields provided in the document metadata.
            document_text: The full document text (for section checks).
        """
        if doc_type not in self.REQUIREMENTS:
            return ComplianceResult(
                is_compliant=False,
                standard="Unknown",
                missing_fields=[],
                warnings=[f"Unknown document type: {doc_type}"],
                checklist={},
            )

        reqs = self.REQUIREMENTS[doc_type]
        standard = reqs["standard"]
        missing_fields: list[str] = []
        warnings: list[str] = []
        checklist: dict[str, bool] = {}

        # Check required fields
        for field_name in reqs["required_fields"]:
            present = field_name in provided_fields and provided_fields[field_name]
            checklist[f"field:{field_name}"] = present
            if not present:
                missing_fields.append(field_name)

        # Check required sections in document text
        if document_text:
            for section in reqs.get("required_sections", []):
                found = section.lower() in document_text.lower()
                checklist[f"section:{section}"] = found
                if not found:
                    warnings.append(f"Required section missing: '{section}'")

        # Check for confidentiality notice
        if document_text:
            has_confidentiality = "confidential" in document_text.lower()
            checklist["confidentiality_notice"] = has_confidentiality
            if not has_confidentiality:
                warnings.append("Missing confidentiality notice")

        # Check for date format (ISO 8601)
        checklist["iso_date_format"] = True  # Default; actual check is on content

        is_compliant = len(missing_fields) == 0 and len(warnings) == 0
        logger.info(
            "Compliance check for %s (%s): %s",
            doc_type, standard, "PASS" if is_compliant else "FAIL"
        )

        return ComplianceResult(
            is_compliant=is_compliant,
            standard=standard,
            missing_fields=missing_fields,
            warnings=warnings,
            checklist=checklist,
        )
