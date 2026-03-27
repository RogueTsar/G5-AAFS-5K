"""Tests for hallucination_detector guardrail module."""

import pytest
from src.guardrails.hallucination_detector import (
    check_entity_attribution,
    verify_company_in_output,
    flag_fabricated_metrics,
)


class TestCheckEntityAttribution:
    def test_grounded_risks_score_high(self):
        risks = [
            {"description": "Company faces debt concerns due to rising interest rates"},
        ]
        strengths = [
            {"description": "Strong quarterly revenue growth reported"},
        ]
        source_data = [
            {"title": "Company faces debt concerns due to rising interest rates"},
            {"snippet": "Strong quarterly revenue growth reported by analysts"},
        ]
        result = check_entity_attribution("TestCo", risks, strengths, source_data)
        assert result["attribution_score"] >= 0.5
        assert len(result["grounded_risks"]) == 1
        assert len(result["ungrounded_risks"]) == 0

    def test_ungrounded_risks_score_low(self):
        risks = [
            {"description": "Xyz qwp zzt alien invasion threatens supply chain"},
        ]
        strengths = []
        source_data = [
            {"title": "BQ7 stable quarterly earnings"},
        ]
        result = check_entity_attribution("TestCo", risks, strengths, source_data)
        assert result["attribution_score"] < 0.5
        assert len(result["ungrounded_risks"]) == 1

    def test_no_sources_scores_zero(self):
        risks = [{"description": "Some risk"}]
        result = check_entity_attribution("TestCo", risks, [], [])
        assert result["attribution_score"] == 0.0

    def test_empty_risks_scores_perfect(self):
        result = check_entity_attribution("TestCo", [], [], [{"text": "data"}])
        assert result["attribution_score"] == 1.0

    def test_mixed_grounding(self):
        risks = [
            {"description": "Revenue declined sharply in Q4"},
            {"description": "CEO spotted riding unicorn to work"},
        ]
        source_data = [
            {"snippet": "Revenue declined sharply in Q4 2025"},
        ]
        result = check_entity_attribution("TestCo", risks, [], source_data)
        assert result["attribution_score"] == 0.5
        assert len(result["grounded_risks"]) == 1
        assert len(result["ungrounded_risks"]) == 1


class TestVerifyCompanyInOutput:
    def test_company_found(self):
        found, warnings = verify_company_in_output(
            "Apple Inc", "This report covers Apple Inc and its subsidiaries."
        )
        assert found is True
        assert len(warnings) == 0

    def test_company_not_found(self):
        found, warnings = verify_company_in_output(
            "Apple Inc", "This report covers Microsoft Corporation."
        )
        assert found is False
        assert len(warnings) == 1

    def test_alias_found(self):
        found, warnings = verify_company_in_output(
            "Alphabet Inc", "Google reported strong cloud growth.",
            aliases=["Google", "GOOGL"]
        )
        assert found is True

    def test_case_insensitive(self):
        found, warnings = verify_company_in_output(
            "TESLA", "tesla motors reported record deliveries."
        )
        assert found is True


class TestFlagFabricatedMetrics:
    def test_known_value_not_flagged(self):
        report = "Revenue was $395 billion in 2025."
        financial_data = [{"metric": "revenue", "value": 395}]
        flagged = flag_fabricated_metrics(report, financial_data)
        # 395 is known, so it shouldn't be flagged
        known_flagged = [f for f in flagged if "395" in f]
        assert len(known_flagged) == 0

    def test_unknown_value_flagged(self):
        report = "The company reported revenue of $999 billion."
        financial_data = [{"metric": "revenue", "value": 100}]
        flagged = flag_fabricated_metrics(report, financial_data)
        assert len(flagged) > 0

    def test_empty_financial_data(self):
        report = "Revenue was $100 million."
        flagged = flag_fabricated_metrics(report, [])
        # With no known values, everything could be flagged
        assert isinstance(flagged, list)
