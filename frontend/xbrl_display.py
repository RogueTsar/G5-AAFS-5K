"""
Visual display component for parsed XBRL financial statements.
Renders Balance Sheet, Income Statement, and Cash Flows as formatted Streamlit tables.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List


def format_currency(value, currency="SGD"):
    """Format a numeric value as currency string."""
    if value is None:
        return "-"
    if abs(value) >= 1_000_000:
        return f"({currency} {abs(value)/1_000_000:,.2f}M)" if value < 0 else f"{currency} {value/1_000_000:,.2f}M"
    elif abs(value) >= 1_000:
        return f"({currency} {abs(value)/1_000:,.1f}K)" if value < 0 else f"{currency} {value/1_000:,.1f}K"
    else:
        return f"({currency} {abs(value):,.0f})" if value < 0 else f"{currency} {value:,.0f}"


def _rows_to_dataframe(rows: List[Dict], current_year: str, prior_year: str, currency: str) -> pd.DataFrame:
    """Convert statement rows to a display DataFrame."""
    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        label = row["label"]
        current = row.get("current")
        prior = row.get("prior")

        # Bold formatting for totals
        if row.get("is_total"):
            label = f"**{label}**"

        data.append({
            "": label,
            f"FY {current_year}": format_currency(current, currency),
            f"FY {prior_year}": format_currency(prior, currency),
        })

    return pd.DataFrame(data)


def _compute_change(current, prior):
    """Compute YoY change percentage."""
    if current is None or prior is None or prior == 0:
        return None
    return ((current - prior) / abs(prior)) * 100


def render_entity_info(entity_info: Dict[str, str]):
    """Render company information card."""
    if not entity_info:
        return

    company_name = entity_info.get("Company Name", "Unknown Company")
    st.markdown(f"#### {company_name}")

    col1, col2 = st.columns(2)
    left_fields = ["UEN", "Currency", "Accounting Standard", "Statement Type", "Audit Opinion"]
    right_fields = ["Principal Activities", "Place of Business", "Employees (Company)", "Going Concern Uncertainty"]

    with col1:
        for field in left_fields:
            if field in entity_info:
                val = entity_info[field]
                # Color-code audit opinion
                if field == "Audit Opinion":
                    color = "green" if "Unqualified" in val else "red"
                    st.markdown(f"**{field}:** <span style='color:{color}'>{val}</span>", unsafe_allow_html=True)
                elif field == "Going Concern Uncertainty":
                    color = "red" if val == "Yes" else "green"
                    st.markdown(f"**{field}:** <span style='color:{color}'>{val}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{field}:** {val}")

    with col2:
        for field in right_fields:
            if field in entity_info:
                st.markdown(f"**{field}:** {entity_info[field]}")


def render_key_metrics(parsed_data: Dict[str, Any]):
    """Render key financial metrics as metric cards."""
    currency = parsed_data.get("currency", "SGD")
    current_year = parsed_data["periods"]["current"]
    prior_year = parsed_data["periods"]["prior"]

    # Extract key values
    def _find_value(statement_rows, concept, period="current"):
        for row in statement_rows:
            if row["concept"] == concept:
                return row.get(period)
        return None

    def _find_bs_value(concept, period="current"):
        for section in parsed_data["balance_sheet"].values():
            val = _find_value(section, concept, period)
            if val is not None:
                return val
        return None

    revenue_curr = _find_value(parsed_data["income_statement"], "Revenue", "current")
    revenue_prior = _find_value(parsed_data["income_statement"], "Revenue", "prior")
    profit_curr = _find_value(parsed_data["income_statement"], "ProfitLoss", "current")
    profit_prior = _find_value(parsed_data["income_statement"], "ProfitLoss", "prior")
    assets_curr = _find_bs_value("Assets", "current")
    equity_curr = _find_bs_value("Equity", "current")
    liabilities_curr = _find_bs_value("Liabilities", "current")
    cash_curr = _find_bs_value("CashAndBankBalances", "current")
    current_assets = _find_bs_value("CurrentAssets", "current")
    current_liabilities = _find_bs_value("CurrentLiabilities", "current")

    cols = st.columns(4)

    with cols[0]:
        if revenue_curr is not None:
            delta = f"{_compute_change(revenue_curr, revenue_prior):+.1f}% YoY" if revenue_prior else None
            st.metric("Revenue", format_currency(revenue_curr, currency), delta=delta)

    with cols[1]:
        if profit_curr is not None:
            delta = f"{_compute_change(profit_curr, profit_prior):+.1f}% YoY" if profit_prior and _compute_change(profit_curr, profit_prior) is not None else None
            st.metric("Net Profit/(Loss)", format_currency(profit_curr, currency), delta=delta)

    with cols[2]:
        if assets_curr is not None:
            st.metric("Total Assets", format_currency(assets_curr, currency))

    with cols[3]:
        if cash_curr is not None:
            st.metric("Cash & Bank", format_currency(cash_curr, currency))

    # Second row of metrics - ratios
    cols2 = st.columns(4)

    with cols2[0]:
        if current_assets and current_liabilities and current_liabilities != 0:
            ratio = current_assets / current_liabilities
            st.metric("Current Ratio", f"{ratio:.2f}x")

    with cols2[1]:
        if liabilities_curr and equity_curr and equity_curr != 0:
            de_ratio = liabilities_curr / equity_curr
            st.metric("Debt-to-Equity", f"{de_ratio:.2f}x")

    with cols2[2]:
        if profit_curr is not None and revenue_curr and revenue_curr != 0:
            margin = (profit_curr / revenue_curr) * 100
            st.metric("Net Margin", f"{margin:.1f}%")

    with cols2[3]:
        if equity_curr and assets_curr and assets_curr != 0:
            equity_ratio = (equity_curr / assets_curr) * 100
            st.metric("Equity Ratio", f"{equity_ratio:.1f}%")


def render_financial_statement(title: str, rows: List[Dict], current_year: str, prior_year: str, currency: str):
    """Render a single financial statement section as a styled table."""
    if not rows:
        return

    df = _rows_to_dataframe(rows, current_year, prior_year, currency)
    if df.empty:
        return

    st.markdown(f"**{title}**")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


def render_balance_sheet(parsed_data: Dict[str, Any]):
    """Render full balance sheet."""
    bs = parsed_data["balance_sheet"]
    cy = parsed_data["periods"]["current"]
    py = parsed_data["periods"]["prior"]
    currency = parsed_data.get("currency", "SGD")

    st.markdown("#### Statement of Financial Position")

    render_financial_statement("Current Assets", bs["current_assets"], cy, py, currency)
    render_financial_statement("Non-Current Assets", bs["noncurrent_assets"], cy, py, currency)
    render_financial_statement("Assets", bs["total_assets"], cy, py, currency)
    st.markdown("---")
    render_financial_statement("Current Liabilities", bs["current_liabilities"], cy, py, currency)
    render_financial_statement("Non-Current Liabilities", bs["noncurrent_liabilities"], cy, py, currency)
    render_financial_statement("Liabilities", bs["total_liabilities"], cy, py, currency)
    st.markdown("---")
    render_financial_statement("Equity", bs["equity"], cy, py, currency)


def render_income_statement(parsed_data: Dict[str, Any]):
    """Render income statement."""
    rows = parsed_data["income_statement"]
    cy = parsed_data["periods"]["current"]
    py = parsed_data["periods"]["prior"]
    currency = parsed_data.get("currency", "SGD")

    st.markdown("#### Statement of Profit or Loss")
    render_financial_statement("Income Statement", rows, cy, py, currency)


def render_cash_flow(parsed_data: Dict[str, Any]):
    """Render cash flow statement."""
    rows = parsed_data["cash_flow"]
    cy = parsed_data["periods"]["current"]
    py = parsed_data["periods"]["prior"]
    currency = parsed_data.get("currency", "SGD")

    st.markdown("#### Statement of Cash Flows")
    render_financial_statement("Cash Flows", rows, cy, py, currency)


def render_xbrl_financials(xbrl_parsed_list: List[Dict[str, Any]]):
    """
    Main entry point: render all parsed XBRL documents as visual financial statements.
    Called from ui.py when xbrl_parsed_data is available.
    """
    if not xbrl_parsed_list:
        return

    for i, parsed_data in enumerate(xbrl_parsed_list):
        entity_info = parsed_data.get("entity_info", {})
        company_name = entity_info.get("Company Name", f"XBRL Document {i+1}")

        with st.expander(f"XBRL Financial Statements: {company_name}", expanded=True):
            # Company info
            render_entity_info(entity_info)
            st.markdown("---")

            # Key metrics summary
            st.markdown("#### Key Financial Metrics")
            render_key_metrics(parsed_data)
            st.markdown("---")

            # Tabbed view for the three financial statements
            tab_bs, tab_is, tab_cf, tab_json = st.tabs([
                "Balance Sheet",
                "Income Statement",
                "Cash Flows",
                "Raw JSON",
            ])

            with tab_bs:
                render_balance_sheet(parsed_data)

            with tab_is:
                render_income_statement(parsed_data)

            with tab_cf:
                render_cash_flow(parsed_data)

            with tab_json:
                st.json(parsed_data)
