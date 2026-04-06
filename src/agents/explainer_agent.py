"""Explainer Agent — deep pipeline-quality analysis with LLM-powered reasoning audit.

Performs two-pass analysis of the entire agent pipeline output:
  Pass 1 (analysis):  Contradictions, reasoning gaps, epistemic uncertainty,
                       anchoring bias, completeness gaps, severity assessment.
  Pass 2 (adversarial): Devil's advocate counterargument to the final score.

Budget: 2 LLM calls (~500 tokens total).  Falls back to static heuristics
if the LLM is unavailable.
"""

from __future__ import annotations

import json
import re
import traceback
from typing import Any, Dict, List, Optional

from src.core.llm import get_llm, sanitize_for_prompt
from src.core.logger import log_agent_action
from src.core.state import AgentState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ANALYSIS_CATEGORIES = [
    "CONTRADICTION",
    "REASONING_GAP",
    "EPISTEMIC_UNCERTAINTY",
    "ANCHORING_BIAS",
    "COMPLETENESS_GAP",
    "DATA_QUALITY",
]

_SEVERITY_LEVELS = ("CRITICAL", "HIGH", "MEDIUM", "LOW")

_MAX_CONTEXT_CHARS = 3000  # keep prompts within budget

# ---------------------------------------------------------------------------
# Helpers — extract structured signals from pipeline state
# ---------------------------------------------------------------------------


def _safe_score(risk_score: Dict[str, Any]) -> Optional[float]:
    """Pull a numeric score from the risk_score dict, tolerating various shapes."""
    if not risk_score:
        return None
    for key in ("overall_score", "score", "total_score", "composite_score",
                "final_score", "risk_score"):
        val = risk_score.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    # Try unwrapping one level (some agents nest under "result" or "data")
    for wrapper in ("result", "data", "output"):
        nested = risk_score.get(wrapper)
        if isinstance(nested, dict):
            return _safe_score(nested)
    return None


def _count_sources(state: AgentState) -> Dict[str, int]:
    """Count items in each data-source list."""
    source_keys = [
        "news_data", "social_data", "review_data",
        "financial_data", "financial_news_data",
        "doc_structured_data", "xbrl_parsed_data",
    ]
    counts: Dict[str, int] = {}
    for key in source_keys:
        data = state.get(key)
        if isinstance(data, list):
            counts[key] = len(data)
    return counts


def _build_pipeline_summary(state: AgentState) -> str:
    """Compact text digest of the full pipeline output for the LLM prompt."""
    company = sanitize_for_prompt(state.get("company_name", "Unknown"), max_length=100)
    risks = state.get("extracted_risks", [])
    strengths = state.get("extracted_strengths", [])
    risk_score = state.get("risk_score", {})
    explanations = state.get("explanations", [])
    report = state.get("final_report", "")
    source_counts = _count_sources(state)
    errors = state.get("errors", [])
    score_val = _safe_score(risk_score)

    lines: List[str] = [
        f"Company: {company}",
        f"Overall risk score: {score_val}",
        f"Data sources: {json.dumps(source_counts)}",
        f"Errors during pipeline: {len(errors)}",
    ]

    # Risks summary (truncated)
    risk_descs = [r.get("description", r.get("risk", "")) for r in risks[:8]]
    lines.append(f"Risks ({len(risks)} total): {risk_descs}")

    # Strengths summary
    str_descs = [s.get("description", s.get("strength", "")) for s in strengths[:8]]
    lines.append(f"Strengths ({len(strengths)} total): {str_descs}")

    # Risk score breakdown (categories/sub-scores)
    if isinstance(risk_score, dict):
        breakdown = {k: v for k, v in risk_score.items()
                     if k not in ("overall_score", "score", "result", "data")}
        if breakdown:
            lines.append(f"Score breakdown: {json.dumps(breakdown, default=str)[:600]}")

    # Explanations
    expl_texts = [e.get("text", e.get("explanation", "")) for e in explanations[:5]]
    if expl_texts:
        lines.append(f"Explanations: {expl_texts}")

    # Report excerpt
    if report:
        lines.append(f"Report excerpt: {report[:800]}")

    return "\n".join(lines)[:_MAX_CONTEXT_CHARS]


