"""Tests for output_enforcer guardrail module."""

import pytest
from src.guardrails.output_enforcer import (
    enforce_risk_extraction,
    enforce_risk_score,
    enforce_explanations,
    confidence_floor_filter,
    schema_hard_stop,
)


# ── enforce_risk_extraction ──────────────────────────────────────────────────

class TestEnforceRiskExtraction:
    def test_valid_risks_pass(self):
        output = {
            "risks": [
                {"type": "Traditional Risk", "description": "High debt ratio"},
                {"type": "Non-traditional Risk", "description": "Negative social sentiment"},
            ]
        }
        cleaned, warnings = enforce_risk_extraction(output)
        assert len(cleaned["risks"]) == 2
        assert len(warnings) == 0

    def test_invalid_risk_type_removed(self):
        output = {
            "risks": [
                {"type": "Invalid Type", "description": "Something"},
                {"type": "Traditional Risk", "description": "Valid risk"},
            ]
        }
        cleaned, warnings = enforce_risk_extraction(output)
        assert len(cleaned["risks"]) == 1
        assert "invalid type" in warnings[0].lower()

    def test_empty_description_removed(self):
        output = {
            "risks": [{"type": "Traditional Risk", "description": ""}]
        }
        cleaned, warnings = enforce_risk_extraction(output)
        assert len(cleaned["risks"]) == 0
        assert len(warnings) == 1

    def test_long_description_truncated(self):
        output = {
            "risks": [{"type": "Traditional Risk", "description": "x" * 600}]
        }
        cleaned, warnings = enforce_risk_extraction(output)
        assert len(cleaned["risks"][0]["description"]) == 500
        assert "truncated" in warnings[0].lower()

    def test_valid_strengths_pass(self):
        output = {
            "strengths": [
                {"type": "Financial Strength", "description": "Strong cash flow"},
                {"type": "Market Strength", "description": "Market leader"},
            ]
        }
        cleaned, warnings = enforce_risk_extraction(output)
        assert len(cleaned["strengths"]) == 2
        assert len(warnings) == 0

    def test_invalid_strength_type_removed(self):
        output = {
            "strengths": [{"type": "Bad Type", "description": "Something"}]
        }
        cleaned, warnings = enforce_risk_extraction(output)
        assert len(cleaned["strengths"]) == 0


# ── enforce_risk_score ───────────────────────────────────────────────────────

class TestEnforceRiskScore:
    def test_valid_score_and_rating(self):
        output = {"score": 75, "rating": "High"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 75
        assert cleaned["rating"] == "High"
        assert len(warnings) == 0

    def test_score_clamped_above_100(self):
        output = {"score": 150, "rating": "High"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 100
        assert any("clamped" in w.lower() for w in warnings)

    def test_score_clamped_below_0(self):
        output = {"score": -10, "rating": "Low"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 0

    def test_missing_score_defaults_to_50(self):
        output = {"rating": "Medium"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 50

    def test_inconsistent_rating_corrected(self):
        output = {"score": 80, "rating": "Low"}  # Low should be 0-33
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["rating"] == "High"
        assert any("inconsistent" in w.lower() for w in warnings)

    def test_invalid_rating_derived_from_score(self):
        output = {"score": 20, "rating": "Invalid"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["rating"] == "Low"


# ── enforce_explanations ─────────────────────────────────────────────────────

class TestEnforceExplanations:
    def test_valid_explanations(self):
        output = {
            "explanations": [
                {"metric": "Debt Ratio", "reason": "Above industry average"},
            ]
        }
        cleaned, warnings = enforce_explanations(output)
        assert len(cleaned["explanations"]) == 1
        assert len(warnings) == 0

    def test_empty_metric_removed(self):
        output = {
            "explanations": [{"metric": "", "reason": "Some reason"}]
        }
        cleaned, warnings = enforce_explanations(output)
        # Should have placeholder since all were invalid
        assert cleaned["explanations"][0]["metric"] == "Overall Assessment"

    def test_no_explanations_gets_placeholder(self):
        output = {"explanations": []}
        cleaned, warnings = enforce_explanations(output)
        assert len(cleaned["explanations"]) == 1
        assert "placeholder" in warnings[0].lower()


# ── confidence_floor_filter ──────────────────────────────────────────────────

class TestConfidenceFloorFilter:
    def test_above_threshold_kept(self):
        items = [{"finbert_sentiment": {"score": 0.8, "label": "positive"}}]
        kept, warnings = confidence_floor_filter(items, min_confidence=0.3)
        assert len(kept) == 1
        assert len(warnings) == 0

    def test_below_threshold_removed(self):
        items = [{"finbert_sentiment": {"score": 0.1, "label": "neutral"}}]
        kept, warnings = confidence_floor_filter(items, min_confidence=0.3)
        assert len(kept) == 0
        assert len(warnings) == 1

    def test_no_sentiment_kept(self):
        items = [{"title": "No sentiment data"}]
        kept, warnings = confidence_floor_filter(items)
        assert len(kept) == 1


# ── schema_hard_stop ─────────────────────────────────────────────────────────

class TestSchemaHardStop:
    def test_all_keys_present(self):
        output = {"score": 50, "rating": "Medium", "max": 100}
        assert schema_hard_stop(output, ["score", "rating", "max"]) is True

    def test_missing_key_returns_false(self):
        output = {"score": 50}
        assert schema_hard_stop(output, ["score", "rating"]) is False

    def test_none_value_returns_false(self):
        output = {"score": None, "rating": "Low"}
        assert schema_hard_stop(output, ["score", "rating"]) is False

    def test_non_dict_returns_false(self):
        assert schema_hard_stop("not a dict", ["key"]) is False
