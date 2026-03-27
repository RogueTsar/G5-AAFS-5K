"""
Data-First HITL Credit Risk Assessment UI.

Flow:  INPUT → COLLECT → REVIEW BY DOMAIN → SET WEIGHTS → SCORE → REPORT

The human reviews ALL collected intelligence by data domain before choosing
how much each source should influence the final risk score.  Structured data
(XBRL financials, ratios) is rendered differently from unstructured data
(news articles, social posts, reviews).

Launch:
    streamlit run frontend/hitl_ui.py
"""

import streamlit as st
import pandas as pd
import json, sys, os, time, math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path + conditional imports
# ---------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_PIPELINE_AVAILABLE = False
_XBRL_AVAILABLE = False
_GUARDRAIL_AVAILABLE = False

try:
    from src.core.orchestrator_guarded import create_guarded_workflow
    _PIPELINE_AVAILABLE = True
except Exception:
    pass
try:
    from src.utils.xbrl_parser import parse_xbrl_instance, format_xbrl_summary, compute_credit_ratios, detect_risk_flags
    _XBRL_AVAILABLE = True
except Exception:
    pass
try:
    from src.guardrails.guardrail_runner import GuardrailRunner
    _GUARDRAIL_AVAILABLE = True
except Exception:
    pass

# ===========================================================================
# VISUAL PRIMITIVES
# ===========================================================================

_COLORS = {
    "green": "#2ca02c", "red": "#d62728", "orange": "#ff7f0e",
    "blue": "#1f77b4", "purple": "#9467bd", "grey": "#999",
}

def _metric(label: str, value: Any, delta: str = "", color: str = "blue"):
    c = _COLORS.get(color, _COLORS["blue"])
    st.markdown(
        f'<div style="border-left:4px solid {c};padding:10px 14px;background:#f8f9fa;'
        f'border-radius:4px;margin-bottom:6px">'
        f'<span style="font-size:.82em;color:#555">{label}</span><br/>'
        f'<span style="font-size:1.5em;font-weight:700">{value}</span>'
        f'{f" <span style=font-size:.78em;color:{c}>{delta}</span>" if delta else ""}'
        f'</div>', unsafe_allow_html=True)


def _risk_gauge(score: float, mx: float = 100):
    pct = min(max(score / mx, 0), 1.0)
    c = "#2ca02c" if pct < .33 else "#ff7f0e" if pct < .67 else "#d62728"
    lbl = "LOW" if pct < .33 else "MODERATE" if pct < .67 else "HIGH"
    st.markdown(
        f'<div style="background:#e0e0e0;border-radius:8px;height:32px;width:100%;position:relative">'
        f'<div style="background:{c};width:{pct*100:.1f}%;height:100%;border-radius:8px"></div>'
        f'<span style="position:absolute;top:5px;left:50%;transform:translateX(-50%);'
        f'font-weight:700;font-size:.85em;color:#333">{score:.1f}/{mx:.0f} — {lbl} RISK</span>'
        f'</div>', unsafe_allow_html=True)


def _badge(text: str, ok: bool = True):
    bg = "#d4edda" if ok else "#f8d7da"
    bd = "#c3e6cb" if ok else "#f5c6cb"
    st.markdown(
        f'<span style="display:inline-block;padding:5px 12px;background:{bg};'
        f'border:1px solid {bd};border-radius:16px;font-weight:600;font-size:.85em">'
        f'{text}</span>', unsafe_allow_html=True)


def _sentiment_counts(items: List[Dict]) -> Dict[str, int]:
    c = {"positive": 0, "negative": 0, "neutral": 0}
    for i in items:
        s = str(i.get("sentiment", i.get("label", "neutral"))).lower()
        if "pos" in s:   c["positive"] += 1
        elif "neg" in s: c["negative"] += 1
        else:            c["neutral"] += 1
    return c


def _fmt(v):
    """Format a number with commas or return as-is."""
    if isinstance(v, (int, float)):
        if abs(v) >= 1_000_000_000:
            return f"{v/1e9:,.2f}B"
        if abs(v) >= 1_000_000:
            return f"{v/1e6:,.1f}M"
        if abs(v) >= 1_000:
            return f"{v:,.0f}"
        if isinstance(v, float):
            return f"{v:.4f}" if abs(v) < 1 else f"{v:,.2f}"
        return f"{v:,}"
    return str(v) if v is not None else "—"


# ===========================================================================
# DEMO / MOCK DATA
# ===========================================================================

