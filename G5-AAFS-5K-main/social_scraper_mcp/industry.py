import os
import json
import asyncio
import re
import time
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import AsyncTavilyClient

load_dotenv(dotenv_path="../.env")

mcp = FastMCP("IndustryOutlookResearchAgent")
tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

CURRENT_YEAR = 2026

# -----------------------------
# Config
# -----------------------------
DEFAULT_LIMIT_PER_QUERY = 3
MAX_TOTAL_RESULTS = 10
MAX_SNIPPET_CHARS = 280
MAX_SNIPPET_SENTENCES = 4

INDUSTRY_KEYWORDS = {
    "energy & utilities": [
        "energy", "power", "utilities", "renewable", "solar", "wind", "electricity",
        "grid", "gas", "utility", "energy transition"
    ],
    "banking & financial services": [
        "bank", "banking", "financial services", "payments", "insurance",
        "lending", "wealth", "asset management", "credit", "fintech"
    ],
    "technology": [
        "software", "technology", "cloud", "saas", "ai", "artificial intelligence",
        "platform", "semiconductor", "cybersecurity", "data center"
    ],
    "real estate & property": [
        "real estate", "property", "reit", "commercial property", "residential",
        "developer", "asset enhancement", "office leasing"
    ],
    "transport & logistics": [
        "logistics", "shipping", "transport", "fleet", "delivery", "freight",
        "mobility", "ride-hailing", "supply chain"
    ],
    "consumer & retail": [
        "retail", "consumer", "e-commerce", "fmcg", "shopping", "store",
        "brand", "food delivery", "marketplace"
    ],
    "healthcare": [
        "healthcare", "hospital", "medical", "pharma", "biotech", "clinic",
        "health services", "diagnostics"
    ],
    "telecommunications": [
        "telecom", "telecommunications", "mobile network", "broadband", "5g",
        "connectivity", "carrier"
    ],
    "industrial & manufacturing": [
        "manufacturing", "industrial", "factory", "engineering", "equipment",
        "precision engineering", "production", "automation"
    ],
    "hospitality & travel": [
        "travel", "hospitality", "hotel", "tourism", "airline", "booking",
        "resort", "leisure"
    ],
}

OUTLOOK_POSITIVE_KEYWORDS = [
    "growth", "expansion", "strong demand", "tailwinds", "investment",
    "adoption", "digitalization", "recovery", "upside", "opportunity",
    "resilient", "capacity addition", "market share gains", "favorable demand"
]

OUTLOOK_NEGATIVE_KEYWORDS = [
    "headwinds", "slowdown", "inflation", "margin pressure", "competition",
    "regulation", "oversupply", "volatility", "geopolitical", "weak demand",
    "cost pressure", "downturn", "recession", "tightening", "uncertainty"
]

# Optional weights for stronger credit interpretation
POSITIVE_WEIGHTS = {
    "growth": 1.5,
    "expansion": 1.3,
    "strong demand": 1.8,
    "tailwinds": 1.3,
    "investment": 1.2,
    "adoption": 1.1,
    "digitalization": 1.1,
    "recovery": 1.2,
    "upside": 1.0,
    "opportunity": 1.0,
    "resilient": 1.4,
    "capacity addition": 1.0,
    "market share gains": 1.4,
    "favorable demand": 1.6,
}

NEGATIVE_WEIGHTS = {
    "headwinds": 1.2,
    "slowdown": 1.5,
    "inflation": 1.1,
    "margin pressure": 1.6,
    "competition": 1.1,
    "regulation": 1.3,
    "oversupply": 1.5,
    "volatility": 1.3,
    "geopolitical": 1.2,
    "weak demand": 1.8,
    "cost pressure": 1.5,
    "downturn": 1.8,
    "recession": 2.0,
    "tightening": 1.2,
    "uncertainty": 1.1,
}

