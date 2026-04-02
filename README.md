# G5-AAFS: AI-Augmented Credit Risk Assessment

> **UBS x SMU IS4000** | Multi-agent LangGraph pipeline with HITL scoring, ACRA XBRL parsing, guardrails, and IMDA AI governance compliance.

---

## Quick Start (3 commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment (copy and fill in your API keys)
cp .env.example .env   # Then edit .env with your keys

# 3. Launch the app
streamlit run app.py
```

The app opens at **http://localhost:8501**. Demo mode works without API keys.

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: streamlit` | Run `pip install -r requirements.txt` |
| `ModuleNotFoundError: yfinance` | Run `pip install yfinance` |
| `OPENAI_API_KEY not set` | App runs in **demo mode** with mock data — no keys needed |
| `set_page_config can only be called once` | Use `streamlit run app.py` (not `frontend/ui.py`) |
| Port 8501 in use | `lsof -ti :8501 \| xargs kill -9` then retry |
| XBRL parser not loading | Check Python 3.10+ and `from src.utils.xbrl_parser import parse_xbrl_instance` |

---

## Application Flow

```
                        G5-AAFS Credit Risk Workstation
                        ===============================

    SIDEBAR (always visible)                    MAIN AREA
    ========================                    =========

    [UBS Logo]                          Tab 1: CREDIT ASSESSMENT
    Pipeline Status                     ├── Company Input + XBRL Upload
      - Live / Demo mode                ├── Domain Review (6 tabs)
      - XBRL Parser status              │   ├── Financial Statements (XBRL)
      - Guardrails status               │   ├── Credit Quality (MAS grading)
                                        │   ├── Companies Act disclosures
    NEXT STEP GUIDANCE                  │   ├── News & Press Releases
      Step 1: Enter company             │   ├── Social & Reviews
      Step 2: Review + Set weights      │   └── Industry & Market
      Step 3: Export / Email            ├── Weight Selection (5 framework presets)
                                        ├── Weighted Risk Score + Sub-Scores
    Progress: [====>    ] 2/4           └── Risk vs Strength Signals

    Data Treatment                      Tab 2: PIPELINE TRACE
      - Structured / Semi / Unstructured├── Step 1-8 agent-by-agent view
                                        ├── Visual diagnostics per step
    Scoring Frameworks                  └── Guardrail badges + audit trail
      - Basel IRB / Altman / S&P
      - Moody's KMV / MAS FEAT         Tab 3: AI GOVERNANCE
                                        ├── IMDA AI Verify (7 principles)
    AI Governance                       ├── Project Moonshot (red-team tests)
      - IMDA / MAS / EU AI Act          ├── MAS FEAT (4 principles)
                                        └── EU AI Act (7 requirements)
    Quick Actions
      [Reset Assessment]                Tab 4: REPORT & EMAIL
      [Re-run Collection]               ├── Download JSON / Markdown / CSV
                                        └── Email draft with mailto: link
```

---

## Design Rationale

### Why Dual-View (Domain Review + Pipeline Trace)?

**Domain Review** answers: *"What does the data say?"*
- Credit analysts need to see all collected intelligence organized by data source before making weight decisions
- Structured data (XBRL) rendered as tables/ratios; unstructured data (news) rendered with sentiment analysis
- This enables informed human-in-the-loop weight selection

**Pipeline Trace** answers: *"What did each agent do and why?"*
- Required for MAS FEAT Accountability and EU AI Act transparency
- Shows the decision chain: Input > Discovery > Collection > Cleaning > Extraction > Scoring > Explanation > Report
- Each step shows inputs, outputs, and diagnostics

### Why Sidebar-Driven Workflow?

- **Always-visible context**: Pipeline status, next step, and progress never scroll out of view
- **No separate commands**: Everything (reset, re-run, framework selection) accessible from sidebar
- **Progressive disclosure**: Shows only what's relevant at each stage

### Why 5 Scoring Framework Presets?

Each preset mirrors a real-world credit assessment methodology:

| Preset | Methodology | Weight Distribution |
|--------|-------------|-------------------|
| **Basel IRB** | Basel II/III Internal Ratings-Based (PD/LGD focus) | FSH 40%, CCA 20%, News 15%, Press 10%, Social 5%, Reviews 10% |
| **Altman Z-Score** | 5 financial ratio zones (WC/TA, RE/TA, EBIT/TA, MVE/TL, Sales/TA) | FSH 60%, CCA 15%, News 10%, Press 5%, Social 5%, Reviews 5% |
| **S&P Global** | Business Risk Profile + Financial Risk Profile | FSH 30%, CCA 10%, News 15%, Press 15%, Social 10%, Reviews 20% |
| **Moody's KMV** | Distance-to-Default (financial + market equity signals) | FSH 35%, CCA 10%, News 25%, Press 15%, Social 10%, Reviews 5% |
| **MAS FEAT** | Singapore regulatory balanced multi-source assessment | FSH 25%, CCA 15%, News 20%, Press 15%, Social 10%, Reviews 15% |