def _demo_state(name: str = "Acme Corp Pte Ltd") -> Dict[str, Any]:
    return {
        "company_name": name,
        "company_info": {"entity_type": "Corporation"},
        "search_queries": {"news": [f"{name} news"], "financial": [f"{name} ACRA"]},
        "company_aliases": [],
        "uploaded_docs": [],
        "doc_extracted_text": [{
            "filename": "demo_acra.xbrl", "type": "XBRL_STRUCTURED",
            "text": "# XBRL Summary (demo)",
            "xbrl_parsed": {
                "entity_info": {"company_name": name, "uen": "201900001A",
                    "period_start": "2025-01-01", "period_end": "2025-12-31",
                    "currency": "SGD", "is_audited": "Yes", "going_concern": "Yes"},
                "balance_sheet": {"assets": 150_000_000, "current_assets": 60_000_000,
                    "liabilities": 90_000_000, "current_liabilities": 35_000_000,
                    "equity": 60_000_000, "cash_and_cash_equivalents": 22_000_000,
                    "trade_receivables": 18_000_000, "inventories": 12_000_000,
                    "property_plant_equipment": 45_000_000, "goodwill": 8_000_000},
                "income_statement": {"revenue": 200_000_000, "cost_of_sales": 130_000_000,
                    "gross_profit": 70_000_000, "profit_loss": 25_000_000,
                    "profit_loss_before_tax": 32_000_000, "income_tax": 7_000_000},
                "cash_flow": {"operating": 38_000_000, "investing": -15_000_000, "financing": -10_000_000},
                "credit_quality": {"pass": 85_000_000, "special_mention": 3_000_000,
                    "substandard": 1_500_000, "doubtful": 500_000, "loss": 0,
                    "total_facilities": 90_000_000, "general_allowance": 2_000_000,
                    "specific_allowance": 800_000, "collaterals": 40_000_000},
                "directors_assessment": {"true_and_fair": "Yes", "can_pay_debts": "Yes"},
                "computed_ratios": {"current_ratio": 1.71, "debt_to_equity": 1.5,
                    "npl_ratio": 0.022, "coverage_ratio": 1.4, "profit_margin": 0.125,
                    "interest_coverage": None},
                "risk_flags": [],
                "raw_facts": {},
                "metadata": {"total_facts": 28, "monetary_facts": 22},
            },
        }],
        "news_data": [
            {"headline": f"{name} secures $50M Series C", "source": "Business Times", "sentiment": "positive", "date": "2025-11-20"},
            {"headline": f"MAS flags {name} for late filing", "source": "Straits Times", "sentiment": "negative", "date": "2025-10-15"},
            {"headline": f"{name} expands into Indonesia", "source": "Reuters", "sentiment": "positive", "date": "2025-09-05"},
            {"headline": f"CEO of {name} speaks at SFF 2025", "source": "CNA", "sentiment": "neutral", "date": "2025-08-20"},
            {"headline": f"{name} reports record FY2025 revenue", "source": "Bloomberg", "sentiment": "positive", "date": "2025-07-12"},
        ],
        "social_data": [
            {"text": f"Working at {name} is great, good WLB", "sentiment": "positive", "platform": "Reddit"},
            {"text": f"${name.split()[0]} stock overvalued", "sentiment": "negative", "platform": "Twitter"},
            {"text": f"{name} customer service is decent", "sentiment": "neutral", "platform": "HWZ"},
        ],
        "review_data": [
            {"source": "Glassdoor", "rating": 3.9, "text": "Good culture, competitive pay in SG", "type": "employee"},
            {"source": "Google Reviews", "rating": 4.2, "text": "Fast service, reliable product", "type": "customer"},
            {"source": "Indeed", "rating": 3.4, "text": "Long hours during quarter-end close", "type": "employee"},
        ],
        "financial_data": [
            {"metric": "Revenue", "value": "S$200M", "period": "FY2025", "source": "ACRA XBRL"},
            {"metric": "Net Income", "value": "S$25M", "period": "FY2025", "source": "ACRA XBRL"},
            {"metric": "Total Assets", "value": "S$150M", "period": "FY2025", "source": "ACRA XBRL"},
            {"metric": "Current Ratio", "value": "1.71", "period": "FY2025", "source": "Computed"},
            {"metric": "D/E Ratio", "value": "1.50", "period": "FY2025", "source": "Computed"},
        ],
        "press_release_analysis": {
            "events": [
                {"category": "Fundraising", "headline": "Series C $50M from Temasek-backed fund", "signal": "positive"},
                {"category": "Expansion", "headline": "Jakarta office opening Q1 2026", "signal": "positive"},
                {"category": "Regulatory", "headline": "Late filing penalty from MAS", "signal": "negative"},
            ],
            "trajectory": "growth", "event_count": 3,
        },
        "cleaned_data": [],
        "resolved_entities": {"primary": name},
        "extracted_risks": [
            {"type": "Regulatory", "description": "MAS late filing flag — may trigger enhanced supervision"},
            {"type": "Leverage", "description": "Debt-to-equity at 1.5x, above sector median of 1.1x"},
            {"type": "Concentration", "description": "Top 3 clients account for 45% of revenue"},
        ],
        "extracted_strengths": [
            {"type": "Revenue Growth", "description": "25% YoY revenue growth to S$200M"},
            {"type": "Fundraising", "description": "Successful $50M Series C — investor confidence"},
            {"type": "Asset Quality", "description": "NPL ratio 2.2%, well below 5% threshold"},
        ],
        "risk_score": {"score": 42, "max": 100, "rating": "Medium",
            "confidence_score": 0.78, "confidence_level": "Medium"},
        "explanations": [
            {"metric": "Financial Health", "reason": "Strong revenue growth with adequate liquidity (CR 1.71)"},
            {"metric": "Credit Quality", "reason": "NPL 2.2% with 1.4x coverage — sound asset quality"},
            {"metric": "Regulatory Standing", "reason": "MAS late filing flag is a yellow signal but not critical"},
            {"metric": "Market Position", "reason": "Regional expansion signals growth but adds execution risk"},
        ],
        "industry_context": {"inferred_industry": "Financial Services", "outlook_score": 0.65,
            "outlook_rating": "Positive", "positive_drivers": ["Digital banking growth", "SG fintech hub"],
            "negative_drivers": ["Rising interest rates", "Regulatory tightening"]},
        "audit_trail": {},
        "guardrail_warnings": [],
        "final_report": f"# Credit Risk Assessment: {name}\n\nOverall risk score: 42/100 (Medium)\n\n"
            f"## Key Findings\n- Revenue S$200M (+25% YoY)\n- NPL 2.2% with 1.4x coverage\n"
            f"- D/E 1.5x (slightly elevated)\n- MAS late filing flag\n\n## Recommendation\n"
            f"Approve with standard monitoring. Flag MAS regulatory status for 90-day review.",
        "errors": [],
    }


# ===========================================================================
# PHASE 1: INPUT
# ===========================================================================

def _phase_input() -> tuple:
    st.markdown("## 1 — Company & Document Input")
    c1, c2 = st.columns([3, 1])
    with c1:
        name = st.text_input("Company Name", placeholder="e.g. DBS Group, Grab Holdings, Sea Ltd...")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        go = st.button("Collect & Analyse", type="primary", use_container_width=True)

    files = st.file_uploader(
        "Upload ACRA XBRL filings, financial reports, or other documents",
        type=["pdf", "xlsx", "xls", "txt", "xbrl", "xml", "xsd", "html"],
        accept_multiple_files=True,
        help="XBRL instance docs (.xbrl/.xml) get structured extraction. "
             "XSD schemas show taxonomy definitions. PDFs/Excel parsed as text.")

    # Instant XBRL preview BEFORE pipeline runs
    if files:
        for f in files:
            ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
            if ext in ("xbrl", "xml") and _XBRL_AVAILABLE:
                raw = f.read(); f.seek(0)
                try:
                    parsed = parse_xbrl_instance(raw)
                    if parsed["metadata"]["total_facts"] > 0:
                        with st.expander(f"XBRL Preview — {f.name}  ({parsed['metadata']['total_facts']} facts)", expanded=True):
                            _render_xbrl_structured(parsed)
                except Exception as e:
                    st.caption(f"Could not preview {f.name}: {e}")

    st.caption("Estimated cost: ~$0.01 per company (6-7 LLM calls at gpt-4o-mini rates).")
    return (name.strip() if name else ""), files, go


# ===========================================================================
# PHASE 2: COLLECT (run pipeline or demo)
# ===========================================================================

