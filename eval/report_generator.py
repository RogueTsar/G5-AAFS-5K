"""
Report generation module for the G5-AAFS credit risk evaluation framework.

Produces both human-readable Markdown reports (suitable for UBS presentation)
and machine-readable JSON reports from evaluation metrics and per-company details.
Includes LLM-generated executive insights and recommendations.
"""

import json
from datetime import datetime
from typing import Optional

from eval.metrics import EvalMetrics
from src.core.llm import get_llm, extract_json_from_llm


def generate_markdown_report(
    metrics: EvalMetrics,
    details: list[dict],
    config: Optional[dict] = None,
) -> str:
    """Generate a formatted Markdown evaluation report.

    Produces a comprehensive report suitable for stakeholder presentation,
    including metrics summary, per-company results, guardrail statistics,
    cost analysis, and regulatory compliance status.

    Args:
        metrics: Aggregated evaluation metrics.
        details: List of per-company result dictionaries. Each should contain:
            - ``company_name`` (str)
            - ``category`` (str)
            - ``score_in_range`` (bool)
            - ``rating_match`` (bool)
            - ``risk_signal_precision`` (float)
            - ``risk_signal_recall`` (float)
            - ``overall_score`` (float)
            - ``actual_score`` (int | float, optional)
            - ``expected_range`` (list[int], optional)
        config: Optional configuration dictionary with keys such as:
            - ``model`` (str): Model used for evaluation.
            - ``pipeline_version`` (str): Version of the pipeline.
            - ``eval_date`` (str): Date of evaluation run.
            - ``guardrail_results`` (dict): Injection/spoofing test results.

    Returns:
        Formatted Markdown string.
    """
    config = config or {}
    model = config.get("model", "N/A")
    pipeline_version = config.get("pipeline_version", "N/A")
    eval_date = config.get("eval_date", datetime.now().strftime("%Y-%m-%d"))
    guardrail_results = config.get("guardrail_results", {})

    lines = []

    # --- Header ---
    lines.append("# G5-AAFS Credit Risk Assessment - Evaluation Report")
    lines.append("")
    lines.append(f"**Date:** {eval_date}")
    lines.append(f"**Pipeline Version:** {pipeline_version}")
    lines.append(f"**Model:** {model}")
    lines.append(f"**Report Generated:** {metrics.timestamp}")
    lines.append("")

    # --- Executive Summary ---
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"Evaluated **{len(details)}** companies across known defaults, "
        f"distressed/recovered, healthy, and ambiguous categories. "
        f"Overall score accuracy: **{metrics.score_accuracy:.1%}**."
    )
    lines.append("")

    # --- Metrics Summary Table ---
    lines.append("## Metrics Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Score Accuracy | {metrics.score_accuracy:.2%} |")
    lines.append(f"| Risk Signal Precision | {metrics.precision:.2%} |")
    lines.append(f"| Risk Signal Recall | {metrics.recall:.2%} |")
    lines.append(f"| Entity Attribution | {metrics.entity_attribution:.2%} |")
    lines.append(f"| Schema Conformance | {metrics.schema_conformance:.2%} |")
    lines.append(f"| Bias Pass Rate | {metrics.bias_pass_rate:.2%} |")
    lines.append(f"| Confidence Calibration | {metrics.confidence_calibration:.4f} |")
    lines.append(f"| Avg Latency | {metrics.avg_latency_seconds:.2f}s |")
    lines.append(f"| Total Tokens | {metrics.total_tokens_used:,} |")
    lines.append(f"| Estimated Cost | ${metrics.estimated_cost_usd:.4f} |")
    lines.append("")

    # --- Per-Company Results ---
    lines.append("## Per-Company Results")
    lines.append("")
    lines.append(
        "| Company | Category | Score in Range | Rating Match | "
        "Signal Precision | Signal Recall | Overall |"
    )
    lines.append("|---|---|---|---|---|---|---|")

    for d in details:
        company = d.get("company_name", "Unknown")
        category = d.get("category", "N/A")
        sir = "PASS" if d.get("score_in_range") else "FAIL"
        rm = "PASS" if d.get("rating_match") else "FAIL"
        sp = f"{d.get('risk_signal_precision', 0.0):.0%}"
        sr = f"{d.get('risk_signal_recall', 0.0):.0%}"
        overall = f"{d.get('overall_score', 0.0):.2f}"

        actual = d.get("actual_score")
        expected = d.get("expected_range")
        score_info = ""
        if actual is not None and expected is not None:
            score_info = f" ({actual} in [{expected[0]}-{expected[1]}])"

        lines.append(
            f"| {company}{score_info} | {category} | {sir} | {rm} | {sp} | {sr} | {overall} |"
        )

    lines.append("")

    # --- Category Breakdown ---
    lines.append("## Category Breakdown")
    lines.append("")
    categories = {}
    for d in details:
        cat = d.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "score_pass": 0, "rating_pass": 0}
        categories[cat]["total"] += 1
        if d.get("score_in_range"):
            categories[cat]["score_pass"] += 1
        if d.get("rating_match"):
            categories[cat]["rating_pass"] += 1

    lines.append("| Category | Total | Score Accuracy | Rating Accuracy |")
    lines.append("|---|---|---|---|")
    for cat, stats in sorted(categories.items()):
        score_acc = stats["score_pass"] / stats["total"] if stats["total"] else 0
        rating_acc = stats["rating_pass"] / stats["total"] if stats["total"] else 0
        lines.append(
            f"| {cat} | {stats['total']} | {score_acc:.0%} | {rating_acc:.0%} |"
        )
    lines.append("")

    # --- Guardrail Statistics ---
    lines.append("## Guardrail & Security Statistics")
    lines.append("")
    injection_results = guardrail_results.get("prompt_injection", {})
    spoofing_results = guardrail_results.get("entity_spoofing", {})

    if injection_results:
        inj_total = injection_results.get("total", 0)
        inj_blocked = injection_results.get("blocked", 0)
        inj_rate = (inj_blocked / inj_total * 100) if inj_total else 0
        lines.append(f"- **Prompt Injection Tests:** {inj_blocked}/{inj_total} blocked ({inj_rate:.0f}%)")
        by_type = injection_results.get("by_type", {})
        for attack_type, counts in sorted(by_type.items()):
            lines.append(
                f"  - {attack_type}: {counts.get('blocked', 0)}/{counts.get('total', 0)} blocked"
            )
    else:
        lines.append("- **Prompt Injection Tests:** Not evaluated")

    if spoofing_results:
        spoof_total = spoofing_results.get("total", 0)
        spoof_correct = spoofing_results.get("correct", 0)
        spoof_rate = (spoof_correct / spoof_total * 100) if spoof_total else 0
        lines.append(
            f"- **Entity Spoofing Tests:** {spoof_correct}/{spoof_total} "
            f"correctly resolved ({spoof_rate:.0f}%)"
        )
    else:
        lines.append("- **Entity Spoofing Tests:** Not evaluated")

    lines.append("")

    # --- Cost Analysis ---
    lines.append("## Cost Analysis")
    lines.append("")
    lines.append(f"- **Model:** {model}")
    lines.append(f"- **Total Tokens Used:** {metrics.total_tokens_used:,}")
    lines.append(f"- **Estimated Cost:** ${metrics.estimated_cost_usd:.4f}")
    if len(details) > 0:
        cost_per = metrics.estimated_cost_usd / len(details)
        tokens_per = metrics.total_tokens_used / len(details)
        lines.append(f"- **Cost per Company:** ${cost_per:.4f}")
        lines.append(f"- **Tokens per Company:** {tokens_per:,.0f}")
    lines.append("")

    # --- Regulatory Compliance Status ---
    lines.append("## Regulatory Compliance Status")
    lines.append("")
    lines.append("| Requirement | Status |")
    lines.append("|---|---|")

    # Determine compliance based on metrics thresholds
    score_acc_pass = metrics.score_accuracy >= 0.70
    lines.append(
        f"| Score Accuracy >= 70% | {'PASS' if score_acc_pass else 'FAIL'} |"
    )

    entity_pass = metrics.entity_attribution >= 0.95
    lines.append(
        f"| Entity Attribution >= 95% | {'PASS' if entity_pass else 'FAIL'} |"
    )

    schema_pass = metrics.schema_conformance >= 0.99
    lines.append(
        f"| Schema Conformance >= 99% | {'PASS' if schema_pass else 'FAIL'} |"
    )

    bias_pass = metrics.bias_pass_rate >= 0.90
    lines.append(
        f"| Bias Pass Rate >= 90% | {'PASS' if bias_pass else 'FAIL'} |"
    )

    latency_pass = metrics.avg_latency_seconds <= 30.0
    lines.append(
        f"| Avg Latency <= 30s | {'PASS' if latency_pass else 'FAIL'} |"
    )

    lines.append("")

    # --- Methodology Notes ---
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- **Score Accuracy**: Percentage of companies where the pipeline's "
        "numeric risk score fell within the expected range defined in ground truth."
    )
    lines.append(
        "- **Signal Precision/Recall**: Fuzzy-matched (difflib, threshold=0.65) "
        "overlap between pipeline-extracted signals and ground truth signals."
    )
    lines.append(
        "- **Entity Attribution**: Rate at which pipeline correctly identifies "
        "and attributes financial data to the intended company entity."
    )
    lines.append(
        "- **Confidence Calibration**: Mean absolute difference between predicted "
        "confidence and observed accuracy across confidence buckets."
    )
    lines.append(
        "- **Guardrail Tests**: Prompt injection payloads and entity spoofing "
        "cases designed to probe pipeline security boundaries."
    )
    lines.append("")
    lines.append("---")
    lines.append(
        "*Report generated by G5-AAFS Evaluation Framework. "
        "For questions, contact the G5-AAFS development team.*"
    )

    # --- AI-Generated Insights ---
    llm_insights = generate_llm_insights(metrics, details, config)
    if llm_insights:
        lines.append("")
        lines.append("## AI-Generated Insights")
        lines.append("")
        lines.append(llm_insights)
        lines.append("")

    return "\n".join(lines)


