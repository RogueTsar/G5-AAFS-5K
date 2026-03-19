import os
import json
import asyncio
import re
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import AsyncTavilyClient
from openai import OpenAI

load_dotenv(dotenv_path="../.env")

mcp = FastMCP("SourceDiscoveryAgent")
tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_SOURCES = 4
DEFAULT_LIMIT_PER_QUERY = 3
MAX_CANDIDATES_FOR_LLM = 10

COMPANY_SUFFIXES = [
    "pte ltd", "private limited", "ltd", "llp", "inc", "corp",
    "corporation", "company", "co.", "plc", "holdings", "group"
]

# -----------------------------
# Prompts
# -----------------------------
SOURCE_EVALUATION_PROMPT = """
You are a source discovery analyst.

Your task is to evaluate candidate web sources for a target entity and select the 3 to 4 best sources for researching:
1. current status
2. future outlook
3. business context or professional context

Do not assume only large, globally known websites are useful.
If the entity is small, private, or niche, you may choose smaller or lesser-known sources if they appear directly relevant and useful.

Evaluate each candidate source based on:
- direct relevance to the target entity
- likely trustworthiness
- likely usefulness for understanding current status
- likely usefulness for understanding future outlook or business direction
- whether it appears to be official, regulatory, professional, media, directory, or supplementary

Prefer sources that are:
- directly about the target
- informative and specific
- likely to contain useful evidence

Return strictly valid JSON in this format:
{
  "selected_sources": [
    {
      "source_name": "...",
      "url": "...",
      "selection_rank": 1,
      "trust_level": "high | medium | low",
      "relevance_level": "high | medium | low",
      "source_type": "official | regulatory | professional_profile | media | directory | supplementary",
      "why_chosen": "...",
      "expected_information": "...",
      "possible_limitations": "..."
    }
  ]
}
"""

# -----------------------------
# Helpers
# -----------------------------
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def estimate_tokens(obj: Any) -> int:
    try:
        return max(1, len(json.dumps(obj, ensure_ascii=False)) // 4)
    except Exception:
        return 1


def detect_entity_type(entity_name: str) -> str:
    text = normalize_text(entity_name)
    if any(s in text for s in COMPANY_SUFFIXES):
        return "company"

    words = [w for w in entity_name.split() if w]
    if 2 <= len(words) <= 4:
        return "person"

    return "unknown"


def clean_snippet(text: str, max_chars: int = 220) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].rsplit(" ", 1)[0] + "..." if len(text) > max_chars else text


def get_domain(url: str) -> str:
    match = re.search(r"https?://([^/]+)", url or "")
    return match.group(1).lower() if match else ""


def dedupe_by_domain_or_url(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_urls = set()
    seen_domains = set()
    final = []

    for r in results:
        url = r.get("url", "")
        domain = get_domain(url)
        if not url or url in seen_urls:
            continue

        # keep only one per domain except linkedin where multiple pages can still matter
        if domain in seen_domains and "linkedin.com" not in domain:
            continue

        seen_urls.add(url)
        seen_domains.add(domain)
        final.append(r)

    return final


def domain_prior_score(url: str) -> int:
    """
    Light hint only.
    Not the final decision.
    """
    domain = get_domain(url)

    if any(x in domain for x in ["acra.gov.sg", "mas.gov.sg", "sgx.com"]):
        return 4
    if "linkedin.com" in domain:
        return 3
    if any(x in domain for x in ["reuters.com", "bloomberg.com", "wsj.com", "ft.com", "marketwatch.com"]):
        return 3
    if ".gov" in domain:
        return 3
    return 1


def build_queries(entity_name: str, entity_type: str) -> List[str]:
    if entity_type == "company":
        return [
            f'"{entity_name}" official website',
            f'"{entity_name}" LinkedIn',
            f'"{entity_name}" investor relations OR annual report OR company profile',
            f'"{entity_name}" leadership OR management OR about us',
            f'"{entity_name}" outlook OR strategy OR market OR Reuters OR Bloomberg'
        ]

    if entity_type == "person":
        return [
            f'"{entity_name}" LinkedIn',
            f'"{entity_name}" biography OR profile OR leadership',
            f'"{entity_name}" director OR founder OR shareholder',
            f'"{entity_name}" company OR board OR management',
            f'"{entity_name}" Reuters OR Bloomberg OR profile'
        ]

    return [
        f'"{entity_name}" official website',
        f'"{entity_name}" LinkedIn',
        f'"{entity_name}" profile OR company OR leadership',
        f'"{entity_name}" outlook OR market OR Reuters OR Bloomberg'
    ]


# -----------------------------
# Tavily
# -----------------------------
async def scrape_tavily(query: str, limit: int = DEFAULT_LIMIT_PER_QUERY) -> List[Dict[str, Any]]:
    try:
        response = await tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=limit
        )

        output = []
        for r in response.get("results", []):
            output.append({
                "title": (r.get("title", "") or "")[:140],
                "url": r.get("url", ""),
                "snippet": clean_snippet(r.get("content", "")),
                "query": query
            })
        return output[:limit]

    except Exception as e:
        print(f"Tavily error on '{query}': {e}")
        return []