### Why IMDA AI Governance?

Singapore's IMDA requires AI systems in financial services to comply with:
- **AI Verify**: Testing framework for transparency, fairness, safety, accountability
- **Project Moonshot**: Open-source red-teaming toolkit for LLM evaluation
- **MAS FEAT**: Fairness, Ethics, Accountability, Transparency principles
- **EU AI Act**: Credit scoring classified as high-risk AI (Article 6/Annex III)

---

## Architecture

### Multi-Agent Pipeline (LangGraph)

```
[INPUT AGENT] + [DOCUMENT PROCESSOR]    ← Validate + XBRL structured extraction (0 tokens)
       |
[DISCOVERY AGENT]                       ← Generate targeted search queries
       |
 Fan-Out (parallel):
  [NEWS] [SOCIAL] [REVIEW] [FINANCIAL] [PRESS RELEASE]
       |
 Fan-In:
  [DATA CLEANING + FinBERT]             ← Sentiment enrichment
  [ENTITY RESOLUTION]                   ← Deduplication + credibility weighting
       |
  [RISK EXTRACTION]                     ← LLM structured output (risks + strengths)
  [RISK SCORING]                        ← LLM 0-100 score with rating
       |
  [CONFIDENCE CALIBRATION]              ← 0 LLM tokens (data coverage + agreement)
  [EXPLAINABILITY]                      ← Per-factor reasoning
       |
  [REVIEWER]                            ← Final markdown report
  [AUDIT TRAIL]                         ← MAS FEAT compliant decision lineage
```

### Guardrails Layer (0 LLM tokens)

| Module | What It Does |
|--------|-------------|
| `input_guardrails.py` | Regex injection detection, code patterns, entity classification |
| `output_enforcer.py` | Schema validation, score-rating consistency, hard-stop on malformed output |
| `hallucination_detector.py` | Entity attribution verification, metric fabrication detection |
| `bias_fairness.py` | 50+ proxy variable detection, MAS FEAT / EU AI Act compliance |
| `cascade_guard.py` | Inter-agent error propagation prevention, fallback outputs |
| `content_safety.py` | Softens definitive credit recommendations, regulatory footer |
| `guardrail_runner.py` | Unified orchestration with timestamped audit log |

### XBRL Parser (ACRA BizFinx Taxonomy 2026)

- **57 credit-risk elements** mapped across 6 categories
- **Zero external dependencies** (stdlib `xml.etree` only)
- Computes: current_ratio, debt_to_equity, npl_ratio, coverage_ratio, profit_margin, interest_coverage
- Detects 9 risk flags (going concern, NPL>5%, negative equity, etc.)
- MAS credit classification: Pass / Special Mention / Substandard / Doubtful / Loss

---

## Project Structure