# ---------------------------------------------------------------------------
# Static / heuristic fallback analysis (no LLM required)
# ---------------------------------------------------------------------------


def _static_analysis(state: AgentState) -> Dict[str, Any]:
    """Deterministic checks that run when the LLM is unavailable."""
    issues: List[Dict[str, Any]] = []
    risks = state.get("extracted_risks", [])
    strengths = state.get("extracted_strengths", [])
    risk_score = state.get("risk_score", {})
    score_val = _safe_score(risk_score)
    source_counts = _count_sources(state)
    errors = state.get("errors", [])

    # 1. Contradiction: many strengths + high risk score (or vice versa)
    if score_val is not None:
        if score_val >= 70 and len(strengths) > len(risks):
            issues.append({
                "id": "static-contradiction-1",
                "category": "CONTRADICTION",
                "severity": "HIGH",
                "title": "High risk score despite more strengths than risks",
                "detail": (
                    f"The pipeline assigned a risk score of {score_val} but identified "
                    f"{len(strengths)} strengths vs {len(risks)} risks.  Either the "
                    "scoring model is over-weighting a single negative signal or the "
                    "risk extraction missed important negatives."
                ),
                "affected_agents": ["risk_scoring", "risk_extraction"],
                "recommendation": "Review sub-score breakdown for disproportionate weight.",
            })
        if score_val <= 30 and len(risks) > len(strengths):
            issues.append({
                "id": "static-contradiction-2",
                "category": "CONTRADICTION",
                "severity": "HIGH",
                "title": "Low risk score despite more risks than strengths",
                "detail": (
                    f"Score is {score_val} (low risk) but the pipeline found "
                    f"{len(risks)} risks vs {len(strengths)} strengths."
                ),
                "affected_agents": ["risk_scoring", "risk_extraction"],
                "recommendation": "Check if risk descriptions are being down-weighted incorrectly.",
            })

    # 2. Data sparsity — any source with zero items
    empty_sources = [k for k, v in source_counts.items() if v == 0]
    if empty_sources:
        issues.append({
            "id": "static-data-quality-1",
            "category": "DATA_QUALITY",
            "severity": "MEDIUM",
            "title": "Empty data sources detected",
            "detail": (
                f"The following sources returned no data: {empty_sources}.  "
                "Conclusions drawn without these inputs may be incomplete."
            ),
            "affected_agents": ["data_collection"],
            "recommendation": "Flag missing sources in the report and qualify conclusions.",
        })

    # 3. Anchoring bias — one source dominates
    total_items = sum(source_counts.values()) or 1
    for src, count in source_counts.items():
        if count / total_items > 0.6 and total_items > 5:
            issues.append({
                "id": f"static-anchoring-{src}",
                "category": "ANCHORING_BIAS",
                "severity": "MEDIUM",
                "title": f"Analysis may be anchored to {src}",
                "detail": (
                    f"{src} contributes {count}/{total_items} "
                    f"({count*100//total_items}%) of all data items.  The score "
                    "may be disproportionately influenced by this single channel."
                ),
                "affected_agents": ["data_collection", "risk_scoring"],
                "recommendation": "Cross-validate key findings against other sources.",
            })

    # 4. Pipeline errors
    if errors:
        issues.append({
            "id": "static-data-quality-errors",
            "category": "DATA_QUALITY",
            "severity": "HIGH" if len(errors) >= 3 else "MEDIUM",
            "title": f"{len(errors)} pipeline error(s) may have degraded output",
            "detail": "; ".join(str(e)[:120] for e in errors[:5]),
            "affected_agents": ["pipeline"],
            "recommendation": "Treat output with caution and disclose errors to reviewers.",
        })

    # 5. Completeness — missing report or explanations
    if not state.get("final_report"):
        issues.append({
            "id": "static-completeness-no-report",
            "category": "COMPLETENESS_GAP",
            "severity": "CRITICAL",
            "title": "No final report generated",
            "detail": "The pipeline did not produce a final_report string.",
            "affected_agents": ["report_generation"],
            "recommendation": "Investigate upstream failures that prevented report generation.",
        })
    if not state.get("explanations"):
        issues.append({
            "id": "static-completeness-no-explanations",
            "category": "COMPLETENESS_GAP",
            "severity": "HIGH",
            "title": "No explanations generated for the risk score",
            "detail": "Without explanations the score is opaque and non-auditable.",
            "affected_agents": ["explainability"],
            "recommendation": "Ensure explainability agent ran and produced output.",
        })

    severity_summary = _compute_severity_summary(issues)
    quality = _estimate_quality_score(issues)

    return {
        "issues": issues,
        "severity_summary": severity_summary,
        "counterargument": "LLM unavailable -- no counterargument generated.",
        "committee_questions": [
            "How reliable is the risk score given the data gaps noted above?",
            "Are there any off-balance-sheet exposures not captured?",
            "What is the company's liquidity position under stress scenarios?",
        ],
        "overall_quality_score": quality,
        "analysis_mode": "static_fallback",
    }


