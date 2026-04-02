"""
Evaluation metrics for the G5-AAFS credit risk assessment pipeline.

Provides dataclasses for tracking evaluation metrics, decorators for
latency measurement, and cost estimation utilities.
"""

from dataclasses import dataclass, field
from datetime import datetime
import time
import functools
from typing import Callable, Any


# Pricing per 1M tokens (USD) as of 2024
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
}


@dataclass
class EvalMetrics:
    """Container for all evaluation metrics produced by the scoring pipeline.

    Attributes:
        precision: Fraction of extracted risk signals that match expected signals.
        recall: Fraction of expected risk signals that were successfully extracted.
        entity_attribution: Rate at which pipeline correctly attributes data to
            the intended company entity (0.0 - 1.0).
        schema_conformance: Rate at which pipeline outputs conform to the
            expected JSON schema (0.0 - 1.0).
        avg_latency_seconds: Mean wall-clock time per pipeline invocation.
        total_tokens_used: Sum of input and output tokens across all invocations.
        estimated_cost_usd: Estimated API cost based on token usage and model pricing.
        score_accuracy: Fraction of companies whose risk score fell within the
            expected_risk_range from ground truth.
        bias_pass_rate: Fraction of bias/fairness test cases that passed.
        confidence_calibration: Measures how well predicted confidence aligns
            with actual accuracy (lower is better, 0.0 = perfectly calibrated).
        timestamp: ISO-8601 timestamp when metrics were computed.
    """

    precision: float = 0.0
    recall: float = 0.0
    entity_attribution: float = 0.0
    schema_conformance: float = 0.0
    avg_latency_seconds: float = 0.0
    total_tokens_used: int = 0
    estimated_cost_usd: float = 0.0
    score_accuracy: float = 0.0
    bias_pass_rate: float = 0.0
    confidence_calibration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert metrics to a plain dictionary for serialization.

        Returns:
            Dictionary with all metric fields and their current values.
        """
        return {
            "precision": self.precision,
            "recall": self.recall,
            "entity_attribution": self.entity_attribution,
            "schema_conformance": self.schema_conformance,
            "avg_latency_seconds": self.avg_latency_seconds,
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost_usd": self.estimated_cost_usd,
            "score_accuracy": self.score_accuracy,
            "bias_pass_rate": self.bias_pass_rate,
            "confidence_calibration": self.confidence_calibration,
            "timestamp": self.timestamp,
        }


def track_latency(func: Callable) -> Callable:
    """Decorator that measures function execution time.

    Wraps a function to record its wall-clock execution time. The elapsed
    time in seconds is stored in the ``_last_latency`` attribute of the
    wrapper function after each call.

    Args:
        func: The function to measure.

    Returns:
        Wrapped function with latency tracking.

    Example:
        >>> @track_latency
        ... def slow_function():
        ...     time.sleep(0.1)
        ...     return "done"
        >>> result = slow_function()
        >>> assert slow_function._last_latency >= 0.1
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start
            wrapper._last_latency = elapsed

    wrapper._last_latency = 0.0
    return wrapper


def estimate_cost(tokens: int, model: str = "gpt-4o-mini") -> float:
    """Estimate API cost in USD for a given token count and model.

    Assumes a 60/40 split between input and output tokens, which is a
    reasonable approximation for credit risk analysis workloads where
    prompts (including financial data) tend to be longer than responses.

    Args:
        tokens: Total number of tokens (input + output combined).
        model: Model identifier. Must be a key in MODEL_PRICING.

    Returns:
        Estimated cost in USD.

    Raises:
        ValueError: If the model is not found in the pricing table.

    Example:
        >>> cost = estimate_cost(1_000_000, model="gpt-4o-mini")
        >>> assert abs(cost - 0.33) < 0.01  # 600K * 0.15/1M + 400K * 0.60/1M
    """
    if model not in MODEL_PRICING:
        raise ValueError(
            f"Unknown model '{model}'. Available models: {list(MODEL_PRICING.keys())}"
        )

    pricing = MODEL_PRICING[model]
    input_tokens = int(tokens * 0.6)
    output_tokens = int(tokens * 0.4)

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return round(input_cost + output_cost, 6)
