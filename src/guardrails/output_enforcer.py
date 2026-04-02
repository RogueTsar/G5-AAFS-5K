"""Output enforcement guardrails for structured agent outputs.

All functions are pure (no LLM calls). They validate, clamp, and clean
Pydantic-serialized dicts produced by the credit risk pipeline agents.
"""

from typing import Tuple

VALID_RISK_TYPES = ["Traditional Risk", "Non-traditional Risk"]
VALID_STRENGTH_TYPES = ["Financial Strength", "Market Strength"]
VALID_RATINGS = ["Low", "Medium", "High"]

RATING_RANGES = {
    "Low": (0, 33),
    "Medium": (34, 66),
    "High": (67, 100),
}


def enforce_risk_extraction(output: dict) -> Tuple[dict, list]:
    """Validate and clean risk/strength extraction output.

    Checks risk.type, strength.type validity; ensures descriptions are
    non-empty and under 500 characters. Removes invalid entries.
    """
    warnings = []
    cleaned = dict(output)

    # --- validate risks ---
    if "risks" in cleaned:
        valid_risks = []
        for i, risk in enumerate(cleaned["risks"]):
            if not isinstance(risk, dict):
                warnings.append(f"Risk at index {i} is not a dict, removed.")
                continue
            rtype = risk.get("type", "")
            desc = risk.get("description", "")
            if rtype not in VALID_RISK_TYPES:
                warnings.append(
                    f"Risk at index {i} has invalid type '{rtype}', removed."
                )
                continue
            if not desc or not desc.strip():
                warnings.append(
                    f"Risk at index {i} has empty description, removed."
                )
                continue
            if len(desc) > 500:
                risk = dict(risk)
                risk["description"] = desc[:500]
                warnings.append(
                    f"Risk at index {i} description truncated to 500 chars."
                )
            valid_risks.append(risk)
        cleaned["risks"] = valid_risks

    # --- validate strengths ---
    if "strengths" in cleaned:
        valid_strengths = []
        for i, strength in enumerate(cleaned["strengths"]):
            if not isinstance(strength, dict):
                warnings.append(f"Strength at index {i} is not a dict, removed.")
                continue
            stype = strength.get("type", "")
            desc = strength.get("description", "")
            if stype not in VALID_STRENGTH_TYPES:
                warnings.append(
                    f"Strength at index {i} has invalid type '{stype}', removed."
                )
                continue
            if not desc or not desc.strip():
                warnings.append(
                    f"Strength at index {i} has empty description, removed."
                )
                continue
            if len(desc) > 500:
                strength = dict(strength)
                strength["description"] = desc[:500]
                warnings.append(
                    f"Strength at index {i} description truncated to 500 chars."
                )
            valid_strengths.append(strength)
        cleaned["strengths"] = valid_strengths

    return cleaned, warnings


def enforce_risk_score(output: dict) -> Tuple[dict, list]:
    """Validate and clamp risk score output.

    Ensures score is int 0-100, rating is valid, and rating-score
    consistency (Low: 0-33, Medium: 34-66, High: 67-100).
    Clamps out-of-range scores.
    """
    warnings = []
    cleaned = dict(output)

    # --- score ---
    score = cleaned.get("score")
    if score is None:
        warnings.append("Missing score, defaulting to 50.")
        score = 50
    try:
        score = int(score)
    except (TypeError, ValueError):
        warnings.append(f"Non-integer score '{score}', defaulting to 50.")
        score = 50

    if score < 0:
        warnings.append(f"Score {score} below 0, clamped to 0.")
        score = 0
    elif score > 100:
        warnings.append(f"Score {score} above 100, clamped to 100.")
        score = 100
    cleaned["score"] = score

    # --- max ---
    cleaned["max"] = 100

    # --- rating ---
    rating = cleaned.get("rating", "")
    if rating not in VALID_RATINGS:
        # Derive rating from score
        for r, (lo, hi) in RATING_RANGES.items():
            if lo <= score <= hi:
                rating = r
                break
        warnings.append(
            f"Invalid rating '{cleaned.get('rating', '')}', derived '{rating}' from score."
        )
    else:
        # Consistency check
        lo, hi = RATING_RANGES[rating]
        if not (lo <= score <= hi):
            old_rating = rating
            for r, (rlo, rhi) in RATING_RANGES.items():
                if rlo <= score <= rhi:
                    rating = r
                    break
            warnings.append(
                f"Rating '{old_rating}' inconsistent with score {score}, corrected to '{rating}'."
            )
    cleaned["rating"] = rating

    return cleaned, warnings


def enforce_explanations(output: dict) -> Tuple[dict, list]:
    """Validate explanation entries.

    Each explanation must have non-empty metric and reason.
    At least one valid explanation is required.
    """
    warnings = []
    cleaned = dict(output)

    explanations = cleaned.get("explanations", [])
    if not isinstance(explanations, list):
        warnings.append("Explanations field is not a list, reset to empty.")
        explanations = []

    valid = []
    for i, exp in enumerate(explanations):
        if not isinstance(exp, dict):
            warnings.append(f"Explanation at index {i} is not a dict, removed.")
            continue
        metric = exp.get("metric", "")
        reason = exp.get("reason", "")
        if not metric or not metric.strip():
            warnings.append(f"Explanation at index {i} has empty metric, removed.")
            continue
        if not reason or not reason.strip():
            warnings.append(f"Explanation at index {i} has empty reason, removed.")
            continue
        valid.append(exp)

    if not valid:
        warnings.append(
            "No valid explanations found. Adding placeholder explanation."
        )
        valid.append({
            "metric": "Overall Assessment",
            "reason": "Insufficient data to generate detailed explanations.",
        })

    cleaned["explanations"] = valid
    return cleaned, warnings


def confidence_floor_filter(
    items: list, min_confidence: float = 0.3
) -> Tuple[list, list]:
    """Filter FinBERT-enriched items below a confidence threshold.

    Items without finbert_sentiment are kept. Items with
    finbert_sentiment.score below min_confidence are removed.
    Returns (kept_items, warnings).
    """
    warnings = []
    kept = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            kept.append(item)
            continue
        sentiment = item.get("finbert_sentiment")
        if sentiment is None or not isinstance(sentiment, dict):
            kept.append(item)
            continue
        score = sentiment.get("score")
        if score is None:
            kept.append(item)
            continue
        try:
            score = float(score)
        except (TypeError, ValueError):
            kept.append(item)
            continue
        if score < min_confidence:
            warnings.append(
                f"Item at index {i} filtered: FinBERT confidence {score:.3f} < {min_confidence}."
            )
        else:
            kept.append(item)
    return kept, warnings


def schema_hard_stop(output: dict, required_keys: list) -> bool:
    """Return False if any required key is missing or None in output."""
    if not isinstance(output, dict):
        return False
    for key in required_keys:
        if key not in output or output[key] is None:
            return False
    return True
