"""
ACRA BizFinx XBRL Instance Document Parser for Credit Risk Assessment.

Parses XBRL instance documents conforming to the ACRA BizFinx 2026 taxonomy
and extracts structured financial data suitable for credit risk evaluation.

Uses ONLY Python stdlib — zero external dependencies, zero LLM tokens.

Taxonomy reference:
    https://www.bizfinx.gov.sg/taxonomy/2026-01-01/

Author:  G5-AAFS-5K
Version: 1.0
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

__all__ = [
    "parse_xbrl_instance",
    "compute_credit_ratios",
    "detect_risk_flags",
    "parse_xbrl_taxonomy_xsd",
    "format_xbrl_summary",
    "CREDIT_RISK_ELEMENTS",
    "NAMESPACES",
]

# ---------------------------------------------------------------------------
# Namespace registry — ACRA BizFinx 2026 taxonomy
# ---------------------------------------------------------------------------

NAMESPACES: Dict[str, str] = {
    "sg-as":  "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-as",
    "sg-fsh": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-fsh",
    "sg-dei": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-dei",
    "sg-ca":  "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-ca",
    "sg-ssa": "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-ssa",
    "sg-lm":  "http://www.bizfinx.gov.sg/taxonomy/2026-01-01/elts/sg-lm",
    "xbrli":  "http://www.xbrl.org/2003/instance",
}

# Register all namespaces so ET preserves prefixes on round-trip.
for _prefix, _uri in NAMESPACES.items():
    ET.register_namespace(_prefix, _uri)

# ---------------------------------------------------------------------------
# Credit-critical element catalogue
# ---------------------------------------------------------------------------
# Each entry: local_name -> (human_label, category, output_section, output_key)
#   category  = one of entity_info | balance_sheet | income_statement
#               | cash_flow | credit_quality | directors_assessment
#   output_key = key used in the returned dict's sub-section

_E = "entity_info"
_B = "balance_sheet"
_I = "income_statement"
_CF = "cash_flow"
_CQ = "credit_quality"
_DA = "directors_assessment"

CREDIT_RISK_ELEMENTS: Dict[str, Tuple[str, str, str, str]] = {
    # --- Entity Info (sg-dei) ------------------------------------------------
    "NameOfCompany":
        ("Company Name", "sg-dei", _E, "company_name"),
    "UniqueEntityNumber":
        ("UEN", "sg-dei", _E, "uen"),
    "CurrentPeriodStartDate":
        ("Current Period Start", "sg-dei", _E, "period_start"),
    "CurrentPeriodEndDate":
        ("Current Period End", "sg-dei", _E, "period_end"),
    "PriorPeriodStartDate":
        ("Prior Period Start", "sg-dei", _E, "prior_period_start"),
    "PriorPeriodEndDate":
        ("Prior Period End", "sg-dei", _E, "prior_period_end"),
    "WhetherFinancialStatementsAreAudited":
        ("Audited", "sg-dei", _E, "is_audited"),
    "NatureOfFinancialStatementsCompanyLevelOrConsolidated":
        ("Consolidation Level", "sg-dei", _E, "consolidation_level"),
    "DescriptionOfPresentationCurrency":
        ("Currency", "sg-dei", _E, "currency"),
    "WhetherFinancialStatementsArePreparedOnGoingConcernBasis":
        ("Going Concern Basis", "sg-dei", _E, "going_concern"),
    "TypeOfCompanyDuringCurrentPeriod":
        ("Company Type", "sg-dei", _E, "company_type"),
    "WhetherCompanyIsDormantForCurrentPeriod":
        ("Dormant", "sg-dei", _E, "is_dormant"),

    # --- Balance Sheet (sg-as) -----------------------------------------------
    "Assets":
        ("Total Assets", "sg-as", _B, "assets"),
    "Liabilities":
        ("Total Liabilities", "sg-as", _B, "liabilities"),
    "Equity":
        ("Total Equity", "sg-as", _B, "equity"),
    "CurrentAssets":
        ("Current Assets", "sg-as", _B, "current_assets"),
    "NoncurrentAssets":
        ("Non-current Assets", "sg-as", _B, "noncurrent_assets"),
    "CurrentLiabilities":
        ("Current Liabilities", "sg-as", _B, "current_liabilities"),
    "NoncurrentLiabilities":
        ("Non-current Liabilities", "sg-as", _B, "noncurrent_liabilities"),
    "CashAndCashEquivalents":
        ("Cash & Equivalents", "sg-as", _B, "cash_and_equivalents"),
    "TradeAndOtherReceivablesCurrent":
        ("Trade Receivables (Current)", "sg-as", _B, "trade_receivables_current"),
    "TradeAndOtherPayablesCurrent":
        ("Trade Payables (Current)", "sg-as", _B, "trade_payables_current"),
    "Inventories":
        ("Inventories", "sg-as", _B, "inventories"),
    "PropertyPlantAndEquipment":
        ("PP&E", "sg-as", _B, "ppe"),
    "IntangibleAssetsOtherThanGoodwill":
        ("Intangible Assets (excl. Goodwill)", "sg-as", _B, "intangible_assets"),
    "Goodwill":
        ("Goodwill", "sg-as", _B, "goodwill"),
    "InvestmentProperties":
        ("Investment Properties", "sg-as", _B, "investment_properties"),
    "AllowanceForCreditLosses":
        ("Allowance for Credit Losses", "sg-as", _B, "allowance_credit_losses"),
    "AccruedExpenses":
        ("Accrued Expenses", "sg-as", _B, "accrued_expenses"),

    # --- Income Statement (sg-as) --------------------------------------------
    "Revenue":
        ("Revenue", "sg-as", _I, "revenue"),
    "CostOfSales":
        ("Cost of Sales", "sg-as", _I, "cost_of_sales"),
    "GrossProfit":
        ("Gross Profit", "sg-as", _I, "gross_profit"),
    "ProfitLoss":
        ("Profit / Loss", "sg-as", _I, "profit_loss"),
    "ProfitLossBeforeTax":
        ("Profit Before Tax", "sg-as", _I, "profit_before_tax"),
    "IncomeTaxExpenseContinuingOperations":
        ("Income Tax Expense", "sg-as", _I, "income_tax_expense"),
    "OtherComprehensiveIncome":
        ("Other Comprehensive Income", "sg-as", _I, "other_comprehensive_income"),
    "TotalComprehensiveIncome":
        ("Total Comprehensive Income", "sg-as", _I, "total_comprehensive_income"),

    # --- Cash Flow (sg-as) ---------------------------------------------------
    "CashFlowsFromUsedInOperatingActivities":
        ("Operating Cash Flow", "sg-as", _CF, "operating"),
    "CashFlowsFromUsedInInvestingActivities":
        ("Investing Cash Flow", "sg-as", _CF, "investing"),
    "CashFlowsFromUsedInFinancingActivities":
        ("Financing Cash Flow", "sg-as", _CF, "financing"),
    "AdjustmentsForDepreciationAndAmortisationExpense":
        ("D&A Adjustment", "sg-as", _CF, "depreciation_amortisation"),
    "AdjustmentsForFinanceCosts":
        ("Finance Cost Adjustment", "sg-as", _CF, "finance_costs"),
    "AdjustmentsForImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss":
        ("Impairment Adjustment", "sg-as", _CF, "impairment_adjustment"),

    # --- Credit Quality (sg-fsh) — critical for UBS -------------------------
    "CreditFacilitiesCategorisedAsPass":
        ("Credit Facilities — Pass", "sg-fsh", _CQ, "pass"),
    "CreditFacilitiesCategorisedAsSpecialMention":
        ("Credit Facilities — Special Mention", "sg-fsh", _CQ, "special_mention"),
    "CreditFacilitiesCategorisedAsSubstandard":
        ("Credit Facilities — Substandard", "sg-fsh", _CQ, "substandard"),
    "CreditFacilitiesCategorisedAsDoubtful":
        ("Credit Facilities — Doubtful", "sg-fsh", _CQ, "doubtful"),
    "CreditFacilitiesCategorisedAsLoss":
        ("Credit Facilities — Loss", "sg-fsh", _CQ, "loss"),
    "CreditFacilities":
        ("Total Credit Facilities", "sg-fsh", _CQ, "total_facilities"),
    "GeneralAllowanceForDebts":
        ("General Allowance", "sg-fsh", _CQ, "general_allowance"),
    "SpecificAllowanceForDebts":
        ("Specific Allowance", "sg-fsh", _CQ, "specific_allowance"),
    "CollateralsForDebts":
        ("Collaterals", "sg-fsh", _CQ, "collaterals"),
    "CommitmentsAgainstDebts":
        ("Commitments Against Debts", "sg-fsh", _CQ, "commitments"),
    "RevenueFromInterestNet":
        ("Net Interest Revenue", "sg-fsh", _CQ, "net_interest_revenue"),
    "InterestExpenditure":
        ("Interest Expenditure", "sg-fsh", _CQ, "interest_expenditure"),

    # --- Directors Assessment (sg-ca) ----------------------------------------
    "WhetherThereAreReasonableGroundsToBelieveThatCompanyWillBeAbleToPayItsDebtsAsAndWhenTheyFallDueAtDateOfStatement":
        ("Directors: Can Pay Debts", "sg-ca", _DA, "can_pay_debts"),
    "WhetherInDirectorsOpinionFinancialStatementsAreDrawnUpSoAsToExhibitATrueAndFairView":
        ("Directors: True & Fair View", "sg-ca", _DA, "true_and_fair"),
}

# Reverse lookup: namespace_uri + local_name -> element key
_NS_LOCAL_TO_KEY: Dict[Tuple[str, str], str] = {}
for _elem_name, (_label, _ns_prefix, _section, _key) in CREDIT_RISK_ELEMENTS.items():
    _ns_uri = NAMESPACES.get(_ns_prefix, "")
    _NS_LOCAL_TO_KEY[(_ns_uri, _elem_name)] = _elem_name


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"\{([^}]*)\}(.*)")


def _split_clark(tag: str) -> Tuple[str, str]:
    """Split a Clark-notation tag ``{uri}local`` into ``(uri, local)``."""
    m = _TAG_RE.match(tag)
    if m:
        return m.group(1), m.group(2)
    return "", tag


def _to_numeric(value: str) -> Optional[float]:
    """Try to parse a string as a float. Returns None on failure."""
    if value is None:
        return None
    value = value.strip().replace(",", "")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_bool(value: str) -> Optional[bool]:
    """Interpret XBRL boolean-ish values."""
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("true", "yes", "1"):
        return True
    if v in ("false", "no", "0"):
        return False
    return None


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Safe division returning None when inputs are missing or denominator is zero."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def _extract_contexts(root: ET.Element) -> Dict[str, Dict[str, Any]]:
    """
    Parse all ``<xbrli:context>`` elements into a lookup dict.

    Returns a dict keyed by context id with structure::

        {
            "id": str,
            "entity": str,         # identifier value
            "scheme": str,         # identifier scheme
            "instant": str | None, # ISO date for instant contexts
            "start": str | None,   # period startDate
            "end": str | None,     # period endDate
            "dimensions": dict,    # explicit dimension member pairs
        }
    """
    xbrli_ns = NAMESPACES["xbrli"]
    contexts: Dict[str, Dict[str, Any]] = {}

    for ctx in root.iter(f"{{{xbrli_ns}}}context"):
        ctx_id = ctx.get("id", "")
        entry: Dict[str, Any] = {
            "id": ctx_id,
            "entity": "",
            "scheme": "",
            "instant": None,
            "start": None,
            "end": None,
            "dimensions": {},
        }

        # Entity identifier
        ident = ctx.find(f".//{{{xbrli_ns}}}identifier")
        if ident is not None:
            entry["entity"] = (ident.text or "").strip()
            entry["scheme"] = ident.get("scheme", "")

        # Period
        instant = ctx.find(f".//{{{xbrli_ns}}}instant")
        if instant is not None and instant.text:
            entry["instant"] = instant.text.strip()
        start = ctx.find(f".//{{{xbrli_ns}}}startDate")
        end = ctx.find(f".//{{{xbrli_ns}}}endDate")
        if start is not None and start.text:
            entry["start"] = start.text.strip()
        if end is not None and end.text:
            entry["end"] = end.text.strip()

        # Explicit dimensions (scenario or segment)
        for member in ctx.iter():
            tag_ns, tag_local = _split_clark(member.tag)
            if tag_local in ("explicitMember", "typedMember"):
                dim = member.get("dimension", "")
                val = (member.text or "").strip()
                entry["dimensions"][dim] = val

        contexts[ctx_id] = entry

    return contexts


def _extract_units(root: ET.Element) -> Dict[str, str]:
    """
    Parse all ``<xbrli:unit>`` elements.

    Returns a dict keyed by unit id with a string representation
    (e.g. ``"SGD"``, ``"SGD/shares"``).
    """
    xbrli_ns = NAMESPACES["xbrli"]
    units: Dict[str, str] = {}

    for unit in root.iter(f"{{{xbrli_ns}}}unit"):
        uid = unit.get("id", "")
        measure = unit.find(f".//{{{xbrli_ns}}}measure")
        if measure is not None and measure.text:
            # Strip namespace prefix from measure (e.g. "iso4217:SGD" -> "SGD")
            raw = measure.text.strip()
            units[uid] = raw.split(":")[-1] if ":" in raw else raw
            continue

        # Compound unit (divide)
        divide = unit.find(f"{{{xbrli_ns}}}divide")
        if divide is not None:
            num = divide.find(f".//{{{xbrli_ns}}}unitNumerator//{{{xbrli_ns}}}measure")
            den = divide.find(f".//{{{xbrli_ns}}}unitDenominator//{{{xbrli_ns}}}measure")
            n_txt = (num.text.split(":")[-1] if num is not None and num.text else "?")
            d_txt = (den.text.split(":")[-1] if den is not None and den.text else "?")
            units[uid] = f"{n_txt}/{d_txt}"
        else:
            units[uid] = ""

    return units


def _pick_current_period_context(
    contexts: Dict[str, Dict[str, Any]],
    fact_contexts: List[str],
) -> Optional[str]:
    """
    Among the context ids in *fact_contexts*, return the one whose period
    end date is the latest (heuristic for 'current period').  Prefers
    duration contexts over instant contexts when both exist.
    """
    best_id: Optional[str] = None
    best_end: str = ""
    best_is_duration = False

    for cid in fact_contexts:
        ctx = contexts.get(cid)
        if ctx is None:
            continue
        end = ctx.get("end") or ctx.get("instant") or ""
        is_dur = ctx.get("end") is not None
        if end > best_end or (end == best_end and is_dur and not best_is_duration):
            best_end = end
            best_id = cid
            best_is_duration = is_dur

    return best_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_xbrl_instance(content: Union[str, bytes]) -> dict:
    """
    Parse an ACRA BizFinx XBRL instance document and extract structured
    financial data for credit risk assessment.

    Args:
        content: The raw XML content of the XBRL instance document,
                 as a string or bytes object.

    Returns:
        A dict with the following top-level keys:

        - ``entity_info``          -- company name, UEN, period dates, etc.
        - ``balance_sheet``        -- assets, liabilities, equity, sub-items
        - ``income_statement``     -- revenue, profit/loss, etc.
        - ``cash_flow``            -- operating, investing, financing
        - ``credit_quality``       -- MAS credit grading buckets & allowances
        - ``directors_assessment`` -- going-concern and true & fair opinions
        - ``computed_ratios``      -- current ratio, D/E, NPL ratio, etc.
        - ``risk_flags``           -- list of auto-detected red flags
        - ``raw_facts``            -- every extracted fact with context/unit metadata
        - ``metadata``             -- parser statistics
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    root = ET.fromstring(content)

    contexts = _extract_contexts(root)
    units = _extract_units(root)

    # Collect all facts -------------------------------------------------------
    raw_facts: Dict[str, Dict[str, Any]] = {}
    # Track which context ids each element appears in
    element_context_map: Dict[str, List[str]] = {}

    total_facts = 0
    monetary_facts = 0

    for elem in root:
        ns_uri, local_name = _split_clark(elem.tag)
        if ns_uri == NAMESPACES["xbrli"]:
            # Skip xbrli infrastructure elements (context, unit, schemaRef)
            continue

        total_facts += 1
        ctx_ref = elem.get("contextRef", "")
        unit_ref = elem.get("unitRef", "")
        decimals = elem.get("decimals", "")
        value = (elem.text or "").strip()
        unit_str = units.get(unit_ref, unit_ref)

        if unit_str and unit_str not in ("", "shares", "pure"):
            monetary_facts += 1

        fact_key = f"{local_name}|{ctx_ref}"
        raw_facts[fact_key] = {
            "element": local_name,
            "namespace": ns_uri,
            "value": value,
            "context": ctx_ref,
            "unit": unit_str,
            "decimals": decimals,
        }

        if local_name not in element_context_map:
            element_context_map[local_name] = []
        element_context_map[local_name].append(ctx_ref)

    # Build output sections ---------------------------------------------------
    output: Dict[str, Any] = {
        "entity_info": {},
        "balance_sheet": {},
        "income_statement": {},
        "cash_flow": {},
        "credit_quality": {},
        "directors_assessment": {},
        "computed_ratios": {},
        "risk_flags": [],
        "raw_facts": {},
        "metadata": {},
    }

    # For each known element, pick the best fact (current period, no dimensions)
    for elem_name, (label, ns_prefix, section, out_key) in CREDIT_RISK_ELEMENTS.items():
        ns_uri = NAMESPACES.get(ns_prefix, "")
        ctx_ids = element_context_map.get(elem_name, [])

        if not ctx_ids:
            continue

        # Prefer contexts with no dimensions
        simple_ctx_ids = [
            c for c in ctx_ids
            if c in contexts and not contexts[c].get("dimensions")
        ]
        pool = simple_ctx_ids if simple_ctx_ids else ctx_ids

        best_ctx = _pick_current_period_context(contexts, pool)
        if best_ctx is None:
            best_ctx = pool[0]

        fact_key = f"{elem_name}|{best_ctx}"
        fact = raw_facts.get(fact_key)
        if fact is None:
            continue

        value = fact["value"]

        # Store into the appropriate section
        if section == _E:
            # Entity info: keep as string
            output["entity_info"][out_key] = value
        elif section == _DA:
            output["directors_assessment"][out_key] = value
        else:
            # Financial sections: attempt numeric conversion
            num = _to_numeric(value)
            if num is not None:
                output[section][out_key] = num
            else:
                output[section][out_key] = value

    # Flatten raw_facts for output (remove pipe-delimited keys)
    clean_raw: Dict[str, Dict[str, Any]] = {}
    for fk, fv in raw_facts.items():
        elem_name = fv["element"]
        if elem_name not in clean_raw:
            clean_raw[elem_name] = {
                "value": fv["value"],
                "context": fv["context"],
                "unit": fv["unit"],
                "decimals": fv["decimals"],
            }
        else:
            # Store multiple contexts as a list
            existing = clean_raw[elem_name]
            if isinstance(existing.get("value"), list):
                existing["value"].append(fv["value"])
                existing["context"].append(fv["context"])
            else:
                existing["value"] = [existing["value"], fv["value"]]
                existing["context"] = [existing["context"], fv["context"]]

    output["raw_facts"] = clean_raw

    # Compute ratios and flags ------------------------------------------------
    output["computed_ratios"] = compute_credit_ratios(output)
    output["risk_flags"] = detect_risk_flags(output)

    # Count distinct namespace URIs found
    seen_ns = set()
    for fv in raw_facts.values():
        if fv["namespace"]:
            seen_ns.add(fv["namespace"])

    output["metadata"] = {
        "namespace_count": len(seen_ns),
        "total_facts": total_facts,
        "monetary_facts": monetary_facts,
        "parser_version": "1.0",
    }

    return output