# -----------------------------
# Helpers
# -----------------------------
def estimate_tokens(obj: Any) -> int:
    try:
        text = json.dumps(obj, ensure_ascii=False)
    except Exception:
        text = str(obj)
    return max(1, len(text) // 4)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def clean_and_truncate_snippet(
    text: str,
    max_sentences: int = MAX_SNIPPET_SENTENCES,
    max_chars: int = MAX_SNIPPET_CHARS
) -> str:
    if not text:
        return ""

    text = re.sub(r"<.*?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\%[A-Fa-f0-9]{2}", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    truncated = " ".join(sentences[:max_sentences])

    if len(truncated) > max_chars:
        truncated = truncated[:max_chars].rsplit(" ", 1)[0] + "..."

    return truncated.strip()


def dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for r in results:
        link = (r.get("link") or "").strip()
        if link and link not in seen:
            seen.add(link)
            unique.append(r)
    return unique


def compress_results(results: List[Dict[str, Any]], limit: int = MAX_TOTAL_RESULTS) -> List[Dict[str, Any]]:
    return [
        {
            "title": r.get("title", ""),
            "link": r.get("link", ""),
            "snippet": r.get("snippet", ""),
            "query": r.get("query", "")
        }
        for r in results[:limit]
    ]


def keyword_hits(text: str, keywords: List[str]) -> List[str]:
    text_n = normalize_text(text)
    return [kw for kw in keywords if kw in text_n]


def init_trace(company_name: str) -> Dict[str, Any]:
    return {
        "company": company_name,
        "started_at": time.time(),
        "steps": [],
        "token_usage_estimate": {
            "query_tokens": 0,
            "company_result_tokens": 0,
            "outlook_result_tokens": 0,
            "final_payload_tokens": 0
        }
    }


def log_step(trace: Dict[str, Any], step: str, status: str, details: Dict[str, Any] = None) -> None:
    trace["steps"].append({
        "step": step,
        "status": status,
        "elapsed_seconds": round(time.time() - trace["started_at"], 3),
        "details": details or {}
    })


def finalize_trace(trace: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    trace["completed_in_seconds"] = round(time.time() - trace["started_at"], 3)
    trace["token_usage_estimate"]["final_payload_tokens"] = estimate_tokens(payload)
    return trace

# -----------------------------
# Tavily search
# -----------------------------
async def scrape_tavily(query: str, limit: int = DEFAULT_LIMIT_PER_QUERY) -> List[Dict[str, Any]]:
    results = []
    try:
        response = await tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=limit
        )

        for r in response.get("results", []):
            if len(results) >= limit:
                break

            results.append({
                "title": (r.get("title", "") or "")[:140],
                "link": r.get("url", ""),
                "snippet": clean_and_truncate_snippet(r.get("content", "")),
                "query": query,
                "source_engine": "tavily",
            })
    except Exception as e:
        print(f"Tavily error on '{query}': {e}")

    return results


async def run_queries(
    queries: List[str],
    limit_per_query: int = DEFAULT_LIMIT_PER_QUERY,
    max_total_results: int = MAX_TOTAL_RESULTS
) -> List[Dict[str, Any]]:
    tasks = [scrape_tavily(q, limit_per_query) for q in queries]
    query_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for res in query_results:
        if isinstance(res, list):
            all_results.extend(res)

    return dedupe_results(all_results)[:max_total_results]

# -----------------------------
# Industry inference
# -----------------------------
def infer_industry_from_results(company_name: str, results: List[Dict[str, Any]]) -> Tuple[str, float, Dict[str, Any]]:
    text_blob = " ".join(
        f"{r.get('title', '')} {r.get('snippet', '')}" for r in results
    )
    text_blob_n = normalize_text(text_blob)

    scores = {}
    evidence = {}

    for industry, keywords in INDUSTRY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text_blob_n]
        score = len(hits)
        scores[industry] = score
        evidence[industry] = hits

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_industry, best_score = ranked[0] if ranked else ("unknown", 0)
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score == 0:
        return "unknown", 0.2, {
            "reason": "No industry keywords matched company evidence.",
            "ranked_scores": ranked
        }

    confidence = min(0.95, 0.45 + 0.1 * best_score + 0.05 * max(0, best_score - second_score))

    return best_industry, round(confidence, 2), {
        "matched_keywords": evidence.get(best_industry, []),
        "ranked_scores": ranked[:5]
    }

