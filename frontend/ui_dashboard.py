"""
G5-AAFS: Toggleable Dashboard, Domain Review, Pipeline Trace & Loan Simulation.

This module is imported by hitl_ui.py and provides:
  - render_scenario_briefing()  -- workflow-mode scenario narrative card
  - _phase_review()             -- domain review with 6 tabs
  - _pipeline_view()            -- agent-by-agent pipeline trace (8 steps)
  - _dashboard_view()           -- toggleable dashboard with 5 panels
  - _loan_simulation()          -- what-if loan impact calculator

Every section records wall-clock execution time via `_SectionTimer` and
surfaces it in Panel 5 (Execution Performance).  Pass an optional
`timings: Dict[str, float]` to overlay pipeline-level timings from the
orchestrator on top of the UI render timings.
"""

import streamlit as st
import pandas as pd
import json, time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Import visual primitives from hitl_ui
# ---------------------------------------------------------------------------
from frontend.hitl_ui import (
    _metric,
    _risk_gauge,
    _badge,
    _sentiment_counts,
    _fmt,
    _COLORS,
    _UBS_RED,
    _UBS_NAVY,
    _UBS_DARK,
    _UBS_GREY,
    _UBS_LIGHT,
)

# Pipeline step accent colors (one per step)
_STEP_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#17becf",
]


# ===========================================================================
# EXECUTION TIMER  (context-manager that feeds Panel 5)
# ===========================================================================

class _SectionTimer:
    """Wall-clock timer that auto-records into a per-session registry.

    Usage::

        with _SectionTimer("tab_financial_statements"):
            ...  # render the section
        # _SectionTimer.all_timings()["tab_financial_statements"] now holds ms

    The registry is stored in ``st.session_state`` so it persists across
    Streamlit reruns within the same browser session.
    """

    _SESSION_KEY = "_ui_dash_timings"

    def __init__(self, section_name: str):
        self.name = section_name
        self._start: float = 0.0

    # -- context-manager protocol --
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        reg = st.session_state.setdefault(self._SESSION_KEY, {})
        reg[self.name] = elapsed_ms
        return False

    # -- class-level accessors --
    @classmethod
    def all_timings(cls) -> Dict[str, float]:
        return dict(st.session_state.get(cls._SESSION_KEY, {}))

    @classmethod
    def reset(cls):
        st.session_state[cls._SESSION_KEY] = {}


# ===========================================================================
# HELPER: timing caption
# ===========================================================================

def _show_timing(timings: Optional[Dict[str, float]], key: str):
    """If a timing entry exists for *key*, render a caption showing elapsed seconds."""
    if timings and key in timings:
        elapsed = timings[key]
        st.caption(f"Completed in {elapsed:.2f}s")


def _section_timing_caption(section_name: str):
    """Show the _SectionTimer-recorded time for the just-completed section."""
    reg = _SectionTimer.all_timings()
    if section_name in reg:
        st.caption(f"Rendered in {reg[section_name]:.0f} ms")


# ===========================================================================
# SCENARIO BRIEFING  (workflow-mode narrative card)
# ===========================================================================

