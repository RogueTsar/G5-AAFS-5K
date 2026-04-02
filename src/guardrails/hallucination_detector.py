"""Hallucination detection guardrails.

Uses difflib fuzzy matching and regex to verify that agent outputs
are grounded in source data rather than fabricated.
"""

import re
import difflib
from typing import Tuple


def _fuzzy_match_against_sources(
    description: str, source_texts: list, threshold: float = 0.4
) -> bool:
    """Return True if description fuzzy-matches any source text above threshold."""
    desc_lower = description.lower().strip()
    for source_text in source_texts:
        src_lower = source_text.lower().strip()
        # Check substring containment first (fast path)
        if desc_lower in src_lower or src_lower in desc_lower:
            return True
        # Sliding window: compare description against chunks of source
        ratio = difflib.SequenceMatcher(None, desc_lower, src_lower).ratio()
        if ratio >= threshold:
            return True
        # Also check if any sentence in source matches
        sentences = re.split(r'[.!?]+', src_lower)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            ratio = difflib.SequenceMatcher(None, desc_lower, sentence).ratio()
            if ratio >= threshold:
                return True
    return False


def _extract_source_texts(source_data: list) -> list:
    """Extract text strings from source_data entries."""
    texts = []
    for item in source_data:
        if isinstance(item, str):
            texts.append(item)
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    texts.append(value)
    return texts


def check_entity_attribution(
    company_name: str,
    risks: list,
    strengths: list,
    source_data: list,
) -> dict:
    """Verify that risk and strength descriptions are grounded in source data.

    Uses difflib.SequenceMatcher with threshold 0.4 for fuzzy matching.
    Returns a dict with grounded/ungrounded lists and an attribution score.
    """
    source_texts = _extract_source_texts(source_data)
    if not source_texts:
        # No sources means nothing can be grounded
        return {
            "grounded_risks": [],
            "ungrounded_risks": list(risks),
            "grounded_strengths": [],
            "ungrounded_strengths": list(strengths),
            "attribution_score": 0.0,
        }

    grounded_risks = []
    ungrounded_risks = []
    for risk in risks:
        desc = risk.get("description", "") if isinstance(risk, dict) else str(risk)
        if _fuzzy_match_against_sources(desc, source_texts, threshold=0.4):
            grounded_risks.append(risk)
        else:
            ungrounded_risks.append(risk)

    grounded_strengths = []
    ungrounded_strengths = []
    for strength in strengths:
        desc = strength.get("description", "") if isinstance(strength, dict) else str(strength)
        if _fuzzy_match_against_sources(desc, source_texts, threshold=0.4):
            grounded_strengths.append(strength)
        else:
            ungrounded_strengths.append(strength)

    total = len(risks) + len(strengths)
    grounded_count = len(grounded_risks) + len(grounded_strengths)
    attribution_score = grounded_count / total if total > 0 else 1.0

    return {
        "grounded_risks": grounded_risks,
        "ungrounded_risks": ungrounded_risks,
        "grounded_strengths": grounded_strengths,
        "ungrounded_strengths": ungrounded_strengths,
        "attribution_score": round(attribution_score, 4),
    }


def verify_company_in_output(
    company_name: str, report: str, aliases: list = None
) -> Tuple[bool, list]:
    """Check that the company name or aliases appear in the report.

    Returns (found: bool, warnings: list[str]).
    """
    warnings = []
    names_to_check = [company_name]
    if aliases:
        names_to_check.extend(aliases)

    report_lower = report.lower()
    found_any = False
    for name in names_to_check:
        if name and name.lower() in report_lower:
            found_any = True
            break

    if not found_any:
        warnings.append(
            f"Company name '{company_name}' (and aliases) not found in report. "
            "Possible hallucination or wrong entity."
        )

    return found_any, warnings


def flag_fabricated_metrics(report: str, financial_data: list) -> list:
    """Extract numeric values from report and cross-check against financial data.

    Regex extracts percentages, dollar amounts, and plain numbers from the
    report text. Each is compared against known values in financial_data.
    Returns a list of flagged fabrication strings.
    """
    # Build a set of known numeric values from financial_data
    known_values = set()
    for item in financial_data:
        if isinstance(item, dict):
            for value in item.values():
                if isinstance(value, (int, float)):
                    known_values.add(str(value))
                    known_values.add(f"{value:.1f}")
                    known_values.add(f"{value:.2f}")
                elif isinstance(value, str):
                    # Extract numbers from string values
                    nums = re.findall(r'-?[\d,]+\.?\d*', value)
                    for n in nums:
                        known_values.add(n.replace(',', ''))
        elif isinstance(item, (int, float)):
            known_values.add(str(item))

    # Extract numeric claims from report
    # Patterns: $1,234.56, 12.5%, 1,234, plain numbers
    patterns = [
        (r'\$[\d,]+\.?\d*', "dollar amount"),
        (r'-?[\d,]+\.?\d*\s*%', "percentage"),
        (r'(?<!\$)(?<!\w)-?[\d,]+\.?\d+(?!\s*%)', "number"),
    ]

    flagged = []
    for pattern, label in patterns:
        matches = re.findall(pattern, report)
        for match in matches:
            # Normalize: strip $, %, commas, whitespace
            normalized = match.replace('$', '').replace('%', '').replace(',', '').strip()
            if not normalized or normalized in ('.', '-'):
                continue
            # Check if this value is known
            if normalized not in known_values:
                flagged.append(
                    f"Unverified {label} in report: '{match.strip()}' "
                    "not found in source financial data."
                )

    return flagged