async def run_queries(queries: List[str], limit_per_query: int = DEFAULT_LIMIT_PER_QUERY) -> List[Dict[str, Any]]:
    tasks = [scrape_tavily(q, limit_per_query) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for res in results:
        if isinstance(res, list):
            all_results.extend(res)

    return dedupe_by_domain_or_url(all_results)


# -----------------------------
# LLM evaluation
# -----------------------------
async def evaluate_sources_with_llm(
    entity_name: str,
    entity_type: str,
    raw_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    candidate_payload = []
    for r in raw_results[:MAX_CANDIDATES_FOR_LLM]:
        candidate_payload.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
            "domain": get_domain(r.get("url", "")),
            "query": r.get("query", ""),
            "domain_prior_score": domain_prior_score(r.get("url", ""))
        })

    user_prompt = f"""
Target entity: {entity_name}
Entity type: {entity_type}

Candidate sources:
{json.dumps(candidate_payload, indent=2)}
"""

    response = await asyncio.to_thread(
        openai_client.chat.completions.create,
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SOURCE_EVALUATION_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)
    selected = parsed.get("selected_sources", [])

    return selected[:MAX_SOURCES]


# -----------------------------
# Main logic
# -----------------------------
async def discover_best_sources_logic(entity_name: str, entity_type: str = "") -> Dict[str, Any]:
    start = time.time()

    inferred_type = entity_type.strip().lower() if entity_type else detect_entity_type(entity_name)
    if inferred_type not in {"company", "person", "unknown"}:
        inferred_type = "unknown"

    queries = build_queries(entity_name, inferred_type)
    raw_results = await run_queries(queries, limit_per_query=DEFAULT_LIMIT_PER_QUERY)

    selected_sources = await evaluate_sources_with_llm(
        entity_name=entity_name,
        entity_type=inferred_type,
        raw_results=raw_results
    )

    payload = {
        "metadata": {
            "entity_name": entity_name,
            "entity_type": inferred_type,
            "research_type": "source_discovery_for_outlook_and_status"
        },
        "recommended_sources": selected_sources,
        "debug": {
            "queries_executed": queries,
            "candidate_count": len(raw_results),
            "selected_count": len(selected_sources),
            "token_usage_estimate": {
                "candidate_results_tokens": estimate_tokens(raw_results[:MAX_CANDIDATES_FOR_LLM]),
                "selected_sources_tokens": estimate_tokens(selected_sources)
            },
            "raw_candidates": raw_results[:MAX_CANDIDATES_FOR_LLM],
            "completed_in_seconds": round(time.time() - start, 3)
        }
    }

    return payload


# -----------------------------
# MCP Tool
# -----------------------------
@mcp.tool()
async def discover_best_sources(entity_name: str, entity_type: str = "") -> str:
    """
    Identify up to 3-4 trustworthy sources most useful for understanding
    a company or individual's current status, future outlook, and business context.
    """
    result = await discover_best_sources_logic(entity_name, entity_type)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()