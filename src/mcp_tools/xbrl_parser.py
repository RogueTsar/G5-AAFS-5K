"""
XBRL Parser for Singapore BizFinx/ACRA taxonomy.
Converts XBRL instance documents into structured JSON for display.
"""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import re

# Singapore BizFinx XBRL namespaces
NAMESPACES = {
    "xbrli": "http://www.xbrl.org/2003/instance",
    "link": "http://www.xbrl.org/2003/linkbase",
    "xlink": "http://www.w3.org/1999/xlink",
    "iso4217": "http://www.xbrl.org/2003/iso4217",
    "xbrldi": "http://xbrl.org/2006/xbrldi",
    "sg-dei": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-dei",
    "sg-as": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-as",
    "sg-ca": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-ca",
    "sg-ssa": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-ssa",
    "sg-lm": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-lm",
}

# Human-readable labels for XBRL concept names
LABEL_MAP = {
    # Entity info
    "NameOfCompany": "Company Name",
    "UniqueEntityNumber": "UEN",
    "DescriptionOfPresentationCurrency": "Currency",
    "DescriptionOfNatureOfEntitysOperationsAndPrincipalActivities": "Principal Activities",
    "PrincipalPlaceOfBusinessIfDifferentFromRegisteredOffice": "Place of Business",
    "NumberOfEmployeesOfCompany": "Employees (Company)",
    "NumberOfEmployeesOfGroup": "Employees (Group)",
    "NatureOfFinancialStatementsCompanyLevelOrConsolidated": "Statement Type",
    "TypeOfAccountingStandardUsedToPrepareFinancialStatements": "Accounting Standard",
    "TypeOfAuditOpinionInIndependentAuditorsReport": "Audit Opinion",
    "WhetherThereIsAnyMaterialUncertaintyRelatingToGoingConcern": "Going Concern Uncertainty",

    # Balance Sheet - Current Assets
    "CashAndBankBalances": "Cash & Bank Balances",
    "TradeAndOtherReceivablesCurrent": "Trade & Other Receivables (Current)",
    "CurrentFinanceLeaseReceivables": "Finance Lease Receivables (Current)",
    "CurrentDerivativeFinancialAssets": "Derivative Financial Assets (Current)",
    "CurrentFinancialAssetsMeasuredAtFairValueThroughProfitOrLoss": "Financial Assets at FVTPL (Current)",
    "OtherCurrentFinancialAssets": "Other Financial Assets (Current)",
    "DevelopmentProperties": "Development Properties",
    "Inventories": "Inventories",
    "OtherCurrentNonfinancialAssets": "Other Non-Financial Assets (Current)",
    "NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleOrAsHeldForDistributionToOwners": "Assets Held for Sale",
    "CurrentAssets": "Total Current Assets",

    # Balance Sheet - Non-Current Assets
    "TradeAndOtherReceivablesNoncurrent": "Trade & Other Receivables (Non-Current)",
    "NoncurrentFinanceLeaseReceivables": "Finance Lease Receivables (Non-Current)",
    "NoncurrentDerivativeFinancialAssets": "Derivative Financial Assets (Non-Current)",
    "NoncurrentFinancialAssetsMeasuredAtFairValueThroughProfitOrLoss": "Financial Assets at FVTPL (Non-Current)",
    "OtherNoncurrentFinancialAssets": "Other Financial Assets (Non-Current)",
    "PropertyPlantAndEquipment": "Property, Plant & Equipment",
    "InvestmentProperties": "Investment Properties",
    "Goodwill": "Goodwill",
    "IntangibleAssetsOtherThanGoodwill": "Intangible Assets",
    "InvestmentsInSubsidiariesAssociatesOrJointVentures": "Investments in Subsidiaries/Associates/JVs",
    "DeferredTaxAssets": "Deferred Tax Assets",
    "OtherNoncurrentNonfinancialAssets": "Other Non-Financial Assets (Non-Current)",
    "NoncurrentAssets": "Total Non-Current Assets",
    "Assets": "Total Assets",

    # Balance Sheet - Current Liabilities
    "TradeAndOtherPayablesCurrent": "Trade & Other Payables (Current)",
    "CurrentLoansAndBorrowings": "Loans & Borrowings (Current)",
    "CurrentFinancialLiabilitiesMeasuredAtFairValueThroughProfitOrLoss": "Financial Liabilities at FVTPL (Current)",
    "CurrentFinanceLeaseLiabilities": "Finance Lease Liabilities (Current)",
    "OtherCurrentFinancialLiabilities": "Other Financial Liabilities (Current)",
    "CurrentIncomeTaxLiabilities": "Income Tax Liabilities (Current)",
    "CurrentProvisions": "Provisions (Current)",
    "OtherCurrentNonfinancialLiabilities": "Other Non-Financial Liabilities (Current)",
    "LiabilitiesClassifiedAsHeldForSale": "Liabilities Held for Sale",
    "CurrentLiabilities": "Total Current Liabilities",

    # Balance Sheet - Non-Current Liabilities
    "TradeAndOtherPayablesNoncurrent": "Trade & Other Payables (Non-Current)",
    "NoncurrentLoansAndBorrowings": "Loans & Borrowings (Non-Current)",
    "NoncurrentFinancialLiabilitiesMeasuredAtFairValueThroughProfitOrLoss": "Financial Liabilities at FVTPL (Non-Current)",
    "NoncurrentFinanceLeaseLiabilities": "Finance Lease Liabilities (Non-Current)",
    "OtherNoncurrentFinancialLiabilities": "Other Financial Liabilities (Non-Current)",
    "DeferredTaxLiabilities": "Deferred Tax Liabilities",
    "NoncurrentProvisions": "Provisions (Non-Current)",
    "OtherNoncurrentNonfinancialLiabilities": "Other Non-Financial Liabilities (Non-Current)",
    "NoncurrentLiabilities": "Total Non-Current Liabilities",
    "Liabilities": "Total Liabilities",

    # Equity
    "ShareCapital": "Share Capital",
    "TreasuryShares": "Treasury Shares",
    "AccumulatedProfitsLosses": "Accumulated Profits/(Losses)",
    "ReservesOtherThanAccumulatedProfitsLosses": "Other Reserves",
    "Equity": "Total Equity",

    # Income Statement
    "Revenue": "Revenue",
    "OtherIncome": "Other Income",
    "EmployeeBenefitsExpense": "Employee Benefits Expense",
    "DepreciationExpense": "Depreciation Expense",
    "AmortisationExpense": "Amortisation Expense",
    "RepairsAndMaintenanceExpense": "Repairs & Maintenance",
    "SalesAndMarketingExpense": "Sales & Marketing",
    "OtherExpensesByNature": "Other Expenses",
    "OtherGainsLosses": "Other Gains/(Losses)",
    "FinanceCosts": "Finance Costs",
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": "Share of Profit/(Loss) of Associates/JVs",
    "ProfitLossBeforeTaxation": "Profit/(Loss) Before Tax",
    "TaxExpenseBenefitContinuingOperations": "Tax Expense/(Benefit)",
    "ProfitLossFromDiscontinuedOperations": "Profit/(Loss) from Discontinued Operations",
    "ProfitLoss": "Profit/(Loss) for the Year",
    "ProfitLossAttributableToOwnersOfCompany": "Profit/(Loss) Attributable to Owners",

    # Cash Flow
    "CashFlowsFromUsedInOperatingActivities": "Operating Activities",
    "CashFlowsFromUsedInInvestingActivities": "Investing Activities",
    "CashFlowsFromUsedInFinancingActivities": "Financing Activities",
}