def generate_llm_insights(
    metrics: EvalMetrics,
    details: list[dict],
    config: Optional[dict] = None,
) -> str:
    """Use LLM to generate executive insights and recommendations.

    Analyzes the eval metrics and per-company results to produce:
    1. An executive summary paragraph
    2. Top 3 areas of concern
    3. Top 3 recommendations for improvement
    4. Compliance risk narrative

    Returns markdown text, or empty string if LLM unavailable.
    """
    llm = get_llm(temperature=0.3)
    if not llm:
        return ""

    from langchain_core.messages import SystemMessage, HumanMessage

    # Build a concise summary for the LLM
    metrics_summary = (
        f"Score Accuracy: {metrics.score_accuracy:.1%}, "
        f"Precision: {metrics.precision:.1%}, "
        f"Recall: {metrics.recall:.1%}, "
        f"Entity Attribution: {metrics.entity_attribution:.1%}, "
        f"Bias Pass Rate: {metrics.bias_pass_rate:.1%}, "
        f"Avg Latency: {metrics.avg_latency_seconds:.1f}s, "
        f"Companies Evaluated: {len(details)}"
    )

    # Identify failures for context
    failures = [d for d in details if not d.get("score_in_range") or not d.get("rating_match")]
    failure_summary = ""
    if failures:
        failure_names = [d.get("company_name", "?") for d in failures[:5]]
        failure_summary = f"\nFailed companies (sample): {', '.join(failure_names)}"

    prompt = (
        "You are a senior credit risk evaluation analyst at UBS. "
        "Based on these pipeline evaluation results, provide actionable insights.\n\n"
        f"METRICS:\n{metrics_summary}{failure_summary}\n\n"
        "Write in markdown format:\n"
        "1. **Executive Summary** (2-3 sentences on overall pipeline health)\n"
        "2. **Top Concerns** (bullet list, max 3 items)\n"
        "3. **Recommendations** (bullet list, max 3 items)\n"
        "4. **Compliance Risk** (1-2 sentences on regulatory readiness)\n\n"
        "Be specific and reference the metrics. Keep it under 300 words total."
    )

    try:
        response = llm.invoke([
            SystemMessage(content="You are a senior credit risk analyst. Write concise, professional insights."),
            HumanMessage(content=prompt),
        ])
        return response.content.strip()
    except Exception:
        return "*LLM insights generation failed. Review metrics manually.*"


