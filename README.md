# G5-AAFS: AI-Augmented Credit Risk Assessment

> **18-agent LangGraph pipeline** for enterprise credit risk evaluation, built for UBS compliance analysts.
> Zero-token guardrails | ACRA XBRL parsing | Human-in-the-Loop gates | Full regulatory compliance

**257 tests** | **6 safety modules** | **5 scoring frameworks** | **65 synthetic test cases** | **10 mock fixtures**

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Quick Start](#quick-start)
3. [Workflow Modes](#workflow-modes)
4. [Architecture](#architecture)
5. [Agent Inventory](#agent-inventory)
6. [Guardrail Layer](#guardrail-layer)
7. [Tools & External APIs](#tools--external-apis)
8. [Evaluation Framework](#evaluation-framework)
9. [Regulatory Compliance](#regulatory-compliance)
10. [Cost Analysis](#cost-analysis)
11. [Project Structure](#project-structure)
12. [Environment Variables](#environment-variables)
13. [Dataset & Fixture Reference](#dataset--fixture-reference)
14. [Running Tests](#running-tests)
15. [Team](#team)

---

## Problem Statement

### The Challenge

Credit analysts at UBS spend **3-5 hours per company** manually gathering data from financial filings, news sources, social media, and regulatory databases. This process is:

- **Slow**: Multiple data sources must be checked individually
- **Inconsistent**: Different analysts weight factors differently
- **Opaque**: Scoring rationale is often undocumented
- **Unscalable**: Annual reviews for 200+ clients create bottlenecks

### Our Solution

G5-AAFS automates the data collection and structuring phase using **18 specialized AI agents** coordinated via LangGraph, while keeping the analyst **in full control** of every critical decision. The system:

1. **Collects** intelligence from 6+ data sources in parallel (news, social, financial, press releases, XBRL filings, industry reports)
2. **Structures** raw data through cleaning, entity resolution, and FinBERT sentiment analysis
3. **Scores** risk using established credit frameworks (Basel IRB, Altman Z-Score, S&P, Moody's KMV)
4. **Guards** every output with 6 deterministic safety modules that cost zero LLM tokens
5. **Audits** the full decision trail for MAS FEAT, IMDA AI Verify, and EU AI Act compliance

The analyst reviews findings by data domain, adjusts scoring weights, approves or overrides agent decisions at every Human-in-the-Loop gate, and exports the final assessment with full provenance.

---

## Quick Start

### Prerequisites

- Python 3.9+
- pip (package manager)
- OpenAI API key (optional — app runs in demo mode without it)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/RogueTsar/AAFS.git
cd AAFS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (optional)
cp .env.example .env
# Edit .env with your API keys — or skip this step for demo mode

# 4. Launch the application
streamlit run app.py
```

Opens at **http://localhost:8501**. Without API keys, the app runs in **demo mode** using realistic Singapore mock data at zero cost.

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `set_page_config called twice` | Use `streamlit run app.py` (never `python frontend/ui.py`) |
| Port 8501 busy | `lsof -ti :8501 \| xargs kill -9` then retry |
| No API key warnings | Expected — app works in demo mode. Set `OPENAI_API_KEY` in `.env` for live LLM calls |
| FinBERT slow on first run | Model downloads ~500 MB on first use; cached after that |
| XBRL parsing fails | Upload `.xbrl` or `.xml` files from ACRA BizFinx only (Singapore format) |

---

## Workflow Modes

The sidebar offers three pre-configured workflow modes, each optimized for a different analyst scenario:

| Mode | Use Case | Agents Active | LLM Calls | Est. Cost | Duration |
|------|----------|---------------|-----------|-----------|----------|
| **Exploratory** | Initial screening for a new prospect | 12 (skips social + press) | ~4 | ~$0.005 | ~2 min |
| **Deep Dive** | Annual review for established client | All 18 | ~8 | ~$0.03 | ~5 min |
| **Loan Simulation** | Client requesting new credit facility | Scoring subset + simulator | ~6 | ~$0.01 | ~30 sec |

### Exploratory Mode
Quick snapshot for first-time assessments. Uses a faster model configuration, skips social media and press release agents, runs a single reviewer round. Ideal for call preparation or initial due diligence.

### Deep Dive Mode
Full pipeline activation for comprehensive annual reviews. All 18 agents run with maximum data collection, the stronger model is used, and the reviewer agent makes 3 passes to cross-check findings. Produces the most thorough assessment.

### Loan Simulation Mode
What-if analysis for credit facility requests. Enter a hypothetical loan amount to see how the company's debt-to-equity ratio, interest coverage, and composite risk score shift. No new data collection — uses the most recent assessment as baseline.

---

## Architecture

### Pipeline Design

The system uses **LangGraph** for agent orchestration with a fan-out/fan-in pattern that maximizes parallelism:

```
                              ┌──────────────────────────────────┐
                              │       GUARDRAIL LAYER            │
                              │  (wraps every stage, 0 tokens)   │
                              └──────────────────────────────────┘
                                              │
START ─→ [INPUT AGENT] ─→ [DISCOVERY] ─→ [DOCUMENT PROCESSOR (XBRL)]
                               │
                    ┌──────────┼──────────────────┐
                    │          │                   │
              ┌─────┴───┐ ┌───┴────┐ ┌───────┐ ┌──┴──────┐ ┌────────┐
              │  NEWS    │ │ SOCIAL │ │REVIEW │ │FINANCIAL│ │ PRESS  │
              │  AGENT   │ │ AGENT  │ │ AGENT │ │  AGENT  │ │RELEASE │
              └─────┬───┘ └───┬────┘ └───┬───┘ └──┬──────┘ └───┬────┘
                    │         │          │         │            │
                    └─────────┴────┬─────┴─────────┴────────────┘
                                   │
                         [DATA CLEANING + FinBERT]
                                   │
                        ┌──────────┼──────────┐
                        │                     │
                  [SOURCE CREDIBILITY]  [INDUSTRY CONTEXT]
                   (deterministic)       (LLM-powered)
                        │                     │
                        └──────────┬──────────┘
                                   │
                         [ENTITY RESOLUTION]
                                   │
                         [RISK EXTRACTION]
                                   │
                         [RISK SCORING]
                                   │
                         [CONFIDENCE CALIBRATION]
                          (deterministic)
                                   │
                         [EXPLAINABILITY]
                                   │
                         [REVIEWER] (1-3 passes)
                                   │
                         [AUDIT TRAIL]
                          (deterministic)
                                   │
                                  END
```

### Why LangGraph?

We chose LangGraph over alternatives (AutoGen, CrewAI) for three reasons:

1. **Fan-out/fan-in parallelism**: The 5 collection agents (news, social, review, financial, press) run simultaneously via LangGraph's native parallel branching. This cuts collection time from ~25s (sequential) to ~6s.

2. **State accumulation with `operator.add`**: LangGraph's `Annotated[List, operator.add]` pattern lets parallel agents append to shared lists (e.g., `news_data`, `social_data`) without race conditions. Each agent writes to its own slice; the framework merges them atomically.

3. **Typed state graph**: `GuardedAgentState` extends the base `AgentState` TypedDict with additional fields (`industry_context`, `press_release_analysis`, `audit_trail`, `guardrail_warnings`), ensuring type safety across the entire pipeline.

### State Design

```python
class AgentState(TypedDict):
    company_name: str
    company_info: Dict[str, Any]
    search_queries: Dict[str, List[str]]
    company_aliases: List[str]
    uploaded_docs: List[Dict[str, Any]]
    doc_extracted_text: List[Dict[str, Any]]
    doc_structured_data: Annotated[List[Dict], operator.add]   # parallel-safe
    xbrl_parsed_data: List[Dict[str, Any]]
    news_data: Annotated[List[Dict], operator.add]              # parallel-safe
    social_data: Annotated[List[Dict], operator.add]            # parallel-safe
    review_data: Annotated[List[Dict], operator.add]            # parallel-safe
    financial_data: Annotated[List[Dict], operator.add]         # parallel-safe
    financial_news_data: Annotated[List[Dict], operator.add]    # parallel-safe
    cleaned_data: List[Dict[str, Any]]
    resolved_entities: Dict[str, Any]
    extracted_risks: List[Dict[str, Any]]
    extracted_strengths: List[Dict[str, Any]]
    risk_score: Dict[str, Any]
    explanations: List[Dict[str, Any]]
    final_report: str
    errors: Annotated[List[str], operator.add]                  # parallel-safe
```

The `GuardedAgentState` adds: `industry_context`, `press_release_analysis`, `source_credibility`, `confidence_metrics`, `audit_trail`, `guardrail_warnings`.

---

## Agent Inventory

| # | Agent | File | Purpose | LLM? | Key Output |
|---|-------|------|---------|------|------------|
| 1 | Input Agent | `input_agent.py` | Validates company name, classifies entity type | Yes | `company_info` |
| 2 | Discovery Agent | `discovery_agent.py` | Generates targeted search queries per data domain | Yes | `search_queries` |
| 3 | News Agent | `collection_agents.py` | Collects news articles via NewsAPI + Tavily | Yes | `news_data` |
| 4 | Social Agent | `collection_agents.py` | Gathers social media and review sentiment | Yes | `social_data` |
| 5 | Review Agent | `collection_agents.py` | Aggregates employee/customer reviews | Yes | `review_data` |
| 6 | Financial Agent | `collection_agents.py` | Pulls market data via Yahoo Finance | Yes | `financial_data` |
| 7 | Press Release Agent | `press_release_agent.py` | Analyzes corporate events (M&A, restructuring, leadership changes) | Yes | `press_release_analysis` |
| 8 | Document Processor | `document_processing_agent.py` | Extracts text from PDFs, parses XBRL filings | **No** | `doc_extracted_text`, `xbrl_parsed_data` |
| 9 | Document Metrics | `document_metrics_agent.py` | Computes financial ratios from extracted documents | Yes | `doc_structured_data` |
| 10 | Data Cleaning | `processing_agents.py` | Deduplicates, normalizes, runs FinBERT sentiment | Yes | `cleaned_data` |
| 11 | Entity Resolution | `processing_agents.py` | Disambiguates company names and aliases | Yes | `resolved_entities`, `company_aliases` |
| 12 | Source Credibility | `source_credibility_agent.py` | 4-tier credibility weighting (regulatory > financial > news > social) | **No** | `source_credibility` |
| 13 | Industry Context | `industry_context_agent.py` | Infers sector, identifies industry-specific risk drivers | Yes | `industry_context` |
| 14 | Risk Extraction | `analysis_agents.py` | Identifies risk signals and strength indicators | Yes | `extracted_risks`, `extracted_strengths` |
| 15 | Risk Scoring | `analysis_agents.py` | Computes weighted composite score across 5 frameworks | Yes | `risk_score` |
| 16 | Confidence Agent | `confidence_agent.py` | Calibrates confidence intervals based on data completeness | **No** | `confidence_metrics` |
| 17 | Explainability | `analysis_agents.py` | Generates per-factor explanations with methodology attribution | Yes | `explanations` |
| 18 | Audit Agent | `audit_agent.py` | Produces compliance audit trail for every agent decision | **No** | `audit_trail` |

**Design principle**: 4 agents (Document Processor, Source Credibility, Confidence, Audit) are **fully deterministic** — they use no LLM tokens. This ensures critical safety and compliance functions are reproducible and cost-free.

---

## Guardrail Layer

All 6 guardrail modules are **deterministic** (regex, fuzzy matching, rule-based). They require **zero LLM tokens** and run in <50ms combined. The `GuardrailRunner` orchestrator applies them at pipeline entry, after collection, after scoring, and before export.

| Module | File | What It Catches | # Rules |
|--------|------|-----------------|---------|
| **Input Guardrails** | `input_guardrails.py` | Prompt injection, code injection, suspicious Unicode, SQL injection patterns | 6 detection functions |
| **Output Enforcer** | `output_enforcer.py` | Schema violations, risk scores outside 0-100, rating-score mismatches, missing required fields | 5 enforcement rules |
| **Hallucination Detector** | `hallucination_detector.py` | Ungrounded claims (fuzzy match against sources), company name fabrication, metric fabrication | 3 detection functions, 0.6 similarity threshold |
| **Bias & Fairness** | `bias_fairness.py` | 50+ proxy variable terms (race, religion, gender, nationality), geographic bias, MAS FEAT violations, EU AI Act non-compliance | ~50 proxy terms, 4 MAS principles, 4 EU checks |
| **Cascade Guard** | `cascade_guard.py` | Error propagation between agents, empty/null upstream data, malformed intermediate state | 3 guard functions with safe fallbacks |
| **Content Safety** | `content_safety.py` | Harsh credit language ("bankruptcy guaranteed", "worthless"), missing regulatory disclaimers, score-language inconsistency | 10 softening rules, 3 disclaimer checks |

### How Guardrails Integrate

```python
# In orchestrator_guarded.py — thin wrappers apply guardrails around agents
def guarded_input(state):
    state = input_agent(state)
    warnings = runner.check_input(state["company_name"])
    state["guardrail_warnings"].extend(warnings)
    return state

def guarded_risk_scoring(state):
    state = risk_scoring_agent(state)
    state = runner.enforce_output(state)  # clamp scores, validate schema
    return state
```

The guardrail layer is **additive-only** — it wraps existing agents without modifying them. This means the original 13-agent pipeline (`orchestrator.py`) still works independently.

---

## Tools & External APIs

### LLM Provider

| Setting | Value |
|---------|-------|
| Provider | OpenAI (via `langchain-openai`) |
| Default model | `gpt-4o-mini` |
| Temperature | 0.0 (deterministic) |
| Timeout | 30 seconds per call |
| Fallback | Returns `None` if no API key (demo mode) |

### External Data Sources

| Tool | Library | Purpose | Cost |
|------|---------|---------|------|
| **OpenAI GPT-4o-mini** | `langchain-openai` | Agent reasoning, text analysis, risk extraction | ~$0.15/1M input tokens |
| **NewsAPI** | `requests` | Real-time news article collection (1,000 free calls/day) | Free tier |
| **Tavily Search** | `tavily-python` | Targeted web search for company intelligence | Free tier (1,000/month) |
| **Yahoo Finance** | `yfinance` | Stock price, market cap, financial statements | Free |
| **FinBERT** | `transformers` + `torch` | Financial sentiment classification (positive/negative/neutral) | Free (local model) |
| **PyPDF** | `pypdf` | PDF text extraction for uploaded financial reports | Free |
| **OpenPyXL** | `openpyxl` | Excel spreadsheet parsing for structured data | Free |

### MCP Tools (`src/mcp_tools/`)

| Tool | File | Description |
|------|------|-------------|
| XBRL Parser | `xbrl_parser.py` | Extracts 57 credit-risk elements from ACRA BizFinx filings (stdlib XML, no LLM) |
| News API | `news_api.py` | NewsAPI wrapper with query generation and pagination |
| Financial Lookup | `financial_lookup.py` | Yahoo Finance wrapper for market data retrieval |
| Sentiment Tool | `sentiment_tool.py` | Sentiment analysis pipeline |
| FinBERT Tool | `finbert_tool.py` | FinBERT embedding generation for financial text |

### ACRA XBRL Parser (Custom, 958 lines)

The `src/utils/xbrl_parser.py` is a **fully deterministic, stdlib-only** parser that extracts 57 credit-relevant elements from Singapore ACRA BizFinx XBRL filings:

- **Balance sheet**: Total assets, liabilities, equity, cash, receivables, inventory
- **P&L**: Revenue, COGS, operating profit, net income, EBITDA
- **Cash flow**: Operating, investing, financing cash flows
- **Key ratios**: Current ratio, D/E, interest coverage, ROE, ROA
- **Going concern**: Auditor opinion, directors' statement, Companies Act compliance

No LLM is used — parsing is done via Python's built-in `xml.etree.ElementTree` with a custom ACRA taxonomy mapping.

---

## Evaluation Framework

### Overview

The `eval/` directory contains a three-component evaluation pipeline:

| Component | File | Purpose |
|-----------|------|---------|
| **Metrics** | `eval/metrics.py` | `EvalMetrics` dataclass: precision, recall, F1, signal coverage, latency, cost |
| **Scorer** | `eval/scorer.py` | Fuzzy matching (difflib `SequenceMatcher`, threshold 0.65) to compare extracted signals against ground truth |
| **Report Generator** | `eval/report_generator.py` | Produces Markdown and JSON evaluation reports with per-company breakdowns |

### Test Suite Summary

**257 tests total**, organized across 7 categories. **All tests run without API keys** (deterministic, offline).

| Category | File | Tests | What It Validates |
|----------|------|-------|-------------------|
| **Guardrail Tests** | `test_guardrails/` (5 files) | 74 | All 6 safety modules: injection detection, score clamping, hallucination catching, bias term flagging, cascade prevention, content softening |
| **App Validation** | `test_app_validation.py` | 121 | End-to-end integration: agent outputs, state propagation, workflow correctness across all 3 modes |
| **Synthetic Suite** | `test_synthetic_suite.py` | 46 | 30 synthetic companies (8 known defaults + 22 healthy/ambiguous) tested for signal extraction accuracy and cascade guard integration |
| **Safety Evals** | `test_safety_evals.py` | 14 | Inspired by HarmBench, BBQ, XSTest — adversarial inputs, stereotype detection, content boundary testing |
| **Behavioral Tests** | `test_behavioral.py` | 12 | Pipeline behavioral properties: idempotency, ordering invariance, graceful degradation under missing data |
| **Distress Backtest** | `test_distress_backtest.py` | 10 | 10 historical corporate failures (SVB, Evergrande, FTX, Wirecard, etc.) — validates the system would have flagged them |
| **Edge Cases** | `test_metrics_error.py` + `test_separation.py` | 2 | Metrics null handling, agent data isolation |

### Running the Evaluation Pipeline

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests (no API key needed)
pytest tests/ -v --ignore=tests/test_graph.py --ignore=tests/test_input.py

# Run specific categories
pytest tests/test_guardrails/ -v          # Guardrail tests (74 tests, <2s)
pytest tests/test_evals/ -v               # Eval tests (82 tests, <5s)
pytest tests/test_evals/test_safety_evals.py -v   # Safety evals only

# Run with coverage
pytest tests/ --cov=src --cov=eval --cov-report=term-missing
```

---

## Regulatory Compliance

### MAS FEAT (Monetary Authority of Singapore — Fairness, Ethics, Accountability, Transparency)

| Principle | Implementation | Verification |
|-----------|---------------|--------------|
| **Fairness** | `bias_fairness.py`: 50+ proxy variable detection (race, religion, gender, age, nationality, marital status). No demographic data used in scoring. | 14 bias tests, MAS FEAT compliance checker |
| **Ethics** | `content_safety.py`: 10 softening rules for harsh credit language. Regulatory disclaimers enforced on every output. | 11 content safety tests |
| **Accountability** | `audit_agent.py`: Per-agent decision trail with timestamps, inputs, outputs, and confidence. Full provenance chain. | Audit trail in UI Pipeline Trace tab |
| **Transparency** | `explainability_agent.py`: Per-factor scoring rationale with methodology attribution. Analyst can inspect every weight and source. | Explainability tests, UI domain review panels |

### IMDA AI Verify (7 Principles)

| # | Principle | How Addressed |
|---|-----------|---------------|
| 1 | **Transparency** | Scoring methodology visible, per-domain explanations, source attribution |
| 2 | **Fairness** | Proxy variable detection, no protected-class inputs to scoring |
| 3 | **Safety** | 6 guardrail modules, cascade prevention, content filtering |
| 4 | **Accountability** | Audit trail, Human-in-the-Loop gates at every critical point |
| 5 | **Human Agency** | Analyst approves/overrides at collection, scoring, and export stages |
| 6 | **Data Governance** | 4-tier source credibility weighting, data quality metrics dashboard |
| 7 | **Inclusiveness** | No geographic or demographic bias in scoring; MAS-compliant language |

### Project Moonshot (IMDA Red-Teaming)

Addressed via adversarial test data:
- **15 prompt injection payloads** (`datasets/prompt_injection_payloads.json`): jailbreak attempts, system prompt extraction, role hijacking
- **10 entity spoofing cases** (`datasets/entity_spoofing_cases.json`): disambiguation attacks, misleading company names
- Validated in `test_safety_evals.py` and `test_behavioral.py`

### EU AI Act (High-Risk AI System — Article 6)

| Requirement | Implementation |
|-------------|---------------|
| Risk management system | `guardrail_runner.py` — layered safety checks at every pipeline stage |
| Data governance | 4-tier source credibility (regulatory > financial > news > social) |
| Technical documentation | This README + `docs/GUARDRAILS_AND_EVALS.md` + `WALKTHROUGH.md` |
| Record-keeping | Audit agent logs every decision; run history preserved |
| Transparency | Disclaimers on all outputs; methodology attribution |
| Human oversight | HITL gates; analyst can override any agent decision |
| Accuracy & robustness | 257 tests; hallucination detection; cascade guard |

---

## Cost Analysis

### Per-Assessment Costs

| Component | Exploratory | Deep Dive | Loan Sim |
|-----------|-------------|-----------|----------|
| Input + Discovery | $0.001 | $0.001 | — |
| Collection agents (parallel) | $0.002 | $0.005 | — |
| Processing + Resolution | $0.001 | $0.002 | — |
| Analysis + Scoring | $0.001 | $0.003 | $0.002 |
| Explainability + Review | — | $0.015 | — |
| Loan simulator | — | — | $0.008 |
| **Guardrails (6 modules)** | **$0.000** | **$0.000** | **$0.000** |
| **Total** | **~$0.005** | **~$0.03** | **~$0.01** |

### Budget Context

- SMU-X allocation: **$150 per group**
- At $0.03/deep-dive, this covers **~5,000 full assessments**
- All guardrails and 4 deterministic agents incur $0 LLM cost
- Demo mode with mock data: **$0** (no API calls)

### Model Pricing (gpt-4o-mini)

| Metric | Rate |
|--------|------|
| Input tokens | $0.150 / 1M tokens |
| Output tokens | $0.600 / 1M tokens |
| Average tokens per assessment | ~2,000 input + ~1,500 output |

---

## Project Structure

```
AAFS/
├── app.py                              # Entry point (streamlit run app.py)
├── requirements.txt                    # 20 production dependencies
├── requirements-dev.txt                # Test dependencies (pytest, freezegun)
├── .env.example                        # Environment variable template
├── README.md                           # This file
├── WALKTHROUGH.md                      # Step-by-step user guide (296 lines)
│
├── frontend/                           # Streamlit UI layer (5,907 LOC)
│   ├── hitl_ui.py                      # Main HITL workstation — 8 tabs (2,904 lines)
│   ├── ui_dashboard.py                 # 6 domain review panels + toggleable metrics (1,401 lines)
│   ├── ui_history.py                   # Run history + side-by-side comparison (266 lines)
│   ├── ui_export.py                    # Selective export + email composer (300 lines)
│   ├── xbrl_display.py                 # XBRL data visualization (259 lines)
│   └── ui.py                           # Legacy analysis view (828 lines)
│
├── src/                                # Core pipeline
│   ├── core/
│   │   ├── state.py                    # AgentState TypedDict (15 fields + 7 annotated)
│   │   ├── orchestrator.py             # Standard 13-agent pipeline
│   │   ├── orchestrator_guarded.py     # Guarded 18-agent pipeline (286 lines)
│   │   ├── llm.py                      # LLM client: gpt-4o-mini, 30s timeout (74 lines)
│   │   └── logger.py                   # Structured logging
│   │
│   ├── agents/                         # 18 agent implementations (3,573 LOC)
│   │   ├── input_agent.py              # Entry validation + entity classification
│   │   ├── discovery_agent.py          # Search query generation per domain
│   │   ├── collection_agents.py        # news, social, review, financial (4 agents)
│   │   ├── document_processing_agent.py # XBRL + PDF extraction
│   │   ├── document_metrics_agent.py   # Financial ratio computation
│   │   ├── processing_agents.py        # Data cleaning + entity resolution
│   │   ├── analysis_agents.py          # Risk extraction, scoring, explainability
│   │   ├── reviewer_agent.py           # Multi-pass final review
│   │   ├── press_release_agent.py      # Corporate event analysis (258 lines)
│   │   ├── industry_context_agent.py   # Sector inference + risk drivers (237 lines)
│   │   ├── source_credibility_agent.py # 4-tier source weighting [deterministic] (187 lines)
│   │   ├── confidence_agent.py         # Confidence calibration [deterministic] (278 lines)
│   │   ├── audit_agent.py             # Compliance audit trail [deterministic] (303 lines)
│   │   └── explainer_agent.py          # Reasoning quality analysis (550 lines)
│   │
│   ├── guardrails/                     # 6 safety modules [ALL deterministic] (1,502 LOC)
│   │   ├── guardrail_runner.py         # Unified orchestrator (339 lines)
│   │   ├── input_guardrails.py         # Injection detection (106 lines)
│   │   ├── output_enforcer.py          # Schema + score enforcement (234 lines)
│   │   ├── hallucination_detector.py   # Fuzzy attribution checking (187 lines)
│   │   ├── bias_fairness.py            # Proxy variable + MAS FEAT (250 lines)
│   │   ├── cascade_guard.py            # Error propagation prevention (172 lines)
│   │   └── content_safety.py           # Credit language filtering (163 lines)
│   │
│   ├── utils/
│   │   └── xbrl_parser.py             # ACRA BizFinx parser, 57 elements (958 lines)
│   │
│   └── mcp_tools/                      # Model Context Protocol tools
│       ├── xbrl_parser.py              # MCP XBRL tool (407 lines)
│       ├── news_api.py                 # NewsAPI wrapper
│       ├── financial_lookup.py         # Yahoo Finance wrapper
│       ├── sentiment_tool.py           # Sentiment analysis
│       └── finbert_tool.py             # FinBERT embeddings
│
├── eval/                               # Evaluation framework (667 LOC)
│   ├── metrics.py                      # EvalMetrics dataclass (precision, recall, F1, cost)
│   ├── scorer.py                       # Fuzzy matching scorer (SequenceMatcher, threshold 0.65)
│   └── report_generator.py            # Markdown + JSON report generation
│
├── tests/                              # 257 tests, ALL offline (0 API calls)
│   ├── conftest.py                     # Shared pytest fixtures
│   ├── eval_runner.py                  # CLI evaluation pipeline runner
│   ├── test_app_validation.py          # Integration tests (457 lines)
│   ├── test_metrics_error.py           # Metrics edge cases
│   ├── test_separation.py             # Agent isolation verification
│   │
│   ├── test_guardrails/               # 5 files, 74 test methods
│   │   ├── test_output_enforcer.py     # 22 tests — schema validation, score clamping
│   │   ├── test_bias_fairness.py       # 14 tests — proxy detection, MAS FEAT, EU AI Act
│   │   ├── test_cascade_guard.py       # 15 tests — error propagation, safe fallbacks
│   │   ├── test_hallucination_detector.py # 12 tests — attribution, fabrication
│   │   └── test_content_safety.py      # 11 tests — language softening, disclaimers
│   │
│   ├── test_evals/                     # 4 files, 60 test methods
│   │   │   ├── test_synthetic_suite.py     # 46 tests — 30 companies + cascade integration
│   │   ├── test_distress_backtest.py   # 10 tests — historical corporate failures
│   │   ├── test_behavioral.py          # 12 tests — idempotency, ordering, degradation
│   │   └── test_safety_evals.py        # 14 tests — HarmBench, BBQ, XSTest inspired
│   │
│   ├── datasets/                       # 4 synthetic test datasets (65 cases)
│   │   ├── synthetic_companies.json    # 30 companies (8 defaults, 22 healthy/ambiguous)
│   │   ├── distress_events.json        # 10 historical defaults (SVB, FTX, Wirecard...)
│   │   ├── prompt_injection_payloads.json  # 15 adversarial inputs
│   │   └── entity_spoofing_cases.json  # 10 disambiguation attacks
│   │
│   └── fixtures/                       # 10 mock API responses (offline testing)
│       ├── mock_apple_inc.json, mock_svb.json, mock_tesla.json
│       ├── mock_evergrande.json, mock_ftx.json, mock_credit_suisse.json
│       ├── mock_microsoft.json, mock_wirecard.json
│       ├── mock_grab_holdings.json, mock_dbs_bank.json
│
└── docs/
    └── GUARDRAILS_AND_EVALS.md         # Technical implementation guide (563 lines)
```

---

## Environment Variables

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `OPENAI_API_KEY` | Optional | — | OpenAI API key. Without it, app runs in demo mode. |
| `OPENAI_MODEL` | Optional | `gpt-4o-mini` | Model to use for LLM agents |
| `NEWS_API_KEY` | Optional | — | NewsAPI.org key for real-time news collection (1,000 free/day) |
| `TAVILY_API_KEY` | Optional | — | Tavily search API for targeted web intelligence |

**API Key Handling**: All keys are loaded via `python-dotenv` from a `.env` file (gitignored). The `get_llm()` function in `src/core/llm.py` returns `None` when no API key is set, and every agent that uses LLM checks for `None` before proceeding — ensuring the app never crashes due to missing credentials.

```bash
# Copy the template
cp .env.example .env

# Edit with your keys (or leave empty for demo mode)
nano .env
```

---

## Dataset & Fixture Reference

### Test Datasets (`tests/datasets/`)

| File | Records | Purpose |
|------|---------|---------|
| `synthetic_companies.json` | 30 | Synthetic company profiles. 8 are known defaults (Lehman, Enron-like). 22 are healthy or ambiguous. Each has: name, sector, signals, expected risk level. |
| `distress_events.json` | 10 | Historical corporate failures with dates, causes, and expected signals. Used for backtesting. |
| `prompt_injection_payloads.json` | 15 | Adversarial inputs: jailbreak, system prompt extraction, role hijacking, encoding tricks. |
| `entity_spoofing_cases.json` | 10 | Company name disambiguation attacks: similar names, subsidiaries, defunct entities. |

### Mock Fixtures (`tests/fixtures/`)

10 complete mock API response sets for offline testing. Each fixture contains simulated outputs for all data-collection agents (news, financial, social, reviews) for one company:

| Fixture | Company Type | Why Included |
|---------|-------------|--------------|
| `mock_apple_inc.json` | Large-cap healthy | Baseline positive case |
| `mock_microsoft.json` | Large-cap healthy | Cross-validation |
| `mock_dbs_bank.json` | Singapore bank | ACRA/MAS context |
| `mock_grab_holdings.json` | SEA tech | Emerging market case |
| `mock_tesla.json` | Volatile | Edge case for mixed signals |
| `mock_svb.json` | Bank failure | Should flag high risk |
| `mock_evergrande.json` | Real estate default | Should flag extreme risk |
| `mock_ftx.json` | Crypto fraud | Should flag fraud indicators |
| `mock_wirecard.json` | Accounting fraud | Should flag fabrication |
| `mock_credit_suisse.json` | Bank failure | Should flag systemic risk |

**Adding new test companies**: Create a JSON file in `tests/fixtures/` following the existing schema (see `mock_apple_inc.json` for the template), then add a corresponding entry in `tests/datasets/synthetic_companies.json`.

---

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# ─── Quick smoke test (guardrails only, <2 seconds) ───
pytest tests/test_guardrails/ -v

# ─── Full test suite (all 257 tests, <10 seconds, no API calls) ───
pytest tests/ -v --ignore=tests/test_graph.py --ignore=tests/test_input.py

# ─── Specific test categories ───
pytest tests/test_evals/test_safety_evals.py -v        # HarmBench/BBQ/XSTest
pytest tests/test_evals/test_distress_backtest.py -v   # Historical failures
pytest tests/test_evals/test_synthetic_suite.py -v     # 30-company synthetic suite
pytest tests/test_evals/test_behavioral.py -v          # Pipeline behavior

# ─── With coverage report ───
pytest tests/ --cov=src --cov=eval --cov-report=term-missing \
       --ignore=tests/test_graph.py --ignore=tests/test_input.py

# ─── Run evaluation pipeline (generates report) ───
python tests/eval_runner.py
```

**All 134 tests are fully offline** — no API keys, no network calls. Tests use mock fixtures and synthetic data exclusively.

---

## Team

**Agentic Fintech Consultancy (AFC)** — G5 Team

**IS4000: Application of AI in Financial Services**
**Singapore Management University** | 2025

---

*Built with LangGraph, Streamlit, and OpenAI. Designed for UBS credit risk compliance.*
