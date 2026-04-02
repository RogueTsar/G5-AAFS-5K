"""
Scoring module for the G5-AAFS credit risk evaluation framework.

Compares actual pipeline output against ground truth data from
synthetic_companies.json, computing precision, recall, score accuracy,
and other quality metrics.
"""

import difflib
from typing import Optional


# Threshold for fuzzy string matching of risk signals
FUZZY_MATCH_THRESHOLD = 0.65


def score_against_ground_truth(actual: dict, expected: dict) -> dict:
    """Compare actual pipeline output against ground truth.

    Evaluates three dimensions:
    1. Whether the numeric risk score falls within the expected range.
    2. Whether the categorical risk rating matches.
    3. How well the extracted signals overlap with expected signals.

    Args:
        actual: Pipeline output dictionary. Expected keys:
            - ``risk_score`` (int | float): Numeric risk score (0-100).
            - ``risk_rating`` (str): Categorical rating (e.g., "Low", "High").
            - ``risk_signals`` (list[str]): Extracted risk signal descriptions.
            - ``strength_signals`` (list[str], optional): Extracted strength signals.
        expected: Ground truth dictionary from synthetic_companies.json.
            Expected keys:
            - ``expected_risk_range`` (list[int]): [min, max] acceptable score.
            - ``expected_rating`` (str): Expected risk rating.
            - ``key_risk_signals`` (list[str]): Expected risk signals.
            - ``key_strength_signals`` (list[str]): Expected strength signals.

    Returns:
        Dictionary containing:
            - ``score_in_range`` (bool): Whether risk_score is within expected range.
            - ``rating_match`` (bool): Whether risk_rating matches expected.
            - ``risk_signal_precision`` (float): Precision of risk signal extraction.
            - ``risk_signal_recall`` (float): Recall of risk signal extraction.
            - ``strength_signal_precision`` (float): Precision of strength signal extraction.
            - ``strength_signal_recall`` (float): Recall of strength signal extraction.
            - ``overall_score`` (float): Weighted composite score (0.0 - 1.0).
    """
    result = {}

    # --- Score range check ---
    risk_score = actual.get("risk_score")
    expected_range = expected.get("expected_risk_range", [0, 100])
    if risk_score is not None:
        result["score_in_range"] = expected_range[0] <= risk_score <= expected_range[1]
    else:
        result["score_in_range"] = False

    # --- Rating match ---
    actual_rating = (actual.get("risk_rating") or "").strip().lower()
    expected_rating = (expected.get("expected_rating") or "").strip().lower()
    # Handle compound ratings like "Medium/High" by accepting either component
    expected_parts = [p.strip().lower() for p in expected_rating.split("/")]
    result["rating_match"] = actual_rating in expected_parts or actual_rating == expected_rating

    # --- Risk signal precision/recall ---
    actual_risk_signals = actual.get("risk_signals", [])
    expected_risk_signals = expected.get("key_risk_signals", [])
    risk_prec, risk_rec = compute_precision_recall(actual_risk_signals, expected_risk_signals)
    result["risk_signal_precision"] = risk_prec
    result["risk_signal_recall"] = risk_rec

    # --- Strength signal precision/recall ---
    actual_strength_signals = actual.get("strength_signals", [])
    expected_strength_signals = expected.get("key_strength_signals", [])
    str_prec, str_rec = compute_precision_recall(actual_strength_signals, expected_strength_signals)
    result["strength_signal_precision"] = str_prec
    result["strength_signal_recall"] = str_rec

    # --- Weighted overall score ---
    # Weights: score_in_range (30%), rating_match (20%),
    # risk signal recall (30%), risk signal precision (20%)
    result["overall_score"] = round(
        0.30 * float(result["score_in_range"])
        + 0.20 * float(result["rating_match"])
        + 0.30 * risk_rec
        + 0.20 * risk_prec,
        4,
    )

    return result