def compute_credit_ratios(parsed: dict) -> dict:
    """
    Compute key credit risk ratios from parsed XBRL data.

    Ratios computed:
        - **current_ratio**: current_assets / current_liabilities
        - **debt_to_equity**: total_liabilities / total_equity
        - **npl_ratio**: (substandard + doubtful + loss) / total_facilities
        - **coverage_ratio**: (general_allowance + specific_allowance) / NPL
        - **profit_margin**: profit_loss / revenue
        - **interest_coverage**: profit_before_tax / finance_costs

    Args:
        parsed: The output dict from ``parse_xbrl_instance`` (or a dict
                with at least ``balance_sheet``, ``income_statement``,
                ``cash_flow``, and ``credit_quality`` sub-dicts).

    Returns:
        A dict of ratio names to float values (or None if not computable).
    """
    bs = parsed.get("balance_sheet", {})
    inc = parsed.get("income_statement", {})
    cf = parsed.get("cash_flow", {})
    cq = parsed.get("credit_quality", {})

    current_assets = bs.get("current_assets")
    current_liabilities = bs.get("current_liabilities")
    liabilities = bs.get("liabilities")
    equity = bs.get("equity")
    revenue = inc.get("revenue")
    profit_loss = inc.get("profit_loss")
    profit_before_tax = inc.get("profit_before_tax")
    finance_costs = cf.get("finance_costs")

    substandard = cq.get("substandard")
    doubtful = cq.get("doubtful")
    loss_val = cq.get("loss")
    total_facilities = cq.get("total_facilities")
    gen_allowance = cq.get("general_allowance")
    spec_allowance = cq.get("specific_allowance")

    # NPL = substandard + doubtful + loss
    npl: Optional[float] = None
    if any(v is not None for v in (substandard, doubtful, loss_val)):
        npl = (substandard or 0) + (doubtful or 0) + (loss_val or 0)

    # Total allowance
    total_allowance: Optional[float] = None
    if gen_allowance is not None or spec_allowance is not None:
        total_allowance = (gen_allowance or 0) + (spec_allowance or 0)

    return {
        "current_ratio": _safe_div(current_assets, current_liabilities),
        "debt_to_equity": _safe_div(liabilities, equity),
        "npl_ratio": _safe_div(npl, total_facilities),
        "coverage_ratio": _safe_div(total_allowance, npl),
        "profit_margin": _safe_div(profit_loss, revenue),
        "interest_coverage": _safe_div(profit_before_tax, finance_costs),
    }


