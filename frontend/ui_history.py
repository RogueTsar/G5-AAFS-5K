"""
Run History & Comparison Module for G5-AAFS Credit Risk Workstation.

Stores assessment snapshots in st.session_state["run_history"].
Provides side-by-side comparison with delta highlighting.
"""

import streamlit as st
import pandas as pd
import json, uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# UBS palette
_UBS_RED = "#EC0000"
_UBS_NAVY = "#0E1726"
_GREEN = "#00875A"
_ORANGE = "#D4760A"


def _init_history():
    if "run_history" not in st.session_state:
        st.session_state["run_history"] = []


def save_run(state: Dict[str, Any], config: Optional[Dict] = None) -> str:
    """Snapshot current assessment into history. Returns run_id."""
    _init_history()
    run_id = str(uuid.uuid4())[:8]
    weights = {}
    for k in ["fsh", "cca", "news", "press", "social", "reviews"]:
        raw = st.session_state.get(f"w_{k}", 0)
        weights[k] = raw

    entry = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "company_name": state.get("company_name", "—"),
        "workflow_mode": st.session_state.get("workflow_mode", "deep_dive"),
        "model_used": st.session_state.get("selected_model", "gpt-4o-mini"),
        "reviewer_rounds": st.session_state.get("reviewer_rounds", 3),
        "weights": weights,
        "composite_score": st.session_state.get("composite_score"),
        "rating": st.session_state.get("composite_rating",
                                        state.get("risk_score", {}).get("rating")),
        "risks_count": len(state.get("extracted_risks", [])),
        "strengths_count": len(state.get("extracted_strengths", [])),
        "risks": state.get("extracted_risks", []),
        "strengths": state.get("extracted_strengths", []),
        "explanations": state.get("explanations", []),
        "config": config or {
            "agent_news": st.session_state.get("agent_news", True),
            "agent_social": st.session_state.get("agent_social", True),
            "agent_review": st.session_state.get("agent_review", True),
            "agent_financial": st.session_state.get("agent_financial", True),
            "agent_press": st.session_state.get("agent_press", True),
            "agent_xbrl": st.session_state.get("agent_xbrl", True),
        },
    }
    st.session_state["run_history"].append(entry)
    return run_id


