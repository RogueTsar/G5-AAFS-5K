"""Shared pytest fixtures for G5-AAFS evaluation and guardrail tests."""

import json
import os
from pathlib import Path
from typing import Dict, Any

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────

TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
DATASETS_DIR = TESTS_DIR / "datasets"


# ── Dataset fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def synthetic_companies() -> list:
    """Load the 30-company synthetic test suite."""
    path = DATASETS_DIR / "synthetic_companies.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def distress_events() -> list:
    """Load the 10 distress-event backtest cases."""
    path = DATASETS_DIR / "distress_events.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def prompt_injection_payloads() -> list:
    """Load the 15 prompt injection test payloads."""
    path = DATASETS_DIR / "prompt_injection_payloads.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def entity_spoofing_cases() -> list:
    """Load the 10 entity spoofing/disambiguation cases."""
    path = DATASETS_DIR / "entity_spoofing_cases.json"
    with open(path) as f:
        return json.load(f)


# ── Mock fixture loader ─────────────────────────────────────────────────────

def _load_mock(company_key: str) -> Dict[str, Any]:
    """Load a pre-cached mock API response for a company."""
    path = FIXTURES_DIR / f"mock_{company_key}.json"
    if not path.exists():
        pytest.skip(f"Mock fixture not found: {path}")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def mock_apple():
    return _load_mock("apple_inc")


@pytest.fixture(scope="session")
def mock_svb():
    return _load_mock("svb")


@pytest.fixture(scope="session")
def mock_tesla():
    return _load_mock("tesla")


@pytest.fixture(scope="session")
def mock_evergrande():
    return _load_mock("evergrande")


@pytest.fixture(scope="session")
def mock_microsoft():
    return _load_mock("microsoft")


@pytest.fixture(scope="session")
def mock_credit_suisse():
    return _load_mock("credit_suisse")


@pytest.fixture(scope="session")
def mock_grab():
    return _load_mock("grab_holdings")


@pytest.fixture(scope="session")
def mock_wirecard():
    return _load_mock("wirecard")


@pytest.fixture(scope="session")
def mock_dbs():
    return _load_mock("dbs_bank")


@pytest.fixture(scope="session")
def mock_ftx():
    return _load_mock("ftx")


# ── Helper: build a minimal AgentState from mock data ────────────────────────

@pytest.fixture
def make_state():
    """Factory fixture to create an AgentState-like dict from mock data."""
    def _make(mock_data: Dict[str, Any], **overrides) -> Dict[str, Any]:
        state = {
            "company_name": mock_data.get("company_name", "Test Company"),
            "company_info": {},
            "search_queries": {},
            "company_aliases": [],
            "uploaded_docs": [],
            "doc_extracted_text": mock_data.get("doc_extracted_text", []),
            "news_data": mock_data.get("news_data", []),
            "social_data": mock_data.get("social_data", []),
            "review_data": mock_data.get("review_data", []),
            "financial_data": mock_data.get("financial_data", []),
            "cleaned_data": (
                mock_data.get("news_data", [])
                + mock_data.get("social_data", [])
                + mock_data.get("review_data", [])
                + mock_data.get("financial_data", [])
            ),
            "resolved_entities": {},
            "extracted_risks": [],
            "extracted_strengths": [],
            "risk_score": {},
            "explanations": [],
            "final_report": "",
            "errors": [],
            # GuardedAgentState fields
            "industry_context": {},
            "press_release_analysis": {},
            "audit_trail": {},
            "guardrail_warnings": [],
        }
        state.update(overrides)
        return state
    return _make


# ── Guardrail runner fixture ─────────────────────────────────────────────────

@pytest.fixture
def guardrail_runner():
    """Create a fresh GuardrailRunner instance."""
    from src.guardrails.guardrail_runner import GuardrailRunner
    return GuardrailRunner()