def detect_risk_flags(parsed: dict) -> List[str]:
    """
    Detect credit risk red flags from parsed XBRL data.

    Flags detected:
        - Going concern basis is ``No`` / ``false``
        - NPL ratio exceeds 5%
        - Negative equity
        - Current ratio below 1.0
        - Debt-to-equity exceeds 3.0
        - Negative net profit
        - Company is dormant
        - Financial statements are not audited
        - Directors do not believe company can pay debts
        - Directors' true & fair view is negative

    Args:
        parsed: The output dict from ``parse_xbrl_instance``.

    Returns:
        A list of human-readable risk flag strings.
    """
    flags: List[str] = []

    ei = parsed.get("entity_info", {})
    bs = parsed.get("balance_sheet", {})
    inc = parsed.get("income_statement", {})
    da = parsed.get("directors_assessment", {})
    ratios = parsed.get("computed_ratios", {})

    # Going concern
    gc = ei.get("going_concern", "")
    if _to_bool(gc) is False:
        flags.append("CRITICAL: Financial statements NOT prepared on going concern basis")

    # Dormant
    dormant = ei.get("is_dormant", "")
    if _to_bool(dormant) is True:
        flags.append("WARNING: Company is dormant for the current period")

    # Not audited
    audited = ei.get("is_audited", "")
    if _to_bool(audited) is False:
        flags.append("WARNING: Financial statements are NOT audited")

    # Directors: can pay debts
    cpd = da.get("can_pay_debts", "")
    if _to_bool(cpd) is False:
        flags.append(
            "CRITICAL: Directors do NOT believe company can pay debts as they fall due"
        )

    # Directors: true and fair view
    taf = da.get("true_and_fair", "")
    if _to_bool(taf) is False:
        flags.append(
            "CRITICAL: Directors' opinion — statements do NOT exhibit a true and fair view"
        )

    # Negative equity
    equity = bs.get("equity")
    if isinstance(equity, (int, float)) and equity < 0:
        flags.append(f"CRITICAL: Negative equity ({equity:,.0f})")

    # Current ratio < 1
    cr = ratios.get("current_ratio")
    if cr is not None and cr < 1.0:
        flags.append(f"WARNING: Current ratio below 1.0 ({cr:.2f})")

    # Debt-to-equity > 3
    de = ratios.get("debt_to_equity")
    if de is not None and de > 3.0:
        flags.append(f"WARNING: High debt-to-equity ratio ({de:.2f})")

    # Negative profit
    pl = inc.get("profit_loss")
    if isinstance(pl, (int, float)) and pl < 0:
        flags.append(f"WARNING: Net loss reported ({pl:,.0f})")

    # NPL ratio > 5%
    npl = ratios.get("npl_ratio")
    if npl is not None and npl > 0.05:
        flags.append(f"WARNING: NPL ratio exceeds 5% ({npl:.2%})")

    return flags


