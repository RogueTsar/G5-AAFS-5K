"""
Confidence Agent — computes a confidence interval for the risk score
based on data coverage, source diversity, sentiment agreement, and
high-tier source ratio. Uses 0 LLM tokens.
"""

import math
from typing import Dict, Any, List
from collections import Counter
from src.core.state import AgentState
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
WEIGHT_COVERAGE = 0.3
WEIGHT_DIVERSITY = 0.2
WEIGHT_AGREEMENT = 0.3
WEIGHT_TIER = 0.2


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


def confidence_agent(state: AgentState) -> Dict[str, Any]:
    """Calculate confidence interval for the risk score."""
    cleaned_data = state.get("cleaned_data", [])
    risk_score = state.get("risk_score", {})

    data_coverage = _compute_data_coverage(state)
    source_diversity = _compute_source_diversity(cleaned_data)
    sentiment_agreement = _compute_sentiment_agreement(cleaned_data)
    high_tier_ratio = _compute_high_tier_ratio(cleaned_data)

    confidence_score = (
        WEIGHT_COVERAGE * data_coverage
        + WEIGHT_DIVERSITY * source_diversity
        + WEIGHT_AGREEMENT * sentiment_agreement
        + WEIGHT_TIER * high_tier_ratio
    )
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
    }

    log_agent_action(AGENT_NAME, f"Confidence assessment: {level} ({confidence_score})", {
        "confidence_score": confidence_score,
        "confidence_level": level,
        "breakdown": breakdown,
    })

    updated_risk_score = {
        **risk_score,
        "confidence_level": level,
        "confidence_score": confidence_score,
        "confidence_breakdown": breakdown,
    }

    return {"risk_score": updated_risk_score}