# Which concepts belong to which financial statement section
BALANCE_SHEET_CURRENT_ASSETS = [
    "CashAndBankBalances", "TradeAndOtherReceivablesCurrent",
    "CurrentFinanceLeaseReceivables", "CurrentDerivativeFinancialAssets",
    "CurrentFinancialAssetsMeasuredAtFairValueThroughProfitOrLoss",
    "OtherCurrentFinancialAssets", "DevelopmentProperties", "Inventories",
    "OtherCurrentNonfinancialAssets",
    "NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleOrAsHeldForDistributionToOwners",
    "CurrentAssets",
]

BALANCE_SHEET_NONCURRENT_ASSETS = [
    "TradeAndOtherReceivablesNoncurrent", "NoncurrentFinanceLeaseReceivables",
    "NoncurrentDerivativeFinancialAssets",
    "NoncurrentFinancialAssetsMeasuredAtFairValueThroughProfitOrLoss",
    "OtherNoncurrentFinancialAssets", "PropertyPlantAndEquipment",
    "InvestmentProperties", "Goodwill", "IntangibleAssetsOtherThanGoodwill",
    "InvestmentsInSubsidiariesAssociatesOrJointVentures",
    "DeferredTaxAssets", "OtherNoncurrentNonfinancialAssets", "NoncurrentAssets",
]

