"""Hallucination detection guardrails.

Uses difflib fuzzy matching and regex to verify that agent outputs
are grounded in source data rather than fabricated. Optionally uses
LLM as a second-pass verifier for claims that fail fuzzy matching
(reduces false negatives from overly strict string comparison).
"""

import json
import re
import difflib
from typing import Tuple

from src.core.llm import get_llm, sanitize_for_prompt, extract_json_from_llm


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


def llm_verify_claims(
    claims: list[str],
    source_texts: list[str],
    company_name: str,
) -> dict:
    """Use LLM to verify whether ungrounded claims are supported by source data.

    This is a second-pass verifier for claims that failed fuzzy matching.
    The LLM can catch semantic equivalence that string matching misses
    (e.g., "high leverage" vs "debt-to-equity ratio of 3.5x").

    Returns dict with verified/unverified lists and llm_available flag.
    """
    llm = get_llm(temperature=0.0)
    if not llm or not claims:
        return {"verified": [], "unverified": claims, "llm_available": llm is not None}

    from langchain_core.messages import SystemMessage, HumanMessage

    # Truncate sources to avoid token overflow
    source_summary = "\n".join(source_texts[:20])[:4000]
    claims_text = "\n".join(f"- {c}" for c in claims[:15])
    safe_name = sanitize_for_prompt(company_name)

    prompt = (
        f"You are a fact-checking assistant for credit risk assessments about {safe_name}.\n\n"
        f"SOURCE DOCUMENTS:\n{source_summary}\n\n"
        f"CLAIMS TO VERIFY:\n{claims_text}\n\n"
        "For each claim, determine if it is reasonably supported by the source documents. "
        "A claim is 'verified' if the sources contain evidence that supports or implies it, "
        "even if not stated in identical words.\n\n"
        'Return JSON: {"verified": ["claim1", ...], "unverified": ["claim2", ...]}'
    )

    try:
        response = llm.invoke([
            SystemMessage(content="You are a precise fact-checker. Return only valid JSON."),
            HumanMessage(content=prompt),
        ])
        raw = extract_json_from_llm(response.content)
        result = json.loads(raw)
        return {
            "verified": result.get("verified", []),
            "unverified": result.get("unverified", claims),
            "llm_available": True,
        }
    except Exception:
        return {"verified": [], "unverified": claims, "llm_available": True}


def check_entity_attribution(
    company_name: str,
    risks: list,
    strengths: list,
    source_data: list,
    use_llm: bool = True,
) -> dict:
    """Verify that risk and strength descriptions are grounded in source data.

    Uses difflib.SequenceMatcher with threshold 0.4 for fuzzy matching.
    When use_llm=True (default), sends fuzzy-match failures to LLM for
    semantic verification as a second pass, recovering false negatives.

    Returns a dict with grounded/ungrounded lists and an attribution score.
    """
    source_texts = _extract_source_texts(source_data)
    if not source_texts:
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

    # LLM second-pass: verify claims that failed fuzzy matching
    if use_llm and (ungrounded_risks or ungrounded_strengths):
        all_ungrounded_descs = []
        risk_descs = []
        strength_descs = []
        for r in ungrounded_risks:
            d = r.get("description", "") if isinstance(r, dict) else str(r)
            all_ungrounded_descs.append(d)
            risk_descs.append(d)
        for s in ungrounded_strengths:
            d = s.get("description", "") if isinstance(s, dict) else str(s)
            all_ungrounded_descs.append(d)
            strength_descs.append(d)

        llm_result = llm_verify_claims(all_ungrounded_descs, source_texts, company_name)
        verified_set = set(llm_result.get("verified", []))

        # Move LLM-verified items from ungrounded to grounded
        if verified_set:
            still_ungrounded_risks = []
            for r in ungrounded_risks:
                d = r.get("description", "") if isinstance(r, dict) else str(r)
                if d in verified_set:
                    grounded_risks.append(r)
                else:
                    still_ungrounded_risks.append(r)
            ungrounded_risks = still_ungrounded_risks

            still_ungrounded_strengths = []
            for s in ungrounded_strengths:
                d = s.get("description", "") if isinstance(s, dict) else str(s)
                if d in verified_set:
                    grounded_strengths.append(s)
                else:
                    still_ungrounded_strengths.append(s)
            ungrounded_strengths = still_ungrounded_strengths

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

    # System-generated numbers that are always valid (not hallucinations)
    # Risk scores, thresholds, percentage labels used by the scoring system
    system_numbers = {
        "0", "33", "34", "50", "66", "67", "100",  # score thresholds/defaults
        "0.0", "33.0", "50.0", "67.0", "100.0",
    }
    known_values.update(system_numbers)

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