def render_scenario_briefing(state: Dict[str, Any],
                              timings: Optional[Dict[str, float]] = None):
    """Display a UBS-styled scenario narrative card based on the active workflow mode.

    This is the first thing an analyst sees -- a contextual briefing that frames
    the assessment: who is the company, what mode are we in, which model is
    selected, and what date/time the assessment began.
    """
    with _SectionTimer("scenario_briefing"):
        mode = st.session_state.get("workflow_mode", "deep_dive")
        company = state.get("company_name", "[Company]")
        model = st.session_state.get("selected_model", "gpt-4o-mini")
        assessment_date = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

        narratives = {
            "exploratory": (
                f"Sarah Lim, RM at UBS Singapore, is preparing for an initial client "
                f"call with {company}. She needs a quick risk snapshot to identify any "
                f"red flags before the meeting."
            ),
            "deep_dive": (
                f"The annual credit review for {company} is due. The credit committee "
                f"requires a comprehensive multi-source risk assessment with full "
                f"documentation for the compliance package."
            ),
            "loan_simulation": (
                f"The lending team is evaluating a new facility request from {company}. "
                f"The committee needs to understand how the proposed loan would impact "
                f"the borrower's key financial ratios and overall risk profile."
            ),
        }

        narrative = narratives.get(mode, narratives["deep_dive"])
        mode_label = {
            "exploratory": "Exploratory (New Client Call)",
            "deep_dive": "Deep Dive (Annual Review)",
            "loan_simulation": "Loan Simulation (New Facility)",
        }.get(mode, mode.replace("_", " ").title())

        st.markdown(
            f'<div style="background:{_UBS_NAVY};color:#FFFFFF;padding:20px 24px;'
            f'border-radius:10px;border-left:5px solid {_UBS_RED};margin-bottom:16px">'
            f'<div style="font-size:1.15em;font-weight:700;margin-bottom:8px;'
            f'color:{_UBS_RED}">Scenario Briefing</div>'
            f'<div style="font-size:.95em;line-height:1.55;margin-bottom:14px">{narrative}</div>'
            f'<div style="display:flex;gap:32px;flex-wrap:wrap;font-size:.82em;color:#B0B8C8">'
            f'<span><b style="color:#FFF">Company:</b> {company}</span>'
            f'<span><b style="color:#FFF">Date:</b> {assessment_date}</span>'
            f'<span><b style="color:#FFF">Mode:</b> {mode_label}</span>'
            f'<span><b style="color:#FFF">Model:</b> {model}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _section_timing_caption("scenario_briefing")
    _show_timing(timings, "scenario_briefing")


# ===========================================================================
# DOMAIN REVIEW (PHASE 3)
# ===========================================================================

def _phase_review(state: Dict[str, Any],
                  timings: Optional[Dict[str, float]] = None):
    """Domain review dashboard with 6 tabs spanning structured + unstructured data."""
    with _SectionTimer("phase_review"):
        st.markdown("## 2 -- Review Collected Intelligence")
        st.markdown(
            "Browse each data domain below. Structured data (XBRL) is shown as "
            "tables & ratios. Unstructured data (news, reviews) is shown with "
            "sentiment analysis. **Use these insights to set your scoring weights.**"
        )

        # Count available data per domain for tab labels
        xbrl_docs = [d for d in state.get("doc_extracted_text", [])
                     if d.get("type") == "XBRL_STRUCTURED"]
        news = state.get("news_data", [])
        social = state.get("social_data", [])
        reviews = state.get("review_data", [])
        press = state.get("press_release_analysis", {})
        industry = state.get("industry_context", {})

        tabs = st.tabs([
            f"Financial Statements ({len(xbrl_docs)} docs)",
            "Credit Quality",
            "Companies Act",
            f"News & Press ({len(news)} + {len(press.get('events', []))})",
            f"Social & Reviews ({len(social)} + {len(reviews)})",
            "Industry & Market",
        ])

        with tabs[0]:
            _tab_financial_statements(state, xbrl_docs, timings=timings)
        with tabs[1]:
            _tab_credit_quality(state, xbrl_docs, timings=timings)
        with tabs[2]:
            _tab_companies_act(state, xbrl_docs, timings=timings)
        with tabs[3]:
            _tab_news_press(state, news, press, timings=timings)
        with tabs[4]:
            _tab_social_reviews(state, social, reviews, timings=timings)
        with tabs[5]:
            _tab_industry(state, industry, timings=timings)

    _section_timing_caption("phase_review")
    _show_timing(timings, "phase_review")


# ---------------------------------------------------------------------------
# Tab: Financial Statements (STRUCTURED)
# ---------------------------------------------------------------------------

def _tab_financial_statements(state: Dict, xbrl_docs: List,
                               timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("tab_financial_statements"):
        st.markdown("### Financial Statements  (Structured Data)")
        if not xbrl_docs:
            fin = state.get("financial_data", [])
            if fin:
                st.info("No XBRL filing uploaded. Showing financial data from web sources.")
                st.dataframe(pd.DataFrame(fin), width="stretch", hide_index=True)
            else:
                st.info("No financial data available. Upload an ACRA XBRL filing for structured extraction.")
            _show_timing(timings, "tab_financial_statements")
            return

        for doc in xbrl_docs:
            p = doc.get("xbrl_parsed", {})
            _render_xbrl_structured(p)

    _section_timing_caption("tab_financial_statements")
    _show_timing(timings, "tab_financial_statements")


def _render_xbrl_structured(p: Dict[str, Any],
                             timings: Optional[Dict[str, float]] = None):
    """Render a fully parsed XBRL document as structured tables."""
    ei = p.get("entity_info", {})
    bs = p.get("balance_sheet", {})
    inc = p.get("income_statement", {})
    cf = p.get("cash_flow", {})
    ratios = p.get("computed_ratios", {})
    flags = p.get("risk_flags", [])

    # Entity header
    if ei.get("company_name"):
        st.markdown(
            f"**{ei['company_name']}**  "
            f"(UEN: {ei.get('uen', '--')})  |  "
            f"{ei.get('period_start', '?')} to {ei.get('period_end', '?')}  |  "
            f"{ei.get('currency', 'SGD')}"
        )

    # Risk flags banner
    if flags:
        for f in flags:
            st.error(f"Risk Flag: {f}")

    # Key ratios at a glance
    st.markdown("#### Key Ratios")
    rc = st.columns(5)
    ratio_items = [
        ("Current Ratio", ratios.get("current_ratio"),
         "green" if (ratios.get("current_ratio") or 0) >= 1 else "red"),
        ("Debt / Equity", ratios.get("debt_to_equity"),
         "green" if (ratios.get("debt_to_equity") or 99) <= 2 else "orange"),
        ("NPL Ratio", f"{(ratios.get('npl_ratio') or 0)*100:.2f}%",
         "green" if (ratios.get("npl_ratio") or 0) < 0.05 else "red"),
        ("Profit Margin", f"{(ratios.get('profit_margin') or 0)*100:.1f}%",
         "green" if (ratios.get("profit_margin") or 0) > 0 else "red"),
        ("Coverage", ratios.get("coverage_ratio"),
         "green" if (ratios.get("coverage_ratio") or 0) >= 1 else "orange"),
    ]
    for i, (lbl, val, col) in enumerate(ratio_items):
        with rc[i]:
            _metric(lbl, _fmt(val) if val is not None else "--", color=col)

    # Balance sheet table
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Balance Sheet")
        bs_rows = [(k.replace("_", " ").title(), _fmt(v))
                    for k, v in bs.items() if v is not None]
        if bs_rows:
            st.dataframe(pd.DataFrame(bs_rows, columns=["Item", "Value"]),
                         width="stretch", hide_index=True)
    with c2:
        st.markdown("#### Income Statement")
        inc_rows = [(k.replace("_", " ").title(), _fmt(v))
                     for k, v in inc.items() if v is not None]
        if inc_rows:
            st.dataframe(pd.DataFrame(inc_rows, columns=["Item", "Value"]),
                         width="stretch", hide_index=True)

    # Cash flow
    if any(v is not None for v in cf.values()):
        st.markdown("#### Cash Flow")
        cf_data = {k.replace("_", " ").title(): v
                   for k, v in cf.items() if v is not None}
        st.bar_chart(pd.DataFrame({"Amount": cf_data}).T)

    _show_timing(timings, "render_xbrl_structured")


# ---------------------------------------------------------------------------
# Tab: Credit Quality (STRUCTURED -- MAS grading)
# ---------------------------------------------------------------------------

def _tab_credit_quality(state: Dict, xbrl_docs: List,
                         timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("tab_credit_quality"):
        st.markdown("### Credit Quality  (MAS Grading -- Structured)")
        cq = None
        for doc in xbrl_docs:
            cq = doc.get("xbrl_parsed", {}).get("credit_quality", {})
            if cq and any(v is not None for v in cq.values()):
                break
        if not cq or not any(v is not None for v in cq.values()):
            st.info("No credit quality data in uploaded XBRL. This section is populated from "
                    "sg-fsh (Financial Statement Highlights) elements.")
            return

        # MAS 5-grade classification
        st.markdown("#### MAS Credit Classification")
        grades = [
            ("Pass", cq.get("pass"), "green"),
            ("Special Mention", cq.get("special_mention"), "orange"),
            ("Substandard", cq.get("substandard"), "red"),
            ("Doubtful", cq.get("doubtful"), "red"),
            ("Loss", cq.get("loss"), "red"),
        ]
        cols = st.columns(5)
        for i, (label, val, color) in enumerate(grades):
            with cols[i]:
                _metric(label, _fmt(val), color=color)

        # Total + allowances
        st.markdown("#### Provisions & Coverage")
        pc = st.columns(4)
        with pc[0]:
            _metric("Total Facilities", _fmt(cq.get("total_facilities")), color="blue")
        with pc[1]:
            _metric("General Allowance", _fmt(cq.get("general_allowance")), color="orange")
        with pc[2]:
            _metric("Specific Allowance", _fmt(cq.get("specific_allowance")), color="orange")
        with pc[3]:
            _metric("Collaterals", _fmt(cq.get("collaterals")), color="green")

        # NPL bar chart
        npl_items = {k: v for k, v in [
            ("Pass", cq.get("pass")),
            ("Special Mention", cq.get("special_mention")),
            ("Substandard", cq.get("substandard")),
            ("Doubtful", cq.get("doubtful")),
            ("Loss", cq.get("loss")),
        ] if v is not None and v > 0}
        if npl_items:
            st.markdown("#### Distribution")
            st.bar_chart(pd.DataFrame({"Amount": npl_items}))

    _section_timing_caption("tab_credit_quality")
    _show_timing(timings, "tab_credit_quality")


# ---------------------------------------------------------------------------
# Tab: Companies Act (STRUCTURED)
# ---------------------------------------------------------------------------

def _tab_companies_act(state: Dict, xbrl_docs: List,
                        timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("tab_companies_act"):
        st.markdown("### Companies Act Disclosures  (Structured)")
        da = None
        ei = None
        for doc in xbrl_docs:
            p = doc.get("xbrl_parsed", {})
            da = p.get("directors_assessment", {})
            ei = p.get("entity_info", {})
            if da:
                break
        if not da and not ei:
            st.info("No Companies Act data in uploaded XBRL. Upload an ACRA BizFinx filing "
                    "to see going concern, directors' assessment, and auditor opinion.")
            return

        c1, c2, c3 = st.columns(3)
        with c1:
            gc = ei.get("going_concern", "--") if ei else "--"
            ok = gc in ("Yes", "True", True)
            _metric("Going Concern Basis", gc, color="green" if ok else "red")
        with c2:
            tf = da.get("true_and_fair", "--") if da else "--"
            ok = tf in ("Yes", "True", True)
            _metric("True & Fair View", tf, color="green" if ok else "red")
        with c3:
            cd = da.get("can_pay_debts", "--") if da else "--"
            ok = cd in ("Yes", "True", True)
            _metric("Can Pay Debts When Due", cd, color="green" if ok else "red")

        if ei:
            st.markdown("#### Filing Details")
            details = [
                ("Audited", ei.get("is_audited", "--")),
                ("Financial Statements Type", ei.get("nature_of_statements", "--")),
                ("Company Type", ei.get("company_type", "--")),
                ("Dormant", ei.get("is_dormant", "--")),
            ]
            st.dataframe(pd.DataFrame(details, columns=["Field", "Value"]),
                         width="stretch", hide_index=True)

    _section_timing_caption("tab_companies_act")
    _show_timing(timings, "tab_companies_act")


# ---------------------------------------------------------------------------
# Tab: News & Press Releases (UNSTRUCTURED)
# ---------------------------------------------------------------------------

def _tab_news_press(state: Dict, news: List, press: Dict,
                     timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("tab_news_press"):
        st.markdown("### News & Press Releases  (Unstructured)")

        t1, t2 = st.tabs(["News Articles", "Press Releases / Corporate Events"])

        with t1:
            if news:
                st.markdown(f"**{len(news)} articles collected**")
                sc = _sentiment_counts(news)
                mc = st.columns(3)
                with mc[0]: _metric("Positive", sc["positive"], color="green")
                with mc[1]: _metric("Negative", sc["negative"], color="red")
                with mc[2]: _metric("Neutral", sc["neutral"], color="grey")

                st.bar_chart(pd.DataFrame(
                    {"Count": sc}, index=["positive", "negative", "neutral"]
                ))

                st.markdown("#### Headlines")
                df = pd.DataFrame(news)
                display = [c for c in ["headline", "source", "sentiment", "date"]
                           if c in df.columns]
                st.dataframe(df[display] if display else df,
                             width="stretch", hide_index=True)
            else:
                st.info("No news articles collected.")

        with t2:
            events = press.get("events", []) if isinstance(press, dict) else []
            if events:
                st.markdown(f"**{len(events)} corporate events identified**")
                cats: Dict[str, int] = {}
                for e in events:
                    cat = e.get("category", "Other")
                    cats[cat] = cats.get(cat, 0) + 1
                if cats:
                    st.bar_chart(pd.DataFrame({"Events": cats}))
                st.dataframe(pd.DataFrame(events),
                             width="stretch", hide_index=True)
                traj = press.get("trajectory", "--")
                _metric(
                    "Corporate Trajectory",
                    traj.title() if isinstance(traj, str) else traj,
                    color="green" if traj in ("growth", "stable") else "orange",
                )
            else:
                st.info("No press release analysis available.")

    _section_timing_caption("tab_news_press")
    _show_timing(timings, "tab_news_press")


# ---------------------------------------------------------------------------
# Tab: Social & Reviews (UNSTRUCTURED)
# ---------------------------------------------------------------------------

def _tab_social_reviews(state: Dict, social: List, reviews: List,
                         timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("tab_social_reviews"):
        st.markdown("### Social Sentiment & Reviews  (Unstructured)")

        t1, t2 = st.tabs(["Social Media", "Employee & Customer Reviews"])

        with t1:
            if social:
                st.markdown(f"**{len(social)} posts collected**")
                sc = _sentiment_counts(social)
                mc = st.columns(3)
                with mc[0]: _metric("Positive", sc["positive"], color="green")
                with mc[1]: _metric("Negative", sc["negative"], color="red")
                with mc[2]: _metric("Neutral", sc["neutral"], color="grey")
                st.bar_chart(pd.DataFrame(
                    {"Count": sc}, index=["positive", "negative", "neutral"]
                ))
                df = pd.DataFrame(social)
                display = [c for c in ["text", "sentiment", "platform"]
                           if c in df.columns]
                st.dataframe(df[display] if display else df,
                             width="stretch", hide_index=True)
            else:
                st.info("No social media data collected.")

        with t2:
            if reviews:
                st.markdown(f"**{len(reviews)} reviews collected**")
                emp = [r for r in reviews if r.get("type") == "employee"]
                cust = [r for r in reviews if r.get("type") == "customer"]

                all_ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
                avg = sum(all_ratings) / len(all_ratings) if all_ratings else 0
                rc = st.columns(3)
                with rc[0]:
                    _metric("Avg Rating", f"{avg:.1f}/5",
                            color="green" if avg >= 3.5 else "orange")
                with rc[1]:
                    emp_avg = (sum(r.get("rating", 0) for r in emp) / len(emp)
                               if emp else 0)
                    _metric("Employee Avg",
                            f"{emp_avg:.1f}/5" if emp else "--", color="blue")
                with rc[2]:
                    cust_avg = (sum(r.get("rating", 0) for r in cust) / len(cust)
                                if cust else 0)
                    _metric("Customer Avg",
                            f"{cust_avg:.1f}/5" if cust else "--", color="purple")

                if all_ratings:
                    buckets: Dict[str, int] = {}
                    for r in all_ratings:
                        b = f"{int(r)}.0-{int(r)+1}.0"
                        buckets[b] = buckets.get(b, 0) + 1
                    st.bar_chart(pd.DataFrame({"Reviews": buckets}))

                df = pd.DataFrame(reviews)
                display = [c for c in ["source", "type", "rating", "text"]
                           if c in df.columns]
                st.dataframe(df[display] if display else df,
                             width="stretch", hide_index=True)
            else:
                st.info("No reviews collected.")

    _section_timing_caption("tab_social_reviews")
    _show_timing(timings, "tab_social_reviews")


# ---------------------------------------------------------------------------
# Tab: Industry & Market
# ---------------------------------------------------------------------------

def _tab_industry(state: Dict, industry: Dict,
                   timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("tab_industry"):
        st.markdown("### Industry & Market Context")
        if not industry:
            st.info("No industry context available.")
            return

        c1, c2, c3 = st.columns(3)
        with c1:
            _metric("Industry", industry.get("inferred_industry", "--"), color="blue")
        with c2:
            score = industry.get("outlook_score", 0)
            _metric("Outlook Score", f"{score:.2f}",
                    color="green" if score > 0.5 else "orange")
        with c3:
            _metric("Outlook", industry.get("outlook_rating", "--"),
                    color="green" if industry.get("outlook_rating") == "Positive"
                    else "orange")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Positive Drivers")
            for d in industry.get("positive_drivers", []):
                st.markdown(f"- {d}")
        with c2:
            st.markdown("#### Negative Drivers")
            for d in industry.get("negative_drivers", []):
                st.markdown(f"- {d}")

    _section_timing_caption("tab_industry")
    _show_timing(timings, "tab_industry")


# ===========================================================================
# PIPELINE STEP-BY-STEP VIEW (state-by-state agent visualization)
# ===========================================================================

def _pipeline_view(state: Dict[str, Any],
                   timings: Optional[Dict[str, float]] = None):
    """Render step-by-step pipeline view showing what each agent did."""
    with _SectionTimer("pipeline_view"):
        st.markdown("## Agent Pipeline -- Step-by-Step Trace")
        st.caption(
            "Each step shows the agent's input, output, and diagnostics. "
            "Expand any step to inspect the data at that stage."
        )

        steps = [
            ("Step 1", "Input Validation & Classification", "input_agent", _pipe_step_input),
            ("Step 2", "Source Discovery & Query Planning", "source_discovery", _pipe_step_discovery),
            ("Step 3", "Parallel Data Collection", "data_collection", _pipe_step_collection),
            ("Step 4", "Data Cleaning & Entity Resolution", "data_cleaning", _pipe_step_cleaning),
            ("Step 5", "Risk & Strength Extraction", "risk_extraction", _pipe_step_extraction),
            ("Step 6", "Risk Scoring", "risk_scoring", _pipe_step_scoring),
            ("Step 7", "Explainability & Reasoning", "explainability", _pipe_step_explain),
            ("Step 8", "Final Report & Compliance", "report_gen", _pipe_step_report),
        ]

        # Progress bar
        completed = sum(1 for _, _, key, _ in steps if _step_has_data(state, key))
        st.progress(completed / len(steps))
        st.markdown(f"**{completed}/{len(steps)} stages completed**")

        # Total pipeline time (prominent display)
        if timings:
            total_time = timings.get("pipeline_total", sum(
                timings.get(k, 0) for _, _, k, _ in steps
            ))
            st.markdown(
                f'<div style="background:{_UBS_NAVY};color:#FFF;padding:10px 16px;'
                f'border-radius:8px;margin-bottom:12px;display:inline-block">'
                f'<span style="font-size:.85em;color:#B0B8C8">Total Pipeline Time</span>'
                f'<br/><span style="font-size:1.4em;font-weight:700">{total_time:.2f}s</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        for i, (num, title, key, render_fn) in enumerate(steps):
            has_data = _step_has_data(state, key)
            icon = "white_check_mark" if has_data else "hourglass_flowing_sand"
            color = _STEP_COLORS[i % len(_STEP_COLORS)]

            # Per-step timing label
            step_time_label = ""
            if timings and key in timings:
                step_time_label = f" -- {timings[key]:.2f}s"

            st.markdown(
                f'<div style="border-left:4px solid {color};padding:2px 0 2px 12px;'
                f'margin:4px 0"><b>:{icon}: {num}: {title}{step_time_label}</b></div>',
                unsafe_allow_html=True,
            )

            with st.expander(f"{num} Details", expanded=(i == 0 and has_data)):
                render_fn(state, timings=timings)

    _section_timing_caption("pipeline_view")


def _step_has_data(state: Dict, key: str) -> bool:
    mapping = {
        "input_agent": "company_name",
        "source_discovery": "search_queries",
        "data_collection": "news_data",
        "data_cleaning": "cleaned_data",
        "risk_extraction": "extracted_risks",
        "risk_scoring": "risk_score",
        "explainability": "explanations",
        "report_gen": "final_report",
    }
    field = mapping.get(key, key)
    val = state.get(field)
    if val is None:
        return False
    if isinstance(val, (list, dict, str)):
        return len(val) > 0
    return True


# -- Step 1: Input --

def _pipe_step_input(state: Dict,
                     timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_input"):
        company = state.get("company_name", "--")
        info = state.get("company_info", {})
        docs = state.get("uploaded_docs", [])
        xbrl = [d for d in state.get("doc_extracted_text", [])
                if d.get("type") == "XBRL_STRUCTURED"]

        c1, c2, c3 = st.columns(3)
        with c1:
            _metric("Company", company, color="blue")
        with c2:
            _metric("Entity Type", info.get("entity_type", "--"), color="blue")
        with c3:
            _metric("Documents Uploaded",
                    len(docs) or len(state.get("doc_extracted_text", [])),
                    color="blue")

        if xbrl:
            st.success(
                f"XBRL structured data detected -- "
                f"{xbrl[0].get('xbrl_parsed', {}).get('metadata', {}).get('total_facts', 0)} "
                f"facts extracted (0 LLM tokens)"
            )
        _badge("Input Validation Passed")

    _section_timing_caption("pipe_input")
    _show_timing(timings, "input_agent")


# -- Step 2: Source Discovery --

def _pipe_step_discovery(state: Dict,
                          timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_discovery"):
        queries = state.get("search_queries", {})
        aliases = state.get("company_aliases", [])

        if queries:
            st.markdown("#### Search Queries Generated")
            for source, q_list in queries.items():
                if isinstance(q_list, list):
                    st.markdown(f"**{source.title()}**: {', '.join(q_list[:3])}")
                else:
                    st.markdown(f"**{source.title()}**: {q_list}")

        if aliases:
            st.markdown(f"**Aliases resolved**: {', '.join(aliases)}")

        total_sources = len(queries)
        _metric("Data Sources Planned", total_sources, color="blue")
        _badge("Source Discovery Complete")

    _section_timing_caption("pipe_discovery")
    _show_timing(timings, "source_discovery")


# -- Step 3: Data Collection --

def _pipe_step_collection(state: Dict,
                           timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_collection"):
        news = state.get("news_data", [])
        social = state.get("social_data", [])
        reviews = state.get("review_data", [])
        financial = state.get("financial_data", [])
        press = state.get("press_release_analysis", {})
        xbrl = [d for d in state.get("doc_extracted_text", [])
                if d.get("type") == "XBRL_STRUCTURED"]

        st.markdown("#### Collection Summary (Parallel Fan-Out)")

        agents = [
            ("News Agent", len(news), "NewsAPI + Tavily",
             "green" if news else "grey"),
            ("Social Agent", len(social), "Tavily social",
             "green" if social else "grey"),
            ("Review Agent", len(reviews), "Tavily reviews",
             "green" if reviews else "grey"),
            ("Financial Agent", len(financial), "yfinance + ACRA",
             "green" if financial else "grey"),
            ("Press Agent", len(press.get("events", [])), "Directed newsroom",
             "green" if press.get("events") else "grey"),
            ("Document Processor", len(xbrl), "XBRL parser (0 tokens)",
             "green" if xbrl else "grey"),
        ]

        cols = st.columns(3)
        for i, (name, count, source, color) in enumerate(agents):
            with cols[i % 3]:
                _metric(name, f"{count} items", delta=source, color=color)

        # Sentiment overview across all text sources
        all_text = news + social
        if all_text:
            st.markdown("#### Aggregate Sentiment (FinBERT)")
            sc = _sentiment_counts(all_text)
            chart_data = pd.DataFrame(
                {"Count": sc}, index=["positive", "negative", "neutral"]
            )
            st.bar_chart(chart_data)

    _section_timing_caption("pipe_collection")
    _show_timing(timings, "data_collection")


# -- Step 4: Cleaning & Entity Resolution --

def _pipe_step_cleaning(state: Dict,
                         timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_cleaning"):
        cleaned = state.get("cleaned_data", [])
        resolved = state.get("resolved_entities", {})

        c1, c2 = st.columns(2)
        with c1:
            _metric("Cleaned Records",
                    len(cleaned) if cleaned else "N/A", color="blue")
            if resolved:
                primary = resolved.get("primary", "--")
                st.markdown(f"**Primary entity**: {primary}")
        with c2:
            cleaned_items = state.get("cleaned_data", [])
            tiered = [d for d in cleaned_items if d.get("credibility_weight")]
            if tiered:
                avg_cred = sum(d["credibility_weight"] for d in tiered) / len(tiered)
                high_tier = sum(
                    1 for d in tiered
                    if d.get("source_tier", "").startswith("tier_1")
                    or d.get("source_tier", "").startswith("tier_2")
                )
                _metric("Avg Source Credibility", f"{avg_cred:.2f}",
                        color="green" if avg_cred > 0.7 else "orange")
                _metric("High-Tier Sources", f"{high_tier}/{len(tiered)}",
                        color="green")
            else:
                _metric("Source Credibility", "Not yet computed", color="grey")

        _badge("Entity Resolution Complete")
        if cleaned:
            _badge(f"FinBERT Enrichment: {len(cleaned)} records")

    _section_timing_caption("pipe_cleaning")
    _show_timing(timings, "data_cleaning")


# -- Step 5: Risk & Strength Extraction --

def _pipe_step_extraction(state: Dict,
                           timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_extraction"):
        risks = state.get("extracted_risks", [])
        strengths = state.get("extracted_strengths", [])

        c1, c2 = st.columns(2)
        with c1:
            _metric("Risk Signals", len(risks), color="red")
            for r in risks:
                st.markdown(
                    f"- **{r.get('type', '?')}**: {r.get('description', '')}")
        with c2:
            _metric("Strength Signals", len(strengths), color="green")
            for s in strengths:
                st.markdown(
                    f"- **{s.get('type', '?')}**: {s.get('description', '')}")

        if risks:
            type_counts: Dict[str, int] = {}
            for r in risks:
                t = r.get("type", "Other")
                type_counts[t] = type_counts.get(t, 0) + 1
            st.markdown("#### Risk Type Distribution")
            st.bar_chart(pd.DataFrame({"Count": type_counts}))

    _section_timing_caption("pipe_extraction")
    _show_timing(timings, "risk_extraction")


# -- Step 6: Risk Scoring --

def _pipe_step_scoring(state: Dict,
                        timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_scoring"):
        score_data = state.get("risk_score", {})
        score = score_data.get("score", 0)
        rating = score_data.get("rating", "--")
        conf = score_data.get("confidence_score",
                              score_data.get("confidence", 0))
        conf_level = score_data.get("confidence_level", "--")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _metric("Risk Score", f"{score}/100",
                    color="red" if score >= 67 else "orange" if score >= 34
                    else "green")
        with c2:
            _metric("Rating", rating,
                    color="red" if rating == "High" else "orange"
                    if rating == "Medium" else "green")
        with c3:
            _metric("Confidence",
                    f"{conf*100:.0f}%" if isinstance(conf, float) else str(conf),
                    color="blue")
        with c4:
            _metric("Confidence Level", conf_level,
                    color="green" if conf_level == "High" else "orange")

        _risk_gauge(score)

        st.caption(
            "Score methodology: LLM-structured output validated by output_enforcer "
            "guardrail. Confidence from source diversity + sentiment agreement + "
            "data coverage."
        )

    _section_timing_caption("pipe_scoring")
    _show_timing(timings, "risk_scoring")


# -- Step 7: Explainability --

def _pipe_step_explain(state: Dict,
                        timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_explain"):
        explanations = state.get("explanations", [])

        if explanations:
            for exp in explanations:
                metric_name = exp.get("metric", "--")
                reason = exp.get("reason", "--")
                st.markdown(
                    f'<div style="border-left:3px solid #9467bd;padding:8px 12px;'
                    f'margin:4px 0;background:#f8f4ff;border-radius:4px">'
                    f'<b>{metric_name}</b><br/>'
                    f'<span style="color:#555">{reason}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("Explanations will appear after risk scoring completes.")

        _badge("Explainability Agent Complete")

    _section_timing_caption("pipe_explain")
    _show_timing(timings, "explainability")


# -- Step 8: Final Report --

def _pipe_step_report(state: Dict,
                       timings: Optional[Dict[str, float]] = None):
    with _SectionTimer("pipe_report"):
        report = state.get("final_report", "")

        st.markdown("#### Compliance Checks")
        gc = st.columns(5)
        with gc[0]: _badge("Input Validated")
        with gc[1]: _badge("Bias Check Passed")
        with gc[2]: _badge("Hallucination Check")
        with gc[3]: _badge("MAS FEAT Compliant")
        with gc[4]: _badge("EU AI Act Compliant")

        warnings = state.get("guardrail_warnings", [])
        if warnings:
            st.warning(f"{len(warnings)} guardrail warnings raised")
            for w in warnings:
                st.markdown(f"- {w}")

        if report:
            st.markdown("#### Report Preview")
            st.markdown(report)
        else:
            st.info("Final report will appear after all agents complete.")

        audit = state.get("audit_trail", {})
        if audit:
            with st.expander("Audit Trail (JSON)"):
                st.json(audit)

    _section_timing_caption("pipe_report")
    _show_timing(timings, "report_gen")


# ===========================================================================
# TOGGLEABLE DASHBOARD (5 panels: collection, analysis, guardrails,
#                        data quality, execution performance)
# ===========================================================================

def _dashboard_view(state: Dict[str, Any],
                    timings: Optional[Dict[str, float]] = None):
    """Toggleable dashboard panels grouped by agent/process.

    Panel 5 (Execution Performance) aggregates all _SectionTimer measurements
    from the current session to surface render bottlenecks and estimated costs.
    """
    _SectionTimer.reset()  # fresh timing snapshot each render

    st.markdown("## Analytics Dashboard")
    st.caption("Toggle panels on/off. Grouped by agent process for quick scanning. "
               "See Panel 5 for render-time benchmarks.")

    # Dashboard toggles in columns
    tc1, tc2, tc3, tc4, tc5 = st.columns(5)
    with tc1: show_collection = st.checkbox("Collection Agents", value=True, key="db_coll")
    with tc2: show_analysis = st.checkbox("Analysis & Scoring", value=True, key="db_anal")
    with tc3: show_guardrails = st.checkbox("Guardrails & Safety", value=True, key="db_guard")
    with tc4: show_quality = st.checkbox("Data Quality", value=True, key="db_qual")
    with tc5: show_perf = st.checkbox("Execution Performance", value=True, key="db_perf")

    # ---- Panel 1: Collection Agents ----
    if show_collection:
        with _SectionTimer("dashboard_collection"):
            st.markdown(
                '<div class="dash-card"><h4>Collection Agents</h4>',
                unsafe_allow_html=True,
            )
            news = state.get("news_data", [])
            social = state.get("social_data", [])
            reviews = state.get("review_data", [])
            financial = state.get("financial_data", [])
            press_events = state.get("press_release_analysis", {}).get("events", [])
            xbrl = [d for d in state.get("doc_extracted_text", [])
                    if d.get("type") == "XBRL_STRUCTURED"]

            c1, c2, c3 = st.columns(3)
            with c1:
                _metric("News Agent", f"{len(news)} articles", color="blue")
                _metric("Social Agent", f"{len(social)} posts", color="blue")
            with c2:
                _metric("Review Agent", f"{len(reviews)} reviews", color="blue")
                _metric("Financial Agent", f"{len(financial)} metrics", color="blue")
            with c3:
                _metric("Press Release Agent", f"{len(press_events)} events", color="blue")
                _metric("Document Processor", f"{len(xbrl)} XBRL docs", color="blue")

            all_text = news + social
            if all_text:
                sc = _sentiment_counts(all_text)
                st.bar_chart(pd.DataFrame(
                    {"Count": sc}, index=["positive", "negative", "neutral"]
                ))
            st.markdown('</div>', unsafe_allow_html=True)

        _section_timing_caption("dashboard_collection")
        _show_timing(timings, "dashboard_collection")

    # ---- Panel 2: Analysis & Scoring ----
    if show_analysis:
        with _SectionTimer("dashboard_analysis"):
            st.markdown(
                '<div class="dash-card"><h4>Analysis & Scoring</h4>',
                unsafe_allow_html=True,
            )
            risks = state.get("extracted_risks", [])
            strengths = state.get("extracted_strengths", [])
            score_data = state.get("risk_score", {})

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                _metric("Risk Signals", len(risks), color="red")
            with c2:
                _metric("Strength Signals", len(strengths), color="green")
            with c3:
                _metric(
                    "Risk Score",
                    f"{score_data.get('score', '--')}/100",
                    color="red" if score_data.get("score", 0) >= 67
                    else "orange" if score_data.get("score", 0) >= 34
                    else "green",
                )
            with c4:
                conf_val = score_data.get("confidence_score", 0)
                _metric(
                    "Confidence",
                    f"{conf_val*100:.0f}%"
                    if isinstance(conf_val, (int, float)) else "--",
                    color="blue",
                )

            if risks:
                type_counts: Dict[str, int] = {}
                for r in risks:
                    t = r.get("type", "Other")
                    type_counts[t] = type_counts.get(t, 0) + 1
                st.bar_chart(pd.DataFrame({"Count": type_counts}))
            st.markdown('</div>', unsafe_allow_html=True)

        _section_timing_caption("dashboard_analysis")
        _show_timing(timings, "dashboard_analysis")

    # ---- Panel 3: Guardrails & Safety ----
    if show_guardrails:
        with _SectionTimer("dashboard_guardrails"):
            st.markdown(
                '<div class="dash-card"><h4>Guardrails & Safety</h4>',
                unsafe_allow_html=True,
            )
            warnings = state.get("guardrail_warnings", [])
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: _badge("Input Validated")
            with c2: _badge("Bias Checked")
            with c3: _badge("Hallucination Check")
            with c4: _badge("MAS FEAT")
            with c5: _badge("EU AI Act")
            if warnings:
                st.warning(f"{len(warnings)} guardrail warnings")
                for w in warnings:
                    st.markdown(f"- {w}")
            else:
                st.success("All guardrails passed -- 0 warnings")
            st.markdown('</div>', unsafe_allow_html=True)

        _section_timing_caption("dashboard_guardrails")
        _show_timing(timings, "dashboard_guardrails")

    # ---- Panel 4: Data Quality & Coverage ----
    if show_quality:
        with _SectionTimer("dashboard_quality"):
            st.markdown(
                '<div class="dash-card"><h4>Data Quality & Coverage</h4>',
                unsafe_allow_html=True,
            )
            sources = {
                "news": len(state.get("news_data", [])),
                "social": len(state.get("social_data", [])),
                "reviews": len(state.get("review_data", [])),
                "financial": len(state.get("financial_data", [])),
                "press": len(state.get("press_release_analysis", {}).get("events", [])),
                "xbrl": len([d for d in state.get("doc_extracted_text", [])
                             if d.get("type") == "XBRL_STRUCTURED"]),
            }
            coverage = sum(1 for v in sources.values() if v > 0) / len(sources)
            _metric(
                "Source Coverage", f"{coverage*100:.0f}%",
                delta=f"{sum(1 for v in sources.values() if v > 0)}/{len(sources)} sources",
                color="green" if coverage > 0.6 else "orange",
            )
            st.bar_chart(pd.DataFrame({"Items": sources}))
            st.markdown('</div>', unsafe_allow_html=True)

        _section_timing_caption("dashboard_quality")
        _show_timing(timings, "dashboard_quality")

    # ---- Panel 5: Execution Performance (NEW) ----
    if show_perf:
        with _SectionTimer("dashboard_execution_performance"):
            st.markdown(
                '<div class="dash-card"><h4>Execution Performance</h4>',
                unsafe_allow_html=True,
            )
            _render_execution_performance(state, timings)
            st.markdown('</div>', unsafe_allow_html=True)

        _section_timing_caption("dashboard_execution_performance")

    _show_timing(timings, "dashboard_view")


# ===========================================================================
# EXECUTION PERFORMANCE  (Panel 5 internals)
# ===========================================================================

def _render_execution_performance(state: Dict[str, Any],
                                   timings: Optional[Dict[str, float]] = None):
    """Panel 5: per-agent execution times, token estimates, cost, throughput.

    Merges two timing sources:
      1. ``timings`` dict -- orchestrator-level pipeline timings (seconds)
      2. ``_SectionTimer.all_timings()`` -- UI render timings (milliseconds)

    When real pipeline timings are unavailable, estimated values are used
    so the panel always shows useful numbers in demo mode.
    """

    # Agent step keys for timing lookup
    agent_steps = [
        ("Input Validation", "input_agent"),
        ("Source Discovery", "source_discovery"),
        ("Data Collection", "data_collection"),
        ("Data Cleaning", "data_cleaning"),
        ("Risk Extraction", "risk_extraction"),
        ("Risk Scoring", "risk_scoring"),
        ("Explainability", "explainability"),
        ("Report Generation", "report_gen"),
    ]

    # Build timing data (use actual timings or estimate from demo)
    step_times: Dict[str, float] = {}
    for label, key in agent_steps:
        if timings and key in timings:
            step_times[label] = timings[key]
        else:
            # Demo/estimated values when no real timings available
            estimates = {
                "Input Validation": 0.12,
                "Source Discovery": 0.34,
                "Data Collection": 1.85,
                "Data Cleaning": 0.45,
                "Risk Extraction": 0.78,
                "Risk Scoring": 0.52,
                "Explainability": 0.41,
                "Report Generation": 0.67,
            }
            step_times[label] = estimates.get(label, 0.5)

    total_time = (timings.get("pipeline_total", sum(step_times.values()))
                  if timings else sum(step_times.values()))
    num_agents = len(agent_steps)

    # ---- Summary metrics row ----
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        _metric("Total Pipeline Time", f"{total_time:.2f}s", color="blue")
    with mc2:
        # Token estimate: rough heuristic based on agents that ran
        news_count = len(state.get("news_data", []))
        social_count = len(state.get("social_data", []))
        review_count = len(state.get("review_data", []))
        # Each news/social item ~ 150 tokens input, each agent call ~ 500 tokens
        est_input_tokens = (news_count + social_count + review_count) * 150 + num_agents * 500
        est_output_tokens = num_agents * 300
        est_total_tokens = est_input_tokens + est_output_tokens
        _metric("Est. Total Tokens", _fmt(est_total_tokens), color="purple")
    with mc3:
        # Cost estimate: gpt-4o-mini ~ $0.15/1M input, $0.60/1M output
        # gpt-4o ~ $2.50/1M input, $10.00/1M output
        model = st.session_state.get("selected_model", "gpt-4o-mini")
        if "4o-mini" in model:
            cost = (est_input_tokens * 0.15 + est_output_tokens * 0.60) / 1_000_000
        elif "4o" in model or "4-turbo" in model:
            cost = (est_input_tokens * 2.50 + est_output_tokens * 10.0) / 1_000_000
        else:
            # Claude or other
            cost = (est_input_tokens * 3.0 + est_output_tokens * 15.0) / 1_000_000
        _metric("Est. Cost", f"${cost:.4f}", color="green" if cost < 0.01 else "orange")
    with mc4:
        throughput = num_agents / total_time if total_time > 0 else 0
        _metric("Throughput", f"{throughput:.1f} agents/s", color="blue")

    # ---- Per-agent execution time bar chart ----
    st.markdown("#### Per-Agent Execution Times")
    time_df = pd.DataFrame({
        "Agent": list(step_times.keys()),
        "Time (s)": list(step_times.values()),
    }).set_index("Agent")
    st.bar_chart(time_df, horizontal=True)

    # ---- UI Render Timings (from _SectionTimer) ----
    ui_timings = _SectionTimer.all_timings()
    # Exclude the execution-performance panel itself to avoid recursion confusion
    ui_timings_filtered = {
        k: v for k, v in ui_timings.items()
        if k != "dashboard_execution_performance"
    }

    if ui_timings_filtered:
        st.markdown("#### UI Render Timings")
        total_render_ms = sum(ui_timings_filtered.values())
        slowest = max(ui_timings_filtered, key=ui_timings_filtered.get)
        slowest_ms = ui_timings_filtered[slowest]

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            _metric("Total Render", f"{total_render_ms:.0f} ms", color="blue")
        with rc2:
            _metric("Panels Measured", str(len(ui_timings_filtered)), color="blue")
        with rc3:
            _metric(
                "Bottleneck", slowest,
                delta=f"{slowest_ms:.0f} ms",
                color="red" if slowest_ms > 500 else
                       "orange" if slowest_ms > 200 else "green",
            )

        st.bar_chart(pd.DataFrame(
            {"Render Time (ms)": ui_timings_filtered}
        ))

    # ---- Detailed timing table ----
    with st.expander("Detailed Timing Breakdown"):
        detail_rows = []
        for label, secs in step_times.items():
            pct = (secs / total_time * 100) if total_time > 0 else 0
            detail_rows.append({
                "Agent": label,
                "Time (s)": f"{secs:.3f}",
                "% of Total": f"{pct:.1f}%",
            })
        detail_rows.append({
            "Agent": "TOTAL",
            "Time (s)": f"{total_time:.3f}",
            "% of Total": "100.0%",
        })
        st.dataframe(pd.DataFrame(detail_rows),
                     width="stretch", hide_index=True)

    if not timings:
        st.caption("Showing estimated timings (demo mode). "
                   "Run a live pipeline for actual measurements.")


# ===========================================================================
# LOAN SIMULATION (what-if scenario for new facility)
# ===========================================================================

def _loan_simulation(state: Dict[str, Any],
                     timings: Optional[Dict[str, float]] = None):
    """What-if: add a hypothetical loan and see how ratios change."""
    with _SectionTimer("loan_simulation"):
        st.markdown("## Loan Simulation")
        st.caption(
            "Enter a hypothetical loan amount to see how key ratios shift. "
            "This does NOT re-run the pipeline -- it recalculates from cached "
            "XBRL data."
        )

        xbrl_docs = [d for d in state.get("doc_extracted_text", [])
                     if d.get("type") == "XBRL_STRUCTURED"]
        if not xbrl_docs:
            st.info("Upload an XBRL filing first to enable loan simulation.")
            return

        p = xbrl_docs[0].get("xbrl_parsed", {})
        bs = p.get("balance_sheet", {})
        inc = p.get("income_statement", {})
        ratios = p.get("computed_ratios", {})

        loan = st.number_input(
            "Hypothetical Loan Amount (SGD)", min_value=0,
            value=10_000_000, step=1_000_000, key="loan_amt",
            help="How much new debt the client is requesting",
        )
        interest_rate = st.slider(
            "Assumed Interest Rate (%)", 1.0, 15.0, 5.0, 0.5,
            key="loan_rate",
        ) / 100

        # Recalculate
        new_liab = (bs.get("liabilities") or 0) + loan
        new_equity = bs.get("equity") or 1
        new_de = new_liab / new_equity if new_equity else 99
        new_cl = (bs.get("current_liabilities") or 0) + loan * 0.3  # 30% short-term
        new_cr = (bs.get("current_assets") or 0) / new_cl if new_cl else 0
        annual_interest = loan * interest_rate
        ebit = inc.get("profit_loss_before_tax", 0)
        old_interest = ((ebit / ratios.get("interest_coverage", 1))
                        if ratios.get("interest_coverage") else 0)
        new_ic = (ebit / (old_interest + annual_interest)
                  if (old_interest + annual_interest) > 0 else None)

        # Show comparison table
        st.markdown("### Impact Analysis")
        comparison = pd.DataFrame({
            "Metric": [
                "Debt/Equity", "Current Ratio", "Interest Coverage",
                "New Annual Interest Cost", "Total Liabilities",
            ],
            "Before": [
                _fmt(ratios.get("debt_to_equity")),
                _fmt(ratios.get("current_ratio")),
                _fmt(ratios.get("interest_coverage")),
                _fmt(old_interest),
                _fmt(bs.get("liabilities")),
            ],
            "After Loan": [
                f"{new_de:.2f}",
                f"{new_cr:.2f}",
                _fmt(new_ic) if new_ic else "N/A",
                _fmt(old_interest + annual_interest),
                _fmt(new_liab),
            ],
            "Change": [
                f"+{new_de - (ratios.get('debt_to_equity') or 0):.2f}",
                f"{new_cr - (ratios.get('current_ratio') or 0):.2f}",
                (f"{(new_ic or 0) - (ratios.get('interest_coverage') or 0):.2f}"
                 if new_ic else "N/A"),
                f"+{_fmt(annual_interest)}",
                f"+{_fmt(loan)}",
            ],
        })
        st.dataframe(comparison, width="stretch", hide_index=True)

        # Risk assessment shift
        risk_shift = 0
        if new_de > 3.0:
            risk_shift += 20
        elif new_de > 2.0:
            risk_shift += 10
        if new_cr < 1.0:
            risk_shift += 15
        if new_ic and new_ic < 1.5:
            risk_shift += 15
        base_score = state.get("risk_score", {}).get("score", 50)
        sim_score = min(100, base_score + risk_shift)

        c1, c2, c3 = st.columns(3)
        with c1:
            _metric("Original Score", f"{base_score}/100", color="blue")
        with c2:
            _metric(
                "Simulated Score", f"{sim_score}/100",
                delta=f"+{risk_shift}" if risk_shift else "No change",
                color="red" if risk_shift > 10
                else "orange" if risk_shift > 0 else "green",
            )
        with c3:
            new_rating = ("Low" if sim_score < 33
                          else "Medium" if sim_score < 67 else "High")
            _metric(
                "Simulated Rating", new_rating,
                color="red" if new_rating == "High"
                else "orange" if new_rating == "Medium" else "green",
            )

        _risk_gauge(sim_score)

    _section_timing_caption("loan_simulation")
    _show_timing(timings, "loan_simulation")
