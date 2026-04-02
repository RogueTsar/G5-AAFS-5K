"""Distress event backtesting suite.

Tests that the guardrails framework correctly handles historical
distress events with known outcomes. Uses pre-cached data for
offline testing.
"""

import json
import pytest
from pathlib import Path

from src.guardrails.output_enforcer import enforce_risk_score
from src.guardrails.hallucination_detector import check_entity_attribution
from src.guardrails.content_safety import validate_score_language_consistency

DATASETS_DIR = Path(__file__).parent.parent / "datasets"


@pytest.fixture(scope="module")
def distress_events():
    with open(DATASETS_DIR / "distress_events.json") as f:
        return json.load(f)


class TestDistressEventScoring:
    """Verify that distress event companies should score in high-risk range."""

    def test_all_events_have_required_fields(self, distress_events):
        """Each event must have required fields for backtesting."""
        required = ["company_name", "event", "event_date"]
        for event in distress_events:
            for field in required:
                assert field in event, (
                    f"Event for '{event.get('company_name', '?')}' missing '{field}'"
                )

    def test_pre_event_range_lower_than_post(self, distress_events):
        """Pre-event expected score range should be lower than post-event."""
        for event in distress_events:
            pre = event.get("pre_event_risk_expectation", [0, 50])
            post = event.get("post_event_risk_expectation", [50, 100])
            assert pre[1] <= post[1], (
                f"{event['company_name']}: pre-event max ({pre[1]}) "
                f"should be <= post-event max ({post[1]})"
            )

    def test_severe_events_expect_high_post_scores(self, distress_events):
        """All distress events should have post-event min score >= 45."""
        for event in distress_events:
            post = event.get("post_event_risk_expectation", [0, 100])
            assert post[0] >= 45, (
                f"{event['company_name']}: post-event min score ({post[0]}) "
                f"should be >= 45 for a distress event"
            )

    def test_all_events_have_signals(self, distress_events):
        """Each event should list expected risk signals."""
        for event in distress_events:
            signals = event.get("signals_that_should_appear", [])
            assert len(signals) >= 1, (
                f"{event['company_name']} missing signals_that_should_appear"
            )


class TestDistressEventRiskScoreEnforcement:
    """Test risk score enforcement for distress-like outputs."""

    def test_high_risk_score_validates(self):
        """A high risk score (like post-distress) should validate correctly."""
        output = {"score": 88, "rating": "High"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 88
        assert cleaned["rating"] == "High"
        assert len(warnings) == 0

    def test_extreme_score_clamped(self):
        """Score above 100 should be clamped."""
        output = {"score": 110, "rating": "High"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 100

    def test_negative_score_clamped(self):
        """Negative scores should be clamped to 0."""
        output = {"score": -5, "rating": "Low"}
        cleaned, warnings = enforce_risk_score(output)
        assert cleaned["score"] == 0


class TestDistressEventAttribution:
    """Test hallucination detection for distress event scenarios."""

    def test_grounded_distress_signals(self):
        """Risk signals matching source data should be grounded."""
        risks = [
            {"description": "Bank experienced a run on deposits in March 2023"},
        ]
        source_data = [
            {"snippet": "SVB experienced a bank run on deposits in March 2023, leading to FDIC takeover"},
        ]
        result = check_entity_attribution("SVB", risks, [], source_data)
        assert result["attribution_score"] >= 0.5

    def test_fabricated_distress_signals_low_score(self):
        """Completely unrelated risk signals should have low attribution."""
        risks = [
            {"description": "xkcd zzqwp discovered alien technology in Q4"},
        ]
        source_data = [
            {"snippet": "Company filed for BK7 due to fraud findings"},
        ]
        result = check_entity_attribution("TestCo", risks, [], source_data)
        assert result["attribution_score"] < 0.5


class TestDistressScoreLanguageConsistency:
    """Ensure score-language consistency for distress event reports."""

    def test_high_risk_with_negative_language_consistent(self):
        """High risk score with negative report language should be consistent."""
        score = {"rating": "High", "score": 85}
        report = (
            "The company faces significant risk of default with declining revenue "
            "and deteriorating debt metrics. Loss provisions have increased."
        )
        warnings = validate_score_language_consistency(score, report)
        assert len(warnings) == 0  # Consistent: high risk + negative language
