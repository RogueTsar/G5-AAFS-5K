# G5-AAFS: AI-Augmented Credit Risk Assessment

Multi-agent pipeline for credit risk assessment. Enter a company, system collects data from 14+ agents, you review and score.

---

## What This App Does

**For a compliance analyst at UBS**: You enter a company name, optionally upload their ACRA filing (XBRL), and the system runs 14+ AI agents in parallel to collect financial data, news, social sentiment, press releases, and industry context. You review all findings by data domain, set your own scoring weights using established frameworks (Basel IRB, Altman Z-Score, S&P, Moody's KMV), and generate a risk assessment with full audit trail.

**Three workflow modes** for different scenarios:

| Mode | When to Use | What Happens |
|------|------------|--------------|
| **Exploratory** | Initial call with new prospect | Quick 5-min snapshot. Skips social/press agents. Fast model. 1 reviewer round. |
| **Deep Dive** | Annual review for established client | Full pipeline, all agents, all data sources. Stronger model. 3 reviewer rounds. |
| **Loan Simulation** | Client requesting new facility | Enter hypothetical loan amount. See how D/E ratio, coverage, and risk score shift instantly. |

**Key differentiators**:
- **Zero-token guardrails**: 6 safety modules (bias detection, hallucination check, cascade prevention) that cost $0 to run
- **ACRA XBRL parsing**: Deterministic extraction of 57 credit-risk elements from Singapore financial filings — no LLM needed
- **Human-in-the-Loop gates**: Analyst must approve at every critical decision point (after data collection, before scoring, before export)
- **IMDA AI governance**: Compliant with AI Verify (7 principles), Project Moonshot, MAS FEAT, EU AI Act
- **Run history & comparison**: Compare assessments side-by-side to see how different configs affect the score

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys (or skip — demo mode works without keys)

# 3. Launch
streamlit run app.py
```

Opens at **http://localhost:8501**. Demo mode runs with mock data and costs nothing.

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `set_page_config called twice` | Use `streamlit run app.py` (not `frontend/ui.py`) |
| Port 8501 busy | `lsof -ti :8501 \| xargs kill -9` then retry |
| No API key | App runs in demo mode with realistic Singapore mock data |

---

## App Walkthrough (for UBS analysts)

### Step 1: Choose Your Workflow
In the **sidebar**, select your scenario: Exploratory, Deep Dive, or Loan Simulation. Each pre-configures the agent pipeline, model, and reviewer depth. You can override any setting.

### Step 2: Enter Company & Upload Documents
Type the company name. Optionally upload ACRA BizFinx XBRL filings (.xbrl, .xml), financial reports (.pdf, .xlsx), or taxonomy schemas (.xsd). XBRL uploads get instant structured extraction preview.

### Step 3: Review Collected Intelligence
After the pipeline runs, review findings across **6 data domains**:
- **Financial Statements** (XBRL structured) — Balance sheet, P&L, cash flow, key ratios
- **Credit Quality** (MAS grading) — Pass/Special Mention/Substandard/Doubtful/Loss classification
- **Companies Act** — Going concern, directors' assessment, auditor opinion
- **News & Press** — Sentiment analysis, corporate event categorization
- **Social & Reviews** — Stakeholder sentiment from employee/customer reviews
- **Industry & Market** — Sector outlook, positive/negative drivers

### Step 4: Set Scoring Weights
Choose a framework preset (Basel IRB, Altman Z-Score, S&P, Moody's KMV, MAS FEAT) or manually adjust 6 domain weight sliders. The system normalizes weights and shows the breakdown.

### Step 5: Generate Risk Score
Click to generate the weighted composite score. See per-domain sub-scores with methodology attribution, contribution breakdown, and risk gauge visualization.

### Step 6: Export & Follow Up
- **Dashboard**: Toggle metric panels (Collection, Analysis, Guardrails, Data Quality, Performance)
- **Pipeline Trace**: Inspect what each agent did, step by step
- **Loan Simulation**: Enter hypothetical loan amount, see ratio impact
- **AI Governance**: IMDA AI Verify, Project Moonshot, MAS FEAT, EU AI Act compliance status
- **Report & Email**: Download JSON/Markdown/CSV, send via email

---

## Architecture

```
[INPUT] → [DOCUMENT PROCESSOR (XBRL 0-token)] + [DISCOVERY]
                                                      |
                                          Fan-out (parallel):
                              [NEWS] [SOCIAL] [REVIEW] [FINANCIAL] [PRESS]
                                                      |
                                          Fan-in:
                              [DATA CLEANING + FinBERT] → [ENTITY RESOLUTION]
                                                      |
                              [SOURCE CREDIBILITY (0-token)] + [INDUSTRY CONTEXT]
                                                      |
                              [RISK EXTRACTION] → [RISK SCORING] → [CONFIDENCE (0-token)]
                                                      |
                              [EXPLAINABILITY] → [REVIEWER] → [AUDIT TRAIL (0-token)]
                                                      |
                                            ┌─────────────────┐
                                            │  GUARDRAIL LAYER │ (wraps every agent, 0 tokens)
                                            │  Input Validator  │
                                            │  Output Enforcer  │
                                            │  Hallucination    │
                                            │  Bias/Fairness    │
                                            │  Cascade Guard    │
                                            │  Content Safety   │
                                            └─────────────────┘
```

### Cost per Assessment
| Mode | LLM Calls | Estimated Cost |
|------|-----------|---------------|
| Exploratory | ~4 | ~$0.005 |
| Deep Dive | ~8 | ~$0.03 |
| Loan Simulation | ~6 | ~$0.01 |
| Guardrails overhead | 0 | $0.00 |

---

## Project Structure

```
├── app.py                          # Entry point: streamlit run app.py
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Test dependencies
├── .env.example                    # Environment variable template
│
├── frontend/
│   ├── hitl_ui.py                  # Main HITL workstation
│   ├── ui_dashboard.py             # Toggleable dashboards + domain review
│   ├── ui_history.py               # Run history + comparison tool
│   ├── ui_export.py                # Selective section export + email
│   └── ui.py                       # Legacy analysis view
│
├── src/
│   ├── core/
│   │   ├── state.py                # AgentState TypedDict
│   │   ├── orchestrator.py         # Standard 13-agent pipeline
│   │   ├── orchestrator_guarded.py # Guarded pipeline (18 agents + guardrails)
│   │   ├── llm.py                  # LLM client
│   │   └── logger.py
│   │
│   ├── agents/                     # 14 agent implementations
│   │   ├── input_agent.py
│   │   ├── discovery_agent.py
│   │   ├── collection_agents.py    # news, social, review, financial
│   │   ├── document_processing_agent.py
│   │   ├── processing_agents.py    # cleaning + entity resolution
│   │   ├── analysis_agents.py      # risk extraction, scoring, explainability
│   │   ├── reviewer_agent.py
│   │   ├── press_release_agent.py
│   │   ├── industry_context_agent.py
│   │   ├── source_credibility_agent.py  # 0 tokens
│   │   ├── confidence_agent.py          # 0 tokens
│   │   └── audit_agent.py              # 0 tokens
│   │
│   ├── guardrails/                 # 6 modules, ALL 0 LLM tokens
│   │   ├── guardrail_runner.py
│   │   ├── input_guardrails.py
│   │   ├── output_enforcer.py
│   │   ├── hallucination_detector.py
│   │   ├── bias_fairness.py
│   │   ├── cascade_guard.py
│   │   └── content_safety.py
│   │
│   └── utils/
│       └── xbrl_parser.py          # ACRA BizFinx (57 elements, stdlib only)
│
├── eval/                           # Evaluation framework
│   ├── metrics.py, scorer.py, report_generator.py
│
├── tests/                          # 134 tests, 0 API calls
│   ├── datasets/                   # 4 synthetic test datasets
│   ├── fixtures/                   # 10 mock company responses
│   ├── test_guardrails/            # 5 test files
│   └── test_evals/                 # 4 test files
│
└── docs/
    └── GUARDRAILS_AND_EVALS.md     # Technical documentation
```

---

## Regulatory Compliance

| Framework | Status | Implementation |
|-----------|--------|---------------|
| **MAS FEAT** (Fairness) | PASS | 50+ proxy variable detection, no demographic scoring |
| **MAS FEAT** (Ethics) | PASS | Content safety filter, regulatory disclaimer |
| **MAS FEAT** (Accountability) | PASS | Full audit trail per agent decision |
| **MAS FEAT** (Transparency) | PASS | Per-factor explainability, visible scoring rationale |
| **IMDA AI Verify** | 7/7 | All principles addressed |
| **Project Moonshot** | PASS | 15 prompt injection tests, 10 spoofing tests |
| **EU AI Act** (High-Risk) | 7/7 | Risk management, data governance, human oversight |

---

## Running Tests

```bash
pip install -r requirements-dev.txt

# Guardrail tests (0 API calls, instant)
pytest tests/test_guardrails/ -v

# Eval tests (0 API calls)
pytest tests/test_evals/ -v

# Full suite
pytest tests/ -v --ignore=tests/test_graph.py --ignore=tests/test_input.py
```

---

## Team

| Role | Scope |
|------|-------|
| R8 — Guardrails | 6 zero-token safety modules, regulatory compliance |
| R9 — Evaluation | 134 tests, 4 datasets, eval framework, safety evals |

**UBS x SMU IS4000** | Singapore 2026
