"""Synthetic company evaluation suite.

Tests that the guardrails and scoring modules produce expected outputs
for 30 synthetic companies across 5 categories. Uses pre-cached mock
data for offline testing; live mode available via --live flag.
"""

import json
import pytest
from pathlib import Path

from src.guardrails.output_enforcer import enforce_risk_score, enforce_risk_extraction
from src.guardrails.hallucination_detector import check_entity_attribution
from src.guardrails.bias_fairness import detect_proxy_variables
from src.guardrails.cascade_guard import validate_agent_output

DATASETS_DIR = Path(__file__).parent.parent / "datasets"


@pytest.fixture(scope="module")
def companies():
    with open(DATASETS_DIR / "synthetic_companies.json") as f:
        return json.load(f)


def _get_company_by_name(companies, name):
    for c in companies:
        if name.lower() in c.get("company_name", "").lower():
            return c
    pytest.skip(f"Company '{name}' not found in dataset")


# ── Schema Validation Tests ──────────────────────────────────────────────────

class TestSchemaConformance:
    """Test that pipeline outputs conform to expected schemas."""

    def test_risk_score_schema_valid_output(self):
        """A well-formed risk score should pass validation with no warnings."""
        output = {"score": 72, "max": 100, "rating": "High"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 72
        assert cleaned["rating"] == "High"
        assert len(warnings) == 0

    def test_risk_extraction_schema_valid(self):
        """Valid risk/strength items should pass extraction validation."""
        output = {
            "risks": [
                {"type": "Traditional Risk", "description": "High leverage ratio"},
                {"type": "Non-traditional Risk", "description": "Negative news sentiment"},
            ],
            "strengths": [
                {"type": "Financial Strength", "description": "Strong cash position"},
            ],
        }
        cleaned, warnings = enforce_risk_extraction(output)
        assert len(cleaned["risks"]) == 2
        assert len(cleaned["strengths"]) == 1
        assert len(warnings) == 0

    @pytest.mark.parametrize("score,expected_rating", [
        (10, "Low"), (25, "Low"), (33, "Low"),
        (34, "Medium"), (50, "Medium"), (66, "Medium"),
        (67, "High"), (85, "High"), (100, "High"),
    ])
    def test_score_rating_consistency(self, score, expected_rating):
        """Score-rating mapping must be consistent."""
        output = {"score": score, "rating": "Invalid"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["rating"] == expected_rating


# ── Known Default Tests ──────────────────────────────────────────────────────

class TestKnownDefaults:
    """Companies that defaulted should trigger high risk indicators."""

    @pytest.mark.parametrize("company_name", [
        "Silicon Valley Bank", "Evergrande", "FTX",
        "Wirecard", "Lehman",
    ])
    def test_default_company_score_expected_high(self, companies, company_name):
        """Known defaults should have expected_rating of High."""
        company = _get_company_by_name(companies, company_name)
        assert company["expected_rating"] == "High"
        risk_range = company.get("expected_risk_range", [0, 100])
        assert risk_range[0] >= 60

    def test_default_companies_have_risk_signals(self, companies):
        """Each default company should have key risk signals defined."""
        defaults = [c for c in companies if c.get("category") == "known_default"]
        for company in defaults:
            signals = company.get("key_risk_signals", [])
            assert len(signals) >= 1, (
                f"{company['company_name']} missing key_risk_signals"
            )


# ── Healthy Company Tests ────────────────────────────────────────────────────

class TestHealthyCompanies:
    """Healthy large-cap companies should have low risk indicators."""

    @pytest.mark.parametrize("company_name", [
        "Apple", "Microsoft", "Johnson",
    ])
    def test_healthy_company_expected_low(self, companies, company_name):
        """Healthy companies should have expected_rating of Low."""
        company = _get_company_by_name(companies, company_name)
        assert company["expected_rating"] == "Low"
        risk_range = company.get("expected_risk_range", [0, 100])
        assert risk_range[1] <= 40


# ── Bias Check Across Companies ──────────────────────────────────────────────

class TestBiasAcrossCompanies:
    """No company description should contain protected class terms."""

    def test_no_protected_terms_in_signals(self, companies):
        for company in companies:
            text = " ".join(
                company.get("key_risk_signals", [])
                + company.get("key_strength_signals", [])
            )
            found = detect_proxy_variables(text)
            assert len(found) == 0, (
                f"{company['company_name']} has protected terms: "
                f"{[f['term'] for f in found]}"
            )


# ── Cascade Guard Integration ────────────────────────────────────────────────

class TestCascadeGuardIntegration:
    """Test that cascade guard handles various agent output shapes."""

    def test_empty_news_agent_output(self):
        output = {"news_data": []}
        validated, warnings = validate_agent_output("news", output, {})
        assert isinstance(validated["news_data"], list)

    def test_missing_risk_scoring_keys(self):
        output = {}
        validated, warnings = validate_agent_output("risk_scoring", output, {})
        assert "risk_score" in validated
        assert validated["risk_score"]["score"] == 50  # fallback
        assert validated["risk_score"]["rating"] == "Medium"

    def test_malformed_output_gets_fallback(self):
        validated, warnings = validate_agent_output("news", "not a dict", {})
        assert isinstance(validated, dict)
        assert "news_data" in validated
