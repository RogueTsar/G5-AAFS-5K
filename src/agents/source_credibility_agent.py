"""
Source Credibility Agent — assigns credibility_weight and source_tier
to each item in cleaned_data based on source_type and URL domain matching.
Uses 0 LLM tokens; purely rule-based.
"""

from typing import Dict, Any
from src.core.state import AgentState
from src.core.logger import log_agent_action

AGENT_NAME = "source_credibility_agent"

CREDIBILITY_TIERS = {
    "tier_1_institutional": {
        "yfinance": 0.95, "sec_edgar": 0.95, "mas_filings": 0.95,
        "acra_gov_sg": 0.95, "annual_report": 0.90, "financial": 0.90,
    },
    "tier_2_reputable_media": {
        "reuters": 0.85, "bloomberg": 0.85, "ft": 0.85,
        "wsj": 0.85, "news_api": 0.80, "news": 0.80,
    },
    "tier_3_contextual": {
        "glassdoor": 0.55, "reviews": 0.50, "review": 0.50, "linkedin": 0.60,
    },
    "tier_4_low_signal": {
        "reddit": 0.35, "twitter": 0.35, "social_media": 0.40, "social": 0.40,
    },
}

# Flat lookup: source_key -> (weight, tier_name)
_SOURCE_LOOKUP: Dict[str, tuple] = {}
for tier_name, sources in CREDIBILITY_TIERS.items():
    for source_key, weight in sources.items():
        _SOURCE_LOOKUP[source_key] = (weight, tier_name)

# Domain-based matching for URL inspection
DOMAIN_TIER_MAP = {
    "sec.gov": ("tier_1_institutional", 0.95),
    "mas.gov.sg": ("tier_1_institutional", 0.95),
    "acra.gov.sg": ("tier_1_institutional", 0.95),
    "finance.yahoo.com": ("tier_1_institutional", 0.95),
    "reuters.com": ("tier_2_reputable_media", 0.85),
    "bloomberg.com": ("tier_2_reputable_media", 0.85),
    "ft.com": ("tier_2_reputable_media", 0.85),
    "wsj.com": ("tier_2_reputable_media", 0.85),
    "cnbc.com": ("tier_2_reputable_media", 0.80),
    "glassdoor.com": ("tier_3_contextual", 0.55),
    "linkedin.com": ("tier_3_contextual", 0.60),
    "reddit.com": ("tier_4_low_signal", 0.35),
    "twitter.com": ("tier_4_low_signal", 0.35),
    "x.com": ("tier_4_low_signal", 0.35),
}

DEFAULT_WEIGHT = 0.50
DEFAULT_TIER = "tier_3_contextual"


def _match_by_source_type(source_type: str):
    """Return (weight, tier) by matching source_type against known keys."""
    st = source_type.lower().strip()
    if st in _SOURCE_LOOKUP:
        return _SOURCE_LOOKUP[st]
    # Partial match: check if any known key is contained in the source_type
    for key, (weight, tier) in _SOURCE_LOOKUP.items():
        if key in st:
            return (weight, tier)
    return None


def _match_by_url(url: str):
    """Return (tier, weight) by checking URL domain against known domains."""
    url_lower = url.lower()
    for domain, (tier, weight) in DOMAIN_TIER_MAP.items():
        if domain in url_lower:
            return (weight, tier)
    return None


def source_credibility_agent(state: AgentState) -> Dict[str, Any]:
    """Annotate each cleaned_data item with credibility_weight and source_tier."""
    cleaned_data = state.get("cleaned_data", [])

    if not cleaned_data:
        log_agent_action(AGENT_NAME, "No cleaned_data to annotate")
        return {"cleaned_data": []}

    updated_data = []
    tier_counts = {}

    for item in cleaned_data:
        source_type = item.get("source_type", "")
        url = item.get("url", "")

        result = _match_by_source_type(source_type)
        if result is None:
            result = _match_by_url(url)
        if result is None:
            result = (DEFAULT_WEIGHT, DEFAULT_TIER)

        weight, tier = result

        annotated = {**item, "credibility_weight": weight, "source_tier": tier}
        updated_data.append(annotated)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    log_agent_action(AGENT_NAME, "Annotated credibility for cleaned_data", {
        "total_items": len(updated_data),
        "tier_distribution": tier_counts,
    })

    return {"cleaned_data": updated_data}
