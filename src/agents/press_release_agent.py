"""
Press Release Agent — directed newsroom scraping with M&A/hiring/layoff
assessment framework. Uses regex-based categorization (0 LLM tokens) for
event classification and a single structured LLM call (<500 tokens) for
corporate trajectory synthesis.
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, List, Literal
from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.core.llm import get_llm

AGENT_NAME = "press_release_agent"
CURRENT_YEAR = datetime.now().year

CORPORATE_EVENT_CATEGORIES = {
    "m_and_a": [
        "acquisition", "merger", "acquired", "takeover", "divest", "sold", "purchase",
    ],
    "workforce": [
        "hiring", "layoff", "restructuring", "headcount", "job cuts",
        "expansion", "new hires",
    ],
    "financial_health": [
        "revenue", "profit", "loss", "guidance", "earnings", "dividend",
        "quarterly results",
    ],
    "market_position": [
        "market share", "partnership", "contract", "new market", "launch", "expand",
    ],
    "leadership": [
        "ceo", "appointed", "resigned", "board", "executive", "succession", "director",
    ],
    "risk_events": [
        "lawsuit", "investigation", "recall", "breach", "sanction", "default", "fraud",
    ],
}

# Pre-compile regex patterns for each category
_CATEGORY_PATTERNS: Dict[str, re.Pattern] = {}
for category, keywords in CORPORATE_EVENT_CATEGORIES.items():
    pattern = "|".join(re.escape(kw) for kw in keywords)
    _CATEGORY_PATTERNS[category] = re.compile(pattern, re.IGNORECASE)


def _build_queries(company: str) -> List[str]:
    """Build targeted Tavily queries for press release discovery."""
    year = CURRENT_YEAR
    return [
        f'{company} press release news {year}',
        f'{company} acquisition merger announcement',
        f'{company} restructuring layoffs hiring',
        f'{company} earnings quarterly results guidance',
        f'{company} partnership expansion new market',
        f'{company} financial results annual report',
        f'{company} regulatory compliance risk',
    ]


def _tavily_search(queries: List[str], max_results: int = 20) -> List[Dict[str, Any]]:
    """Execute Tavily searches. Returns empty list on failure."""
    try:
        from tavily import TavilyClient
    except ImportError:
        return []

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []

    try:
        client = TavilyClient(api_key=api_key)
    except Exception:
        return []

    all_results = []
    seen_urls = set()

    for query in queries:
        if len(all_results) >= max_results:
            break
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=5,
            )
            for r in response.get("results", []):
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("content", ""),
                        "url": url,
                        "query": query,
                    })
                if len(all_results) >= max_results:
                    break
        except Exception:
            continue

    return all_results


def _categorize_results(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Categorize results using regex keyword matching. Returns event counts."""
    event_counts = {cat: 0 for cat in CORPORATE_EVENT_CATEGORIES}

    for result in results:
        text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        for category, pattern in _CATEGORY_PATTERNS.items():
            if pattern.search(text):
                event_counts[category] += 1

    return event_counts


def _synthesize_trajectory(
    company: str,
    results: List[Dict[str, Any]],
    event_counts: Dict[str, int],
) -> Dict[str, Any]:
    """Use a single LLM call to synthesize corporate trajectory from press releases."""
    llm = get_llm(temperature=0)
    if llm is None or not results:
        return _default_trajectory()

    try:
        from pydantic import BaseModel, Field
        from typing import Literal as Lit

        class CorporateTrajectory(BaseModel):
            growth_signals: List[str] = Field(
                description="Evidence of expansion/strength from press releases"
            )
            contraction_signals: List[str] = Field(
                description="Evidence of decline/risk from press releases"
            )
            trajectory: Lit["expanding", "stable", "contracting", "restructuring"]
            key_events: List[str] = Field(
                description="Top 3-5 most significant corporate events"
            )
            outlook_impact: Lit["positive", "neutral", "negative"]

        # Build a compact evidence summary to stay under 500 tokens
        evidence_lines = []
        for r in results[:8]:
            title = (r.get("title", "") or "")[:80]
            snippet = (r.get("snippet", "") or "")[:120]
            if title:
                evidence_lines.append(f"- {title}: {snippet}")

        evidence_text = "\n".join(evidence_lines)
        event_summary = ", ".join(f"{k}: {v}" for k, v in event_counts.items() if v > 0)

        prompt = (
            f"Analyze these press releases for {company} and assess corporate trajectory.\n"
            f"Event counts: {event_summary or 'none detected'}\n\n"
            f"Evidence:\n{evidence_text}\n\n"
            f"Respond with structured JSON output only."
        )

        structured_llm = llm.with_structured_output(CorporateTrajectory)
        result = structured_llm.invoke(prompt)
        return result.model_dump()

    except Exception as e:
        log_agent_action(AGENT_NAME, f"LLM synthesis failed: {str(e)}")
        return _default_trajectory()


def _default_trajectory() -> Dict[str, Any]:
    """Safe default when LLM or data is unavailable."""
    return {
        "growth_signals": [],
        "contraction_signals": [],
        "trajectory": "stable",
        "key_events": [],
        "outlook_impact": "neutral",
    }


def press_release_agent(state: AgentState) -> Dict[str, Any]:
    """Scrape and analyze corporate press releases for event assessment."""
    company = state.get("company_name", "")
    if not company:
        log_agent_action(AGENT_NAME, "No company_name in state, skipping")
        return {"press_release_analysis": {
            **_default_trajectory(),
            "event_counts": {},
            "raw_results": [],
        }}

    # Step 1: Build queries and search
    queries = _build_queries(company)
    log_agent_action(AGENT_NAME, f"Searching press releases with {len(queries)} queries")

    results = _tavily_search(queries, max_results=10)

    # Fallback: use existing news_data from state if Tavily unavailable
    if not results:
        news_data = state.get("news_data", [])
        if news_data:
            log_agent_action(AGENT_NAME, "Tavily unavailable, falling back to state news_data")
            results = [
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", item.get("description", "")),
                    "url": item.get("url", ""),
                    "query": "state_fallback",
                }
                for item in news_data[:10]
            ]

    log_agent_action(AGENT_NAME, f"Collected {len(results)} press release results")

    # Step 2: Categorize events (0 LLM tokens)
    event_counts = _categorize_results(results)
    log_agent_action(AGENT_NAME, "Event categorization complete", {
        "event_counts": event_counts,
    })

    # Step 3: Synthesize trajectory (1 LLM call)
    trajectory = _synthesize_trajectory(company, results, event_counts)

    analysis = {
        **trajectory,
        "event_counts": event_counts,
        "raw_results": results,
    }

    log_agent_action(AGENT_NAME, "Press release analysis complete", {
        "trajectory": trajectory.get("trajectory", "unknown"),
        "outlook_impact": trajectory.get("outlook_impact", "unknown"),
        "total_results": len(results),
        "events_detected": sum(event_counts.values()),
    })

    return {"press_release_analysis": analysis}