def parse_xbrl_taxonomy_xsd(content: Union[str, bytes]) -> dict:
    """
    Parse an XBRL taxonomy XSD schema file and extract element definitions.

    This is useful when a user uploads the taxonomy schema rather than an
    instance document.  Returns a dict of element names to their XSD
    properties.

    Args:
        content: The raw XML content of the ``.xsd`` taxonomy file.

    Returns:
        A dict with structure::

            {
                "elements": {
                    "Revenue": {
                        "name": "Revenue",
                        "id": "sg-as_Revenue",
                        "type": "xbrli:monetaryItemType",
                        "substitutionGroup": "xbrli:item",
                        "periodType": "duration",
                        "balance": "credit",
                        "nillable": "true",
                        "abstract": "false",
                    },
                    ...
                },
                "namespace": "http://www.bizfinx.gov.sg/...",
                "element_count": 1234,
            }
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    root = ET.fromstring(content)
    target_ns = root.get("targetNamespace", "")

    xs_ns = "http://www.w3.org/2001/XMLSchema"
    xbrli_ns = NAMESPACES["xbrli"]

    elements: Dict[str, Dict[str, str]] = {}

    # XSD element declarations can be top-level children of <xs:schema>
    for elem in root:
        ns_uri, local = _split_clark(elem.tag)
        if local != "element":
            continue

        name = elem.get("name", "")
        if not name:
            continue

        entry: Dict[str, str] = {"name": name}
        for attr in (
            "id", "type", "substitutionGroup", "nillable", "abstract",
        ):
            val = elem.get(attr)
            if val is not None:
                entry[attr] = val

        # XBRL-specific attributes often use the xbrli namespace prefix
        # in the source, but ET resolves them as attributes with full URI
        # or sometimes as un-prefixed attributes set by the taxonomy author.
        for xbrl_attr in ("periodType", "balance"):
            # Try un-prefixed first, then with xbrli namespace
            val = elem.get(xbrl_attr)
            if val is None:
                val = elem.get(f"{{{xbrli_ns}}}{xbrl_attr}")
            if val is not None:
                entry[xbrl_attr] = val

        elements[name] = entry

    return {
        "elements": elements,
        "namespace": target_ns,
        "element_count": len(elements),
    }


def format_xbrl_summary(parsed: dict) -> str:
    """
    Format parsed XBRL data as a human-readable Markdown summary.

    Produces a multi-section report with tables for each data category
    and a risk-flags section at the end.

    Args:
        parsed: The output dict from ``parse_xbrl_instance``.

    Returns:
        A Markdown-formatted string.
    """
    lines: List[str] = []

    ei = parsed.get("entity_info", {})
    bs = parsed.get("balance_sheet", {})
    inc = parsed.get("income_statement", {})
    cf = parsed.get("cash_flow", {})
    cq = parsed.get("credit_quality", {})
    da = parsed.get("directors_assessment", {})
    ratios = parsed.get("computed_ratios", {})
    flags = parsed.get("risk_flags", [])
    meta = parsed.get("metadata", {})

    # Title
    company = ei.get("company_name", "Unknown Company")
    period_end = ei.get("period_end", "")
    lines.append(f"# XBRL Financial Summary: {company}")
    if period_end:
        lines.append(f"**Period ending:** {period_end}")
    lines.append("")

    # Entity Information
    if ei:
        lines.append("## Entity Information")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        _label_map = {
            "company_name": "Company Name",
            "uen": "UEN",
            "period_start": "Period Start",
            "period_end": "Period End",
            "prior_period_start": "Prior Period Start",
            "prior_period_end": "Prior Period End",
            "currency": "Currency",
            "is_audited": "Audited",
            "going_concern": "Going Concern Basis",
            "consolidation_level": "Consolidation",
            "company_type": "Company Type",
            "is_dormant": "Dormant",
        }
        for key, label in _label_map.items():
            val = ei.get(key)
            if val is not None:
                lines.append(f"| {label} | {val} |")
        lines.append("")

    # Helper for financial tables
    def _fin_table(title: str, data: dict, label_map: Dict[str, str]) -> None:
        if not data:
            return
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Item | Value |")
        lines.append("|------|------:|")
        for key, label in label_map.items():
            val = data.get(key)
            if val is None:
                continue
            if isinstance(val, float):
                lines.append(f"| {label} | {val:,.0f} |")
            else:
                lines.append(f"| {label} | {val} |")
        lines.append("")

    _fin_table("Balance Sheet", bs, OrderedDict([
        ("assets", "Total Assets"),
        ("current_assets", "Current Assets"),
        ("noncurrent_assets", "Non-current Assets"),
        ("cash_and_equivalents", "Cash & Equivalents"),
        ("trade_receivables_current", "Trade Receivables"),
        ("inventories", "Inventories"),
        ("ppe", "PP&E"),
        ("intangible_assets", "Intangible Assets"),
        ("goodwill", "Goodwill"),
        ("investment_properties", "Investment Properties"),
        ("liabilities", "Total Liabilities"),
        ("current_liabilities", "Current Liabilities"),
        ("noncurrent_liabilities", "Non-current Liabilities"),
        ("trade_payables_current", "Trade Payables"),
        ("accrued_expenses", "Accrued Expenses"),
        ("allowance_credit_losses", "Allowance for Credit Losses"),
        ("equity", "Total Equity"),
    ]))

    _fin_table("Income Statement", inc, OrderedDict([
        ("revenue", "Revenue"),
        ("cost_of_sales", "Cost of Sales"),
        ("gross_profit", "Gross Profit"),
        ("profit_before_tax", "Profit Before Tax"),
        ("income_tax_expense", "Income Tax Expense"),
        ("profit_loss", "Profit / Loss"),
        ("other_comprehensive_income", "Other Comprehensive Income"),
        ("total_comprehensive_income", "Total Comprehensive Income"),
    ]))

    _fin_table("Cash Flow Statement", cf, OrderedDict([
        ("operating", "Operating Activities"),
        ("investing", "Investing Activities"),
        ("financing", "Financing Activities"),
        ("depreciation_amortisation", "D&A Adjustment"),
        ("finance_costs", "Finance Cost Adjustment"),
        ("impairment_adjustment", "Impairment Adjustment"),
    ]))

    _fin_table("Credit Quality (MAS Grading)", cq, OrderedDict([
        ("pass", "Pass"),
        ("special_mention", "Special Mention"),
        ("substandard", "Substandard"),
        ("doubtful", "Doubtful"),
        ("loss", "Loss"),
        ("total_facilities", "Total Facilities"),
        ("general_allowance", "General Allowance"),
        ("specific_allowance", "Specific Allowance"),
        ("collaterals", "Collaterals"),
        ("commitments", "Commitments"),
        ("net_interest_revenue", "Net Interest Revenue"),
        ("interest_expenditure", "Interest Expenditure"),
    ]))

    # Directors Assessment
    if da:
        lines.append("## Directors' Assessment")
        lines.append("")
        lines.append("| Statement | Value |")
        lines.append("|-----------|-------|")
        if "true_and_fair" in da:
            lines.append(f"| True & Fair View | {da['true_and_fair']} |")
        if "can_pay_debts" in da:
            lines.append(f"| Can Pay Debts When Due | {da['can_pay_debts']} |")
        lines.append("")

    # Ratios
    if ratios:
        lines.append("## Computed Ratios")
        lines.append("")
        lines.append("| Ratio | Value |")
        lines.append("|-------|------:|")
        _ratio_labels = OrderedDict([
            ("current_ratio", "Current Ratio"),
            ("debt_to_equity", "Debt-to-Equity"),
            ("npl_ratio", "NPL Ratio"),
            ("coverage_ratio", "Coverage Ratio"),
            ("profit_margin", "Profit Margin"),
            ("interest_coverage", "Interest Coverage"),
        ])
        for key, label in _ratio_labels.items():
            val = ratios.get(key)
            if val is None:
                lines.append(f"| {label} | N/A |")
            elif key in ("npl_ratio", "profit_margin"):
                lines.append(f"| {label} | {val:.2%} |")
            else:
                lines.append(f"| {label} | {val:.2f} |")
        lines.append("")

    # Risk Flags
    lines.append("## Risk Flags")
    lines.append("")
    if flags:
        for flag in flags:
            lines.append(f"- {flag}")
    else:
        lines.append("- No risk flags detected.")
    lines.append("")

    # Metadata
    lines.append("---")
    lines.append(
        f"*Parser v{meta.get('parser_version', '?')} | "
        f"{meta.get('total_facts', '?')} total facts | "
        f"{meta.get('monetary_facts', '?')} monetary facts | "
        f"{meta.get('namespace_count', '?')} namespaces*"
    )

    return "\n".join(lines)
