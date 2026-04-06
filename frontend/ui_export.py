"""
Selective Section Export & Email Module for G5-AAFS Credit Risk Workstation.

Lets analysts choose WHICH sections to include in their report,
organized by process, agent output, or risk factor.
"""

import streamlit as st
import pandas as pd
import json, urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_UBS_RED = "#EC0000"
_UBS_NAVY = "#0E1726"

# ── Section definitions (3 grouping modes) ──

SECTIONS_BY_PROCESS = {
    "Input Validation": "input_validation",
    "Data Collection": "data_collection",
    "Data Cleaning & Entity Resolution": "data_cleaning",
    "Risk Extraction": "risk_extraction",
    "Risk Scoring": "risk_scoring",
    "Explainability": "explainability",
    "Final Report": "final_report",
}

SECTIONS_BY_AGENT = {
    "News Agent": "news_data",
    "Social Agent": "social_data",
    "Review Agent": "review_data",
    "Financial Agent": "financial_data",
    "Press Release Agent": "press_release",
    "XBRL Parser": "xbrl_data",
    "Industry Context": "industry_context",
}

SECTIONS_BY_RISK = {
    "Financial Health": "financial_health",
    "Credit Quality": "credit_quality",
    "Regulatory Standing": "regulatory",
    "Market Position": "market_position",
    "Stakeholder Sentiment": "sentiment",
}


def _extract_section(state: Dict, key: str) -> Dict:
    """Pull relevant data for a section key."""
    extractors = {
        "input_validation": lambda s: {
            "company": s.get("company_name", "—"),
            "entity_type": s.get("company_info", {}).get("entity_type", "—"),
        },
        "data_collection": lambda s: {
            "news_count": len(s.get("news_data", [])),
            "social_count": len(s.get("social_data", [])),
            "review_count": len(s.get("review_data", [])),
            "financial_count": len(s.get("financial_data", [])),
            "press_events": len(s.get("press_release_analysis", {}).get("events", [])),
        },
        "data_cleaning": lambda s: {
            "cleaned_records": len(s.get("cleaned_data", [])),
            "resolved_entity": s.get("resolved_entities", {}).get("primary", "—"),
        },
        "risk_extraction": lambda s: {
            "risks": s.get("extracted_risks", []),
            "strengths": s.get("extracted_strengths", []),
        },
        "risk_scoring": lambda s: s.get("risk_score", {}),
        "explainability": lambda s: {"explanations": s.get("explanations", [])},
        "final_report": lambda s: {"report": s.get("final_report", "")},
        "news_data": lambda s: {"articles": s.get("news_data", [])},
        "social_data": lambda s: {"posts": s.get("social_data", [])},
        "review_data": lambda s: {"reviews": s.get("review_data", [])},
        "financial_data": lambda s: {"metrics": s.get("financial_data", [])},
        "press_release": lambda s: s.get("press_release_analysis", {}),
        "xbrl_data": lambda s: {
            "docs": [d for d in s.get("doc_extracted_text", [])
                     if d.get("type") == "XBRL_STRUCTURED"]
        },
        "industry_context": lambda s: s.get("industry_context", {}),
        "financial_health": lambda s: {
            "risks": [r for r in s.get("extracted_risks", [])
                      if "financial" in r.get("type", "").lower() or
                         "leverage" in r.get("type", "").lower()],
            "explanations": [e for e in s.get("explanations", [])
                             if "financial" in e.get("metric", "").lower()],
        },
        "credit_quality": lambda s: {
            "risks": [r for r in s.get("extracted_risks", [])
                      if "credit" in r.get("type", "").lower() or
                         "npl" in r.get("description", "").lower()],
        },
        "regulatory": lambda s: {
            "risks": [r for r in s.get("extracted_risks", [])
                      if "regulatory" in r.get("type", "").lower() or
                         "mas" in r.get("description", "").lower()],
        },
        "market_position": lambda s: {
            "industry": s.get("industry_context", {}),
            "press": s.get("press_release_analysis", {}),
        },
        "sentiment": lambda s: {
            "social": s.get("social_data", []),
            "reviews": s.get("review_data", []),
        },
    }
    fn = extractors.get(key, lambda s: {})
    return fn(state)


def build_selective_report(state: Dict, selected: List[str],
                           fmt: str = "markdown") -> str:
    """Build report with only selected sections."""
    company = state.get("company_name", "Company")
    score = st.session_state.get("composite_score",
                                  state.get("risk_score", {}).get("score", "N/A"))
    rating = st.session_state.get("composite_rating",
                                   state.get("risk_score", {}).get("rating", "N/A"))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if fmt == "json":
        data = {"company": company, "score": score, "rating": rating,
                "generated": ts, "sections": {}}
        all_defs = {**SECTIONS_BY_PROCESS, **SECTIONS_BY_AGENT, **SECTIONS_BY_RISK}
        for label, key in all_defs.items():
            if key in selected:
                data["sections"][label] = _extract_section(state, key)
        return json.dumps(data, indent=2, default=str)

    if fmt == "csv":
        rows = [f"Company,{company}",
                f"Score,{score}",
                f"Rating,{rating}",
                f"Date,{ts}",
                "---,---"]
        all_defs = {**SECTIONS_BY_PROCESS, **SECTIONS_BY_AGENT, **SECTIONS_BY_RISK}
        for label, key in all_defs.items():
            if key in selected:
                sec = _extract_section(state, key)
                rows.append(f"Section,{label}")
                for k, v in sec.items():
                    if isinstance(v, list):
                        rows.append(f"{k},count={len(v)}")
                    else:
                        rows.append(f"{k},{v}")
        return "\n".join(rows)

    # Markdown (default)
    lines = [
        f"# Credit Risk Assessment: {company}",
        f"**Score**: {score}/100 | **Rating**: {rating} | **Date**: {ts}",
        "",
    ]
    all_defs = {**SECTIONS_BY_PROCESS, **SECTIONS_BY_AGENT, **SECTIONS_BY_RISK}
    for label, key in all_defs.items():
        if key in selected:
            lines.append(f"## {label}")
            sec = _extract_section(state, key)
            if isinstance(sec, dict):
                for k, v in sec.items():
                    if isinstance(v, list):
                        lines.append(f"**{k}** ({len(v)} items)")
                        for item in v[:10]:
                            if isinstance(item, dict):
                                t = item.get("type", item.get("metric", ""))
                                d = item.get("description", item.get("reason",
                                    item.get("headline", item.get("text", str(item)))))
                                lines.append(f"- **{t}**: {d}")
                            else:
                                lines.append(f"- {item}")
                    elif isinstance(v, str) and len(v) > 50:
                        lines.append(v)
                    else:
                        lines.append(f"- **{k}**: {v}")
            lines.append("")
    return "\n".join(lines)