# ---------------------------------------------------------------------------
# LLM prompt construction
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT_TEMPLATE = """\
You are a senior credit committee advisor performing a meta-review of an \
AI-generated credit risk pipeline for {company}.

PIPELINE OUTPUT SUMMARY
========================
{summary}

YOUR TASK
=========
Analyze the pipeline output for quality issues across six dimensions.  For \
EACH issue found, output a JSON object on its own line with these exact keys:
  "category": one of {categories}
  "severity": one of CRITICAL / HIGH / MEDIUM / LOW
  "title": short title (< 80 chars)
  "detail": 1-3 sentence explanation
  "affected_agents": list of agent names involved
  "recommendation": actionable next step

Dimension definitions:
1. CONTRADICTION -- logical conflicts between different agents (e.g., risk \
   says high but strengths are numerous, or sub-scores don't add up).
2. REASONING_GAP -- an agent's conclusion does not follow from its evidence.
3. EPISTEMIC_UNCERTAINTY -- the pipeline expresses confidence that is not \
   warranted by the data (e.g., strong claim from a single news article).
4. ANCHORING_BIAS -- the score is disproportionately driven by one data \
   source or one dramatic event.
5. COMPLETENESS_GAP -- questions a credit committee would ask that the \
   pipeline does not answer (liquidity, covenants, management quality, etc.).
6. DATA_QUALITY -- missing, stale, or unreliable data inputs.

Also output a final line:
COMMITTEE_QUESTIONS: ["question 1", "question 2", ...]
(3-5 questions a credit committee would still need answered.)

Output ONLY the JSON lines and the COMMITTEE_QUESTIONS line.  No preamble."""

