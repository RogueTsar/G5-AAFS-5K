import sys
import os
from typing import Dict, Any

# Mock the environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.analysis_agents import evaluate_financial_metrics

def test_null_metrics():
    print("Testing evaluate_financial_metrics with null values...")
    
    # Case 1: All None
    metrics_all_none = {
        "debtToEquity": None,
        "currentRatio": None,
        "revenueGrowth": None,
        "profitMargins": None
    }
    result = evaluate_financial_metrics(metrics_all_none)
    print(f"  All None: {result} (Expected: neutral)")
    assert result == "neutral"

    # Case 2: Partial None (Liquidity Risk)
    metrics_liquidity_risk = {
        "debtToEquity": 50,
        "currentRatio": 0.5, # Risk
        "revenueGrowth": None,
        "profitMargins": 0.1
    }
    result = evaluate_financial_metrics(metrics_liquidity_risk)
    print(f"  Liquidity Risk: {result} (Expected: negative)")
    assert result == "negative"

    # Case 3: High Leverage (None current ratio)
    metrics_debt_risk = {
        "debtToEquity": 150, # Risk
        "currentRatio": None,
        "revenueGrowth": 0.1,
        "profitMargins": 0.1
    }
    result = evaluate_financial_metrics(metrics_debt_risk)
    print(f"  Debt Risk: {result} (Expected: negative)")
    assert result == "negative"

    print("\nSUCCESS: All null-safe checks passed!")

if __name__ == "__main__":
    try:
        test_null_metrics()
    except Exception as e:
        print(f"\nFAILED: {str(e)}")
        sys.exit(1)
