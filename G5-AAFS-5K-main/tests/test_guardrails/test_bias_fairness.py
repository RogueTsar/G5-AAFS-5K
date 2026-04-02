"""Tests for bias_fairness guardrail module."""

import pytest
from src.guardrails.bias_fairness import (
    detect_proxy_variables,
    filter_protected_class_references,
    generate_fairness_disclaimer,
    check_mas_feat_compliance,
    check_eu_ai_act_compliance,
)


class TestDetectProxyVariables:
    def test_no_bias_terms(self):
        text = "Company has strong revenue growth and diversified product portfolio."
        found = detect_proxy_variables(text)
        assert len(found) == 0

    def test_detects_racial_term(self):
        text = "The company primarily serves the African American community."
        found = detect_proxy_variables(text)
        terms = [f["term"] for f in found]
        assert "african american" in terms

    def test_detects_gender_term(self):
        text = "Most employees are female workers in the manufacturing sector."
        found = detect_proxy_variables(text)
        terms = [f["term"] for f in found]
        assert "female" in terms

    def test_detects_geographic_proxy(self):
        text = "Located in an inner city area with high zip code risk."
        found = detect_proxy_variables(text)
        categories = [f["category"] for f in found]
        assert "geographic_proxy" in categories

    def test_severity_classification(self):
        text = "The racial demographics affect the marital status distribution."
        found = detect_proxy_variables(text)
        severities = {f["term"]: f["severity"] for f in found}
        assert severities.get("racial") == "high"
        assert severities.get("marital status") == "low"

    def test_word_boundary_matching(self):
        # "age" should not match inside "manage" or "average"
        text = "The company manages average performance."
        found = detect_proxy_variables(text)
        terms = [f["term"] for f in found]
        assert "age" not in terms


class TestFilterProtectedClassReferences:
    def test_clean_items_kept(self):
        risks = [{"description": "High debt-to-equity ratio"}]
        strengths = [{"description": "Strong market position"}]
        cr, cs, log = filter_protected_class_references(risks, strengths)
        assert len(cr) == 1
        assert len(cs) == 1
        assert len(log) == 0

    def test_biased_risk_removed(self):
        risks = [
            {"description": "Risk due to predominantly Hispanic workforce"},
            {"description": "Revenue declining"},
        ]
        cr, cs, log = filter_protected_class_references(risks, [])
        assert len(cr) == 1
        assert cr[0]["description"] == "Revenue declining"
        assert len(log) == 1


class TestGenerateFairnessDisclaimer:
    def test_disclaimer_contains_mas_feat(self):
        disclaimer = generate_fairness_disclaimer()
        assert "MAS" in disclaimer
        assert "FEAT" in disclaimer

    def test_disclaimer_contains_eu_ai_act(self):
        disclaimer = generate_fairness_disclaimer()
        assert "EU" in disclaimer
        assert "AI Act" in disclaimer


class TestCheckMasFeatCompliance:
    def test_compliant_report(self):
        report = (
            "This AI system assessment is based on data sourced from publicly "
            "available financial filings. The methodology uses NLP and machine "
            "learning for risk extraction. This report should be reviewed by a "
            "qualified credit analyst with human oversight."
        )
        result = check_mas_feat_compliance(report)
        assert result["fairness"] is True
        assert result["ethics"] is True
        assert result["accountability"] is True
        assert result["transparency"] is True

    def test_non_compliant_report(self):
        report = "Company looks risky."
        result = check_mas_feat_compliance(report)
        assert result["ethics"] is False
        assert result["accountability"] is False
        assert result["transparency"] is False


class TestCheckEuAiActCompliance:
    def test_compliant_report(self):
        report = (
            "This AI system report uses data sourced from SEC filings. "
            "Human oversight is recommended before any credit decision."
        )
        result = check_eu_ai_act_compliance(report)
        assert result["human_oversight"] is True
        assert result["data_provenance"] is True
        assert result["transparency_statement"] is True

    def test_bias_flagged(self):
        report = "The company's racial profile and ethnic demographics suggest risk."
        result = check_eu_ai_act_compliance(report)
        assert result["no_protected_terms"] is False