# -----------------------------
# Outlook extraction
# -----------------------------
def summarize_outlook_drivers(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    text_blob = " ".join(
        f"{r.get('title', '')} {r.get('snippet', '')}" for r in results
    )

    positive_hits = keyword_hits(text_blob, OUTLOOK_POSITIVE_KEYWORDS)
    negative_hits = keyword_hits(text_blob, OUTLOOK_NEGATIVE_KEYWORDS)

    return {
        "positive_drivers": sorted(set(positive_hits)),
        "negative_drivers": sorted(set(negative_hits)),
    }


def compute_industry_outlook_score(outlook_drivers: Dict[str, List[str]], evidence_count: int) -> Dict[str, Any]:
    positive_drivers = outlook_drivers.get("positive_drivers", [])
    negative_drivers = outlook_drivers.get("negative_drivers", [])

    pos_weight = sum(POSITIVE_WEIGHTS.get(k, 1.0) for k in positive_drivers)
    neg_weight = sum(NEGATIVE_WEIGHTS.get(k, 1.0) for k in negative_drivers)

    weighted_total = pos_weight + neg_weight

    # default neutral if almost no signal
    if weighted_total == 0:
        return {
            "industry_outlook_score": 0.5,
            "outlook_rating": "Neutral",
            "outlook_confidence": 0.25,
            "outlook_summary": {
                "positive_signal_count": 0,
                "negative_signal_count": 0,
                "positive_weight": 0.0,
                "negative_weight": 0.0,
                "reason": "Insufficient outlook signals detected from industry evidence."
            }
        }

    # positive proportion
    score = pos_weight / weighted_total

    # conservative penalty for weak evidence
    confidence = min(0.95, 0.35 + 0.08 * evidence_count + 0.05 * weighted_total)

    if evidence_count <= 2 or weighted_total <= 2:
        score = 0.5 + (score - 0.5) * 0.7
        confidence *= 0.7

    score = max(0.0, min(1.0, round(score, 2)))
    confidence = max(0.0, min(1.0, round(confidence, 2)))

    if score >= 0.65:
        rating = "Positive"
    elif score >= 0.4:
        rating = "Neutral"
    else:
        rating = "Negative"

    return {
        "industry_outlook_score": score,
        "outlook_rating": rating,
        "outlook_confidence": confidence,
        "outlook_summary": {
            "positive_signal_count": len(positive_drivers),
            "negative_signal_count": len(negative_drivers),
            "positive_weight": round(pos_weight, 2),
            "negative_weight": round(neg_weight, 2)
        }
    }

# -----------------------------
# Core logic
# -----------------------------
async def research_company_industry_outlook_logic(company_name: str) -> Dict[str, Any]:
    trace = init_trace(company_name)

    company_queries = [
        f'"{company_name}" official website',
        f'"{company_name}" business overview',
        f'"{company_name}" company profile',
        f'"{company_name}" investor relations',
        f'"{company_name}" annual report'
    ]

    log_step(trace, "gather_company_evidence", "running", {
        "query_count": len(company_queries)
    })
    trace["token_usage_estimate"]["query_tokens"] += estimate_tokens(company_queries)

    company_results = await run_queries(company_queries, limit_per_query=2, max_total_results=8)
    trace["token_usage_estimate"]["company_result_tokens"] = estimate_tokens(company_results)

    log_step(trace, "gather_company_evidence", "completed", {
        "results_found": len(company_results)
    })

    log_step(trace, "infer_industry", "running")
    inferred_industry, confidence, industry_debug = infer_industry_from_results(company_name, company_results)
    log_step(trace, "infer_industry", "completed", {
        "inferred_industry": inferred_industry,
        "confidence": confidence
    })

    if inferred_industry != "unknown":
        outlook_queries = [
            f'"{inferred_industry}" industry outlook {CURRENT_YEAR}',
            f'"{inferred_industry}" industry trends {CURRENT_YEAR}',
            f'"{inferred_industry}" market outlook {CURRENT_YEAR}',
            f'"{inferred_industry}" growth drivers risks {CURRENT_YEAR}'
        ]
    else:
        outlook_queries = [
            f'"{company_name}" industry outlook {CURRENT_YEAR}',
            f'"{company_name}" sector outlook {CURRENT_YEAR}'
        ]

    log_step(trace, "gather_industry_outlook", "running", {
        "query_count": len(outlook_queries)
    })
    trace["token_usage_estimate"]["query_tokens"] += estimate_tokens(outlook_queries)

    outlook_results = await run_queries(outlook_queries, limit_per_query=2, max_total_results=8)
    trace["token_usage_estimate"]["outlook_result_tokens"] = estimate_tokens(outlook_results)

    log_step(trace, "gather_industry_outlook", "completed", {
        "results_found": len(outlook_results)
    })

    log_step(trace, "extract_outlook_drivers", "running")
    outlook_drivers = summarize_outlook_drivers(outlook_results)
    log_step(trace, "extract_outlook_drivers", "completed", {
        "positive_driver_count": len(outlook_drivers["positive_drivers"]),
        "negative_driver_count": len(outlook_drivers["negative_drivers"])
    })

    log_step(trace, "score_industry_outlook", "running")
    outlook_score = compute_industry_outlook_score(
        outlook_drivers,
        evidence_count=len(outlook_results)
    )
    log_step(trace, "score_industry_outlook", "completed", {
        "industry_outlook_score": outlook_score["industry_outlook_score"],
        "outlook_rating": outlook_score["outlook_rating"],
        "outlook_confidence": outlook_score["outlook_confidence"]
    })

    payload = {
        "metadata": {
            "company_name": company_name,
            "research_type": "company_industry_outlook"
        },
        "industry_research": {
            "inferred_industry": inferred_industry,
            "industry_confidence": confidence,
            "industry_inference_debug": industry_debug,
            "company_evidence": compress_results(company_results, limit=8),
            "industry_outlook_evidence": compress_results(outlook_results, limit=8),
            "outlook_analysis": {
                "drivers": outlook_drivers,
                **outlook_score
            }
        }
    }

    payload["debug"] = finalize_trace(trace, payload)
    return payload

# -----------------------------
# MCP tool
# -----------------------------
@mcp.tool()
async def research_company_industry_outlook(company_name: str) -> str:
    """
    Research a company's likely industry and gather industry outlook evidence.
    Returns structured JSON for later forecasting / credit risk analysis.
    """
    result = await research_company_industry_outlook_logic(company_name)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()