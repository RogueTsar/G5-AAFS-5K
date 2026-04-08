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
- **Hybrid guardrails**: 6 safety modules with deterministic regex checks + LLM-powered deep analysis (hallucination verification, compliance evaluation)
- **ACRA XBRL parsing**: Deterministic extraction of 57 credit-risk elements from Singapore financial filings — no LLM needed
- **Human-in-the-Loop gates**: Analyst must approve at every critical decision point (after data collection, before scoring, before export)
- **IMDA AI governance**: Compliant with AI Verify (7 principles), Project Moonshot (25 red-team tests), MAS FEAT, EU AI Act
- **LLM-as-Judge evaluation**: Semantic signal matching, report quality scoring, and AI-generated eval insights
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
[INPUT] → [DOCUMENT PROCESSOR (XBRL)] + [DISCOVERY]
                                              |
                                  Fan-out (5 parallel agents):
                     [NEWS] [SOCIAL] [REVIEW] [FINANCIAL] [PRESS RELEASE]
                                              |
                                  Fan-in (6 sources):
                     [DATA CLEANING + FinBERT]
                              |
               ┌──────────────┴──────────────┐
     [SOURCE CREDIBILITY (LLM)]    [INDUSTRY CONTEXT (LLM)]
               └──────────────┬──────────────┘
                    [ENTITY RESOLUTION]
                              |
                    [RISK EXTRACTION] → [RISK SCORING] → [CONFIDENCE (LLM)]
                              |
                    [EXPLAINABILITY] → [REVIEWER] → [EXPLAINER (LLM)]
                              |
                    [AUDIT TRAIL (LLM)]
                              |
              ┌───────────────────────────────┐
              │      GUARDRAIL LAYER          │
              │  Input Validator (regex)       │
              │  Output Enforcer (schema)      │
              │  Cascade Guard (error prop.)   │
              │  Hallucination (fuzzy + LLM)   │
              │  Bias/Fairness (regex + LLM)   │
              │  Content Safety (regex)        │
              └───────────────────────────────┘
```

### Cost per Assessment
| Mode | LLM Calls | Estimated Cost |
|------|-----------|---------------|
| Exploratory | ~6 | ~$0.008 |
| Deep Dive | ~12 | ~$0.04 |
| Loan Simulation | ~8 | ~$0.015 |
| Guardrails (deterministic) | 0 | $0.00 |
| Guardrails (LLM deep checks) | ~2 | ~$0.003 |

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
│   ├── agents/                     # 19 agents (14 original + 5 augmented)
│   │   ├── input_agent.py
│   │   ├── discovery_agent.py
│   │   ├── collection_agents.py    # news, social, review, financial
│   │   ├── document_processing_agent.py
│   │   ├── document_metrics_agent.py
│   │   ├── processing_agents.py    # cleaning + entity resolution
│   │   ├── analysis_agents.py      # risk extraction, scoring, explainability
│   │   ├── reviewer_agent.py
│   │   ├── press_release_agent.py  # LLM: corporate event analysis
│   │   ├── industry_context_agent.py  # LLM: sector inference
│   │   ├── source_credibility_agent.py  # LLM + rule-based fallback
│   │   ├── confidence_agent.py          # LLM + quantitative metrics
│   │   ├── audit_agent.py              # LLM: compliance quality assessment
│   │   └── explainer_agent.py          # LLM: pipeline audit + devil's advocate
│   │
│   ├── guardrails/                 # 6 modules: regex base + LLM deep checks
│   │   ├── guardrail_runner.py     # Orchestrator with LLM deep check toggle
│   │   ├── input_guardrails.py     # Regex: injection, sanitization
│   │   ├── output_enforcer.py      # Schema enforcement, score clamping
│   │   ├── hallucination_detector.py  # Fuzzy match + LLM verification
│   │   ├── bias_fairness.py        # Regex + LLM compliance evaluation
│   │   ├── cascade_guard.py        # Error propagation prevention
│   │   └── content_safety.py       # Language softening, disclaimers
│   │
│   └── utils/
│       └── xbrl_parser.py          # ACRA BizFinx (57 elements, stdlib only)
│
├── eval/                           # Evaluation framework (fuzzy + LLM scoring)
│   ├── metrics.py                  # EvalMetrics with LLM semantic fields
│   ├── scorer.py                   # Fuzzy match + LLM-as-judge scoring
│   └── report_generator.py         # Markdown/JSON + LLM-generated insights
│
├── tests/                          # ~160 tests
│   ├── datasets/                   # 4 synthetic test datasets
│   ├── fixtures/                   # 10 mock company responses
│   ├── test_guardrails/            # 5 test files
│   └── test_evals/                 # 6 test files (incl. Moonshot + LLM Judge)
│
└── docs/
    └── GUARDRAILS_AND_EVALS.md     # Technical documentation
```

---

## Regulatory Compliance

| Framework | Status | Implementation |
|-----------|--------|---------------|
| **MAS FEAT** (Fairness) | PASS | 50+ proxy variable detection + LLM tone bias analysis |
| **MAS FEAT** (Ethics) | PASS | Content safety filter, regulatory disclaimer, LLM compliance audit |
| **MAS FEAT** (Accountability) | PASS | Full audit trail per agent decision (LLM quality assessment) |
| **MAS FEAT** (Transparency) | PASS | Per-factor explainability, visible scoring rationale |
| **IMDA AI Verify** | 7/7 | All principles addressed |
| **Project Moonshot** | PASS | 25 red-team tests (adversarial, toxicity, bias, hallucination probes) |
| **EU AI Act** (High-Risk) | 7/7 | Risk management, data governance, human oversight |

---

## Running Tests

```bash
pip install -r requirements-dev.txt

# Guardrail tests (deterministic, instant)
pytest tests/test_guardrails/ -v

# Eval tests (deterministic suites)
pytest tests/test_evals/ -v

# Project Moonshot red-team suite (deterministic, ~25 tests)
pytest tests/test_evals/test_moonshot.py -v

# LLM-as-Judge suite (requires OPENAI_API_KEY, auto-skips without it)
pytest tests/test_evals/test_llm_judge.py -v

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