_COUNTERARGUMENT_PROMPT_TEMPLATE = """\
You are a devil's advocate on a credit committee reviewing {company}.

The AI pipeline assigned an overall risk score of {score} (0=no risk, \
100=maximum risk).

Key risks identified: {risks}
Key strengths identified: {strengths}

Write a concise (3-5 sentence) counterargument AGAINST the assigned score.
- If the score is high, argue why it might be too pessimistic.
- If the score is low, argue why it might be dangerously optimistic.
- If data is sparse, highlight what hidden risks may exist.

Be specific, cite the evidence provided, and suggest what additional \
diligence would resolve the disagreement.

Output ONLY the counterargument paragraph."""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_analysis_response(content: str) -> tuple[List[Dict[str, Any]], List[str]]:
    """Parse the LLM analysis response into issues and committee questions."""
    issues: List[Dict[str, Any]] = []
    committee_questions: List[str] = []

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Committee questions line
        if line.upper().startswith("COMMITTEE_QUESTIONS"):
            after_colon = line.split(":", 1)[1].strip() if ":" in line else "[]"
            try:
                parsed = json.loads(after_colon)
                if isinstance(parsed, list):
                    committee_questions = [str(q) for q in parsed]
            except json.JSONDecodeError:
                # Try to extract quoted strings
                committee_questions = re.findall(r'"([^"]+)"', after_colon)
            continue

        # Try to parse as JSON issue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "category" in obj:
                # Validate and normalise
                cat = obj.get("category", "").upper()
                if cat not in _ANALYSIS_CATEGORIES:
                    cat = "REASONING_GAP"  # safe default
                sev = obj.get("severity", "MEDIUM").upper()
                if sev not in _SEVERITY_LEVELS:
                    sev = "MEDIUM"
                issues.append({
                    "id": f"llm-{cat.lower()}-{len(issues)+1}",
                    "category": cat,
                    "severity": sev,
                    "title": str(obj.get("title", "Unnamed issue"))[:120],
                    "detail": str(obj.get("detail", ""))[:500],
                    "affected_agents": obj.get("affected_agents", []),
                    "recommendation": str(obj.get("recommendation", ""))[:300],
                })
        except json.JSONDecodeError:
            # Not a JSON line — skip silently
            continue

    return issues, committee_questions