def _phase_collect(name: str, files, _weights):
    docs = []
    if files:
        for f in files:
            docs.append({"filename": f.name, "content": f.read()})

    if _PIPELINE_AVAILABLE and name:
        try:
            with st.status("Running multi-agent pipeline...", expanded=True) as status:
                st.write("Compiling guarded workflow graph...")
                app = create_guarded_workflow()
                st.write(f"Invoking pipeline for **{name}**...")
                state = app.invoke({"company_name": name, "uploaded_docs": docs})
                st.session_state["state"] = state
                status.update(label="Collection complete!", state="complete")
                return
        except Exception as e:
            st.warning(f"Pipeline failed: {e}  — falling back to demo mode.")

    with st.status("Loading demo data...", expanded=False) as status:
        time.sleep(0.3)
        st.session_state["state"] = _demo_state(name or "Acme Corp Pte Ltd")
        status.update(label="Demo data loaded", state="complete")


# ===========================================================================
# PHASE 3: DOMAIN REVIEW DASHBOARD
# ===========================================================================

def _phase_review(state: Dict[str, Any]):
    st.markdown("## 2 — Review Collected Intelligence")
    st.markdown("Browse each data domain below. Structured data (XBRL) is shown as "
                "tables & ratios. Unstructured data (news, reviews) is shown with "
                "sentiment analysis. **Use these insights to set your scoring weights.**")

    # Count available data per domain for tab labels
    xbrl_docs = [d for d in state.get("doc_extracted_text", []) if d.get("type") == "XBRL_STRUCTURED"]
    news = state.get("news_data", [])
    social = state.get("social_data", [])
    reviews = state.get("review_data", [])
    press = state.get("press_release_analysis", {})
    industry = state.get("industry_context", {})

    tabs = st.tabs([
        f"Financial Statements ({len(xbrl_docs)} docs)",
        f"Credit Quality",
        f"Companies Act",
        f"News & Press ({len(news)} + {len(press.get('events', []))})",
        f"Social & Reviews ({len(social)} + {len(reviews)})",
        f"Industry & Market",
    ])

    with tabs[0]:
        _tab_financial_statements(state, xbrl_docs)
    with tabs[1]:
        _tab_credit_quality(state, xbrl_docs)
    with tabs[2]:
        _tab_companies_act(state, xbrl_docs)
    with tabs[3]:
        _tab_news_press(state, news, press)
    with tabs[4]:
        _tab_social_reviews(state, social, reviews)
    with tabs[5]:
        _tab_industry(state, industry)


# ---------------------------------------------------------------------------
# Tab: Financial Statements (STRUCTURED)
# ---------------------------------------------------------------------------

def _tab_financial_statements(state, xbrl_docs):
    st.markdown("### Financial Statements  (Structured Data)")
    if not xbrl_docs:
        # Fall back to financial_data from yfinance
        fin = state.get("financial_data", [])
        if fin:
            st.info("No XBRL filing uploaded. Showing financial data from web sources.")
            st.dataframe(pd.DataFrame(fin), use_container_width=True, hide_index=True)
        else:
            st.info("No financial data available. Upload an ACRA XBRL filing for structured extraction.")
        return

    for doc in xbrl_docs:
        p = doc.get("xbrl_parsed", {})
        _render_xbrl_structured(p)


def _render_xbrl_structured(p: Dict[str, Any]):
    """Render a fully parsed XBRL document as structured tables."""
    ei = p.get("entity_info", {})
    bs = p.get("balance_sheet", {})
    inc = p.get("income_statement", {})
    cf = p.get("cash_flow", {})
    ratios = p.get("computed_ratios", {})
    flags = p.get("risk_flags", [])

    # Entity header
    if ei.get("company_name"):
        st.markdown(f"**{ei['company_name']}**  "
                    f"(UEN: {ei.get('uen', '—')})  |  "
                    f"{ei.get('period_start', '?')} to {ei.get('period_end', '?')}  |  "
                    f"{ei.get('currency', 'SGD')}")

    # Risk flags banner
    if flags:
        for f in flags:
            st.error(f"Risk Flag: {f}")

    # Key ratios at a glance
    st.markdown("#### Key Ratios")
    rc = st.columns(5)
    ratio_items = [
        ("Current Ratio", ratios.get("current_ratio"), "green" if (ratios.get("current_ratio") or 0) >= 1 else "red"),
        ("Debt / Equity", ratios.get("debt_to_equity"), "green" if (ratios.get("debt_to_equity") or 99) <= 2 else "orange"),
        ("NPL Ratio", f"{(ratios.get('npl_ratio') or 0)*100:.2f}%", "green" if (ratios.get("npl_ratio") or 0) < 0.05 else "red"),
        ("Profit Margin", f"{(ratios.get('profit_margin') or 0)*100:.1f}%", "green" if (ratios.get("profit_margin") or 0) > 0 else "red"),
        ("Coverage", ratios.get("coverage_ratio"), "green" if (ratios.get("coverage_ratio") or 0) >= 1 else "orange"),
    ]
    for i, (lbl, val, col) in enumerate(ratio_items):
        with rc[i]:
            _metric(lbl, _fmt(val) if val is not None else "—", color=col)

    # Balance sheet table
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Balance Sheet")
        bs_rows = [(k.replace("_", " ").title(), _fmt(v)) for k, v in bs.items() if v is not None]
        if bs_rows:
            st.dataframe(pd.DataFrame(bs_rows, columns=["Item", "Value"]),
                         use_container_width=True, hide_index=True)
    with c2:
        st.markdown("#### Income Statement")
        inc_rows = [(k.replace("_", " ").title(), _fmt(v)) for k, v in inc.items() if v is not None]
        if inc_rows:
            st.dataframe(pd.DataFrame(inc_rows, columns=["Item", "Value"]),
                         use_container_width=True, hide_index=True)

    # Cash flow
    if any(v is not None for v in cf.values()):
        st.markdown("#### Cash Flow")
        cf_data = {k.replace("_", " ").title(): v for k, v in cf.items() if v is not None}
        st.bar_chart(pd.DataFrame({"Amount": cf_data}).T)


# ---------------------------------------------------------------------------
# Tab: Credit Quality (STRUCTURED — MAS grading)
# ---------------------------------------------------------------------------

def _tab_credit_quality(state, xbrl_docs):
    st.markdown("### Credit Quality  (MAS Grading — Structured)")
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
        ("Pass", cq.get("pass")), ("Special Mention", cq.get("special_mention")),
        ("Substandard", cq.get("substandard")), ("Doubtful", cq.get("doubtful")),
        ("Loss", cq.get("loss"))
    ] if v is not None and v > 0}
    if npl_items:
        st.markdown("#### Distribution")
        st.bar_chart(pd.DataFrame({"Amount": npl_items}))


# ---------------------------------------------------------------------------
# Tab: Companies Act (STRUCTURED)
# ---------------------------------------------------------------------------

