"""
Source Credibility Agent — dynamically evaluates source reliability using LLM.

Analyzes each data source's domain, content quality, recency, and whether it's
a primary source (company IR, regulator) vs secondary (news) vs tertiary (social).
Assigns credibility_weight (0-1) and source_tier with reasoning.
"""

from typing import Dict, Any, List
from src.core.state import AgentState
from src.core.llm import get_llm, sanitize_for_prompt
from src.core.logger import log_agent_action

AGENT_NAME = "source_credibility_agent"

# Baseline domain hints (used as fallback if LLM unavailable)
_DOMAIN_HINTS = {
    "sec.gov": 0.95, "mas.gov.sg": 0.95, "acra.gov.sg": 0.95,
    "finance.yahoo.com": 0.90, "reuters.com": 0.85, "bloomberg.com": 0.85,
    "ft.com": 0.85, "wsj.com": 0.85, "cnbc.com": 0.80, "bbc.com": 0.80,
    "straitstimes.com": 0.80, "channelnewsasia.com": 0.80,
    "glassdoor.com": 0.55, "indeed.com": 0.55, "linkedin.com": 0.60,
    "reddit.com": 0.35, "twitter.com": 0.35, "x.com": 0.35,
}


def _get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _fallback_score(source_type: str, url: str) -> tuple:
    """Rule-based fallback when LLM is unavailable."""
    domain = _get_domain(url)
    for known_domain, weight in _DOMAIN_HINTS.items():
        if known_domain in domain:
            tier = "tier_1" if weight >= 0.90 else "tier_2" if weight >= 0.75 else "tier_3" if weight >= 0.50 else "tier_4"
            return weight, tier, f"Domain match: {known_domain}"

    st = source_type.lower()
    if "financial" in st or "yfinance" in st:
        return 0.90, "tier_1", "Financial data source"
    elif "news" in st:
        return 0.75, "tier_2", "News source"
    elif "review" in st:
        return 0.50, "tier_3", "Review/contextual source"
    elif "social" in st:
        return 0.35, "tier_4", "Social media source"
    return 0.50, "tier_3", "Unknown source type"


def source_credibility_agent(state: AgentState) -> Dict[str, Any]:
    """Evaluate credibility of each data source dynamically."""
    cleaned_data = state.get("cleaned_data", [])
    company = state.get("company_name", "unknown")

    if not cleaned_data:
        log_agent_action(AGENT_NAME, "No cleaned_data to evaluate")
        return {"cleaned_data": []}

    llm = get_llm(temperature=0)
    updated_data = []
    tier_counts = {}
    eval_details = []

    # Separate known-domain items (skip LLM) from unknown ones (need LLM)
    known_items = []  # (index, item, weight, tier, reason)
    unknown_items = []  # (index, item)
    for i, item in enumerate(cleaned_data):
        url = item.get("url", "N/A")
        domain = _get_domain(url)
        matched = False
        for known_domain, weight in _DOMAIN_HINTS.items():
            if known_domain in domain:
                tier = "tier_1" if weight >= 0.90 else "tier_2" if weight >= 0.75 else "tier_3" if weight >= 0.50 else "tier_4"
                known_items.append((i, item, weight, tier, f"Known domain: {known_domain}"))
                matched = True
                break
        if not matched:
            unknown_items.append((i, item))

    if llm and unknown_items and len(unknown_items) <= 25:
        # LLM only evaluates unknown-domain sources (saves tokens)
        safe_company = sanitize_for_prompt(company, max_length=100)
        source_summaries = []
        for idx, (i, item) in enumerate(unknown_items):
            url = item.get("url", "N/A")
            source_type = item.get("source_type", "unknown")
            title = sanitize_for_prompt(str(item.get("title", item.get("snippet", ""))), max_length=80)
            domain = _get_domain(url)
            source_summaries.append(f"{idx+1}. [{source_type}] {domain} — {title}")

        prompt = f"""You are a credit risk analyst evaluating source reliability for {safe_company}.

Rate each source on a scale of 0.0 to 1.0 for credibility in credit risk assessment:
- 0.90-1.00: Tier 1 (regulatory filings, official financial data, central bank reports)
- 0.75-0.89: Tier 2 (major financial news: Reuters, Bloomberg, FT, Straits Times)
- 0.50-0.74: Tier 3 (general news, employee reviews, industry reports)
- 0.00-0.49: Tier 4 (social media, forums, unverified blogs)

Sources to evaluate:
{chr(10).join(source_summaries)}

For each source, respond with ONE line in this exact format:
<number>|<score>|<tier>|<reason>

Example:
1|0.85|tier_2|Reuters is a major global financial news wire service
2|0.35|tier_4|Reddit post with unverified claims"""

        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # Parse LLM response
            scores = {}
            for line in content.strip().split("\n"):
                parts = line.strip().split("|")
                if len(parts) >= 4:
                    try:
                        idx = int(parts[0].strip()) - 1
                        score = float(parts[1].strip())
                        tier = parts[2].strip()
                        reason = parts[3].strip()
                        scores[idx] = (min(max(score, 0.0), 1.0), tier, reason)
                    except (ValueError, IndexError):
                        continue

            log_agent_action(AGENT_NAME, f"LLM evaluated {len(scores)}/{len(unknown_items)} unknown-domain sources")

            # Build index map: unknown_items index -> original cleaned_data index
            llm_results = {}
            for idx, (orig_i, item) in enumerate(unknown_items):
                if idx in scores:
                    llm_results[orig_i] = scores[idx]
                else:
                    llm_results[orig_i] = _fallback_score(
                        item.get("source_type", ""), item.get("url", ""))

        except Exception as e:
            log_agent_action(AGENT_NAME, f"LLM evaluation failed: {e}, using fallback")
            llm_results = {}
            for orig_i, item in unknown_items:
                llm_results[orig_i] = _fallback_score(
                    item.get("source_type", ""), item.get("url", ""))

        # Merge known + LLM-evaluated results in original order
        all_results = {}
        for orig_i, item, weight, tier, reason in known_items:
            all_results[orig_i] = (weight, tier, reason)
        all_results.update(llm_results)

        for i, item in enumerate(cleaned_data):
            weight, tier, reason = all_results.get(i, _fallback_score(
                item.get("source_type", ""), item.get("url", "")))
            annotated = {**item, "credibility_weight": weight, "source_tier": tier,
                         "credibility_reason": reason}
            updated_data.append(annotated)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

    else:
        # Fallback: all known-domain items resolved, unknown items get rule-based
        for orig_i, item, weight, tier, reason in known_items:
            annotated = {**item, "credibility_weight": weight, "source_tier": tier,
                         "credibility_reason": reason}
            updated_data.append(annotated)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        for orig_i, item in unknown_items:
            weight, tier, reason = _fallback_score(
                item.get("source_type", ""), item.get("url", ""))
            annotated = {**item, "credibility_weight": weight, "source_tier": tier,
                         "credibility_reason": reason}
            updated_data.append(annotated)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

    log_agent_action(AGENT_NAME, "Source credibility evaluation complete", {
        "total_items": len(updated_data),
        "tier_distribution": tier_counts,
        "method": "llm" if llm and len(cleaned_data) <= 25 else "rule_based",
    })

    return {"cleaned_data": updated_data}
