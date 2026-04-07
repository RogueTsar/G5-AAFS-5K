from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.llm import sanitize_for_prompt
from src.core.logger import log_agent_action
from src.core.state import AgentState


SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


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


def _count_sources(state: AgentState) -> Dict[str, int]:
    source_keys = [
        "news_data",
        "social_data",
        "review_data",
        "financial_data",
        "financial_news_data",
        "doc_structured_data",
        "xbrl_parsed_data",
        "doc_extracted_text",
    ]

    counts: Dict[str, int] = {}
    for key in source_keys:
        value = state.get(key)
        if isinstance(value, list):
            counts[key] = len(value)

    return counts


def _severity_summary(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {level: 0 for level in SEVERITY_ORDER}
    for issue in issues:
        sev = str(issue.get("severity", "MEDIUM")).upper()
        if sev in summary:
            summary[sev] += 1
        else:
            summary["MEDIUM"] += 1
    return summary


def _quality_score(issues: List[Dict[str, Any]]) -> int:
    penalties = {"CRITICAL": 20, "HIGH": 12, "MEDIUM": 6, "LOW": 2}
    score = 100
    for issue in issues:
        score -= penalties.get(str(issue.get("severity", "MEDIUM")).upper(), 6)
    return max(0, min(100, score))


def pipeline_audit_agent(state: AgentState) -> Dict[str, Any]:
    """
    Audit the full pipeline output using deterministic checks.

    Input:
      - state: full orchestrator state

    Output:
      {
        "issues": [...],
        "severity_summary": {...},
        "overall_quality_score": int,
        "summary": "...",
        "analysis_mode": "pipeline_audit"
      }
    """
    company = sanitize_for_prompt(state.get("company_name", "Unknown"), max_length=100)
    log_agent_action("pipeline_audit_agent", f"Auditing pipeline for {company}")

    issues: List[Dict[str, Any]] = []

    risks = state.get("extracted_risks", []) or []
    strengths = state.get("extracted_strengths", []) or []
    score_val = _safe_score(state.get("risk_score", {}))
    source_counts = _count_sources(state)
    errors = state.get("errors", []) or []
    final_report = state.get("final_report")
    explanations = state.get("explanations")

    if score_val is not None:
        if score_val >= 70 and len(strengths) > len(risks):
            issues.append({
                "category": "CONTRADICTION",
                "severity": "HIGH",
                "title": "High risk score despite more strengths than risks",
                "detail": (
                    f"Risk score is {score_val}, but the pipeline extracted "
                    f"{len(strengths)} strengths and {len(risks)} risks."
                ),
                "recommendation": "Review scoring weights and risk extraction balance.",
            })

        if score_val <= 30 and len(risks) > len(strengths):
            issues.append({
                "category": "CONTRADICTION",
                "severity": "HIGH",
                "title": "Low risk score despite more risks than strengths",
                "detail": (
                    f"Risk score is {score_val}, but the pipeline extracted "
                    f"{len(risks)} risks and {len(strengths)} strengths."
                ),
                "recommendation": "Check whether negative findings are underweighted.",
            })

    empty_sources = [name for name, count in source_counts.items() if count == 0]
    if empty_sources:
        issues.append({
            "category": "DATA_QUALITY",
            "severity": "MEDIUM",
            "title": "Empty data sources detected",
            "detail": f"No data found for: {empty_sources}",
            "recommendation": "Flag missing sources in the UI and qualify conclusions.",
        })

    total_items = sum(source_counts.values())
    if total_items > 5:
        for source_name, count in source_counts.items():
            if count / total_items > 0.6:
                issues.append({
                    "category": "ANCHORING_BIAS",
                    "severity": "MEDIUM",
                    "title": f"Analysis may be dominated by {source_name}",
                    "detail": (
                        f"{source_name} contributes {count}/{total_items} data items, "
                        "which may overweight one channel."
                    ),
                    "recommendation": "Cross-check conclusions across multiple sources.",
                })

    if errors:
        issues.append({
            "category": "DATA_QUALITY",
            "severity": "HIGH" if len(errors) >= 3 else "MEDIUM",
            "title": "Pipeline errors detected",
            "detail": "; ".join(str(e)[:120] for e in errors[:5]),
            "recommendation": "Surface pipeline errors to reviewers before decisioning.",
        })

    if not final_report:
        issues.append({
            "category": "COMPLETENESS_GAP",
            "severity": "CRITICAL",
            "title": "Missing final report",
            "detail": "The pipeline did not produce a final report.",
            "recommendation": "Investigate report-generation stage.",
        })

    if not explanations:
        issues.append({
            "category": "COMPLETENESS_GAP",
            "severity": "HIGH",
            "title": "Missing explanations",
            "detail": "The pipeline did not produce explanation output for its score.",
            "recommendation": "Ensure explanation stage runs before UI rendering.",
        })

    severity_summary = _severity_summary(issues)
    overall_quality_score = _quality_score(issues)

    return {
        "issues": issues,
        "severity_summary": severity_summary,
        "overall_quality_score": overall_quality_score,
        "summary": (
            f"Pipeline audit found {len(issues)} issue(s). "
            f"Quality score: {overall_quality_score}/100."
        ),
        "analysis_mode": "pipeline_audit",
    }