def render_export_panel(state: Dict[str, Any]):
    """Selective section export with checkboxes grouped by mode."""
    st.markdown("## Export Report")
    st.caption("Choose which sections to include. Organize by process, agent, or risk factor.")

    # Section grouping mode
    group_mode = st.radio("Organize sections by", ["By Process", "By Agent Output", "By Risk Factor"],
                           horizontal=True, key="export_group_mode")

    if group_mode == "By Process":
        sections = SECTIONS_BY_PROCESS
    elif group_mode == "By Agent Output":
        sections = SECTIONS_BY_AGENT
    else:
        sections = SECTIONS_BY_RISK

    # Select all / deselect all
    ac1, ac2 = st.columns(2)
    with ac1:
        if st.button("Select All", key="exp_sel_all", width="stretch"):
            for key in sections.values():
                st.session_state[f"exp_{key}"] = True
            st.rerun()
    with ac2:
        if st.button("Deselect All", key="exp_desel_all", width="stretch"):
            for key in sections.values():
                st.session_state[f"exp_{key}"] = False
            st.rerun()

    # Checkboxes
    selected = []
    cols = st.columns(3)
    for i, (label, key) in enumerate(sections.items()):
        with cols[i % 3]:
            if st.checkbox(label, value=st.session_state.get(f"exp_{key}", True),
                          key=f"exp_{key}"):
                selected.append(key)

    # Include comparison section
    history = st.session_state.get("run_history", [])
    if len(history) > 1:
        if st.checkbox("Include comparison with previous run", key="exp_comparison"):
            selected.append("comparison")

    # Format selector
    st.markdown("---")
    fmt = st.radio("Export format", ["Markdown", "JSON", "CSV"],
                    horizontal=True, key="export_fmt")
    fmt_key = fmt.lower()

    # Auto-export toggle
    st.checkbox("Auto-export when pipeline completes",
                key="auto_export",
                help="Automatically download the report when scoring finishes")

    # Preview + Download
    if selected:
        report = build_selective_report(state, selected, fmt_key)

        with st.expander("Preview", expanded=False):
            if fmt_key == "json":
                st.json(json.loads(report))
            else:
                st.text(report[:2000] + ("..." if len(report) > 2000 else ""))

        company = state.get("company_name", "company").replace(" ", "_")
        ext = {"markdown": "md", "json": "json", "csv": "csv"}[fmt_key]
        mime = {"markdown": "text/markdown", "json": "application/json",
                "csv": "text/csv"}[fmt_key]

        st.download_button(f"Download {fmt} Report",
                          report, f"risk_assessment_{company}.{ext}",
                          mime, width="stretch", type="primary")
    else:
        st.warning("Select at least one section to export.")


def render_email_section(state: Dict[str, Any]):
    """Email follow-up with mailto link."""
    st.markdown("## Email Follow-Up")

    company = state.get("company_name", "Company")
    score = st.session_state.get("composite_score",
                                  state.get("risk_score", {}).get("score", "N/A"))
    rating = st.session_state.get("composite_rating",
                                   state.get("risk_score", {}).get("rating", "N/A"))

    ec1, ec2 = st.columns([3, 1])
    with ec1:
        recipient = st.text_input("Recipient", placeholder="analyst@ubs.com",
                                  key="email_to")
    with ec2:
        cc = st.text_input("CC", placeholder="team@ubs.com", key="email_cc")

    subject = st.text_input("Subject",
                            value=f"Credit Risk: {company} — {rating} ({score}/100)",
                            key="email_subject")

    body = (f"Dear Team,\n\n"
            f"Credit risk assessment for {company}:\n"
            f"- Score: {score}/100\n"
            f"- Rating: {rating}\n"
            f"- Date: {datetime.now().strftime('%d %B %Y')}\n\n")

    for r in state.get("extracted_risks", [])[:3]:
        body += f"Risk: {r.get('type', '?')} — {r.get('description', '')}\n"
    body += "\nPlease review and provide approval.\n\nBest regards,\nG5-AAFS"

    body = st.text_area("Body", value=body, height=200, key="email_body")

    if recipient:
        params = {"subject": subject, "body": body}
        if cc:
            params["cc"] = cc
        url = f"mailto:{recipient}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
        st.markdown(
            f'<a href="{url}" target="_blank" style="display:inline-block;'
            f'background:{_UBS_RED};color:white;padding:10px 24px;border-radius:6px;'
            f'text-decoration:none;font-weight:600">Open in Email Client</a>',
            unsafe_allow_html=True)
