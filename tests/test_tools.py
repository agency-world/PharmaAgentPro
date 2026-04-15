"""Tests for pharma-specific tools."""

import json
import pytest

from src.tools.drug_tools import DrugLookupTool, DrugInteractionTool
from src.tools.trial_tools import TrialSearchTool, AdverseEventSearchTool, SafetySignalTool
from src.tools.document_tools import DocumentGeneratorTool


class TestDrugLookupTool:
    def test_lookup_by_name(self):
        result = json.loads(DrugLookupTool.execute("Nexavirin"))
        assert result["status"] == "success"
        assert result["count"] >= 1
        assert result["compounds"][0]["name"] == "Nexavirin"

    def test_lookup_by_id(self):
        result = json.loads(DrugLookupTool.execute("PHA-002", field="compound_id"))
        assert result["status"] == "success"
        assert result["compounds"][0]["name"] == "Oncolytin-B"

    def test_lookup_by_class(self):
        result = json.loads(DrugLookupTool.execute("Kinase Inhibitor", field="class"))
        assert result["status"] == "success"
        assert result["count"] >= 1

    def test_lookup_not_found(self):
        result = json.loads(DrugLookupTool.execute("NonexistentDrug"))
        assert result["status"] == "no_results"

    def test_lipinski_assessment(self):
        result = json.loads(DrugLookupTool.execute("Nexavirin"))
        compound = result["compounds"][0]
        assert "lipinski_compliant" in compound
        assert "drug_likeness" in compound
        assert compound["lipinski_compliant"] is True

    def test_tool_definition(self):
        defn = DrugLookupTool.as_tool_definition()
        assert defn["name"] == "drug_lookup"
        assert "input_schema" in defn


class TestDrugInteractionTool:
    def test_interaction_found(self):
        result = json.loads(DrugInteractionTool.execute(["Nexavirin", "Inflammablock"]))
        assert result["status"] == "success"
        assert "interactions" in result

    def test_compound_not_found(self):
        result = json.loads(DrugInteractionTool.execute(["Nexavirin", "FakeDrug"]))
        assert result["status"] == "partial"

    def test_no_interaction(self):
        result = json.loads(DrugInteractionTool.execute(["Immunex-340", "Cardiofix-200"]))
        assert result["status"] == "success"
        assert result["overall_risk"] == "LOW"


class TestTrialSearchTool:
    def test_search_by_compound(self):
        result = json.loads(TrialSearchTool.execute("Nexavirin"))
        assert result["status"] == "success"
        assert result["count"] >= 1

    def test_search_by_trial_id(self):
        result = json.loads(TrialSearchTool.execute("PCT-2023-0089", field="trial_id"))
        assert result["status"] == "success"

    def test_search_by_phase(self):
        result = json.loads(TrialSearchTool.execute("Phase III", field="phase"))
        assert result["status"] == "success"
        assert result["count"] >= 1

    def test_enrollment_progress(self):
        result = json.loads(TrialSearchTool.execute("Nexavirin"))
        trial = result["trials"][0]
        assert "enrollment_progress_pct" in trial

    def test_search_not_found(self):
        result = json.loads(TrialSearchTool.execute("NonexistentTrial"))
        assert result["status"] == "no_results"


class TestAdverseEventSearchTool:
    def test_search_by_compound(self):
        result = json.loads(AdverseEventSearchTool.execute(compound_name="Oncolytin-B"))
        assert result["status"] == "success"
        assert result["summary"]["total_events"] >= 1

    def test_serious_only(self):
        result = json.loads(AdverseEventSearchTool.execute(compound_name="Oncolytin-B", serious_only=True))
        assert result["status"] == "success"
        for event in result["events"]:
            assert event["serious"] is True

    def test_min_grade_filter(self):
        result = json.loads(AdverseEventSearchTool.execute(min_grade=3))
        assert result["status"] == "success"
        for event in result["events"]:
            assert event["ctcae_grade"] >= 3

    def test_summary_stats(self):
        result = json.loads(AdverseEventSearchTool.execute(compound_name="Nexavirin"))
        summary = result["summary"]
        assert "by_severity" in summary
        assert "by_soc" in summary
        assert "by_causality" in summary


class TestSafetySignalTool:
    def test_signal_analysis(self):
        result = json.loads(SafetySignalTool.execute("Oncolytin-B"))
        assert result["status"] == "success"
        assert "safety_signals" in result
        assert "overall_signal_status" in result

    def test_no_data(self):
        result = json.loads(SafetySignalTool.execute("FakeDrug"))
        assert result["status"] == "no_data"


class TestDocumentGeneratorTool:
    def test_generate_cioms(self):
        result = json.loads(DocumentGeneratorTool.execute(
            document_type="safety_report_cioms",
            compound_name="Oncolytin-B",
            additional_fields={"ae_id": "AE-2023-002298", "event_term": "ILD"},
        ))
        assert result["status"] == "success"
        assert "CONFIDENTIAL" in result["document"]
        assert "ICH E2A" in result["document"]

    def test_generate_ind_report(self):
        result = json.loads(DocumentGeneratorTool.execute(
            document_type="ind_annual_report",
            compound_name="Nexavirin",
            additional_fields={"ind_number": "IND-157832"},
        ))
        assert result["status"] == "success"
        assert "21 CFR 312.33" in result["document"]

    def test_unknown_type(self):
        result = json.loads(DocumentGeneratorTool.execute(
            document_type="invalid_type",
            compound_name="Test",
        ))
        assert result["status"] == "error"

    def test_required_fields_tracking(self):
        result = json.loads(DocumentGeneratorTool.execute(
            document_type="clinical_study_report",
            compound_name="Nexavirin",
            additional_fields={"study_id": "PCT-2024-0147", "phase": "Phase II"},
        ))
        assert result["required_fields_provided"] >= 3