def _compute_severity_summary(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count issues by severity level."""
    summary = {level: 0 for level in _SEVERITY_LEVELS}
    for issue in issues:
        sev = issue.get("severity", "MEDIUM").upper()
        if sev in summary:
            summary[sev] += 1
        else:
            summary["MEDIUM"] += 1
    return summary


def _estimate_quality_score(issues: List[Dict[str, Any]]) -> int:
    """Heuristic quality score (0-100) based on issue count and severity.

    Starts at 100 and deducts points per issue:
      CRITICAL = -20, HIGH = -12, MEDIUM = -6, LOW = -2
    Clamped to [0, 100].
    """
    penalties = {"CRITICAL": 20, "HIGH": 12, "MEDIUM": 6, "LOW": 2}
    score = 100
    for issue in issues:
        sev = issue.get("severity", "MEDIUM").upper()
        score -= penalties.get(sev, 6)
    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def explainer_agent(state: AgentState) -> Dict[str, Any]:
    """Deep meta-analysis of the full pipeline output.

    Returns a dict with:
        issues              - list of categorised findings (for UI cards)
        severity_summary    - {CRITICAL: n, HIGH: n, MEDIUM: n, LOW: n}
        counterargument     - devil's advocate paragraph
        committee_questions - questions a credit committee would still ask
        overall_quality_score - 0-100 pipeline quality estimate
    """
    company = sanitize_for_prompt(state.get("company_name", "Unknown"), max_length=100)
    log_agent_action("explainer_agent", f"Starting deep analysis for {company}")

    # ----- Try to get LLM ---------------------------------------------------
    llm = get_llm(temperature=0.1)

    if llm is None:
        log_agent_action(
            "explainer_agent",
            "LLM unavailable -- falling back to static analysis",
        )
        result = _static_analysis(state)
        result["explainer_issues"] = result["issues"]  # backward compat
        result["explainer_summary"] = (
            f"Static analysis found {len(result['issues'])} issues "
            f"(LLM unavailable)"
        )
        return {"explainer_analysis": result}

    # ----- Build context -----------------------------------------------------
    summary = _build_pipeline_summary(state)
    risk_score = state.get("risk_score", {})
    score_val = _safe_score(risk_score)
    risks = state.get("extracted_risks", [])
    strengths = state.get("extracted_strengths", [])

    risk_descs = [r.get("description", r.get("risk", ""))[:100] for r in risks[:6]]
    strength_descs = [s.get("description", s.get("strength", ""))[:100]
                      for s in strengths[:6]]

    # ===== PASS 1: Deep analysis (LLM call 1) ===============================
    analysis_prompt = _ANALYSIS_PROMPT_TEMPLATE.format(
        company=company,
        summary=summary,
        categories=" / ".join(_ANALYSIS_CATEGORIES),
    )

    llm_issues: List[Dict[str, Any]] = []
    committee_questions: List[str] = []

    try:
        response = llm.invoke(analysis_prompt)
        content = response.content if hasattr(response, "content") else str(response)
        log_agent_action(
            "explainer_agent",
            f"Pass 1 complete -- {len(content)} chars returned",
        )
        llm_issues, committee_questions = _parse_analysis_response(content)
    except Exception as exc:
        log_agent_action(
            "explainer_agent",
            f"Pass 1 LLM error: {exc}\n{traceback.format_exc()}",
        )

    # Merge with static checks (avoid duplicates by category)
    static_result = _static_analysis(state)
    static_issues = static_result["issues"]

    # De-duplicate: if LLM already flagged a category, skip the static one
    llm_categories = {i["category"] for i in llm_issues}
    for si in static_issues:
        if si["category"] not in llm_categories:
            llm_issues.append(si)

    # Sort: CRITICAL first, then HIGH, etc.
    severity_order = {s: i for i, s in enumerate(_SEVERITY_LEVELS)}
    llm_issues.sort(key=lambda x: severity_order.get(x.get("severity", "MEDIUM"), 2))

    # ===== PASS 2: Devil's advocate counterargument (LLM call 2) ============
    counterargument = "Could not generate counterargument."

    counter_prompt = _COUNTERARGUMENT_PROMPT_TEMPLATE.format(
        company=company,
        score=score_val if score_val is not None else "N/A",
        risks=risk_descs[:5],
        strengths=strength_descs[:5],
    )

    try:
        response = llm.invoke(counter_prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        counterargument = raw.strip()[:800]
        log_agent_action(
            "explainer_agent",
            f"Pass 2 complete -- counterargument {len(counterargument)} chars",
        )
    except Exception as exc:
        log_agent_action(
            "explainer_agent",
            f"Pass 2 LLM error: {exc}",
        )

    # Default committee questions if LLM didn't produce them
    if not committee_questions:
        committee_questions = [
            "What is the company's debt maturity profile and refinancing risk?",
            "How would a 200bp rate increase affect debt service coverage?",
            "Are there material off-balance-sheet liabilities or contingent exposures?",
            "What is management's track record through previous downturns?",
            "How concentrated is revenue across customers and geographies?",
        ]

    # ===== Assemble output ===================================================
    severity_summary = _compute_severity_summary(llm_issues)
    quality_score = _estimate_quality_score(llm_issues)

    result: Dict[str, Any] = {
        # Primary output (structured for UI rendering)
        "issues": llm_issues,
        "severity_summary": severity_summary,
        "counterargument": counterargument,
        "committee_questions": committee_questions,
        "overall_quality_score": quality_score,
        # Backward-compatible keys
        "explainer_issues": llm_issues,
        "explainer_summary": (
            f"Deep analysis found {len(llm_issues)} issues "
            f"({severity_summary.get('CRITICAL', 0)} critical, "
            f"{severity_summary.get('HIGH', 0)} high).  "
            f"Pipeline quality: {quality_score}/100."
        ),
        # Metadata
        "analysis_mode": "llm_deep_analysis",
        "llm_calls_made": 2,
    }

    log_agent_action(
        "explainer_agent",
        f"Analysis complete for {company}",
        data={
            "issue_count": len(llm_issues),
            "severity_summary": severity_summary,
            "quality_score": quality_score,
        },
    )

    return {"explainer_analysis": result}