BALANCE_SHEET_CURRENT_LIABILITIES = [
    "TradeAndOtherPayablesCurrent", "CurrentLoansAndBorrowings",
    "CurrentFinancialLiabilitiesMeasuredAtFairValueThroughProfitOrLoss",
    "CurrentFinanceLeaseLiabilities", "OtherCurrentFinancialLiabilities",
    "CurrentIncomeTaxLiabilities", "CurrentProvisions",
    "OtherCurrentNonfinancialLiabilities", "LiabilitiesClassifiedAsHeldForSale",
    "CurrentLiabilities",
]

BALANCE_SHEET_NONCURRENT_LIABILITIES = [
    "TradeAndOtherPayablesNoncurrent", "NoncurrentLoansAndBorrowings",
    "NoncurrentFinancialLiabilitiesMeasuredAtFairValueThroughProfitOrLoss",
    "NoncurrentFinanceLeaseLiabilities", "OtherNoncurrentFinancialLiabilities",
    "DeferredTaxLiabilities", "NoncurrentProvisions",
    "OtherNoncurrentNonfinancialLiabilities", "NoncurrentLiabilities",
]

BALANCE_SHEET_EQUITY = [
    "ShareCapital", "TreasuryShares", "AccumulatedProfitsLosses",
    "ReservesOtherThanAccumulatedProfitsLosses", "Equity",
]

INCOME_STATEMENT = [
    "Revenue", "OtherIncome", "EmployeeBenefitsExpense",
    "DepreciationExpense", "AmortisationExpense", "RepairsAndMaintenanceExpense",
    "SalesAndMarketingExpense", "OtherExpensesByNature", "OtherGainsLosses",
    "FinanceCosts",
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod",
    "ProfitLossBeforeTaxation", "TaxExpenseBenefitContinuingOperations",
    "ProfitLossFromDiscontinuedOperations", "ProfitLoss",
    "ProfitLossAttributableToOwnersOfCompany",
]

CASH_FLOW = [
    "CashFlowsFromUsedInOperatingActivities",
    "CashFlowsFromUsedInInvestingActivities",
    "CashFlowsFromUsedInFinancingActivities",
]

# Totals/subtotals that should be bold in display
TOTAL_LINES = {
    "CurrentAssets", "NoncurrentAssets", "Assets",
    "CurrentLiabilities", "NoncurrentLiabilities", "Liabilities",
    "Equity", "ProfitLossBeforeTaxation", "ProfitLoss",
    "ProfitLossAttributableToOwnersOfCompany",
}


def _detect_namespaces(xml_content: str) -> Dict[str, str]:
    """Auto-detect namespace URIs from the XBRL document to handle version differences."""
    ns = {}
    # Find all xmlns declarations
    for match in re.finditer(r'xmlns:(\S+?)="(\S+?)"', xml_content):
        prefix, uri = match.group(1), match.group(2)
        ns[prefix] = uri
    return ns


def _parse_contexts(root: ET.Element, ns: Dict[str, str]) -> Dict[str, Dict]:
    """Parse all xbrli:context elements into a lookup dict."""
    contexts = {}
    xbrli_ns = ns.get("xbrli", NAMESPACES["xbrli"])

    for ctx in root.findall(f"{{{xbrli_ns}}}context"):
        ctx_id = ctx.get("id", "")
        period_elem = ctx.find(f"{{{xbrli_ns}}}period")
        if period_elem is None:
            continue

        instant = period_elem.find(f"{{{xbrli_ns}}}instant")
        start = period_elem.find(f"{{{xbrli_ns}}}startDate")
        end = period_elem.find(f"{{{xbrli_ns}}}endDate")

        period_info = {}
        if instant is not None:
            period_info = {"type": "instant", "date": instant.text}
        elif start is not None and end is not None:
            period_info = {"type": "duration", "start": start.text, "end": end.text}

        # Check for dimensional info (scenario/segment)
        has_dimension = ctx.find(f".//{{{ns.get('xbrldi', NAMESPACES.get('xbrldi', ''))}}}explicitMember") is not None

        contexts[ctx_id] = {
            "period": period_info,
            "has_dimension": has_dimension,
        }
    return contexts