def compute_precision_recall(
    extracted_signals: list[str], expected_signals: list[str]
) -> tuple[float, float]:
    """Compute fuzzy-matching precision and recall for signal lists.

    Uses ``difflib.SequenceMatcher`` to perform fuzzy string comparison
    between extracted and expected signals. A match is counted when the
    similarity ratio exceeds ``FUZZY_MATCH_THRESHOLD``.

    Args:
        extracted_signals: Signals produced by the pipeline.
        expected_signals: Ground truth signals from the test dataset.

    Returns:
        Tuple of (precision, recall) where each is a float in [0.0, 1.0].
        Returns (0.0, 0.0) if both lists are empty, (0.0, 1.0) if only
        extracted is empty and expected is empty, etc.
    """
    if not extracted_signals and not expected_signals:
        return (1.0, 1.0)
    if not extracted_signals:
        return (0.0, 0.0)
    if not expected_signals:
        # Nothing was expected, so any extraction is a false positive
        return (0.0, 1.0)

    # Normalize signals for comparison
    extracted_normalized = [s.strip().lower() for s in extracted_signals]
    expected_normalized = [s.strip().lower() for s in expected_signals]

    # Count true positives for recall (expected signals that were found)
    matched_expected = set()
    matched_extracted = set()

    for i, exp_signal in enumerate(expected_normalized):
        best_ratio = 0.0
        best_j = -1
        for j, ext_signal in enumerate(extracted_normalized):
            if j in matched_extracted:
                continue
            ratio = difflib.SequenceMatcher(None, exp_signal, ext_signal).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_j = j
        if best_ratio >= FUZZY_MATCH_THRESHOLD and best_j >= 0:
            matched_expected.add(i)
            matched_extracted.add(best_j)

    recall = len(matched_expected) / len(expected_normalized)
    precision = len(matched_extracted) / len(extracted_normalized)

    return (round(precision, 4), round(recall, 4))


def compute_score_accuracy(results: list[dict]) -> float:
    """Compute the fraction of companies whose score fell within expected range.

    Args:
        results: List of per-company result dictionaries, each containing
            at minimum a ``score_in_range`` boolean key (as produced by
            ``score_against_ground_truth``).

    Returns:
        Accuracy as a float in [0.0, 1.0]. Returns 0.0 if results is empty.
    """
    if not results:
        return 0.0

    in_range_count = sum(1 for r in results if r.get("score_in_range", False))
    return round(in_range_count / len(results), 4)


def compute_rating_accuracy(results: list[dict]) -> float:
    """Compute the fraction of companies whose rating matched expected.

    Args:
        results: List of per-company result dictionaries, each containing
            at minimum a ``rating_match`` boolean key.

    Returns:
        Accuracy as a float in [0.0, 1.0]. Returns 0.0 if results is empty.
    """
    if not results:
        return 0.0

    match_count = sum(1 for r in results if r.get("rating_match", False))
    return round(match_count / len(results), 4)


def compute_aggregate_metrics(results: list[dict]) -> dict:
    """Compute aggregate evaluation metrics across all scored companies.

    Args:
        results: List of per-company scoring dictionaries as produced by
            ``score_against_ground_truth``.

    Returns:
        Dictionary with aggregate metrics:
            - ``score_accuracy``: Fraction with score in expected range.
            - ``rating_accuracy``: Fraction with correct rating.
            - ``avg_risk_signal_precision``: Mean risk signal precision.
            - ``avg_risk_signal_recall``: Mean risk signal recall.
            - ``avg_overall_score``: Mean weighted overall score.
            - ``total_evaluated``: Number of companies evaluated.
    """
    if not results:
        return {
            "score_accuracy": 0.0,
            "rating_accuracy": 0.0,
            "avg_risk_signal_precision": 0.0,
            "avg_risk_signal_recall": 0.0,
            "avg_overall_score": 0.0,
            "total_evaluated": 0,
        }

    n = len(results)
    return {
        "score_accuracy": compute_score_accuracy(results),
        "rating_accuracy": compute_rating_accuracy(results),
        "avg_risk_signal_precision": round(
            sum(r.get("risk_signal_precision", 0.0) for r in results) / n, 4
        ),
        "avg_risk_signal_recall": round(
            sum(r.get("risk_signal_recall", 0.0) for r in results) / n, 4
        ),
        "avg_overall_score": round(
            sum(r.get("overall_score", 0.0) for r in results) / n, 4
        ),
        "total_evaluated": n,
    }
