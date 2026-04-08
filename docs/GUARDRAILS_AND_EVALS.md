# G5-AAFS: Guardrails Framework & Evaluation Suite

> **Roles**: R8 (Guardrails Engineer) + R9 (Evaluation Lead)
> **Author**: Vaishnavi Singh | IS4000 — Application of AI in Financial Services
> **Project**: AI-Augmented Credit Risk Assessment for UBS Bank

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Guardrail Reference (Role 8)](#guardrail-reference-role-8)
3. [New Agents](#new-agents)
4. [Guarded Orchestrator](#guarded-orchestrator)
5. [Evaluation Framework (Role 9)](#evaluation-framework-role-9)
6. [Regulatory Compliance](#regulatory-compliance)
7. [Running Tests](#running-tests)
8. [Token Budget Analysis](#token-budget-analysis)
9. [Integration Guide](#integration-guide)
10. [Research Foundations](#research-foundations)

---

## Architecture Overview

### Current Pipeline (13 agents)
```
┌─────────────────────────────────────────────────────────────────────┐
│                    CURRENT G5-AAFS PIPELINE                        │
│                                                                     │
│  ┌───────────┐    ┌───────────┐                                    │
│  │   INPUT    │───▶│ DISCOVERY │                                    │
│  │   AGENT    │    │   AGENT   │                                    │
│  └─────┬─────┘    └─────┬─────┘                                    │
│        │                │                                           │
│        ▼                ▼ Fan-Out                                   │
│  ┌──────────┐   ┌──────┴───────────────────────────┐              │
│  │ DOCUMENT │   │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │PROCESSOR │   │  │ NEWS │ │SOCIAL│ │REVIEW│ │ FIN  │          │
│  └─────┬────┘   │  │AGENT │ │AGENT │ │AGENT │ │AGENT │          │
│        │        │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘          │
│        │        └─────┼────────┼────────┼────────┼───┘           │
│        └──────────────┴────────┴────────┴────────┘                │
│                              │ Fan-In                              │
│                              ▼                                     │
│                    ┌─────────────────┐                             │
│                    │  DATA CLEANING  │  (FinBERT enrichment)      │
│                    └────────┬────────┘                             │
│                             ▼                                      │
│                    ┌─────────────────┐                             │
│                    │ENTITY RESOLUTION│                             │
│                    └────────┬────────┘                             │
│                             ▼                                      │
│                    ┌─────────────────┐                             │
│                    │ RISK EXTRACTION │                             │
│                    └────────┬────────┘                             │
│                             ▼                                      │
│                    ┌─────────────────┐                             │
│                    │  RISK SCORING   │                             │
│                    └────────┬────────┘                             │
│                             ▼                                      │
│                    ┌─────────────────┐                             │
│                    │ EXPLAINABILITY  │                             │
│                    └────────┬────────┘                             │
│                             ▼                                      │
│                    ┌─────────────────┐                             │
│                    │    REVIEWER     │                             │
│                    └─────────────────┘                             │
│                                                                     │
│  ⚠  NO GUARDRAILS  │  NO SOURCE WEIGHTING  │  NO CONFIDENCE       │
│  ⚠  NO AUDIT TRAIL │  NO INDUSTRY CONTEXT  │  NO BIAS CHECKS      │
└─────────────────────────────────────────────────────────────────────┘
```

### Enhanced Pipeline (13 existing + 5 new agents + guardrail layer)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│                   ENHANCED G5-AAFS PIPELINE (Guarded)                       │
│                                                                              │
│  ╔══════════════════════════════════════════════════════════════════════╗    │
│  ║                    GUARDRAIL LAYER (0 LLM tokens)                   ║    │
│  ║  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ║    │
│  ║  │  Input   │ │  Output  │ │Hallucin. │ │  Bias/   │ │Cascade  │ ║    │
│  ║  │Validator │ │ Enforcer │ │ Detector │ │Fairness  │ │ Guard   │ ║    │
│  ║  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘ ║    │
│  ║                    ┌──────────────┐                                ║    │
│  ║                    │Content Safety│                                ║    │
│  ║                    └──────────────┘                                ║    │
│  ╚══════════════════════════════════════════════════════════════════════╝    │
│                                                                              │
│  ┌────────────┐    ┌────────────┐                                           │
│  │   GUARDED  │───▶│  DISCOVERY │                                           │
│  │INPUT AGENT │    │   AGENT    │                                           │
│  └─────┬──────┘    └─────┬──────┘                                           │
│        │                 │                                                   │
│        ▼                 ▼ Fan-Out (5 parallel agents)                       │
│  ┌──────────┐   ┌───────┴──────────────────────────────────────┐           │
│  │ DOCUMENT │   │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐│           │
│  │PROCESSOR │   │ │ NEWS │ │SOCIAL│ │REVIEW│ │ FIN  │ │PRESS││           │
│  └─────┬────┘   │ │AGENT │ │AGENT │ │AGENT │ │AGENT │ │REL. ││           │
│        │        │ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬──┘│           │
│        │        └────┼────────┼────────┼────────┼─────────┼───┘           │
│        └─────────────┴────────┴────────┴────────┴─────────┘               │
│                              │ Fan-In                                       │
│                              ▼                                              │
│              ┌───────────────────────────────────────┐                     │
│              │         DATA CLEANING + FinBERT        │                     │
│              └───────────────┬───────────────────────┘                     │
│                              │                                              │
│            ┌─────────────────┼─────────────────┐                           │
│            ▼                 ▼                  ▼                           │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────┐                   │
│  │   SOURCE     │  │   INDUSTRY     │  │   ENTITY     │                   │
│  │ CREDIBILITY  │  │   CONTEXT      │  │ RESOLUTION   │                   │
│  │  (0 LLM)    │  │  (0 LLM)       │  │              │                   │
│  └──────┬───────┘  └────────┬───────┘  └──────┬───────┘                   │
│         └──────────────────┬┘                  │                           │
│                            ▼                   ▼                           │
│              ┌─────────────────────────────────┐                           │
│              │      GUARDED RISK EXTRACTION     │                          │
│              │   (output enforcer validates)    │                          │
│              └──────────────┬──────────────────┘                           │
│                             ▼                                              │
│              ┌─────────────────────────────────┐                           │
│              │       GUARDED RISK SCORING       │                          │
│              │   (score clamping + validation)  │                          │
│              └──────────────┬──────────────────┘                           │
│                             ▼                                              │
│              ┌─────────────────────────────────┐                           │
│              │    CONFIDENCE CALIBRATION (0 LLM)│                          │
│              │  data_coverage + entropy +        │                          │
│              │  sentiment_agreement + tier_ratio  │                          │
│              └──────────────┬──────────────────┘                           │
│                             ▼                                              │
│              ┌─────────────────────────────────┐                           │
│              │     GUARDED EXPLAINABILITY       │                          │
│              └──────────────┬──────────────────┘                           │
│                             ▼                                              │
│              ┌─────────────────────────────────┐                           │
│              │        GUARDED REVIEWER          │                          │
│              │  (hallucination + bias + content) │                          │
│              └──────────────┬──────────────────┘                           │
│                             ▼                                              │
│              ┌─────────────────────────────────┐                           │
│              │     AUDIT TRAIL AGENT (0 LLM)    │                          │
│              │   MAS FEAT + EU AI Act compliant  │                          │
│              │   Full decision lineage tracking   │                          │
│              └─────────────────────────────────┘                           │
│                                                                             │
│  KEY: All guardrails use 0 LLM tokens (pure regex/string/dict operations)  │
│       3 new agents use 0 LLM tokens | Press release uses 1 LLM call       │
│       Existing 13 agents are UNCHANGED - wrapped, not modified             │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Guardrail Reference (Role 8)

All guardrail modules use **deterministic regex/rule checks** as their base layer (zero LLM cost). An optional **LLM deep check** layer adds semantic hallucination verification and nuanced compliance evaluation when `llm_deep_checks` is enabled (default: ON).

### Module Summary

| Module | File | Key Functions | What It Checks |
|--------|------|---------------|----------------|
| **Input Guardrails** | `src/guardrails/input_guardrails.py` | `run_rule_checks()`, `sanitize_query()` | Prompt injection, code injection, entity classification |
| **Output Enforcer** | `src/guardrails/output_enforcer.py` | `enforce_risk_extraction()`, `enforce_risk_score()` | Schema conformance, score clamping, rating consistency |
| **Hallucination Detector** | `src/guardrails/hallucination_detector.py` | `check_entity_attribution()`, `flag_fabricated_metrics()` | Source grounding, company name verification, metric fabrication |
| **Bias & Fairness** | `src/guardrails/bias_fairness.py` | `detect_proxy_variables()`, `check_mas_feat_compliance()` | Protected class terms, MAS FEAT, EU AI Act compliance |
| **Cascade Guard** | `src/guardrails/cascade_guard.py` | `validate_agent_output()`, `should_abort_pipeline()` | Inter-agent error propagation, safe fallbacks |
| **Content Safety** | `src/guardrails/content_safety.py` | `filter_report_content()`, `add_regulatory_footer()` | Definitive credit language, score-language consistency |
| **Guardrail Runner** | `src/guardrails/guardrail_runner.py` | `GuardrailRunner` class | Unified orchestration with audit trail |

### Output Enforcer Details

```
enforce_risk_extraction(output) → (cleaned, warnings)
  ├── risk.type ∈ {"Traditional Risk", "Non-traditional Risk"}
  ├── strength.type ∈ {"Financial Strength", "Market Strength"}
  ├── descriptions non-empty, max 500 chars
  └── invalid entries removed with warnings

enforce_risk_score(output) → (cleaned, warnings)
  ├── score: int, clamped to 0-100
  ├── rating ∈ {"Low", "Medium", "High"}
  └── rating-score consistency: Low=0-33, Medium=34-66, High=67-100

confidence_floor_filter(items, min=0.3) → (kept, warnings)
  └── filters FinBERT items below confidence threshold

schema_hard_stop(output, required_keys) → bool
  └── returns False if any required key missing → abort trigger
```

### Hallucination Detector Details

```
check_entity_attribution(company, risks, strengths, sources) → dict
  ├── difflib.SequenceMatcher fuzzy match (threshold=0.4)
  ├── returns grounded/ungrounded lists
  └── attribution_score: 0.0 (all fabricated) to 1.0 (all grounded)

verify_company_in_output(company, report, aliases) → (found, warnings)
  └── case-insensitive search for company name/aliases in report

flag_fabricated_metrics(report, financial_data) → list[str]
  ├── regex extracts $amounts, percentages, numbers from report
  └── cross-checks against known values in financial_data
```

### Bias & Fairness Details

```
detect_proxy_variables(text) → list[{term, category, severity}]
  ├── ~50 protected class terms organized by category
  ├── categories: demographics (high), geographic_proxy (medium), personal (low)
  └── word-boundary regex matching to avoid false positives

check_mas_feat_compliance(report) → {fairness, ethics, accountability, transparency}
  ├── Fairness: no high-severity protected class terms
  ├── Ethics: data provenance cited
  ├── Accountability: human oversight note present
  └── Transparency: methodology stated

check_eu_ai_act_compliance(report) → {human_oversight, data_provenance, ...}
  └── Checks Article 14 requirements for high-risk AI systems
```

---

## New Agents

### Source Credibility Agent (LLM + rule-based fallback)

**File**: `src/agents/source_credibility_agent.py`

Assigns credibility weights to each data item based on source type and URL domain:

| Tier | Sources | Weight |
|------|---------|--------|
| Tier 1 — Institutional | yfinance, SEC, MAS filings, annual reports | 0.90-0.95 |
| Tier 2 — Reputable Media | Reuters, Bloomberg, FT, WSJ, NewsAPI | 0.80-0.85 |
| Tier 3 — Contextual | Glassdoor, LinkedIn, reviews | 0.50-0.60 |
| Tier 4 — Low Signal | Reddit, Twitter/X, social media | 0.35-0.40 |

### Confidence Calibration Agent (LLM + quantitative metrics)

**File**: `src/agents/confidence_agent.py`

Computes confidence intervals for risk scores using 4 dimensions:

| Dimension | Weight | How Computed |
|-----------|--------|--------------|
| Data Coverage | 30% | % of 5 source types with data |
| Source Diversity | 20% | Shannon entropy of source types |
| Sentiment Agreement | 30% | % of FinBERT labels agreeing with majority |
| High-Tier Ratio | 20% | % of data from Tier 1-2 sources |

Output: `confidence_level` ∈ {"High" (≥0.7), "Medium" (0.4-0.7), "Low" (<0.4)}

**Why this matters**: "72/100 risk, Low confidence" ≠ "72/100 risk, High confidence"

### Audit Trail Agent (LLM compliance quality assessment)

**File**: `src/agents/audit_agent.py`

Produces structured JSON audit trail for regulatory compliance:
- Run ID, timestamp, company assessed
- Which agents executed and which had errors
- Data source counts and tier distribution
- MAS FEAT and EU AI Act compliance status

### Industry Context Agent (LLM + keyword fallback)

**File**: `src/agents/industry_context_agent.py`

Keyword-based industry inference + outlook scoring:
- 10 industry categories with keyword lists
- Weighted positive/negative outlook drivers
- Falls back to Tavily search if insufficient state data

### Press Release Agent (1 LLM call, <500 tokens)

**File**: `src/agents/press_release_agent.py`

Directed newsroom scraping with corporate event framework:
- 5 targeted Tavily queries per company
- Regex-based event categorization (0 LLM): M&A, workforce, financial health, market position, leadership, risk events
- 1 structured LLM call for `CorporateTrajectory` synthesis

---

## Guarded Orchestrator

**File**: `src/core/orchestrator_guarded.py`

Wraps the existing 13-agent pipeline without modifying any original files:

```python
from src.core.orchestrator_guarded import create_guarded_workflow

# Drop-in replacement for create_workflow()
app = create_guarded_workflow()
result = app.invoke({"company_name": "Apple Inc"})
```

**Integration**: Team changes ONE import in their entry point:
```python
# Before:
from src.core.orchestrator import create_workflow
# After:
from src.core.orchestrator_guarded import create_guarded_workflow as create_workflow
```

---

## Evaluation Framework (Role 9)

### Test Datasets

| Dataset | File | Count | Purpose |
|---------|------|-------|---------|
| Synthetic Companies | `tests/datasets/synthetic_companies.json` | 30 | Full pipeline evaluation |
| Distress Events | `tests/datasets/distress_events.json` | 10 | Temporal backtesting |
| Prompt Injection | `tests/datasets/prompt_injection_payloads.json` | 15 | Input safety |
| Entity Spoofing | `tests/datasets/entity_spoofing_cases.json` | 10 | Disambiguation |

### Synthetic Companies Breakdown

| Category | Count | Examples |
|----------|-------|---------|
| Known defaults | 8 | SVB, Evergrande, FTX, Wirecard, Lehman |
| Distressed/recovered | 5 | GameStop, Boeing 737MAX, Credit Suisse |
| Healthy large-caps | 7 | Apple, Microsoft, J&J, Visa |
| Healthy mid-caps | 5 | Costco, Adobe, ServiceNow |
| Ambiguous/mixed | 5 | Tesla, Meta (2022), Uber |

### Mock Fixtures

10 pre-cached API response files in `tests/fixtures/` for offline testing:
Apple, SVB, Tesla, Evergrande, Microsoft, Credit Suisse, Grab, Wirecard, DBS, FTX.

### Metrics

```python
@dataclass
class EvalMetrics:
    precision: float          # % extracted risks grounded in sources
    recall: float             # % expected signals detected
    entity_attribution: float # hallucination attribution score
    schema_conformance: float # % outputs passing schema validation
    avg_latency_seconds: float
    total_tokens_used: int
    estimated_cost_usd: float
    score_accuracy: float     # % companies in expected range
    bias_pass_rate: float     # % outputs with 0 protected terms
    confidence_calibration: float
```

### Safety Eval Methodology

Adapted from [allenai/safety-eval](https://github.com/allenai/safety-eval):

| Benchmark | Our Adaptation | Test Count |
|-----------|---------------|------------|
| HarmBench | Prompt injection payloads | 15 |
| BBQ | Bias/proxy variable detection | 50+ terms |
| XSTest | Behavioral refusal tests | 5 |
| WildGuard | Content safety classification | 10+ rules |

---

## Regulatory Compliance

### MAS FEAT Principles

| Principle | How Addressed |
|-----------|---------------|
| **Fairness** | `bias_fairness.py`: detects ~50 protected class proxy terms with word-boundary regex |
| **Ethics** | `audit_agent.py`: full data provenance tracking; `content_safety.py`: regulatory disclaimers |
| **Accountability** | `audit_agent.py`: structured audit trail with run_id, agents executed, errors, compliance checks |
| **Transparency** | `confidence_agent.py`: confidence scores with breakdown; `explainability_agent`: metric-level explanations |

### EU AI Act (High-Risk AI)

| Requirement | How Addressed |
|-------------|---------------|
| Human oversight (Art. 14) | Regulatory footer: "reviewed by qualified credit analyst" |
| Data governance (Art. 10) | Source credibility tiering + audit trail of data sources |
| Transparency (Art. 13) | AI-generated disclaimer + methodology statement check |
| Bias monitoring (Art. 10) | Protected class term detection + removal |

---

## Running Tests

### Prerequisites
```bash
pip install -r requirements-dev.txt
```

### Quick: Guardrail Unit Tests (0 API calls, ~5 seconds)
```bash
pytest tests/test_guardrails/ -v
```

### Full: All Tests with Mocks (0 API calls, ~15 seconds)
```bash
pytest tests/test_guardrails/ tests/test_evals/ -v
```

### Using the Eval Runner CLI
```bash
# All tests, mock mode
python -m tests.eval_runner --mode mock --suite all

# Just safety evals
python -m tests.eval_runner --mode mock --suite safety

# Just behavioral evals
python -m tests.eval_runner --mode mock --suite behavioral

# Output to specific directory
python -m tests.eval_runner --mode mock --suite all --output eval/results/
```

### Live Smoke Test (~$0.01)
```bash
pytest tests/test_evals/test_synthetic_suite.py -v --live -k "Apple"
```

---

## Token Budget Analysis

| Component | LLM Calls | Estimated Cost |
|-----------|-----------|----------------|
| 6 guardrail modules (deterministic) | 0 | $0.00 |
| Guardrail LLM deep checks (optional) | ~2 | ~$0.003 |
| Source credibility agent | 1 (+ rule fallback) | ~$0.001 |
| Confidence agent | 1 (+ quantitative) | ~$0.001 |
| Audit agent | 1 | ~$0.001 |
| Industry context agent | 1 (+ keyword fallback) | ~$0.001 |
| Press release agent | 1 per run | ~$0.001 |
| Explainer agent | 2 (audit + devil's advocate) | ~$0.002 |
| Guardrail unit tests | 0 | $0.00 |
| Moonshot red-team tests | 0 | $0.00 |
| LLM-as-Judge eval suite | ~10 | ~$0.01 |
| Full eval suite (mock) | 0 | $0.00 |
| Full eval suite (live, 30 companies) | ~120 | ~$0.05 |
| **Total guardrail overhead per run** | **~2** | **~$0.003** |

---

## Integration Guide

### Step 1: Install dependencies
```bash
pip install -r requirements-dev.txt
```

### Step 2: Run tests to verify
```bash
pytest tests/test_guardrails/ -v
```

### Step 3: Activate guarded orchestrator

Change one import in your entry point (e.g., `main.py` or `frontend/ui.py`):

```python
# Replace:
from src.core.orchestrator import create_workflow
# With:
from src.core.orchestrator_guarded import create_guarded_workflow as create_workflow
```

That's it. All existing agents continue working unchanged. Guardrails wrap them automatically.

### Step 4: Verify integration
```bash
python -m tests.eval_runner --mode mock --suite all
```

---

## Research Foundations

| Source | How Used |
|--------|----------|
| [MASCA: LLM Multi-Agent Credit Assessment](https://arxiv.org/abs/2507.22758) | Architecture inspiration: multi-tier agents, contrastive risk-reward teams |
| [CreditXAI: Explainable Credit Rating](https://arxiv.org/pdf/2510.22222) | Explainability patterns for credit scoring |
| [MAS FEAT Principles](https://www.mas.gov.sg/publications/monographs-or-information-paper/2018/feat) | Fairness, Ethics, Accountability, Transparency compliance framework |
| [MAS AI Risk Management 2025](https://www.mas.gov.sg/news/media-releases/2025/mas-guidelines-for-artificial-intelligence-risk-management) | AI lifecycle controls and audit requirements |
| [Deloitte: Agentic AI in Banking](https://www.deloitte.com/us/en/insights/industry/financial-services/agentic-ai-banking.html) | Source reliability tiering, agent registry patterns |
| [AWS: Multi-Agent Patterns for FinServ](https://aws.amazon.com/blogs/industries/agentic-ai-in-financial-services-choosing-the-right-pattern-for-multi-agent-systems/) | Fan-out/fan-in patterns, guardrail placement |
| [allenai/safety-eval](https://github.com/allenai/safety-eval) | Safety evaluation methodology (HarmBench, BBQ, XSTest, WildGuard) |
| [ML Credit Scoring Review](https://link.springer.com/article/10.1007/s10462-025-11416-2) | Confidence calibration, Gini coefficient analysis |
| [AI Rewrites Lending](https://www.pymnts.com/consumer-finance/2026/ai-rewrites-lending-for-borrowers-fico-scores-miss/) | FICO limitations, AI alternative data advantages |
| [UBS Innovation & AI](https://www.ubs.com/global/en/our-firm/what-we-do/technology/innovation-and-ai.html) | UBS Eliza platform, AI adoption context |

---

## File Inventory

### New Files Added (no existing files modified)

```
src/guardrails/
  __init__.py                          # Module exports
  output_enforcer.py                   # Schema enforcement + confidence floors
  hallucination_detector.py            # Entity attribution + factual grounding
  bias_fairness.py                     # Protected class detection + compliance
  cascade_guard.py                     # Error propagation prevention
  content_safety.py                    # Credit language filtering
  guardrail_runner.py                  # Unified guardrail orchestrator

src/agents/
  source_credibility_agent.py          # 4-tier source weighting (0 LLM)
  confidence_agent.py                  # Confidence intervals (0 LLM)
  audit_agent.py                       # Compliance audit trail (0 LLM)
  industry_context_agent.py            # Industry inference (0 LLM)
  press_release_agent.py               # Corporate event analysis (1 LLM)

src/core/
  orchestrator_guarded.py              # Wraps existing pipeline + guardrails

tests/
  conftest.py                          # Shared pytest fixtures
  eval_runner.py                       # CLI evaluation pipeline
  datasets/
    synthetic_companies.json           # 30 test companies
    distress_events.json               # 10 historical defaults
    prompt_injection_payloads.json     # 15 adversarial inputs
    entity_spoofing_cases.json         # 10 disambiguation tests
  fixtures/
    mock_*.json                        # 10 pre-cached API responses
  test_guardrails/
    test_output_enforcer.py
    test_hallucination_detector.py
    test_bias_fairness.py
    test_cascade_guard.py
    test_content_safety.py
  test_evals/
    test_synthetic_suite.py
    test_distress_backtest.py
    test_behavioral.py
    test_safety_evals.py
    test_moonshot.py                   # Project Moonshot red-team (25 tests, 0 LLM)
    test_llm_judge.py                  # LLM-as-Judge semantic eval (~10 tests)

eval/
  __init__.py
  metrics.py                           # EvalMetrics dataclass
  scorer.py                            # Ground truth comparison
  report_generator.py                  # Markdown/JSON reports

docs/
  GUARDRAILS_AND_EVALS.md             # This file

requirements-dev.txt                   # Testing dependencies
```