def _get_concept_name(tag: str) -> str:
    """Extract the local concept name from a namespaced tag like {uri}ConceptName."""
    if "}" in tag:
        return tag.split("}")[-1]
    if ":" in tag:
        return tag.split(":")[-1]
    return tag


def _get_namespace_prefix(tag: str, ns: Dict[str, str]) -> str:
    """Determine which namespace prefix a tag belongs to."""
    if "}" in tag:
        uri = tag.split("{")[1].split("}")[0]
        for prefix, ns_uri in ns.items():
            if ns_uri == uri:
                return prefix
    return ""


def parse_xbrl(xml_content: str) -> Dict[str, Any]:
    """
    Parse an XBRL instance document and return structured financial data.

    Returns a dict with:
    - entity_info: Company metadata
    - balance_sheet: Structured balance sheet data
    - income_statement: Structured income statement data
    - cash_flow: Structured cash flow data
    - periods: List of reporting periods found
    - currency: Reporting currency
    """
    # Auto-detect namespaces from the document
    detected_ns = _detect_namespaces(xml_content)
    ns = {**NAMESPACES, **detected_ns}

    root = ET.fromstring(xml_content)
    contexts = _parse_contexts(root, ns)

    # Collect all facts (non-dimensional only for financial statements)
    facts = {}  # concept_name -> {context_id: value}

    for elem in root:
        tag = elem.tag
        concept = _get_concept_name(tag)
        prefix = _get_namespace_prefix(tag, ns)

        # Skip non-data elements
        if prefix in ("xbrli", "link", "xlink"):
            continue

        ctx_ref = elem.get("contextRef", "")
        if not ctx_ref or ctx_ref not in contexts:
            continue

        # Skip dimensional facts for the main financial statement view
        ctx_info = contexts[ctx_ref]
        if ctx_info.get("has_dimension"):
            continue

        value = elem.text
        if value is None:
            continue

        # Clean CDATA content
        if value.strip().startswith("{\\rtf"):
            value = "[RTF Text Block]"
        elif len(value) > 500:
            value = value[:200] + "..."

        if concept not in facts:
            facts[concept] = {}
        facts[concept][ctx_ref] = value

    # Identify periods
    current_period_end = facts.get("CurrentPeriodEndDate", {})
    current_end = next(iter(current_period_end.values()), "2024-12-31") if current_period_end else "2024-12-31"
    current_year = current_end[:4]
    prior_year = str(int(current_year) - 1)

    # Build period context mapping
    instant_current = None
    instant_prior = None
    duration_current = None
    duration_prior = None

    for ctx_id, ctx_info in contexts.items():
        if ctx_info.get("has_dimension"):
            continue
        period = ctx_info["period"]
        if period["type"] == "instant":
            if current_year in period["date"]:
                instant_current = ctx_id
            elif prior_year in period["date"]:
                instant_prior = ctx_id
        elif period["type"] == "duration":
            if current_year in period.get("end", ""):
                duration_current = ctx_id
            elif prior_year in period.get("end", ""):
                duration_prior = ctx_id

    # Extract entity info
    entity_info = {}
    entity_fields = [
        "NameOfCompany", "UniqueEntityNumber", "DescriptionOfPresentationCurrency",
        "DescriptionOfNatureOfEntitysOperationsAndPrincipalActivities",
        "PrincipalPlaceOfBusinessIfDifferentFromRegisteredOffice",
        "NumberOfEmployeesOfCompany", "NumberOfEmployeesOfGroup",
        "NatureOfFinancialStatementsCompanyLevelOrConsolidated",
        "TypeOfAccountingStandardUsedToPrepareFinancialStatements",
        "TypeOfAuditOpinionInIndependentAuditorsReport",
        "WhetherThereIsAnyMaterialUncertaintyRelatingToGoingConcern",
    ]
    for field in entity_fields:
        if field in facts:
            val = next(iter(facts[field].values()), None)
            if val:
                entity_info[LABEL_MAP.get(field, field)] = val

    currency = entity_info.get("Currency", "SGD")

    def _build_statement(concept_list, current_ctx, prior_ctx):
        """Build a financial statement section from a list of concepts."""
        rows = []
        for concept in concept_list:
            if concept not in facts:
                continue
            label = LABEL_MAP.get(concept, concept)
            current_val = facts[concept].get(current_ctx, None) if current_ctx else None
            prior_val = facts[concept].get(prior_ctx, None) if prior_ctx else None

            # Parse numeric values
            def to_num(v):
                if v is None:
                    return None
                try:
                    return float(v.replace(",", ""))
                except (ValueError, AttributeError):
                    return None

            current_num = to_num(current_val)
            prior_num = to_num(prior_val)

            rows.append({
                "concept": concept,
                "label": label,
                "current": current_num,
                "prior": prior_num,
                "is_total": concept in TOTAL_LINES,
            })
        return rows

    # Build financial statements
    balance_sheet = {
        "current_assets": _build_statement(BALANCE_SHEET_CURRENT_ASSETS, instant_current, instant_prior),
        "noncurrent_assets": _build_statement(BALANCE_SHEET_NONCURRENT_ASSETS, instant_current, instant_prior),
        "total_assets": _build_statement(["Assets"], instant_current, instant_prior),
        "current_liabilities": _build_statement(BALANCE_SHEET_CURRENT_LIABILITIES, instant_current, instant_prior),
        "noncurrent_liabilities": _build_statement(BALANCE_SHEET_NONCURRENT_LIABILITIES, instant_current, instant_prior),
        "total_liabilities": _build_statement(["Liabilities"], instant_current, instant_prior),
        "equity": _build_statement(BALANCE_SHEET_EQUITY, instant_current, instant_prior),
    }

    income_statement = _build_statement(INCOME_STATEMENT, duration_current, duration_prior)
    cash_flow = _build_statement(CASH_FLOW, duration_current, duration_prior)

    # --- Compute Key Ratios & Flat Summary ---
    def _get_val(stmt, label, period="current"):
        if isinstance(stmt, list):
            for row in stmt:
                if row["label"] == label or row["concept"] == label:
                    return row.get(period)
        elif isinstance(stmt, dict):
            # bs is a dict of lists
            for key, rows in stmt.items():
                v = _get_val(rows, label, period)
                if v is not None: return v
        return None

    rev = _get_val(income_statement, "Revenue")
    prof = _get_val(income_statement, "ProfitLoss")
    assets = _get_val(balance_sheet, "Assets")
    liab = _get_val(balance_sheet, "Liabilities")
    equity = _get_val(balance_sheet, "Equity")
    curr_assets = _get_val(balance_sheet, "CurrentAssets")
    curr_liab = _get_val(balance_sheet, "CurrentLiabilities")
    npl = _get_val(balance_sheet, "sg-ssa:LoansAndAdvancesToExhibitedByCreditQualityPass") # example fallback
    

    # Ratios
    ratios = {}
    if curr_assets and curr_liab and curr_liab != 0:
        ratios["current_ratio"] = curr_assets / curr_liab
    if liab and equity and equity != 0:
        ratios["debt_to_equity"] = liab / equity
    if prof and rev and rev != 0:
        ratios["profit_margin"] = prof / rev
    if equity and assets and assets != 0:
        ratios["equity_ratio"] = equity / assets



    # Map to UI expectations in hitl_ui.py
    # hitl_ui uses: current_ratio, debt_to_equity, npl_ratio, profit_margin, coverage_ratio
    # If missing, we'll leave them for hitl_ui to handle.

    return {
        "entity_info": entity_info,
        "balance_sheet": balance_sheet,
        "income_statement": income_statement,
        "cash_flow": cash_flow,
        "computed_ratios": ratios,
        "summary": {
            "revenue": rev,
            "profit": prof,
            "assets": assets,
            "liabilities": liab,
            "equity": equity,
        },
        "periods": {
            "current": current_year,
            "prior": prior_year,
        },
        "currency": currency,
    }
