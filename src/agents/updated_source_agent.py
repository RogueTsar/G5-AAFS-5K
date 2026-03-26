import asyncio
import json
import os
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from tavily import AsyncTavilyClient
from openai import OpenAI

# Optional: if you use MCP decorators, keep this import
# from mcp.server.fastmcp import FastMCP

# Optional: if you already have a logger utility, use it
# from src.core.logger import log_agent_action


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

LOW_VALUE_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "tiktok.com",
    "www.tiktok.com",
    "youtube.com",
    "www.youtube.com",
    "pinterest.com",
    "www.pinterest.com",
}

COMPANY_HINTS = {
    "inc",
    "corp",
    "corporation",
    "ltd",
    "limited",
    "llc",
    "plc",
    "pte",
    "pte ltd",
    "co",
    "company",
    "holdings",
    "group",
    "bank",
}


# -----------------------------------------------------------------------------
# Lazy client creation (important for tests)
# -----------------------------------------------------------------------------

def get_tavily_client() -> AsyncTavilyClient:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set")
    return AsyncTavilyClient(api_key=api_key)


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def normalize_host(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def detect_entity_type(entity_name: str) -> str:
    lowered = entity_name.lower()

    if any(hint in lowered for hint in COMPANY_HINTS):
        return "company"

    tokens = entity_name.split()
    if 2 <= len(tokens) <= 4 and all(token[:1].isupper() for token in tokens if token):
        return "person"

    return "unknown"


def build_queries(entity_name: str, entity_type: str) -> List[str]:
    """
    Build search queries based on the sanitized entity name and entity type.
    """
    entity_name = entity_name.strip()
    entity_type = entity_type.strip().lower()

    if entity_type == "individual":
        entity_type = "person"

    if entity_type == "company":
        return [
            f'"{entity_name}" company profile',
            f'"{entity_name}" annual report OR business profile OR filings',
            f'"{entity_name}" Reuters OR Bloomberg OR Crunchbase OR LinkedIn',
            f'"{entity_name}" ownership OR subsidiaries OR holdings',
        ]

    if entity_type == "person":
        return [
            f'"{entity_name}" LinkedIn OR profile',
            f'"{entity_name}" director OR executive OR shareholder',
            f'"{entity_name}" business OR company OR holdings',
            f'"{entity_name}" Reuters OR Bloomberg OR business news',
        ]

    return [
        f'"{entity_name}" company OR person OR profile',
        f'"{entity_name}" Reuters OR Bloomberg OR LinkedIn OR Crunchbase',
        f'"{entity_name}" business OR ownership OR filings',
    ]


def dedupe_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_urls = set()
    deduped: List[Dict[str, Any]] = []

    for item in candidates:
        url = item.get("url", "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)

    return deduped


def filter_low_value_hosts(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []

    for item in candidates:
        host = normalize_host(item.get("url", ""))
        if host in LOW_VALUE_HOSTS:
            continue
        filtered.append(item)

    return filtered


# -----------------------------------------------------------------------------
# Tavily query runner
# -----------------------------------------------------------------------------

async def run_queries(queries: List[str], max_results_per_query: int = 5) -> List[Dict[str, Any]]:
    """
    Runs search queries via Tavily, dedupes results, and filters low-value hosts.
    """
    tavily_client = get_tavily_client()
    all_candidates: List[Dict[str, Any]] = []

    for query in queries:
        try:
            response = await tavily_client.search(
                query=query,
                max_results=max_results_per_query,
                search_depth="advanced",
                include_answer=False,
                include_images=False,
            )

            results = response.get("results", []) if isinstance(response, dict) else []

            for r in results:
                all_candidates.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", "") or r.get("snippet", ""),
                        "query": query,
                    }
                )
        except Exception:
            # Fail softly per query
            continue

    all_candidates = dedupe_candidates(all_candidates)
    all_candidates = filter_low_value_hosts(all_candidates)
    return all_candidates


# -----------------------------------------------------------------------------
# LLM source chooser
# -----------------------------------------------------------------------------

async def choose_sources_with_llm(
    entity_name: str,
    entity_type: str,
    candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Uses an LLM to rank and select the best sources from discovered candidates.

    Returns:
        (selected_sources, insufficient_source_confidence)
    """
    if not candidates:
        return [], True

    client = get_openai_client()

    short_candidates = [
        {
            "title": c.get("title", ""),
            "url": c.get("url", ""),
            "snippet": c.get("snippet", "")[:300],
            "host": normalize_host(c.get("url", "")),
        }
        for c in candidates[:12]
    ]

    prompt = f"""
You are a source-quality evaluator for a financial risk assessment workflow.

Entity name: {entity_name}
Entity type: {entity_type}

Your task:
1. Review the candidate sources.
2. Select up to 3 of the best sources.
3. Prefer credible independent business, financial, legal, and official registry sources.
4. Downrank weak, opinionated, low-signal, or irrelevant sources.
5. Mark whether source confidence is insufficient overall.

Return JSON with this exact schema:
{{
  "selected_sources": [
    {{
      "source": "domain.com",
      "tier": 1,
      "score": 0.95,
      "allowed_for_scoring": true,
      "reason": "short explanation"
    }}
  ],
  "insufficient_source_confidence": false
}}

Tier guidance:
- Tier 1: official / primary / highly authoritative
- Tier 2: strong reputable business / financial source
- Tier 3: contextual only, weaker but still useful
- Tier 4: low-confidence / weak / not suitable for scoring

Candidates:
{json.dumps(short_candidates, indent=2)}
""".strip()

    def _call_openai():
        return client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict source selection assistant. Return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

    completion = await asyncio.to_thread(_call_openai)
    content = completion.choices[0].message.content or "{}"

    try:
        parsed = json.loads(content)
    except Exception:
        return [], True

    selected_sources = parsed.get("selected_sources", []) or []
    insufficient = bool(parsed.get("insufficient_source_confidence", True))

    # Cap at 3 to keep downstream evaluation manageable
    selected_sources = selected_sources[:3]

    return selected_sources, insufficient


# -----------------------------------------------------------------------------
# Core business logic
# -----------------------------------------------------------------------------

async def discover_best_sources_logic(entity_name: str, entity_type: str = "") -> Dict[str, Any]:
    inferred_type = (entity_type or "").strip().lower()

    if inferred_type not in {"company", "individual", "person", "unknown"}:
        inferred_type = "unknown"

    if inferred_type == "individual":
        inferred_type = "person"

    if not inferred_type or inferred_type == "unknown":
        inferred_type = detect_entity_type(entity_name)

    queries = build_queries(entity_name, inferred_type)
    candidates = await run_queries(queries)
    selected_sources, insufficient = await choose_sources_with_llm(
        entity_name,
        inferred_type,
        candidates,
    )

    return {
        "entity_name": entity_name,
        "entity_type": inferred_type,
        "queries": queries,
        "source_candidates": candidates,
        "selected_sources": selected_sources,
        "insufficient_source_confidence": insufficient,
    }


# -----------------------------------------------------------------------------
# LangGraph / agent wrapper
# -----------------------------------------------------------------------------

async def source_discovery_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consumes safe, validated output from input_agent.

    Expected upstream fields:
    - entity_input
    - source_query
    - source_entity_type
    """
    entity_input = state.get("entity_input", {}) or {}
    source_query = state.get("source_query", "") or ""
    source_entity_type = state.get("source_entity_type", "unknown") or "unknown"

    if state.get("errors"):
        return {
            "source_query": "",
            "source_entity_type": "unknown",
            "source_candidates": [],
            "selected_sources": [],
            "insufficient_source_confidence": True,
            "errors": state.get("errors", []),
        }

    if entity_input and not entity_input.get("is_valid", False):
        return {
            "source_query": "",
            "source_entity_type": "unknown",
            "source_candidates": [],
            "selected_sources": [],
            "insufficient_source_confidence": True,
            "errors": ["Input agent marked the input as invalid."],
        }

    if not source_query:
        return {
            "source_query": "",
            "source_entity_type": "unknown",
            "source_candidates": [],
            "selected_sources": [],
            "insufficient_source_confidence": True,
            "errors": ["No safe query available for source discovery."],
        }

    try:
        result = await discover_best_sources_logic(
            entity_name=source_query,
            entity_type=source_entity_type,
        )
        return {
            "source_query": source_query,
            "source_entity_type": source_entity_type,
            "source_candidates": result.get("source_candidates", []),
            "selected_sources": result.get("selected_sources", []),
            "insufficient_source_confidence": result.get(
                "insufficient_source_confidence", True
            ),
            "errors": [],
        }
    except Exception as e:
        return {
            "source_query": source_query,
            "source_entity_type": source_entity_type,
            "source_candidates": [],
            "selected_sources": [],
            "insufficient_source_confidence": True,
            "errors": [f"Source discovery failed: {str(e)}"],
        }


# -----------------------------------------------------------------------------
# Optional MCP tool wrapper
# -----------------------------------------------------------------------------

# If you are exposing this through MCP, uncomment and use your real mcp instance.
#
# mcp = FastMCP("source_discovery")
#
# @mcp.tool()
# async def discover_best_sources(entity_name: str, entity_type: str = "") -> Dict[str, Any]:
#     return await discover_best_sources_logic(entity_name, entity_type)