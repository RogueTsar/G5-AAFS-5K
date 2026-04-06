"""
Confidence Agent — computes a confidence interval for the risk score
using both quantitative metrics (coverage, entropy, agreement, tier ratio)
and an LLM-powered qualitative assessment of data quality.
"""

import math
import json
from typing import Dict, Any, List
from collections import Counter
from datetime import datetime, timezone

from src.core.state import AgentState
from src.core.llm import get_llm, sanitize_for_prompt, extract_json_from_llm
from src.core.logger import log_agent_action

AGENT_NAME = "confidence_agent"

# Data source fields to check for coverage
DATA_SOURCE_FIELDS = [
    "news_data",
    "social_data",
    "review_data",
    "financial_data",
    "doc_extracted_text",
]

# Weights for final confidence score
WEIGHT_COVERAGE = 0.25
WEIGHT_DIVERSITY = 0.15
WEIGHT_AGREEMENT = 0.25
WEIGHT_TIER = 0.15
WEIGHT_LLM = 0.20


def _compute_data_coverage(state: AgentState) -> float:
    """Fraction of data source fields that have non-empty data."""
    filled = 0
    for field in DATA_SOURCE_FIELDS:
        value = state.get(field)
        if value and len(value) > 0:
            filled += 1
    return filled / len(DATA_SOURCE_FIELDS)


def _compute_source_diversity(cleaned_data: List[Dict[str, Any]]) -> float:
    """Shannon entropy of source_type distribution, normalized to [0, 1]."""
    if not cleaned_data:
        return 0.0

    source_types = [item.get("source_type", "unknown") for item in cleaned_data]
    counts = Counter(source_types)
    total = len(source_types)
    num_types = len(counts)

    if num_types <= 1:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(num_types)
    if max_entropy == 0:
        return 0.0

    return entropy / max_entropy


def _compute_sentiment_agreement(cleaned_data: List[Dict[str, Any]]) -> float:
    """Fraction of items that agree with the majority FinBERT sentiment label."""
    if not cleaned_data:
        return 0.0

    labels = []
    for item in cleaned_data:
        label = item.get("finbert_label") or item.get("sentiment_label")
        if label:
            labels.append(label.lower().strip())

    if not labels:
        return 0.5  # neutral default when no sentiment data exists

    counts = Counter(labels)
    majority_count = counts.most_common(1)[0][1]
    return majority_count / len(labels)


def _compute_high_tier_ratio(cleaned_data: List[Dict[str, Any]]) -> float:
    """Fraction of items with credibility_weight >= 0.80."""
    if not cleaned_data:
        return 0.0

    high_count = sum(
        1 for item in cleaned_data
        if item.get("credibility_weight", 0.0) >= 0.80
    )
    return high_count / len(cleaned_data)


def _build_data_summary(state: AgentState, cleaned_data: List[Dict[str, Any]]) -> str:
    """Build a concise data summary for the LLM prompt (~100 tokens)."""
    company = state.get("company_name", "Unknown")

    # Source type counts
    source_types = Counter(
        item.get("source_type", "unknown") for item in cleaned_data
    )
    source_summary = ", ".join(f"{t}:{c}" for t, c in source_types.most_common(5))

    # Data freshness: find most recent and oldest dates
    dates = []
    for item in cleaned_data:
        for key in ("published_date", "date", "timestamp", "published_at"):
            d = item.get(key)
            if d and isinstance(d, str) and len(d) >= 10:
                dates.append(d[:10])
                break
    freshness = "no dates found"
    if dates:
        dates_sorted = sorted(dates)
        freshness = f"oldest={dates_sorted[0]}, newest={dates_sorted[-1]}"

    # Sentiment distribution
    sentiments = Counter()
    for item in cleaned_data:
        label = item.get("finbert_label") or item.get("sentiment_label")
        if label:
            sentiments[label.lower().strip()] += 1
    sent_summary = ", ".join(f"{k}:{v}" for k, v in sentiments.most_common(3)) or "none"

    # Missing sources
    missing = [f for f in DATA_SOURCE_FIELDS if not state.get(f)]
    missing_str = ", ".join(missing) if missing else "none"

    safe_company = sanitize_for_prompt(company, max_length=100)
    return (
        f"Company: {safe_company}\n"
        f"Sources ({len(cleaned_data)} items): {source_summary}\n"
        f"Date range: {freshness}\n"
        f"Sentiments: {sent_summary}\n"
        f"Missing data: {missing_str}"
    )


