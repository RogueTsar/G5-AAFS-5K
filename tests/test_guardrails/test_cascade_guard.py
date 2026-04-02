"""Tests for cascade_guard guardrail module."""

import pytest
from src.guardrails.cascade_guard import (
    validate_agent_output,
    should_abort_pipeline,
    create_fallback_output,
)


class TestValidateAgentOutput:
    def test_valid_output_passes(self):
        output = {"news_data": [{"title": "Article"}]}
        validated, warnings = validate_agent_output("news", output, {})
        assert validated["news_data"] == [{"title": "Article"}]
        assert len(warnings) == 0

    def test_missing_key_gets_fallback(self):
        output = {}
        validated, warnings = validate_agent_output("news", output, {})
        assert validated["news_data"] is not None
        assert any("missing" in w.lower() for w in warnings)

    def test_wrong_type_gets_fallback(self):
        output = {"news_data": "not a list"}
        validated, warnings = validate_agent_output("news", output, {})
        assert isinstance(validated["news_data"], list)
        assert any("wrong type" in w.lower() for w in warnings)

    def test_empty_collection_warned(self):
        output = {"news_data": []}
        validated, warnings = validate_agent_output("news", output, {})
        assert any("empty" in w.lower() for w in warnings)

    def test_unknown_agent_skipped(self):
        output = {"data": "something"}
        validated, warnings = validate_agent_output("unknown_agent", output, {})
        assert validated == output
        assert any("unknown" in w.lower() for w in warnings)

    def test_non_dict_output_gets_fallback(self):
        validated, warnings = validate_agent_output("news", "bad output", {})
        assert isinstance(validated, dict)
        assert "news_data" in validated

    def test_risk_extraction_validates_both_keys(self):
        output = {"extracted_risks": [{"type": "Traditional Risk"}], "extracted_strengths": []}
        validated, warnings = validate_agent_output("risk_extraction", output, {})
        assert "extracted_risks" in validated
        assert "extracted_strengths" in validated

    def test_risk_scoring_validates_score(self):
        output = {"risk_score": {"score": 75, "max": 100, "rating": "High"}}
        validated, warnings = validate_agent_output("risk_scoring", output, {})
        assert validated["risk_score"]["score"] == 75
        assert validated["risk_score"]["rating"] == "High"


class TestShouldAbortPipeline:
    def test_below_threshold(self):
        assert should_abort_pipeline(["err1", "err2"], threshold=3) is False

    def test_at_threshold(self):
        assert should_abort_pipeline(["e1", "e2", "e3"], threshold=3) is True

    def test_above_threshold(self):
        assert should_abort_pipeline(["e1", "e2", "e3", "e4"], threshold=3) is True

    def test_empty_errors(self):
        assert should_abort_pipeline([], threshold=3) is False


class TestCreateFallbackOutput:
    def test_known_agent_returns_fallback(self):
        fallback = create_fallback_output("risk_scoring")
        assert fallback["risk_score"]["score"] == 50
        assert fallback["risk_score"]["rating"] == "Medium"

    def test_unknown_agent_returns_empty(self):
        fallback = create_fallback_output("nonexistent")
        assert fallback == {}

    def test_fallback_is_deep_copy(self):
        f1 = create_fallback_output("risk_extraction")
        f2 = create_fallback_output("risk_extraction")
        f1["extracted_risks"].append("mutated")
        assert len(f2["extracted_risks"]) == 0  # f2 should not be affected
