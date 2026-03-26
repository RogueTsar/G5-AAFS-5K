import os
import json
import asyncio
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import AsyncTavilyClient
from openai import OpenAI

load_dotenv(dotenv_path="../.env")

mcp = FastMCP("SourceDiscoveryAgent")
tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_LIMIT_PER_QUERY = 2
MAX_CANDIDATES = 8
MAX_SOURCES = 4

COMPANY_SUFFIXES = [
    "pte ltd", "private limited", "ltd", "llp", "inc", "corp",
    "corporation", "company", "co.", "plc", "holdings", "group"
]

SOURCE_SELECTION_PROMPT = """
You are a source discovery assistant.

Your only task is to choose the 3 to 4 best sources for researching a target company or individual's:
- current status
- future outlook
- business or professional context

Be practical:
- If the entity is large, well-known sources may be useful.
- If the entity is small or niche, choose smaller but directly relevant sources.
- Prefer sources that are likely to contain meaningful information.

Return strictly valid JSON in this format:
{
  "sources": [
    {
      "source": "linkedin.com",
      "reason": "LinkedIn is useful because it can show the entity's official presence, role, company profile, or staff and leadership context."
    }
  ]
}

Rules:
- Return only 3 to 4 sources.
- Keep each reason to 1 to 2 sentences.
- Prefer domain-style source names where possible.
"""

# -----------------------------
# Helpers
# -----------------------------
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def detect_entity_type(entity_name: str) -> str:
    text = normalize_text(entity_name)
    if any(s in text for s in COMPANY_SUFFIXES):
        return "company"

    words = [w for w in entity_name.split() if w]
    if 2 <= len(words) <= 4:
        return "person"

    return "unknown"


def clean_snippet(text: str, max_chars: int = 160) -> str:
    if not text:
        return ""
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].rsplit(" ", 1)[0] + "..." if len(text) > max_chars else text


def get_domain(url: str) -> str:
    match = re.search(r"https?://([^/]+)", url or "")
    if not match:
        return ""
    domain = match.group(1).lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_domains = set()
    final = []

    for r in results:
        domain = get_domain(r.get("url", ""))
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)
        final.append(r)

    return final


def build_queries(entity_name: str, entity_type: str) -> List[str]:
    if entity_type == "company":
        return [
            f'"{entity_name}" official website OR company profile OR annual report',
            f'"{entity_name}" LinkedIn OR Reuters OR Bloomberg OR Yahoo Finance',
            f'"{entity_name}" outlook OR market OR investor relations'
        ]

    if entity_type == "person":
        return [
            f'"{entity_name}" LinkedIn OR biography OR profile',
            f'"{entity_name}" company OR board OR founder OR director',
            f'"{entity_name}" Reuters OR Bloomberg OR leadership'
        ]

    return [
        f'"{entity_name}" official website OR profile',
        f'"{entity_name}" LinkedIn OR Reuters OR Bloomberg',
        f'"{entity_name}" company OR outlook OR leadership'
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
                "title": (r.get("title", "") or "")[:100],
                "url": r.get("url", ""),
                "snippet": clean_snippet(r.get("content", "")),
            })
        return output[:limit]

    except Exception as e:
        print(f"Tavily error on '{query}': {e}")
        return []


async def run_queries(queries: List[str]) -> List[Dict[str, Any]]:
    tasks = [scrape_tavily(q, DEFAULT_LIMIT_PER_QUERY) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for res in results:
        if isinstance(res, list):
            all_results.extend(res)

    deduped = dedupe_results(all_results)
    return deduped[:MAX_CANDIDATES]


# -----------------------------
# LLM source selector
# -----------------------------
async def choose_sources_with_llm(entity_name: str, entity_type: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    compact_candidates = []
    for c in candidates:
        compact_candidates.append({
            "domain": get_domain(c.get("url", "")),
            "title": c.get("title", ""),
            "snippet": c.get("snippet", "")
        })

    user_prompt = f"""
Target entity: {entity_name}
Entity type: {entity_type}

Candidate sources:
{json.dumps(compact_candidates, indent=2)}
"""

    response = await asyncio.to_thread(
        openai_client.chat.completions.create,
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SOURCE_SELECTION_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )

    parsed = json.loads(response.choices[0].message.content)
    sources = parsed.get("sources", [])
    return sources[:MAX_SOURCES]


# -----------------------------
# Main logic
# -----------------------------
async def discover_best_sources_logic(entity_name: str, entity_type: str = "") -> Dict[str, Any]:
    inferred_type = entity_type.strip().lower() if entity_type else detect_entity_type(entity_name)
    if inferred_type not in {"company", "person", "unknown"}:
        inferred_type = "unknown"

    queries = build_queries(entity_name, inferred_type)
    candidates = await run_queries(queries)
    selected_sources = await choose_sources_with_llm(entity_name, inferred_type, candidates)

    return {
        "entity_name": entity_name,
        "entity_type": inferred_type,
        "sources": selected_sources
    }


# -----------------------------
# MCP Tool
# -----------------------------
@mcp.tool()
async def discover_best_sources(entity_name: str, entity_type: str = "") -> str:
    """
    Return 3-4 recommended sources and short reasons for researching
    a company or individual's current status and future outlook.
    """
    result = await discover_best_sources_logic(entity_name, entity_type)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()