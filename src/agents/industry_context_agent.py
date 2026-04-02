"""
Industry Context Agent — infers the company's industry and computes
an industry outlook score. Reuses keyword-based inference logic from
social_scraper_mcp/industry.py, adapted for LangGraph integration.

Prefers using already-collected data from state; falls back to Tavily
search if available. Uses 0 LLM tokens.
"""

import re
import os
from typing import Dict, Any, List, Tuple
from src.core.state import AgentState
from src.core.logger import log_agent_action

AGENT_NAME = "industry_context_agent"
CURRENT_YEAR = 2026

# ---- Industry keyword mappings (from social_scraper_mcp/industry.py) ----

INDUSTRY_KEYWORDS = {
    "energy & utilities": [
        "energy", "power", "utilities", "renewable", "solar", "wind", "electricity",
        "grid", "gas", "utility", "energy transition",
    ],
    "banking & financial services": [
        "bank", "banking", "financial services", "payments", "insurance",
        "lending", "wealth", "asset management", "credit", "fintech",
    ],
    "technology": [
        "software", "technology", "cloud", "saas", "ai", "artificial intelligence",
        "platform", "semiconductor", "cybersecurity", "data center",
    ],
    "real estate & property": [
        "real estate", "property", "reit", "commercial property", "residential",
        "developer", "asset enhancement", "office leasing",
    ],
    "transport & logistics": [
        "logistics", "shipping", "transport", "fleet", "delivery", "freight",
        "mobility", "ride-hailing", "supply chain",
    ],
    "consumer & retail": [
        "retail", "consumer", "e-commerce", "fmcg", "shopping", "store",
        "brand", "food delivery", "marketplace",
    ],
    "healthcare": [
        "healthcare", "hospital", "medical", "pharma", "biotech", "clinic",
        "health services", "diagnostics",
    ],
    "telecommunications": [
        "telecom", "telecommunications", "mobile network", "broadband", "5g",
        "connectivity", "carrier",
    ],
    "industrial & manufacturing": [
        "manufacturing", "industrial", "factory", "engineering", "equipment",
        "precision engineering", "production", "automation",
    ],
    "hospitality & travel": [
        "travel", "hospitality", "hotel", "tourism", "airline", "booking",
        "resort", "leisure",
    ],
}

OUTLOOK_POSITIVE_KEYWORDS = [
    "growth", "expansion", "strong demand", "tailwinds", "investment",
    "adoption", "digitalization", "recovery", "upside", "opportunity",
    "resilient", "capacity addition", "market share gains", "favorable demand",
]

OUTLOOK_NEGATIVE_KEYWORDS = [
    "headwinds", "slowdown", "inflation", "margin pressure", "competition",
    "regulation", "oversupply", "volatility", "geopolitical", "weak demand",
    "cost pressure", "downturn", "recession", "tightening", "uncertainty",
]

POSITIVE_WEIGHTS = {
    "growth": 1.5, "expansion": 1.3, "strong demand": 1.8, "tailwinds": 1.3,
    "investment": 1.2, "adoption": 1.1, "digitalization": 1.1, "recovery": 1.2,
    "upside": 1.0, "opportunity": 1.0, "resilient": 1.4,
    "capacity addition": 1.0, "market share gains": 1.4, "favorable demand": 1.6,
}

NEGATIVE_WEIGHTS = {
    "headwinds": 1.2, "slowdown": 1.5, "inflation": 1.1, "margin pressure": 1.6,
    "competition": 1.1, "regulation": 1.3, "oversupply": 1.5, "volatility": 1.3,
    "geopolitical": 1.2, "weak demand": 1.8, "cost pressure": 1.5,
    "downturn": 1.8, "recession": 2.0, "tightening": 1.2, "uncertainty": 1.1,
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _build_text_blob(items: List[Dict[str, Any]]) -> str:
    """Concatenate title/snippet/text fields from a list of data items."""
    parts = []
    for item in items:
        parts.append(item.get("title", ""))
        parts.append(item.get("snippet", ""))
        parts.append(item.get("text", ""))
        parts.append(item.get("content", ""))
    return " ".join(parts)


def _infer_industry(text_blob: str) -> Tuple[str, float]:
    """Keyword-based industry inference. Returns (industry, confidence)."""
    text_n = _normalize(text_blob)
    scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text_n]
        scores[industry] = len(hits)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_industry, best_score = ranked[0] if ranked else ("unknown", 0)
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score == 0:
        return "unknown", 0.2

    confidence = min(0.95, 0.45 + 0.1 * best_score + 0.05 * max(0, best_score - second_score))
    return best_industry, round(confidence, 2)