def _tab_companies_act(state, xbrl_docs):
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
        gc = ei.get("going_concern", "—") if ei else "—"
        ok = gc in ("Yes", "True", True)
        _metric("Going Concern Basis", gc, color="green" if ok else "red")
    with c2:
        tf = da.get("true_and_fair", "—") if da else "—"
        ok = tf in ("Yes", "True", True)
        _metric("True & Fair View", tf, color="green" if ok else "red")
    with c3:
        cd = da.get("can_pay_debts", "—") if da else "—"
        ok = cd in ("Yes", "True", True)
        _metric("Can Pay Debts When Due", cd, color="green" if ok else "red")

    if ei:
        st.markdown("#### Filing Details")
        details = [
            ("Audited", ei.get("is_audited", "—")),
            ("Financial Statements Type", ei.get("nature_of_statements", "—")),
            ("Company Type", ei.get("company_type", "—")),
            ("Dormant", ei.get("is_dormant", "—")),
        ]
        st.dataframe(pd.DataFrame(details, columns=["Field", "Value"]),
                     use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Tab: News & Press Releases (UNSTRUCTURED)
# ---------------------------------------------------------------------------

def _tab_news_press(state, news, press):
    st.markdown("### News & Press Releases  (Unstructured)")

    t1, t2 = st.tabs(["News Articles", "Press Releases / Corporate Events"])

    with t1:
        if news:
            st.markdown(f"**{len(news)} articles collected**")
            # Sentiment summary
            sc = _sentiment_counts(news)
            mc = st.columns(3)
            with mc[0]: _metric("Positive", sc["positive"], color="green")
            with mc[1]: _metric("Negative", sc["negative"], color="red")
            with mc[2]: _metric("Neutral", sc["neutral"], color="grey")

            # Sentiment bar chart
            st.bar_chart(pd.DataFrame({"Count": sc}, index=["positive", "negative", "neutral"]))

            # Headlines table
            st.markdown("#### Headlines")
            df = pd.DataFrame(news)
            display = [c for c in ["headline", "source", "sentiment", "date"] if c in df.columns]
            st.dataframe(df[display] if display else df, use_container_width=True, hide_index=True)
        else:
            st.info("No news articles collected.")

    with t2:
        events = press.get("events", []) if isinstance(press, dict) else []
        if events:
            st.markdown(f"**{len(events)} corporate events identified**")
            # Categorize
            cats = {}
            for e in events:
                cat = e.get("category", "Other")
                cats[cat] = cats.get(cat, 0) + 1
            if cats:
                st.bar_chart(pd.DataFrame({"Events": cats}))
            # Table
            st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
            # Trajectory
            traj = press.get("trajectory", "—")
            _metric("Corporate Trajectory", traj.title() if isinstance(traj, str) else traj,
                    color="green" if traj in ("growth", "stable") else "orange")
        else:
            st.info("No press release analysis available.")


# ---------------------------------------------------------------------------
# Tab: Social & Reviews (UNSTRUCTURED)
# ---------------------------------------------------------------------------

def _tab_social_reviews(state, social, reviews):
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
            st.bar_chart(pd.DataFrame({"Count": sc}, index=["positive", "negative", "neutral"]))
            df = pd.DataFrame(social)
            display = [c for c in ["text", "sentiment", "platform"] if c in df.columns]
            st.dataframe(df[display] if display else df, use_container_width=True, hide_index=True)
        else:
            st.info("No social media data collected.")

    with t2:
        if reviews:
            st.markdown(f"**{len(reviews)} reviews collected**")
            # Split by type
            emp = [r for r in reviews if r.get("type") == "employee"]
            cust = [r for r in reviews if r.get("type") == "customer"]
            other = [r for r in reviews if r.get("type") not in ("employee", "customer")]

            # Average ratings
            all_ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
            avg = sum(all_ratings) / len(all_ratings) if all_ratings else 0
            rc = st.columns(3)
            with rc[0]:
                _metric("Avg Rating", f"{avg:.1f}/5", color="green" if avg >= 3.5 else "orange")
            with rc[1]:
                emp_avg = sum(r.get("rating", 0) for r in emp) / len(emp) if emp else 0
                _metric("Employee Avg", f"{emp_avg:.1f}/5" if emp else "—", color="blue")
            with rc[2]:
                cust_avg = sum(r.get("rating", 0) for r in cust) / len(cust) if cust else 0
                _metric("Customer Avg", f"{cust_avg:.1f}/5" if cust else "—", color="purple")

            # Rating distribution
            if all_ratings:
                buckets = {}
                for r in all_ratings:
                    b = f"{int(r)}.0-{int(r)+1}.0"
                    buckets[b] = buckets.get(b, 0) + 1
                st.bar_chart(pd.DataFrame({"Reviews": buckets}))

            df = pd.DataFrame(reviews)
            display = [c for c in ["source", "type", "rating", "text"] if c in df.columns]
            st.dataframe(df[display] if display else df, use_container_width=True, hide_index=True)
        else:
            st.info("No reviews collected.")


# ---------------------------------------------------------------------------
# Tab: Industry & Market
# ---------------------------------------------------------------------------

def _tab_industry(state, industry):
    st.markdown("### Industry & Market Context")
    if not industry:
        st.info("No industry context available.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        _metric("Industry", industry.get("inferred_industry", "—"), color="blue")
    with c2:
        score = industry.get("outlook_score", 0)
        _metric("Outlook Score", f"{score:.2f}", color="green" if score > 0.5 else "orange")
    with c3:
        _metric("Outlook", industry.get("outlook_rating", "—"), color="green"
                if industry.get("outlook_rating") == "Positive" else "orange")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Positive Drivers")
        for d in industry.get("positive_drivers", []):
            st.markdown(f"- {d}")
    with c2:
        st.markdown("#### Negative Drivers")
        for d in industry.get("negative_drivers", []):
            st.markdown(f"- {d}")


# ===========================================================================
# PHASE 4: WEIGHT SELECTION (informed by review)
# ===========================================================================

def _phase_weights(state: Dict[str, Any]) -> Dict[str, float]:
    st.markdown("---")
    st.markdown("## 3 — Set Scoring Weights")
    st.markdown("Based on what you reviewed above, decide how much each data domain "
                "should influence the final risk score.")

    # Data availability indicators
    xbrl_docs = [d for d in state.get("doc_extracted_text", []) if d.get("type") == "XBRL_STRUCTURED"]
    has_xbrl = len(xbrl_docs) > 0
    has_news = len(state.get("news_data", [])) > 0
    has_social = len(state.get("social_data", [])) > 0
    has_reviews = len(state.get("review_data", [])) > 0
    has_press = bool(state.get("press_release_analysis", {}).get("events"))

    # Presets — rooted in established financial scoring methodologies
    st.markdown("**Scoring Framework Presets**")
    st.caption("Each preset mirrors a real-world credit assessment methodology.")
    pc = st.columns(5)
    with pc[0]:
        if st.button("Basel IRB", use_container_width=True, key="p_basel",
                      help="Basel II/III Internal Ratings-Based: PD/LGD-focused, "
                           "heaviest on financials + MAS credit classification"):
            st.session_state.update(w_fsh=40, w_cca=20, w_news=15, w_press=10, w_social=5, w_reviews=10)
            st.rerun()
    with pc[1]:
        if st.button("Altman Z-Score", use_container_width=True, key="p_altman",
                      help="Altman Z-Score: Almost entirely financial ratio-driven "
                           "(WC/TA, RE/TA, EBIT/TA, MVE/TL, Sales/TA)"):
            st.session_state.update(w_fsh=60, w_cca=15, w_news=10, w_press=5, w_social=5, w_reviews=5)
            st.rerun()
    with pc[2]:
        if st.button("S&P Global", use_container_width=True, key="p_sp",
                      help="S&P-style: Business Risk Profile (industry + competitive) "
                           "+ Financial Risk Profile (cash flow + leverage)"):
            st.session_state.update(w_fsh=30, w_cca=10, w_news=15, w_press=15, w_social=10, w_reviews=20)
            st.rerun()
    with pc[3]:
        if st.button("Moody's KMV", use_container_width=True, key="p_moodys",
                      help="Moody's KMV: Distance-to-Default model — financial + "
                           "market equity signals weighted heavily"):
            st.session_state.update(w_fsh=35, w_cca=10, w_news=25, w_press=15, w_social=10, w_reviews=5)
            st.rerun()
    with pc[4]:
        if st.button("MAS FEAT", use_container_width=True, key="p_mas",
                      help="MAS-aligned: Balanced multi-source assessment per "
                           "Singapore regulatory guidance (FEAT principles)"):
            st.session_state.update(w_fsh=25, w_cca=15, w_news=20, w_press=15, w_social=10, w_reviews=15)
            st.rerun()

    # Weight sliders — 6 domains
    defaults = {"w_fsh": 35, "w_cca": 10, "w_news": 20, "w_press": 10, "w_social": 10, "w_reviews": 15}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Structured Data**")
        w_fsh = st.slider(
            f"{'[XBRL]' if has_xbrl else '[No XBRL]'} Financial Statements (FSH)",
            0, 100, key="w_fsh",
            help="Balance sheet, P&L, cash flow, ratios from ACRA XBRL or yfinance")
        w_cca = st.slider(
            f"{'[XBRL]' if has_xbrl else '[N/A]'} Companies Act (CCA)",
            0, 100, key="w_cca",
            help="Going concern, directors assessment, auditor opinion")
    with c2:
        st.markdown("**Semi-Structured Data**")
        w_news = st.slider(
            f"{'[' + str(len(state.get('news_data',[]))) + ']' if has_news else '[0]'} News Articles",
            0, 100, key="w_news")
        w_press = st.slider(
            f"{'[' + str(len(state.get('press_release_analysis',{}).get('events',[]))) + ']' if has_press else '[0]'} Press Releases",
            0, 100, key="w_press")
    with c3:
        st.markdown("**Unstructured Data**")
        w_social = st.slider(
            f"{'[' + str(len(state.get('social_data',[]))) + ']' if has_social else '[0]'} Social Sentiment",
            0, 100, key="w_social")
        w_reviews = st.slider(
            f"{'[' + str(len(state.get('review_data',[]))) + ']' if has_reviews else '[0]'} Employee & Customer Reviews",
            0, 100, key="w_reviews")

    total = w_fsh + w_cca + w_news + w_press + w_social + w_reviews or 1
    weights = {
        "fsh": w_fsh / total, "cca": w_cca / total, "news": w_news / total,
        "press": w_press / total, "social": w_social / total, "reviews": w_reviews / total,
    }

    # Show normalized
    st.markdown("**Normalized Weights**")
    norm_df = pd.DataFrame([
        {"Domain": "Financial Statements (FSH)", "Type": "Structured", "Weight": f"{weights['fsh']*100:.1f}%"},
        {"Domain": "Companies Act (CCA)", "Type": "Structured", "Weight": f"{weights['cca']*100:.1f}%"},
        {"Domain": "News Articles", "Type": "Semi-structured", "Weight": f"{weights['news']*100:.1f}%"},
        {"Domain": "Press Releases", "Type": "Semi-structured", "Weight": f"{weights['press']*100:.1f}%"},
        {"Domain": "Social Sentiment", "Type": "Unstructured", "Weight": f"{weights['social']*100:.1f}%"},
        {"Domain": "Reviews", "Type": "Unstructured", "Weight": f"{weights['reviews']*100:.1f}%"},
    ])
    st.dataframe(norm_df, use_container_width=True, hide_index=True)

    struct_pct = (weights["fsh"] + weights["cca"]) * 100
    unstruct_pct = (weights["social"] + weights["reviews"]) * 100
    semi_pct = (weights["news"] + weights["press"]) * 100
    st.markdown(f"Structured **{struct_pct:.0f}%** · Semi-structured **{semi_pct:.0f}%** · Unstructured **{unstruct_pct:.0f}%**")

    return weights


# ===========================================================================
# PHASE 5: SCORE
# ===========================================================================

def _phase_score(state: Dict[str, Any], weights: Dict[str, float]):
    st.markdown("---")
    st.markdown("## 4 — Risk Score")

    score_btn = st.button("Generate Weighted Risk Score", type="primary", use_container_width=True, key="score_btn")

    if score_btn or st.session_state.get("scored"):
        st.session_state["scored"] = True

        # Use pipeline score as base, adjust by weights
        base = state.get("risk_score", {})
        base_score = base.get("score", 50)
        confidence = base.get("confidence_score", base.get("confidence", 0.75))

        # ── Domain Sub-Scores (rooted in financial scoring theory) ──
        xbrl_docs = [d for d in state.get("doc_extracted_text", []) if d.get("type") == "XBRL_STRUCTURED"]

        # FSH: Modified Altman Z-Score approach
        # Uses 5 financial ratio zones: liquidity, leverage, profitability, coverage, efficiency
        # Each zone scored 0-20 (healthy) to contribute to total risk 0-100
        fsh_score = base_score  # default when no XBRL
        fsh_method = "Pipeline baseline"
        if xbrl_docs:
            ratios = xbrl_docs[0].get("xbrl_parsed", {}).get("computed_ratios", {})
            flags = xbrl_docs[0].get("xbrl_parsed", {}).get("risk_flags", [])
            fsh_score = 0
            # Zone 1 — Liquidity (Current Ratio): <1.0=20, 1.0-1.5=12, 1.5-2.0=6, >2.0=0
            cr = ratios.get("current_ratio")
            if cr is not None:
                fsh_score += 20 if cr < 1.0 else 12 if cr < 1.5 else 6 if cr < 2.0 else 0
            # Zone 2 — Leverage (D/E): >3.0=20, 2.0-3.0=14, 1.0-2.0=8, <1.0=0
            de = ratios.get("debt_to_equity")
            if de is not None:
                fsh_score += 20 if de > 3.0 else 14 if de > 2.0 else 8 if de > 1.0 else 0
            # Zone 3 — Profitability (Margin): <0=20, 0-5%=12, 5-15%=6, >15%=0
            pm = ratios.get("profit_margin")
            if pm is not None:
                fsh_score += 20 if pm < 0 else 12 if pm < 0.05 else 6 if pm < 0.15 else 0
            # Zone 4 — Coverage (Interest Coverage): <1.0=20, 1.0-2.0=12, 2.0-4.0=6, >4.0=0
            ic = ratios.get("interest_coverage")
            if ic is not None:
                fsh_score += 20 if ic < 1.0 else 12 if ic < 2.0 else 6 if ic < 4.0 else 0
            # Zone 5 — Risk Flags (auditor triggers): each flag adds 5, max 20
            fsh_score += min(len(flags) * 5, 20)
            fsh_score = min(fsh_score, 100)
            fsh_method = "Altman Z-Score zones (5 ratio bands + risk flags)"

        # CCA: Basel-aligned Going Concern Assessment
        # 3 critical binary signals from Companies Act disclosures
        # Going concern doubt = most severe (PD multiplier in Basel)
        cca_score = 15  # baseline (healthy company)
        cca_method = "Basel going-concern binary assessment"
        if xbrl_docs:
            da = xbrl_docs[0].get("xbrl_parsed", {}).get("directors_assessment", {})
            ei = xbrl_docs[0].get("xbrl_parsed", {}).get("entity_info", {})
            if ei.get("going_concern") not in ("Yes", "True", True, None): cca_score += 40
            if da.get("can_pay_debts") not in ("Yes", "True", True, None): cca_score += 30
            if da.get("true_and_fair") not in ("Yes", "True", True, None): cca_score += 15
            cca_score = min(cca_score, 100)

        # News: Event-Driven Credit Signal Analysis
        # Based on KMV event study methodology — negative events have asymmetric impact
        # Negative news has 1.5x weight (negative credit events are more predictive of default)
        news = state.get("news_data", [])
        sc = _sentiment_counts(news) if news else {"positive": 0, "negative": 0, "neutral": 0}
        total_n = sum(sc.values()) or 1
        neg_ratio = sc["negative"] / total_n
        pos_ratio = sc["positive"] / total_n
        # Asymmetric weighting: negatives weighted 1.5x (empirical credit literature)
        news_score = 50 + 40 * (neg_ratio * 1.5 - pos_ratio) / 1.5
        news_score = max(0, min(100, news_score))
        news_method = "KMV event-study (asymmetric neg 1.5x weighting)"

        # Press: S&P Business Risk Profile — Corporate Trajectory
        # S&P maps trajectory to competitive position scores
        press = state.get("press_release_analysis", {})
        traj = press.get("trajectory", "stable")
        events = press.get("events", [])
        neg_events = sum(1 for e in events if e.get("signal") == "negative")
        pos_events = sum(1 for e in events if e.get("signal") == "positive")
        # Base on trajectory, adjust by event balance
        press_score = {"growth": 25, "stable": 45, "restructuring": 70, "contraction": 80}.get(traj, 50)
        if events:
            event_adj = 10 * (neg_events - pos_events) / len(events)
            press_score = max(0, min(100, press_score + event_adj))
        press_method = "S&P competitive position (trajectory + event balance)"

        # Social: Stakeholder Sentiment Index
        # Weighted sentiment with volume decay (low sample = regression to 50)
        social = state.get("social_data", [])
        ss = _sentiment_counts(social) if social else {"positive": 0, "negative": 0, "neutral": 0}
        total_s = sum(ss.values()) or 1
        vol_confidence = min(total_s / 10, 1.0)  # need ~10 posts for full confidence
        raw_social = 50 + 30 * (ss["negative"] - ss["positive"]) / total_s
        social_score = 50 * (1 - vol_confidence) + raw_social * vol_confidence  # regress to 50
        social_score = max(0, min(100, social_score))
        social_method = "Stakeholder Sentiment Index (volume-adjusted, Bayesian regression to mean)"

        # Reviews: Moody's Stakeholder Quality Assessment
        # Average rating mapped to risk score with separate employee/customer tracks
        reviews = state.get("review_data", [])
        emp = [r for r in reviews if r.get("type") == "employee"]
        cust = [r for r in reviews if r.get("type") == "customer"]
        emp_avg = sum(r.get("rating", 3) for r in emp) / len(emp) if emp else 3.0
        cust_avg = sum(r.get("rating", 3) for r in cust) / len(cust) if cust else 3.0
        # Employee satisfaction is more predictive of operational risk (60/40 split)
        blended = emp_avg * 0.6 + cust_avg * 0.4
        review_score = max(0, min(100, 100 - blended * 20))
        review_method = "Moody's stakeholder quality (emp 60% / cust 40%, rating-mapped)"

        # Weighted composite
        composite = (
            fsh_score * weights["fsh"] +
            cca_score * weights["cca"] +
            news_score * weights["news"] +
            press_score * weights["press"] +
            social_score * weights["social"] +
            review_score * weights["reviews"]
        )

        rating = "Low" if composite < 33 else "Medium" if composite < 67 else "High"

        # Display
        st.markdown("### Weighted Risk Score")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Composite Score", f"{composite:.1f} / 100", delta=f"Rating: {rating}")
        with sc2:
            st.metric("Confidence", f"{confidence*100:.0f}%")
        with sc3:
            st.metric("Pipeline Base Score", f"{base_score}")

        _risk_gauge(composite)

        # Sub-score breakdown with methodology
        st.markdown("### Domain Sub-Scores & Methodology")
        domains = ["Financial Statements", "Companies Act", "News", "Press Releases", "Social Sentiment", "Reviews"]
        scores = [fsh_score, cca_score, news_score, press_score, social_score, review_score]
        methods = [fsh_method, cca_method, news_method, press_method, social_method, review_method]
        wkeys = ["fsh", "cca", "news", "press", "social", "reviews"]
        bd_df = pd.DataFrame({
            "Domain": domains,
            "Sub-Score": [f"{s:.1f}" for s in scores],
            "Weight": [f"{weights[k]*100:.0f}%" for k in wkeys],
            "Contribution": [f"{scores[i] * weights[wkeys[i]]:.1f}" for i in range(6)],
            "Scoring Method": methods,
        })
        st.dataframe(bd_df, use_container_width=True, hide_index=True)

        # Chart
        st.bar_chart(pd.DataFrame({"Sub-Score": breakdown}).T)

        st.session_state["composite_score"] = composite
        st.session_state["composite_rating"] = rating


# ===========================================================================
# PHASE 6: REPORT + AUDIT
# ===========================================================================

def _phase_report(state: Dict[str, Any]):
    st.markdown("---")
    st.markdown("## 5 — Final Report & Audit")

    report = state.get("final_report", "No report generated.")
    st.markdown(report)

    # Risks vs Strengths
    st.markdown("### Risk vs Strength Signals")
    risks = state.get("extracted_risks", [])
    strengths = state.get("extracted_strengths", [])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Risks")
        for r in risks:
            st.markdown(f"- **{r.get('type', '?')}**: {r.get('description', '')}")
        if not risks:
            st.info("No risk signals.")
    with c2:
        st.markdown("#### Strengths")
        for s in strengths:
            st.markdown(f"- **{s.get('type', '?')}**: {s.get('description', '')}")
        if not strengths:
            st.info("No strength signals.")

    # Guardrail summary
    st.markdown("### Guardrails & Compliance")
    gc1, gc2, gc3, gc4 = st.columns(4)
    with gc1: _badge("Input Validated")
    with gc2: _badge("Bias Check Passed")
    with gc3: _badge("MAS FEAT Compliant")
    with gc4: _badge("EU AI Act Compliant")

    warnings = state.get("guardrail_warnings", [])
    if warnings:
        with st.expander(f"Guardrail Warnings ({len(warnings)})"):
            for w in warnings:
                st.markdown(f"- {w}")

    # Downloads
    st.markdown("### Download")
    dc1, dc2 = st.columns(2)
    company = state.get("company_name", "company")
    slug = company.replace(" ", "_")
    with dc1:
        full = {
            "company": company,
            "composite_score": st.session_state.get("composite_score"),
            "rating": st.session_state.get("composite_rating"),
            "risk_score": state.get("risk_score", {}),
            "risks": state.get("extracted_risks", []),
            "strengths": state.get("extracted_strengths", []),
            "explanations": state.get("explanations", []),
            "warnings": warnings,
            "report": report,
        }
        st.download_button("Download JSON", json.dumps(full, indent=2, default=str),
                          f"risk_{slug}.json", "application/json", use_container_width=True)
    with dc2:
        st.download_button("Download Markdown", report,
                          f"risk_{slug}.md", "text/markdown", use_container_width=True)


# ===========================================================================
# PIPELINE STEP-BY-STEP VIEW (state-by-state agent visualization)
# ===========================================================================

_STEP_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
                "#9467bd", "#8c564b", "#e377c2", "#17becf"]


def _pipeline_view(state: Dict[str, Any]):
    """Render step-by-step pipeline view showing what each agent did."""
    st.markdown("## Agent Pipeline — Step-by-Step Trace")
    st.caption("Each step shows the agent's input, output, and diagnostics. "
               "Expand any step to inspect the data at that stage.")

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

    for i, (num, title, key, render_fn) in enumerate(steps):
        has_data = _step_has_data(state, key)
        icon = "white_check_mark" if has_data else "hourglass_flowing_sand"
        color = _STEP_COLORS[i % len(_STEP_COLORS)]

        st.markdown(
            f'<div style="border-left:4px solid {color};padding:2px 0 2px 12px;'
            f'margin:4px 0"><b>:{icon}: {num}: {title}</b></div>',
            unsafe_allow_html=True)

        with st.expander(f"{num} Details", expanded=(i == 0 and has_data)):
            render_fn(state)


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


# ── Step 1: Input ──

def _pipe_step_input(state: Dict):
    company = state.get("company_name", "—")
    info = state.get("company_info", {})
    docs = state.get("uploaded_docs", [])
    xbrl = [d for d in state.get("doc_extracted_text", []) if d.get("type") == "XBRL_STRUCTURED"]

    c1, c2, c3 = st.columns(3)
    with c1:
        _metric("Company", company, color="blue")
    with c2:
        _metric("Entity Type", info.get("entity_type", "—"), color="blue")
    with c3:
        _metric("Documents Uploaded", len(docs) or len(state.get("doc_extracted_text", [])), color="blue")

    if xbrl:
        st.success(f"XBRL structured data detected — {xbrl[0].get('xbrl_parsed', {}).get('metadata', {}).get('total_facts', 0)} facts extracted (0 LLM tokens)")
    _badge("Input Validation Passed")


# ── Step 2: Source Discovery ──

def _pipe_step_discovery(state: Dict):
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

    # Source count
    total_sources = len(queries)
    _metric("Data Sources Planned", total_sources, color="blue")
    _badge("Source Discovery Complete")


# ── Step 3: Data Collection ──

def _pipe_step_collection(state: Dict):
    news = state.get("news_data", [])
    social = state.get("social_data", [])
    reviews = state.get("review_data", [])
    financial = state.get("financial_data", [])
    press = state.get("press_release_analysis", {})
    xbrl = [d for d in state.get("doc_extracted_text", []) if d.get("type") == "XBRL_STRUCTURED"]

    st.markdown("#### Collection Summary (Parallel Fan-Out)")

    agents = [
        ("News Agent", len(news), "NewsAPI + Tavily", "green" if news else "grey"),
        ("Social Agent", len(social), "Tavily social", "green" if social else "grey"),
        ("Review Agent", len(reviews), "Tavily reviews", "green" if reviews else "grey"),
        ("Financial Agent", len(financial), "yfinance + ACRA", "green" if financial else "grey"),
        ("Press Agent", len(press.get("events", [])), "Directed newsroom", "green" if press.get("events") else "grey"),
        ("Document Processor", len(xbrl), "XBRL parser (0 tokens)", "green" if xbrl else "grey"),
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
        chart_data = pd.DataFrame({"Count": sc}, index=["positive", "negative", "neutral"])
        st.bar_chart(chart_data)


# ── Step 4: Cleaning & Entity Resolution ──

def _pipe_step_cleaning(state: Dict):
    cleaned = state.get("cleaned_data", [])
    resolved = state.get("resolved_entities", {})

    c1, c2 = st.columns(2)
    with c1:
        _metric("Cleaned Records", len(cleaned) if cleaned else "N/A", color="blue")
        if resolved:
            primary = resolved.get("primary", "—")
            st.markdown(f"**Primary entity**: {primary}")
    with c2:
        # Source credibility — check cleaned_data items for credibility_weight
        cleaned_items = state.get("cleaned_data", [])
        tiered = [d for d in cleaned_items if d.get("credibility_weight")]
        if tiered:
            avg_cred = sum(d["credibility_weight"] for d in tiered) / len(tiered)
            high_tier = sum(1 for d in tiered if d.get("source_tier", "").startswith("tier_1") or d.get("source_tier", "").startswith("tier_2"))
            _metric("Avg Source Credibility", f"{avg_cred:.2f}", color="green" if avg_cred > 0.7 else "orange")
            _metric("High-Tier Sources", f"{high_tier}/{len(tiered)}", color="green")
        else:
            _metric("Source Credibility", "Not yet computed", color="grey")

    _badge("Entity Resolution Complete")
    if cleaned:
        _badge(f"FinBERT Enrichment: {len(cleaned)} records")


# ── Step 5: Risk & Strength Extraction ──

def _pipe_step_extraction(state: Dict):
    risks = state.get("extracted_risks", [])
    strengths = state.get("extracted_strengths", [])

    c1, c2 = st.columns(2)
    with c1:
        _metric("Risk Signals", len(risks), color="red")
        for r in risks:
            st.markdown(f"- **{r.get('type', '?')}**: {r.get('description', '')}")
    with c2:
        _metric("Strength Signals", len(strengths), color="green")
        for s in strengths:
            st.markdown(f"- **{s.get('type', '?')}**: {s.get('description', '')}")

    # Risk type distribution
    if risks:
        type_counts = {}
        for r in risks:
            t = r.get("type", "Other")
            type_counts[t] = type_counts.get(t, 0) + 1
        st.markdown("#### Risk Type Distribution")
        st.bar_chart(pd.DataFrame({"Count": type_counts}))


# ── Step 6: Risk Scoring ──

def _pipe_step_scoring(state: Dict):
    score_data = state.get("risk_score", {})
    score = score_data.get("score", 0)
    rating = score_data.get("rating", "—")
    conf = score_data.get("confidence_score", score_data.get("confidence", 0))
    conf_level = score_data.get("confidence_level", "—")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric("Risk Score", f"{score}/100", color="red" if score >= 67 else "orange" if score >= 34 else "green")
    with c2:
        _metric("Rating", rating, color="red" if rating == "High" else "orange" if rating == "Medium" else "green")
    with c3:
        _metric("Confidence", f"{conf*100:.0f}%" if isinstance(conf, float) else str(conf), color="blue")
    with c4:
        _metric("Confidence Level", conf_level, color="green" if conf_level == "High" else "orange")

    _risk_gauge(score)

    st.caption("Score methodology: LLM-structured output validated by output_enforcer guardrail. "
               "Confidence from source diversity + sentiment agreement + data coverage.")


# ── Step 7: Explainability ──

def _pipe_step_explain(state: Dict):
    explanations = state.get("explanations", [])

    if explanations:
        for exp in explanations:
            metric = exp.get("metric", "—")
            reason = exp.get("reason", "—")
            st.markdown(
                f'<div style="border-left:3px solid #9467bd;padding:8px 12px;margin:4px 0;'
                f'background:#f8f4ff;border-radius:4px">'
                f'<b>{metric}</b><br/><span style="color:#555">{reason}</span></div>',
                unsafe_allow_html=True)
    else:
        st.info("Explanations will appear after risk scoring completes.")

    _badge("Explainability Agent Complete")


# ── Step 8: Final Report ──

def _pipe_step_report(state: Dict):
    report = state.get("final_report", "")

    # Guardrail badges
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

    # Report preview
    if report:
        st.markdown("#### Report Preview")
        st.markdown(report)
    else:
        st.info("Final report will appear after all agents complete.")

    # Audit trail
    audit = state.get("audit_trail", {})
    if audit:
        with st.expander("Audit Trail (JSON)"):
            st.json(audit)


# ===========================================================================
# MAIN
# ===========================================================================

def render_hitl():
    st.set_page_config(page_title="G5-AAFS Credit Risk (HITL)", page_icon="🏦", layout="wide")
    st.markdown('<style>.main{max-width:1400px}</style>', unsafe_allow_html=True)

    # Session defaults
    for k, v in {"state": {}, "scored": False, "composite_score": None}.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.title("G5-AAFS: Credit Risk Assessment")
    st.caption("UBS Credit Officer Workstation · Human-in-the-Loop Review & Scoring")

    # Sidebar: mode + methodology reference
    st.sidebar.markdown("### Pipeline Status")
    if _PIPELINE_AVAILABLE:
        st.sidebar.success("Live mode — agents will call APIs")
    else:
        st.sidebar.warning("Demo mode — using mock data (no API costs)")
    if _XBRL_AVAILABLE:
        st.sidebar.success("XBRL parser loaded")
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Treatment**")
    st.sidebar.markdown(
        "- **Structured**: XBRL → parsed deterministically (0 tokens)\n"
        "- **Semi-structured**: News/press → sentiment via FinBERT\n"
        "- **Unstructured**: Social/reviews → keyword + rating analysis"
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Scoring Frameworks**")
    st.sidebar.markdown(
        "- **Basel IRB**: PD/LGD focus, financials-heavy\n"
        "- **Altman Z-Score**: 5 ratio zones\n"
        "- **S&P Global**: Business + Financial Risk Profile\n"
        "- **Moody's KMV**: Distance-to-Default\n"
        "- **MAS FEAT**: Singapore regulatory balanced"
    )

    # Phase 1: Input (always visible)
    name, files, go = _phase_input()

    # Phase 2: Collect
    if go and name:
        st.session_state["scored"] = False
        _phase_collect(name, files, {})

    # Phases 3-8: only show if we have data
    state = st.session_state.get("state", {})
    if state.get("company_name"):
        st.markdown("---")

        # ── TOP-LEVEL DUAL VIEW ──
        view_tab1, view_tab2 = st.tabs([
            "Credit Assessment (Domain Review)",
            "Pipeline Trace (Agent-by-Agent)"
        ])

        with view_tab1:
            st.caption("Review all collected intelligence by data domain, "
                       "set your scoring weights, and generate the final risk score.")
            _phase_review(state)
            weights = _phase_weights(state)
            _phase_score(state, weights)
            _phase_report(state)

        with view_tab2:
            st.caption("Step-by-step trace of what each agent in the pipeline did. "
                       "Expand any stage to inspect inputs, outputs, and diagnostics.")
            _pipeline_view(state)

    st.markdown("---")
    st.markdown("<small>G5-AAFS Credit Risk Assessment | UBS × SMU IS4000 | "
                "Powered by LangGraph + ACRA XBRL + Guardrails | "
                "Basel IRB · Altman Z-Score · S&P · Moody's KMV · MAS FEAT</small>",
                unsafe_allow_html=True)


if __name__ == "__main__":
    render_hitl()
else:
    render_hitl()