def generate_json_report(
    metrics: EvalMetrics,
    details: list[dict],
    config: Optional[dict] = None,
) -> str:
    """Generate a machine-readable JSON evaluation report.

    Args:
        metrics: Aggregated evaluation metrics.
        details: List of per-company result dictionaries.
        config: Optional configuration dictionary.

    Returns:
        Pretty-printed JSON string.
    """
    config = config or {}

    report = {
        "report_type": "G5-AAFS Credit Risk Evaluation",
        "generated_at": metrics.timestamp,
        "config": {
            "model": config.get("model", "N/A"),
            "pipeline_version": config.get("pipeline_version", "N/A"),
            "eval_date": config.get("eval_date", datetime.now().strftime("%Y-%m-%d")),
        },
        "summary_metrics": metrics.to_dict(),
        "per_company_results": details,
        "guardrail_results": config.get("guardrail_results", {}),
        "regulatory_compliance": {
            "score_accuracy_gte_70pct": metrics.score_accuracy >= 0.70,
            "entity_attribution_gte_95pct": metrics.entity_attribution >= 0.95,
            "schema_conformance_gte_99pct": metrics.schema_conformance >= 0.99,
            "bias_pass_rate_gte_90pct": metrics.bias_pass_rate >= 0.90,
            "avg_latency_lte_30s": metrics.avg_latency_seconds <= 30.0,
        },
    }

    return json.dumps(report, indent=2, default=str)
