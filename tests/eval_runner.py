"""CLI evaluation runner for G5-AAFS credit risk pipeline.

Usage:
    python -m tests.eval_runner --mode mock --suite all
    python -m tests.eval_runner --mode mock --suite guardrails
    python -m tests.eval_runner --mode mock --suite synthetic
    python -m tests.eval_runner --mode mock --suite safety
    python -m tests.eval_runner --mode mock --suite behavioral
    python -m tests.eval_runner --output eval/results/
"""

import argparse
import json
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Resolve project root
PROJECT_ROOT = Path(__file__).parent.parent
EVAL_RESULTS_DIR = PROJECT_ROOT / "eval" / "results"


SUITE_MAP = {
    "all": [
        "tests/test_guardrails/",
        "tests/test_evals/",
    ],
    "guardrails": [
        "tests/test_guardrails/",
    ],
    "synthetic": [
        "tests/test_evals/test_synthetic_suite.py",
    ],
    "distress": [
        "tests/test_evals/test_distress_backtest.py",
    ],
    "safety": [
        "tests/test_evals/test_safety_evals.py",
    ],
    "behavioral": [
        "tests/test_evals/test_behavioral.py",
    ],
}


def run_pytest(paths: list, mode: str, verbose: bool = True) -> dict:
    """Run pytest on given paths and return results summary."""
    cmd = [sys.executable, "-m", "pytest"]

    for p in paths:
        cmd.append(str(PROJECT_ROOT / p))

    if verbose:
        cmd.append("-v")

    # In mock mode, exclude tests that require live API
    if mode == "mock":
        cmd.extend(["-k", "not live"])

    # Generate JSON report
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_report = EVAL_RESULTS_DIR / f"pytest_report_{timestamp}.json"
    cmd.extend(["--tb=short", f"--junitxml={json_report}"])

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, capture_output=False, cwd=str(PROJECT_ROOT))

    return {
        "returncode": result.returncode,
        "report_path": str(json_report),
        "passed": result.returncode == 0,
    }


def main():
    parser = argparse.ArgumentParser(
        description="G5-AAFS Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Suites:
  all         Run all guardrail + eval tests
  guardrails  Run guardrail unit tests only
  synthetic   Run synthetic company suite
  distress    Run distress event backtest
  safety      Run AI safety evals (injection, spoofing, cascade)
  behavioral  Run behavioral evals (refusal, scope, sycophancy)
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="Test mode: mock (offline, $0) or live (API calls, ~$0.05)",
    )
    parser.add_argument(
        "--suite",
        choices=list(SUITE_MAP.keys()),
        default="all",
        help="Test suite to run",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(EVAL_RESULTS_DIR),
        help="Output directory for results",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = SUITE_MAP.get(args.suite, SUITE_MAP["all"])

    print(f"G5-AAFS Evaluation Runner")
    print(f"Mode: {args.mode}")
    print(f"Suite: {args.suite}")
    print(f"Output: {args.output}")
    print(f"Paths: {paths}")

    result = run_pytest(paths, args.mode, args.verbose)

    # Summary
    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE")
    print(f"Suite: {args.suite}")
    print(f"Mode: {args.mode}")
    print(f"Status: {'PASSED' if result['passed'] else 'FAILED'}")
    print(f"Report: {result['report_path']}")
    print(f"{'='*60}")

    sys.exit(result["returncode"])


if __name__ == "__main__":
    main()
