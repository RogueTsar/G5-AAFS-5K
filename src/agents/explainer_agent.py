from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.core.llm import get_llm, sanitize_for_prompt
from src.core.logger import log_agent_action
from src.core.state import AgentState

CATEGORIES = {
    "CONTRADICTION",
    "REASONING_GAP",
    "EPISTEMIC_UNCERTAINTY",
    "ANCHORING_BIAS",
    "COMPLETENESS_GAP",
    "DATA_QUALITY",
}

SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def _safe_score(risk_score: Dict[str, Any]) -> Optional[float]:
    if not isinstance(risk_score, dict):
        return None

    for key in ("overall_score", "score", "total_score", "final_score", "risk_score"):
        value = risk_score.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass

    return None


def _top_descriptions(items: List[Dict[str, Any]], keys: tuple[str, ...], limit: int = 5) -> List[str]:
    out: List[str] = []
    for item in items[:limit]:
        for key in keys:
            value = item.get(key)
            if value:
                out.append(str(value))
                break
    return out


def _build_context(state: AgentState) -> str:
    company = sanitize_for_prompt(state.get("company_name", "Unknown"), max_length=100)
    score = _safe_score(state.get("risk_score", {}))
    risks = _top_descriptions(state.get("extracted_risks", []), ("description", "risk"))
    strengths = _top_descriptions(state.get("extracted_strengths", []), ("description", "strength"))

    parts = [
        f"Company: {company}",
        f"Risk score: {score if score is not None else 'N/A'}",
        f"Top risks: {risks if risks else 'None'}",
        f"Top strengths: {strengths if strengths else 'None'}",
    ]
    return "\n".join(parts)


def _parse_issues(text: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(obj, dict):
            continue

        category = str(obj.get("category", "REASONING_GAP")).upper()
        severity = str(obj.get("severity", "MEDIUM")).upper()

        if category not in CATEGORIES:
            category = "REASONING_GAP"
        if severity not in SEVERITIES:
            severity = "MEDIUM"

        issues.append({
            "category": category,
            "severity": severity,
            "title": str(obj.get("title", "")).strip(),
            "detail": str(obj.get("detail", "")).strip(),
            "original_text": str(obj.get("original_text", "")).strip(),
            "correction": str(obj.get("correction", "")).strip(),
        })

    return issues


def explainer_agent(state: AgentState, excerpt: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze a specific excerpt of agent output for reasoning issues.

    Input:
      - state: minimal pipeline context
      - excerpt: pasted text from UI

    Output:
      {
        "issues": [...],
        "summary": "...",
        "analysis_mode": "excerpt_reasoning_audit"
      }
    """
    excerpt = (excerpt or "").strip()

    if not excerpt:
        return {
            "issues": [],
            "summary": "No excerpt provided.",
            "analysis_mode": "excerpt_reasoning_audit",
        }

    llm = get_llm(temperature=0.1)
    if llm is None:
        return {
            "issues": [],
            "summary": "LLM unavailable.",
            "analysis_mode": "excerpt_reasoning_audit",
        }

    company = sanitize_for_prompt(state.get("company_name", "Unknown"), max_length=100)
    context = _build_context(state)

    prompt = f"""
You are auditing a credit-risk AI system's OUTPUT EXCERPT for reasoning quality.

COMPANY
{company}

PIPELINE CONTEXT
{context}

EXCERPT TO ANALYZE
{excerpt}

Task:
Find only genuine reasoning-quality issues in the excerpt, using these categories:
- CONTRADICTION
- REASONING_GAP
- EPISTEMIC_UNCERTAINTY
- ANCHORING_BIAS
- COMPLETENESS_GAP
- DATA_QUALITY

Examples of issues to flag:
- severity labels not justified by evidence
- speculative claims stated too confidently
- conclusions that go beyond the evidence shown
- unsupported benchmarking claims
- missing assumptions needed for the conclusion

For each issue, output exactly one JSON object per line with keys:
category, severity, title, detail, original_text, correction

Rules:
- Return only JSON lines
- If there are no real issues, return nothing
"""

    log_agent_action("explainer_agent", f"Analyzing excerpt for {company}")

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        issues = _parse_issues(content)
    except Exception as exc:
        log_agent_action("explainer_agent", f"LLM error: {exc}")
        issues = []

    summary = f"Found {len(issues)} issue(s)." if issues else "No reasoning issues found."

    return {
        "issues": issues,
        "summary": summary,
        "analysis_mode": "excerpt_reasoning_audit",
    }