def _llm_confidence_assessment(
    state: AgentState,
    cleaned_data: List[Dict[str, Any]],
    math_score: float,
    math_level: str,
) -> Dict[str, Any]:
    """
    Call the LLM to provide a qualitative confidence assessment.
    Returns {"llm_score": float 0-1, "narrative": str} or None on failure.
    """
    llm = get_llm(temperature=0)
    if not llm:
        log_agent_action(AGENT_NAME, "LLM not available, skipping qualitative assessment")
        return None

    data_summary = _build_data_summary(state, cleaned_data)

    prompt = (
        "You are a due-diligence data quality auditor. Given the data summary below, "
        "assess confidence in the risk assessment on a 0.0-1.0 scale.\n\n"
        f"Math-based confidence: {math_score:.2f} ({math_level})\n\n"
        f"{data_summary}\n\n"
        "Respond in EXACTLY this JSON format, nothing else:\n"
        '{"score": <float 0.0-1.0>, "narrative": "<2-3 sentences: data freshness, '
        'contradictions, gaps, reliability concerns>"}'
    )

    log_agent_action(AGENT_NAME, "Calling LLM for qualitative confidence assessment")

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        content = extract_json_from_llm(content)
        parsed = json.loads(content)
        llm_score = float(parsed.get("score", math_score))
        llm_score = min(1.0, max(0.0, llm_score))
        narrative = str(parsed.get("narrative", ""))

        log_agent_action(AGENT_NAME, f"LLM confidence assessment: {llm_score:.3f}", {
            "llm_score": llm_score,
            "narrative": narrative[:200],
        })

        return {"llm_score": llm_score, "narrative": narrative}

    except Exception as e:
        log_agent_action(AGENT_NAME, f"LLM confidence call failed: {str(e)}")
        return None


def confidence_agent(state: AgentState) -> Dict[str, Any]:
    """
    Calculate confidence interval for the risk score using quantitative
    metrics as anchors and an LLM call for qualitative data-quality reasoning.
    Falls back to math-only if the LLM is unavailable.
    """
    cleaned_data = state.get("cleaned_data", [])
    risk_score = state.get("risk_score", {})

    # --- Quantitative components (always computed) ---
    data_coverage = _compute_data_coverage(state)
    source_diversity = _compute_source_diversity(cleaned_data)
    sentiment_agreement = _compute_sentiment_agreement(cleaned_data)
    high_tier_ratio = _compute_high_tier_ratio(cleaned_data)

    # Math-only baseline (used for LLM context and as fallback)
    math_score = (
        WEIGHT_COVERAGE * data_coverage
        + WEIGHT_DIVERSITY * source_diversity
        + WEIGHT_AGREEMENT * sentiment_agreement
        + WEIGHT_TIER * high_tier_ratio
    ) / (1.0 - WEIGHT_LLM)  # normalize to 0-1 across the non-LLM weights
    math_score = round(min(1.0, max(0.0, math_score)), 3)

    if math_score >= 0.7:
        math_level = "High"
    elif math_score >= 0.4:
        math_level = "Medium"
    else:
        math_level = "Low"

    # --- LLM qualitative assessment ---
    llm_result = _llm_confidence_assessment(state, cleaned_data, math_score, math_level)

    if llm_result:
        llm_score = llm_result["llm_score"]
        narrative = llm_result["narrative"]

        # Blend: math anchors (80%) + LLM qualitative (20%)
        confidence_score = round(
            (1.0 - WEIGHT_LLM) * math_score + WEIGHT_LLM * llm_score, 3
        )
    else:
        # Fallback: math-only
        confidence_score = math_score
        narrative = "Confidence assessed using quantitative metrics only (LLM unavailable)."

    confidence_score = round(min(1.0, max(0.0, confidence_score)), 3)

    if confidence_score >= 0.7:
        level = "High"
    elif confidence_score >= 0.4:
        level = "Medium"
    else:
        level = "Low"

    breakdown = {
        "data_coverage": round(data_coverage, 3),
        "source_diversity": round(source_diversity, 3),
        "sentiment_agreement": round(sentiment_agreement, 3),
        "high_tier_ratio": round(high_tier_ratio, 3),
        "llm_qualitative": round(llm_result["llm_score"], 3) if llm_result else None,
        "math_baseline": math_score,
    }

    log_agent_action(AGENT_NAME, f"Confidence assessment: {level} ({confidence_score})", {
        "confidence_score": confidence_score,
        "confidence_level": level,
        "breakdown": breakdown,
        "llm_used": llm_result is not None,
    })

    updated_risk_score = {
        **risk_score,
        "confidence_level": level,
        "confidence_score": confidence_score,
        "confidence_breakdown": breakdown,
        "confidence_narrative": narrative,
    }

    return {"risk_score": updated_risk_score}