def render_history_panel():
    """Show table of past runs with expandable detail."""
    _init_history()
    history = st.session_state["run_history"]

    st.markdown("## Assessment History")

    if not history:
        st.info("No assessments saved yet. Complete an assessment and click "
                "**Save to History** to start tracking.")
        return

    # Search filter
    search = st.text_input("Filter by company name", key="hist_search",
                           placeholder="Type to filter...")
    filtered = history
    if search:
        filtered = [h for h in history if search.lower() in h["company_name"].lower()]

    st.caption(f"Showing {len(filtered)} of {len(history)} assessments")

    # Summary table
    rows = []
    for h in reversed(filtered):
        rows.append({
            "ID": h["run_id"],
            "Time": h["timestamp"][:19].replace("T", " "),
            "Company": h["company_name"],
            "Score": h.get("composite_score", "—"),
            "Rating": h.get("rating", "—"),
            "Mode": h.get("workflow_mode", "—"),
            "Model": h.get("model_used", "—"),
            "Risks": h.get("risks_count", 0),
            "Strengths": h.get("strengths_count", 0),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Expandable detail per run
    for h in reversed(filtered):
        with st.expander(f"{h['run_id']} — {h['company_name']} — "
                         f"Score: {h.get('composite_score', '—')}"):
            _render_run_detail(h)


def _render_run_detail(entry: Dict):
    """Show full details of a single run."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Score", entry.get("composite_score", "—"))
    with c2:
        st.metric("Rating", entry.get("rating", "—"))
    with c3:
        st.metric("Risks", entry.get("risks_count", 0))
    with c4:
        st.metric("Strengths", entry.get("strengths_count", 0))

    # Weights
    weights = entry.get("weights", {})
    if weights:
        st.markdown("**Scoring Weights**")
        wdf = pd.DataFrame([{
            "FSH": f"{weights.get('fsh', 0)}",
            "CCA": f"{weights.get('cca', 0)}",
            "News": f"{weights.get('news', 0)}",
            "Press": f"{weights.get('press', 0)}",
            "Social": f"{weights.get('social', 0)}",
            "Reviews": f"{weights.get('reviews', 0)}",
        }])
        st.dataframe(wdf, use_container_width=True, hide_index=True)

    # Config
    config = entry.get("config", {})
    if config:
        enabled = [k.replace("agent_", "").title() for k, v in config.items() if v]
        st.markdown(f"**Agents enabled**: {', '.join(enabled)}")
    st.markdown(f"**Model**: {entry.get('model_used', '—')} | "
                f"**Reviewer rounds**: {entry.get('reviewer_rounds', '—')} | "
                f"**Mode**: {entry.get('workflow_mode', '—')}")

    # Risks & Strengths
    risks = entry.get("risks", [])
    strengths = entry.get("strengths", [])
    if risks or strengths:
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("**Risks**")
            for r in risks:
                st.markdown(f"- **{r.get('type', '?')}**: {r.get('description', '')}")
        with rc2:
            st.markdown("**Strengths**")
            for s in strengths:
                st.markdown(f"- **{s.get('type', '?')}**: {s.get('description', '')}")

    # Download
    st.download_button("Download Run (JSON)",
                       json.dumps(entry, indent=2, default=str),
                       f"run_{entry['run_id']}.json", "application/json",
                       key=f"dl_{entry['run_id']}")


def render_comparison_tool():
    """Side-by-side comparison of two assessment runs."""
    _init_history()
    history = st.session_state["run_history"]

    st.markdown("## Compare Assessments")

    if len(history) < 2:
        st.info("Need at least 2 saved assessments to compare. "
                "Run multiple assessments with different configs and save each one.")
        return

    labels = [f"{h['run_id']} — {h['company_name']} ({h.get('composite_score', '?')}/100)"
              for h in history]

    c1, c2 = st.columns(2)
    with c1:
        idx_a = st.selectbox("Assessment A", range(len(labels)),
                              format_func=lambda i: labels[i], key="cmp_a")
    with c2:
        default_b = min(1, len(labels) - 1) if len(labels) > 1 else 0
        idx_b = st.selectbox("Assessment B", range(len(labels)),
                              format_func=lambda i: labels[i], key="cmp_b",
                              index=default_b)

    if idx_a == idx_b:
        st.warning("Select two different assessments to compare.")
        return

    a, b = history[idx_a], history[idx_b]

    # Score comparison
    st.markdown("### Score Comparison")
    sc1, sc2, sc3 = st.columns(3)
    score_a = a.get("composite_score") or 0
    score_b = b.get("composite_score") or 0
    delta = score_b - score_a

    with sc1:
        st.metric("A: Score", f"{score_a}/100", delta=a.get("rating", ""))
    with sc2:
        st.metric("B: Score", f"{score_b}/100", delta=b.get("rating", ""))
    with sc3:
        color = _GREEN if delta < 0 else _UBS_RED if delta > 0 else _ORANGE
        st.markdown(
            f'<div style="border-left:4px solid {color};padding:10px 14px;'
            f'background:#f8f9fa;border-radius:4px">'
            f'<span style="font-size:.82em;color:#555">Delta</span><br/>'
            f'<span style="font-size:1.5em;font-weight:700">'
            f'{"+" if delta > 0 else ""}{delta:.1f}</span>'
            f'<br/><small>{"Worse" if delta > 0 else "Better" if delta < 0 else "Same"}</small>'
            f'</div>', unsafe_allow_html=True)

    # Weight comparison
    st.markdown("### Weight Comparison")
    wa, wb = a.get("weights", {}), b.get("weights", {})
    all_keys = sorted(set(list(wa.keys()) + list(wb.keys())))
    if all_keys:
        wrows = []
        for k in all_keys:
            va, vb = wa.get(k, 0), wb.get(k, 0)
            d = vb - va
            wrows.append({
                "Domain": k.upper(),
                "A": va, "B": vb,
                "Delta": f"{'+' if d > 0 else ''}{d}",
            })
        st.dataframe(pd.DataFrame(wrows), use_container_width=True, hide_index=True)

    # Risk signal comparison
    st.markdown("### Risk Signals")
    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown(f"**A** ({a.get('risks_count', 0)} risks)")
        for r in a.get("risks", []):
            st.markdown(f"- {r.get('type', '?')}: {r.get('description', '')}")
    with rc2:
        st.markdown(f"**B** ({b.get('risks_count', 0)} risks)")
        for r in b.get("risks", []):
            st.markdown(f"- {r.get('type', '?')}: {r.get('description', '')}")

    # Config diff
    st.markdown("### Configuration Diff")
    ca, cb = a.get("config", {}), b.get("config", {})
    diffs = []
    for k in sorted(set(list(ca.keys()) + list(cb.keys()))):
        va, vb = ca.get(k), cb.get(k)
        if va != vb:
            diffs.append({"Setting": k, "A": str(va), "B": str(vb)})
    if diffs:
        st.dataframe(pd.DataFrame(diffs), use_container_width=True, hide_index=True)
    else:
        st.success("Identical configuration")

    # Model/mode diff
    meta_diff = []
    for field in ["model_used", "reviewer_rounds", "workflow_mode"]:
        va, vb = a.get(field), b.get(field)
        if va != vb:
            meta_diff.append({"Field": field, "A": str(va), "B": str(vb)})
    if meta_diff:
        st.dataframe(pd.DataFrame(meta_diff), use_container_width=True, hide_index=True)