def _compute_outlook(text_blob: str) -> Dict[str, Any]:
    """Compute outlook score and drivers from text evidence."""
    text_n = _normalize(text_blob)

    positive_hits = sorted(set(kw for kw in OUTLOOK_POSITIVE_KEYWORDS if kw in text_n))
    negative_hits = sorted(set(kw for kw in OUTLOOK_NEGATIVE_KEYWORDS if kw in text_n))

    pos_weight = sum(POSITIVE_WEIGHTS.get(k, 1.0) for k in positive_hits)
    neg_weight = sum(NEGATIVE_WEIGHTS.get(k, 1.0) for k in negative_hits)
    total_weight = pos_weight + neg_weight

    if total_weight == 0:
        return {
            "outlook_score": 0.5,
            "outlook_rating": "Neutral",
            "positive_drivers": [],
            "negative_drivers": [],
        }

    score = pos_weight / total_weight
    score = max(0.0, min(1.0, round(score, 2)))

    if score >= 0.65:
        rating = "Positive"
    elif score >= 0.4:
        rating = "Neutral"
    else:
        rating = "Negative"

    return {
        "outlook_score": score,
        "outlook_rating": rating,
        "positive_drivers": positive_hits,
        "negative_drivers": negative_hits,
    }


def _try_tavily_search(company_name: str) -> List[Dict[str, Any]]:
    """Attempt Tavily search for company context. Returns empty list on failure."""
    try:
        from tavily import TavilyClient
    except ImportError:
        return []

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=f'"{company_name}" business overview industry {CURRENT_YEAR}',
            search_depth="basic",
            max_results=5,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
            })
        return results
    except Exception:
        return []


def industry_context_agent(state: AgentState) -> Dict[str, Any]:
    """Infer company industry and compute industry outlook from available data."""
    company_name = state.get("company_name", "unknown")

    # Gather text from all available state data
    all_items = []
    for field in ["news_data", "social_data", "review_data", "financial_data",
                   "cleaned_data", "doc_extracted_text"]:
        data = state.get(field)
        if data and isinstance(data, list):
            all_items.extend(data)

    text_blob = _build_text_blob(all_items)

    # If insufficient state data, try Tavily as supplementary source
    if len(text_blob.strip()) < 100:
        log_agent_action(AGENT_NAME, "Insufficient state data, attempting Tavily search")
        tavily_results = _try_tavily_search(company_name)
        if tavily_results:
            text_blob += " " + _build_text_blob(tavily_results)
            log_agent_action(AGENT_NAME, f"Tavily returned {len(tavily_results)} results")

    inferred_industry, industry_confidence = _infer_industry(text_blob)
    outlook = _compute_outlook(text_blob)

    result = {
        "inferred_industry": inferred_industry,
        "industry_confidence": industry_confidence,
        "outlook_score": outlook["outlook_score"],
        "outlook_rating": outlook["outlook_rating"],
        "positive_drivers": outlook["positive_drivers"],
        "negative_drivers": outlook["negative_drivers"],
    }

    log_agent_action(AGENT_NAME, f"Industry: {inferred_industry} (conf={industry_confidence})", {
        "industry": inferred_industry,
        "confidence": industry_confidence,
        "outlook_rating": outlook["outlook_rating"],
        "outlook_score": outlook["outlook_score"],
        "positive_count": len(outlook["positive_drivers"]),
        "negative_count": len(outlook["negative_drivers"]),
    })

    return {"industry_context": result}
