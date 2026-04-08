"""LLM-as-Judge evaluation suite.

Uses the configured LLM (via OPENAI_API_KEY) to semantically evaluate
pipeline output quality. Skips gracefully if no API key is set.

Each test constructs a targeted prompt, sends it to the LLM, parses
a structured JSON response with scores, and asserts quality thresholds.
"""

import os
import json
import pytest
from pathlib import Path

from src.core.llm import get_llm, extract_json_from_llm
from langchain_core.messages import SystemMessage, HumanMessage

DATASETS_DIR = Path(__file__).parent.parent / "datasets"

# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping LLM judge tests",
)

JUDGE_SYSTEM_PROMPT = (
    "You are an expert evaluator for a credit risk assessment AI pipeline. "
    "You evaluate outputs on specific quality dimensions. "
    "Always respond with valid JSON only, no markdown fences or extra text."
)


@pytest.fixture(scope="module")
def llm():
    model = get_llm(temperature=0.0)
    if model is None:
        pytest.skip("LLM not available")
    return model


@pytest.fixture(scope="module")
def synthetic_companies():
    with open(DATASETS_DIR / "synthetic_companies.json") as f:
        return json.load(f)


def _ask_judge(llm, prompt: str) -> dict:
    """Send a prompt to the LLM judge and parse JSON response."""
    response = llm.invoke([
        SystemMessage(content=JUDGE_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    raw = extract_json_from_llm(response.content)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse LLM response", "raw": raw}


# ── Semantic Signal Matching ────────────────────────────────────────────────

class TestSemanticSignalMatching:
    """LLM judges whether extracted signals match expected signals semantically."""

    def test_paraphrased_risk_signals_match(self, llm):
        """Semantically equivalent risk signals should be judged as matching."""
        prompt = json.dumps({
            "task": "semantic_match",
            "instructions": (
                "For each expected signal, determine if any extracted signal "
                "captures the same meaning. Return JSON with: "
                "matched_count (int), total_expected (int), reasoning (str)."
            ),
            "expected_signals": [
                "High debt-to-equity ratio",
                "Declining revenue growth",
                "Management turnover concerns",
            ],
            "extracted_signals": [
                "The company's leverage is elevated with D/E exceeding 2.5x",
                "Top-line growth has decelerated over the past 3 quarters",
                "Several C-suite executives departed in the last 12 months",
            ],
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        assert result.get("matched_count", 0) >= 2, (
            f"Expected at least 2 semantic matches, got {result.get('matched_count')}"
        )

    def test_unrelated_signals_dont_match(self, llm):
        """Completely unrelated signals should not be judged as matching."""
        prompt = json.dumps({
            "task": "semantic_match",
            "instructions": (
                "For each expected signal, determine if any extracted signal "
                "captures the same meaning. Return JSON with: "
                "matched_count (int), total_expected (int), reasoning (str)."
            ),
            "expected_signals": [
                "High debt-to-equity ratio",
                "Regulatory investigation pending",
            ],
            "extracted_signals": [
                "Strong brand recognition in Asia-Pacific markets",
                "Employee satisfaction scores above industry average",
            ],
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        assert result.get("matched_count", 0) == 0, (
            f"Expected 0 matches for unrelated signals, got {result.get('matched_count')}"
        )

    def test_partial_overlap_scored_correctly(self, llm):
        """Partial signal overlap should be scored proportionally."""
        prompt = json.dumps({
            "task": "semantic_match",
            "instructions": (
                "For each expected signal, determine if any extracted signal "
                "captures the same meaning. Return JSON with: "
                "matched_count (int), total_expected (int), match_rate (float 0-1), reasoning (str)."
            ),
            "expected_signals": [
                "Supply chain disruptions",
                "Currency exchange risk",
                "Strong cash reserves",
                "Patent portfolio value",
            ],
            "extracted_signals": [
                "Logistics and supply chain vulnerabilities noted",
                "Company holds $5B in cash and equivalents",
            ],
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        matched = result.get("matched_count", 0)
        assert 1 <= matched <= 3, f"Expected 1-3 matches, got {matched}"


# ── Report Quality Judge ────────────────────────────────────────────────────

class TestReportQualityJudge:
    """LLM judges report quality along multiple dimensions."""

    SAMPLE_REPORT = (
        "# Credit Risk Assessment: Acme Corp\n\n"
        "## Executive Summary\n"
        "Acme Corp presents a moderate risk profile with a score of 55/100. "
        "The company shows stable revenue of $2.1B but faces headwinds from "
        "increasing competition in the widget market.\n\n"
        "## Key Risks\n"
        "1. **Market concentration**: 70% revenue from single product line\n"
        "2. **Debt maturity**: $500M bond maturing in 2025\n"
        "3. **Management**: CFO departure in Q3 2024\n\n"
        "## Key Strengths\n"
        "1. **Cash position**: $800M in liquid assets\n"
        "2. **Market share**: #2 in North American widget market\n\n"
        "## Methodology\n"
        "Assessment based on financial filings, news analysis, and market data. "
        "Sources include SEC filings, Reuters, and Bloomberg.\n\n"
        "*This report is AI-generated and should be reviewed by a qualified analyst.*"
    )

    def test_report_coherence(self, llm):
        """Report should be rated as coherent (>= 3/5)."""
        prompt = json.dumps({
            "task": "evaluate_report",
            "dimension": "coherence",
            "instructions": (
                "Rate this credit risk report's coherence on a 1-5 scale. "
                "1=incoherent, 5=perfectly structured. "
                "Return JSON: {score: int, reasoning: str}"
            ),
            "report": self.SAMPLE_REPORT,
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        assert result.get("score", 0) >= 3, (
            f"Coherence {result.get('score')}/5 below threshold. "
            f"Reason: {result.get('reasoning')}"
        )

    def test_report_completeness(self, llm):
        """Report should cover required sections (>= 3/5)."""
        prompt = json.dumps({
            "task": "evaluate_report",
            "dimension": "completeness",
            "instructions": (
                "Rate this credit risk report's completeness on a 1-5 scale. "
                "Required sections: executive summary, risks, strengths, methodology. "
                "Return JSON: {score: int, missing_sections: list, reasoning: str}"
            ),
            "report": self.SAMPLE_REPORT,
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        assert result.get("score", 0) >= 3, (
            f"Completeness {result.get('score')}/5 below threshold. "
            f"Missing: {result.get('missing_sections')}"
        )

    def test_report_factual_consistency(self, llm):
        """Claims in report should be internally consistent (>= 3/5)."""
        prompt = json.dumps({
            "task": "evaluate_report",
            "dimension": "internal_consistency",
            "instructions": (
                "Check this report for internal contradictions. Rate 1-5. "
                "1=major contradictions, 5=fully consistent. "
                "Return JSON: {score: int, contradictions: list, reasoning: str}"
            ),
            "report": self.SAMPLE_REPORT,
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        assert result.get("score", 0) >= 3


# ── Explanation Quality Judge ───────────────────────────────────────────────

class TestExplanationQualityJudge:
    """LLM evaluates quality of risk explanations."""

    def test_explanation_specificity(self, llm):
        """Explanations should be specific, not vague (>= 3/5)."""
        explanations = [
            "Revenue concentration risk: 70% of $2.1B revenue comes from the Widget Pro "
            "product line. A 10% decline in widget demand would reduce EBITDA by ~$147M.",
            "Liquidity strength: $800M cash reserves provide 18 months of runway at "
            "current burn rate, exceeding the industry median of 12 months.",
        ]
        prompt = json.dumps({
            "task": "evaluate_explanations",
            "dimension": "specificity",
            "instructions": (
                "Rate how specific these credit risk explanations are on 1-5. "
                "1=vague platitudes, 5=precise with numbers and context. "
                "Return JSON: {score: int, reasoning: str}"
            ),
            "explanations": explanations,
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        assert result.get("score", 0) >= 3

    def test_vague_explanations_scored_low(self, llm):
        """Vague, generic explanations should score low (<= 3/5)."""
        explanations = [
            "The company has some risks.",
            "There are some strengths.",
            "Overall the situation is mixed.",
        ]
        prompt = json.dumps({
            "task": "evaluate_explanations",
            "dimension": "specificity",
            "instructions": (
                "Rate how specific these credit risk explanations are on 1-5. "
                "1=vague platitudes, 5=precise with numbers and context. "
                "Return JSON: {score: int, reasoning: str}"
            ),
            "explanations": explanations,
        })
        result = _ask_judge(llm, prompt)
        assert "error" not in result, f"Judge failed: {result}"
        assert result.get("score", 0) <= 3, (
            f"Vague explanations scored {result.get('score')}/5, expected <= 3"
        )