```
G5-AAFS-5K/
|-- app.py                          # Unified entry point (streamlit run app.py)
|-- requirements.txt                # Production dependencies
|-- requirements-dev.txt            # Test dependencies (pytest, etc.)
|-- .env.example                    # Environment variable template
|
|-- frontend/
|   |-- hitl_ui.py                  # Main HITL workstation (UBS enterprise UI)
|   |-- ui.py                       # Original analysis UI (legacy view)
|   +-- __init__.py
|
|-- src/
|   |-- core/
|   |   |-- state.py                # AgentState TypedDict (LangGraph state)
|   |   |-- orchestrator.py         # Standard 13-agent workflow
|   |   |-- orchestrator_guarded.py # Guarded workflow (18 agents + guardrails)
|   |   |-- llm.py                  # OpenAI / HUD LLM client
|   |   +-- logger.py
|   |
|   |-- agents/                     # 14 agent implementations
|   |   |-- input_agent.py          # Company validation
|   |   |-- discovery_agent.py      # Search query generation
|   |   |-- collection_agents.py    # News, social, review, financial (parallel)
|   |   |-- document_processing_agent.py  # PDF/XBRL/Excel extraction
|   |   |-- processing_agents.py    # Data cleaning + entity resolution
|   |   |-- analysis_agents.py      # Risk extraction, scoring, explainability
|   |   |-- reviewer_agent.py       # Final report generation
|   |   |-- press_release_agent.py  # Corporate event analysis
|   |   |-- industry_context_agent.py # Industry outlook
|   |   |-- source_credibility_agent.py # Source tiering (0 tokens)
|   |   |-- confidence_agent.py     # Confidence calibration (0 tokens)
|   |   +-- audit_agent.py          # Audit trail (0 tokens)
|   |
|   |-- guardrails/                 # 6 guardrail modules (all 0 LLM tokens)
|   |   |-- guardrail_runner.py     # Unified runner
|   |   |-- input_guardrails.py     # Input validation
|   |   |-- output_enforcer.py      # Schema enforcement
|   |   |-- hallucination_detector.py
|   |   |-- bias_fairness.py        # MAS FEAT + EU AI Act
|   |   |-- cascade_guard.py        # Pipeline abort logic
|   |   +-- content_safety.py       # Report filtering
|   |
|   |-- utils/
|   |   +-- xbrl_parser.py          # ACRA BizFinx XBRL parser
|   |
|   +-- mcp_tools/                  # MCP tool layer
|       |-- news_api.py
|       |-- financial_lookup.py
|       |-- finbert_tool.py
|       +-- sentiment_tool.py
|
|-- eval/                           # Evaluation framework
|   |-- metrics.py                  # EvalMetrics dataclass + cost tracking
|   |-- scorer.py                   # Ground truth comparison
|   +-- report_generator.py         # Markdown/JSON eval reports
|
|-- tests/
|   |-- conftest.py                 # Shared pytest fixtures
|   |-- eval_runner.py              # CLI eval pipeline
|   |-- datasets/                   # 4 synthetic test datasets
|   |-- fixtures/                   # 10 pre-cached mock company responses
|   |-- test_guardrails/            # 5 guardrail test files
|   +-- test_evals/                 # 4 evaluation test files
|
|-- docs/
|   +-- GUARDRAILS_AND_EVALS.md     # R8+R9 comprehensive documentation
|
+-- social_scraper_mcp/             # Social media MCP tools
    |-- industry.py
    |-- source2.py
    +-- source3.py
```

---

## Environment Variables

Create a `.env` file (see `.env.example`):

```bash
OPENAI_API_KEY=sk-...           # Required for live mode
OPENAI_MODEL=gpt-4o-mini        # Model selection
NEWS_API_KEY=...                 # NewsAPI key
TAVILY_API_KEY=tvly-dev-...     # Tavily search key
```

**Demo mode**: The app works without any API keys using built-in mock data.

---

## Agents Overview

| Agent | Tokens | Purpose |
|-------|--------|---------|
| Input Agent | 0 | Validate company name, classify entity type |
| Discovery Agent | ~200 | Generate targeted search queries via LLM |
| News Agent | ~100 | Collect news articles via NewsAPI + Tavily |
| Social Agent | ~100 | Collect social media posts via Tavily |
| Review Agent | ~100 | Collect employee/customer reviews |
| Financial Agent | ~100 | Fetch financial data via yfinance |
| Press Release Agent | ~500 | Directed corporate event analysis |
| Document Processor | 0 | XBRL structured extraction (deterministic) |
| Data Cleaning | ~300 | FinBERT sentiment enrichment |
| Entity Resolution | ~200 | LLM deduplication + relevance check |
| Source Credibility | 0 | Hardcoded tier-based source weighting |
| Industry Context | ~200 | Industry outlook from MCP tools |
| Risk Extraction | ~500 | LLM structured risks + strengths |
| Risk Scoring | ~300 | LLM 0-100 score with confidence |
| Confidence Agent | 0 | Data coverage + sentiment agreement |
| Explainability | ~300 | Per-factor reasoning |
| Reviewer | ~500 | Final markdown report |
| Audit Agent | 0 | Decision lineage + compliance log |

**Total per assessment**: ~3,400 tokens (~$0.01 at gpt-4o-mini rates)

---

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run guardrail unit tests (0 API calls)
pytest tests/test_guardrails/ -v

# Run eval tests with mocks (0 API calls)
pytest tests/test_evals/ -v

# Run full eval suite
python -m tests.eval_runner --mode mock --suite all
```

---

## Team

| Role | Member | Scope |
|------|--------|-------|
| R1 | Marcus | Project lead, orchestration |
| R8 | Vaishnavi | Guardrails framework |
| R9 | Vaishnavi | Evaluation & testing |

## License

Internal Use Only | UBS x SMU IS4000
