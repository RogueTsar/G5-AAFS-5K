# G5-AAFS Project Overview — Complete Decision Log

> Generated: 2 April 2026 | Branch: `harmonized-app` | Repo: marcus159260/G5-AAFS-5K

---

## 1. Project Summary

**G5-AAFS** (Automated Anomaly & Financial Screening) is a multi-agent AI system for credit risk assessment, built for UBS bank as part of SMU IS4000 group project.

**What it does**: Analyst enters a company name, system runs 14+ AI agents in parallel to collect financial data, news, social sentiment, press releases, and industry context. Analyst reviews findings by data domain, sets scoring weights, and generates a risk assessment with full audit trail.

**Live test results** (real API calls, gpt-4o-mini):
| Company | Score | Rating | Risks | Strengths | Time |
|---------|-------|--------|-------|-----------|------|
| DBS Group | 20/100 | Low | 0 | 4 | 32.7s |
| Apple Inc | 35/100 | Low | 2 | 2 | 31.8s |
| Tesla Inc | 72/100 | High | 8 | 4 | 43.8s |
| Grab Holdings | 65/100 | High | 3 | 4 | 37.0s |

**Test suite**: 255/255 tests pass (0 API calls, <6s)

---

## 2. Branch History

### 2.1 Main Branch (origin/main) — Original Team Work

| Commit | Author | What |
|--------|--------|------|
| `ed7f651` | Team | Initial commit |
| `aa4adb9` | Team | Basic Streamlit UI |
| `7f5e913` | Team | Core multi-agent system: data collection, processing, LLM-driven risk assessment with LangGraph |
| `e1fb1ce` | Team | Core risk analysis agents + AgentState definition |
| `a3becd4` | Team | Added DuckDuckGo search (needs testing) |
| `35961cf` | Team | Revise project structure in README |
| `964fbd3` | Team | Merge PR #1 (KE-local-tests) |
| `76b1453` | Team | Create .gitignore |
| `1888234` | Team | Test industry MCP tool |
| `b7315db` | Team | File directory changes + dependencies |
| `8e2c8de` | Taz | Tested source discovery agent |
| `6b147ea` | Taz | Integrate Tavily Search, FinBERT, upgraded discovery agent |
| `61e5ccd` | Taz | Optimize discovery agent queries, fix FinBERT 512-token truncation |
| `21d87f5` | Taz | Refine discovery queries for business outlook |
| `657c911` | Taz | Revert |
| `c97426f` | Taz | Added input + source discovery agent |
| `7ab43c0` | Taz | Moved agents |
| `97da779` | Marcus | XBRL parser + visual display (balance sheet, income statement, cash flows, 3 use cases) |
| `a074cd3` | Marcus | PDF data extraction + loading bar |
| `eec0806` | Marcus | HITL features |
| `eb1059f` | Marcus | Update ui.py |
| `4e10771` | Team | Merge eval-+-guardrails branch into main |

### 2.2 Eval + Guardrails Branch (eval-+-guardrails) — Vaishnavi's R8+R9 Work

| Commit | What |
|--------|------|
| `6579c39` | feat: dual-view HITL UI + guardrails + eval suite + XBRL parser — 35+ new files added |

**What was added**:
- 6 guardrail modules (all 0 LLM tokens): input validation, output enforcement, hallucination detection, bias/fairness, cascade guard, content safety
- 5 new agents: source credibility, confidence calibration, audit trail, industry context, press release
- Guarded orchestrator wrapping existing pipeline
- 134 tests, 4 synthetic datasets, 10 mock fixtures
- ACRA BizFinx XBRL parser (57 credit-risk elements, stdlib only)
- Data-first HITL UI with domain review tabs
- Eval framework (metrics, scorer, report generator)

### 2.3 Harmonized-App Branch — Integration + Enterprise UI

| Commit | What Changed | Why |
|--------|-------------|-----|
| `ae47fc3` | Harmonized enterprise app — UBS styling, IMDA governance, sidebar workflow | Merge eval branch features with main, add enterprise look |
| `1cb1145` | Enterprise UBS workstation — workflow modes, HITL gates, dashboard, loan sim | 3 workflow modes (Exploratory/Deep Dive/Loan Sim), HITL decision gates, toggleable dashboard, loan simulation |
| `da14557` | Flatten folder structure — remove G5-AAFS-5K-main/ nesting | Files were nested under G5-AAFS-5K-main/ subfolder, causing confusion on GitHub |
| `7edb342` | Rewrite README for compliance analyst audience | Old README described non-existent file structure and had undone TODOs |
| `435ab7a` | Restore main branch features, fix XBRL parser, restore app.py | Marcus's XBRL parser (src/mcp_tools/xbrl_parser.py), xbrl_display.py, document_metrics_agent.py were missing |
| `a1b3c84` | Add run history/comparison + selective export modules | ui_history.py: save runs, compare side-by-side. ui_export.py: choose sections to export |
| `9b9156c` | Wire all UI modules, eval/guardrail buttons, user guide, demo toggle | Connected ui_history, ui_export into main app. Added Testing tab with pytest buttons |
| `03f509d` | app.py now launches HITL workstation | Was launching blank original UI instead of feature-rich HITL workstation |
| `3d229e6` | 121-point validation suite + deployment env support | test_app_validation.py: file existence, syntax, imports, keys, env, datasets, guardrails, orchestrators |
| `ef2b18f` | Remove double render_hitl() call | `if __name__` + `else` both called render_hitl(), causing duplicate widget keys |
| `cf99729` | Enterprise CSS overhaul, UBS logo, proper topbar | Inter font, UBS logo SVG, top ribbon, tight card spacing, metric card redesign |
| `06230d8` | Remove Font +/- button crash | st.session_state["font_size"] can't be modified after slider widget instantiated |
| `dd15725` | Wire scenario briefing, timing, costs, rationale, demo mode | Demo toggle forces mock data. Timing/cost in ribbon. Comprehensive rationale by category/severity |
| `cfb1e2e` | Fix NameError on breakdown variable | Line 949 referenced undefined `breakdown` dict in _phase_score chart |
| `8fa4482` | Fix KeyError 'blocked' in governance tab | Python `bool` is subclass of `int`, so `isinstance(True, int)` is True — wrong branch taken |
| `198086f` | Dark theme, collapsible sidebar, interactive topbar | Full dark theme (#0B0E14), sidebar expanders (later removed), Inter font |
| `ae2f794` | Remove demo mode, live API only | User wants final version, no mock data fallback |
| `2faf92f` | Remove ALL sidebar expanders | Streamlit 1.55 Material icon ligatures render as `_arr` text when CSS interferes |
| `5313001` | Replace wildcard * CSS selector | `[data-testid="stSidebar"] *` was forcing color on SVG arrow icons |
| `7dc29b8` | Another expander CSS fix attempt | Still had `details`/`summary` selectors |
| `857e8d6` | Explainer agent, workflow rename, testing tab overhaul, sticky ribbon, auto-run | NEW explainer_agent.py, workflow modes renamed, 6 guardrail toggles, 6 eval checkboxes, sticky topbar, auto-run skip gates, compact sidebar |

---

## 3. File Inventory (89 files on harmonized-app)

### 3.1 Entry Points
| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 15 | Main entry — loads AAFS.env, calls `render_hitl()` |
| `frontend/hitl_ui.py` | 2652 | Full HITL workstation: 9 tabs, sidebar, topbar, all phases |
| `frontend/ui.py` | ~350 | Original analysis UI (Marcus's, preserved) |

### 3.2 Frontend Modules
| File | Lines | Purpose |
|------|-------|---------|
| `frontend/ui_dashboard.py` | 1401 | Enhanced dashboard with SectionTimer, execution perf panel, scenario briefing |
| `frontend/ui_history.py` | 266 | Run history: save_run(), render_history_panel(), render_comparison_tool() |
| `frontend/ui_export.py` | 300 | Selective export: 3 grouping modes (process/agent/risk), format selector, email |
| `frontend/xbrl_display.py` | 259 | Marcus's XBRL visual display |
| `frontend/__init__.py` | 7 | Exports `render` from ui.py |

### 3.3 Core
| File | Lines | Purpose |
|------|-------|---------|
| `src/core/state.py` | 36 | AgentState TypedDict — shared data contract |
| `src/core/orchestrator.py` | ~80 | Standard 13-agent LangGraph workflow |
| `src/core/orchestrator_guarded.py` | ~280 | Guarded workflow: 18 agents + guardrail hooks |
| `src/core/llm.py` | ~50 | get_llm() — returns ChatOpenAI instance |
| `src/core/logger.py` | 48 | Agent logging to files |

### 3.4 Agents (16 total)
| File | Tokens | Source | Purpose |
|------|--------|--------|---------|
| `input_agent.py` | 0 | Original | Validate company name |
| `discovery_agent.py` | ~200 | Original | Generate search queries |
| `collection_agents.py` | ~400 | Original | News, social, review, financial (parallel) |
| `document_processing_agent.py` | 0 | Original+Edit | PDF/XBRL/Excel extraction |
| `processing_agents.py` | ~500 | Original | Data cleaning + entity resolution |
| `analysis_agents.py` | ~1000 | Original | Risk extraction, scoring, explainability |
| `reviewer_agent.py` | ~500 | Original | Final report generation |
| `press_release_agent.py` | ~500 | New (R8) | Corporate event analysis |
| `industry_context_agent.py` | 0 | New (R8) | Industry outlook (wraps MCP tool) |
| `source_credibility_agent.py` | 0 | New (R8) | 4-tier source weighting |
| `confidence_agent.py` | 0 | New (R8) | Confidence calibration |
| `audit_agent.py` | 0 | New (R8) | MAS FEAT audit trail |
| `explainer_agent.py` | ~500 | New (R8) | Find reasoning/logic errors in agent output |
| `updated_input_agent.py` | ~200 | Taz | New input agent with guardrails |
| `updated_source_agent.py` | ~300 | Taz | Tavily + LLM source discovery |
| `document_metrics_agent.py` | ~70 | Marcus | Document metrics |
| `input_models.py` | ~100 | Taz | Pydantic models for input validation |

### 3.5 Guardrails (7 files, ALL 0 LLM tokens)
| File | Purpose |
|------|---------|
| `input_guardrails.py` | Regex injection detection, entity classification (Original by Taz) |
| `output_enforcer.py` | Schema validation, score-rating consistency |
| `hallucination_detector.py` | Entity attribution, metric fabrication detection |
| `bias_fairness.py` | 50+ proxy variable detection, MAS FEAT/EU AI Act |
| `cascade_guard.py` | Inter-agent error propagation, fallback outputs |
| `content_safety.py` | Report filtering, regulatory footer |
| `guardrail_runner.py` | Unified orchestration with audit log |

### 3.6 MCP Tools
| File | Purpose |
|------|---------|
| `src/mcp_tools/xbrl_parser.py` | Marcus's ACRA BizFinx XBRL parser (407 lines) |
| `src/mcp_tools/financial_lookup.py` | Financial data tools |
| `src/mcp_tools/finbert_tool.py` | FinBERT sentiment analysis |
| `src/mcp_tools/news_api.py` | NewsAPI integration |
| `src/mcp_tools/sentiment_tool.py` | Sentiment scoring |

### 3.7 Eval Framework
| File | Purpose |
|------|---------|
| `eval/metrics.py` | EvalMetrics dataclass, cost tracking, latency decorator |
| `eval/scorer.py` | Ground truth comparison, precision/recall |
| `eval/report_generator.py` | Markdown/JSON eval report generation |

### 3.8 Tests (255 total, 0 API calls)
| File | Tests | What |
|------|-------|------|
| `test_app_validation.py` | 121 | File structure, syntax, keys, imports, env, datasets |
| `test_guardrails/test_output_enforcer.py` | ~30 | Schema enforcement |
| `test_guardrails/test_hallucination_detector.py` | ~20 | Attribution verification |
| `test_guardrails/test_bias_fairness.py` | ~20 | Proxy variable detection |
| `test_guardrails/test_cascade_guard.py` | ~15 | Pipeline abort logic |
| `test_guardrails/test_content_safety.py` | ~15 | Report filtering |
| `test_evals/test_behavioral.py` | ~10 | Refusal, scope, sycophancy |
| `test_evals/test_safety_evals.py` | ~15 | Injection, spoofing, cascade |
| `test_evals/test_synthetic_suite.py` | ~20 | 30 company backtest |
| `test_evals/test_distress_backtest.py` | ~10 | Historical defaults |

### 3.9 Datasets
| File | Records | What |
|------|---------|------|
| `synthetic_companies.json` | 30 | Healthy, distressed, ambiguous companies |
| `distress_events.json` | 10 | SVB, Evergrande, FTX, Wirecard, etc. |
| `prompt_injection_payloads.json` | 15 | Adversarial inputs |
| `entity_spoofing_cases.json` | 10 | Disambiguation test cases |

### 3.10 Mock Fixtures (10 companies)
Apple, Microsoft, Tesla, DBS Bank, Grab, SVB, Evergrande, Credit Suisse, Wirecard, FTX

---

## 4. Key Architectural Decisions

### 4.1 Zero-Token Guardrails
**Decision**: All 6 guardrail modules use regex, string matching, and dict lookups — zero LLM API calls.
**Why**: $150 total budget. Guardrails run on EVERY pipeline invocation. Deterministic = auditable for MAS FEAT.
**Trade-off**: Limited detection capability (regex can't catch sophisticated attacks). Documented in safety eval tests (80% threshold, not 100%).

### 4.2 Guarded Orchestrator as Wrapper
**Decision**: `orchestrator_guarded.py` wraps existing agents with guardrail hooks via function composition, rather than modifying original agent files.
**Why**: User constraint "DO NOT DELETE OR MODIFY EXISTING FILES." Team can activate by changing one import.
**Trade-off**: Duplicate code (GuardedAgentState re-declares all fields). LangGraph TypedDict inheritance bug forced flattening.

### 4.3 Dark Theme
**Decision**: Full dark background (#0B0E14) with subtle borders.
**Why**: User requested enterprise look. Dark themes are standard in financial terminals (Bloomberg, Refinitiv).
**Trade-off**: Some Streamlit widgets don't fully respect dark CSS (file uploader, some labels).

### 4.4 No Sidebar Expanders
**Decision**: All sidebar sections use flat widgets (radio, checkbox, slider) with `---` dividers.
**Why**: Streamlit 1.55 Material icon ligatures render as `_arr` text when CSS interferes with icon fonts. 3 attempts to fix with CSS failed. Only fix: don't use expanders.
**Trade-off**: Sidebar is longer (can't collapse sections). Mitigated by 220px width and tight spacing.

### 4.5 AAFS.env Not Committed
**Decision**: API keys in local `AAFS.env` file, excluded from git via `.gitignore`.
**Why**: GitHub Push Protection blocks commits containing OpenAI API keys.
**Trade-off**: Teammates must create their own AAFS.env. For deployment, use Streamlit Cloud secrets.

### 4.6 Demo Mode Removed
**Decision**: No mock data fallback. Always uses live API.
**Why**: User said "remove demo mode, only have live api use nonstop, assume final version."
**Trade-off**: App won't work without API keys set in AAFS.env.

### 4.7 Scoring Framework Presets
**Decision**: 5 presets (Basel IRB, Altman Z-Score, S&P Global, Moody's KMV, MAS FEAT) with different weight distributions.
**Why**: Each represents decades of empirical default prediction research. Gives analysts informed starting points.
**Trade-off**: Sub-scores use simplified approximations (e.g., Altman Z-Score zones instead of actual Z computation — we don't have all 5 Altman variables from every data source).

### 4.8 Two XBRL Parsers
**Decision**: Marcus's `src/mcp_tools/xbrl_parser.py` (407 lines) AND ours `src/utils/xbrl_parser.py` (958 lines) both exist.
**Why**: Marcus's is proven and integrated with his UI. Ours has more credit-risk elements. Both kept for compatibility.
**Trade-off**: Redundancy. hitl_ui.py imports Marcus's first, falls back to ours.

---

## 5. Bugs Found and Fixed

| Bug | Root Cause | Fix | Commit |
|-----|-----------|-----|--------|
| Double render_hitl() call | `if __name__` + `else` both call it | Remove `else` block | `ef2b18f` |
| Font +/- crash | `st.session_state["font_size"]` modified after slider widget | Remove font slider, use A-/A+ buttons | `06230d8` |
| `breakdown` NameError | Undefined variable in _phase_score chart | Add `breakdown = dict(zip(domains, scores))` | `cfb1e2e` |
| `KeyError 'blocked'` | `isinstance(True, int)` is True in Python (bool subclass) | Check `"blocked" in result` first | `8fa4482` |
| Sidebar `_arr` text | CSS wildcard `*` selector overrides Streamlit icon fonts | Replace `*` with specific element selectors, then remove all expanders | `5313001`, `2faf92f` |
| GuardedAgentState inheritance | LangGraph introspects `__annotations__` directly — child TypedDict misses parent reducers | Flatten all fields into one TypedDict | Earlier session |
| guardrail_runner.py wrong keys | Used `risks`, `score` instead of `extracted_risks`, `risk_score` | Fixed key names | Earlier session |
| cascade_guard.py schema mismatch | `processed_documents` vs `doc_extracted_text` | Fixed to match AgentState | Earlier session |
| NumPy 2.x incompatibility | torch/transformers compiled against NumPy 1.x | `pip install "numpy<2"` → 1.26.4 | Runtime fix |
| GitHub push protection | AAFS.env contains OpenAI API key | Add AAFS.env to .gitignore, don't commit | `9b9156c` |

---

## 6. Regulatory Compliance

| Framework | Status | Implementation |
|-----------|--------|---------------|
| MAS FEAT — Fairness | PASS | 50+ proxy variable detection in bias_fairness.py |
| MAS FEAT — Ethics | PASS | Content safety filter, regulatory footer |
| MAS FEAT — Accountability | PASS | Audit trail agent, guardrail_runner audit log |
| MAS FEAT — Transparency | PASS | Explainability agent, per-factor reasoning, visible scoring |
| IMDA AI Verify | 7/7 | All principles addressed |
| Project Moonshot | PASS | 15 prompt injection + 10 spoofing tests |
| EU AI Act (High-Risk) | 7/7 | Risk management, data governance, human oversight |

---

## 7. What's PENDING

### 7.1 UI Polish (P1)
- Top ribbon should be fully interactive (clickable history count, inline settings)
- Sidebar needs progress timer during live pipeline execution
- Source credibility recommendations after agent runs (high/med/low per source)
- Agent output should have inline "Explain This" buttons (currently only in Pipeline tab)

### 7.2 Features (P2)
- `reviewer_rounds` is UI-only — not wired to actual reviewer agent (needs multi-round review loop)
- `ui_dashboard.py` has enhanced versions of dashboard/pipeline/review with SectionTimer — not imported by hitl_ui.py (would cause circular import)
- Extended workflow config (temperature, max_tokens) stored but not passed to LLM calls
- Explainer agent needs to be wirable to any agent output section, not just Pipeline tab
- Project Moonshot eval needs actual IMDA toolkit integration (currently a checkbox placeholder)
- LLM-as-Judge eval needs implementation (currently a checkbox placeholder)

### 7.3 Infrastructure (P3)
- Deployment to Streamlit Cloud / Railway / Vercel not yet done
- Streamlit secrets support added but not tested in cloud
- No CI/CD pipeline
- No automated cost tracking per session (eval/metrics.py exists but not wired to live runs)

### 7.4 Team Integration (P3)
- Teammates need AAFS.env with API keys (not committed)
- Original `frontend/ui.py` still works via `frontend/__init__.py` but is disconnected from new features
- `updated_input_agent.py` and `updated_source_agent.py` exist but aren't wired into either orchestrator

---

## 8. How to Run

```bash
# Clone and checkout
git clone https://github.com/marcus159260/G5-AAFS-5K.git
cd G5-AAFS-5K
git checkout harmonized-app

# Install dependencies
pip install -r requirements.txt

# Set up API keys
cat > AAFS.env << 'EOF'
OPENAI_API_KEY=your-key-here
NEWS_API_KEY=your-newsapi-key
OPENAI_MODEL=gpt-4o-mini
TAVILY_API_KEY=your-tavily-key
EOF

# Launch
streamlit run app.py

# Run tests (0 API calls)
pip install -r requirements-dev.txt
pytest tests/test_guardrails/ tests/test_evals/ tests/test_app_validation.py -v
```

---

## 9. Cost Analysis

| Component | LLM Calls | Cost per Run |
|-----------|-----------|-------------|
| Standard pipeline (14 agents) | ~8 | ~$0.01-0.03 |
| All guardrails | 0 | $0.00 |
| Source credibility + confidence + audit | 0 | $0.00 |
| Explainer agent (on demand) | 1 | ~$0.002 |
| Full test suite (255 tests) | 0 | $0.00 |
| Full eval (live, 30 companies) | ~120 | ~$0.05 |

---

## 10. Things to Remember (Hard-Won Lessons)

1. **NO expanders in sidebar** — Streamlit 1.55 icon bug renders `_arr` text
2. **NO wildcard `*` CSS on sidebar** — breaks icon fonts
3. **NO duplicate widget keys** — Streamlit crashes
4. **NO `st.session_state[key] = value` after widget with same key** — StreamlitAPIException
5. **NO `else: render_hitl()` at bottom** — double render crash
6. **`bool` is subclass of `int`** — `isinstance(True, int)` is True
7. **AAFS.env in .gitignore** — GitHub blocks API keys
8. **Top ribbon needs `position:sticky`** — or it scrolls away
9. **font_size must use ONE method** — either slider OR manual set, not both
10. **LangGraph TypedDict inheritance** — flatten, don't subclass

---

## 11. AgentState — Complete Data Contract

Every agent reads from and writes to this shared TypedDict. The `Annotated[List, operator.add]` fields accumulate results from parallel agents (fan-in pattern).

```python
class AgentState(TypedDict):
    company_name: str                                    # Input
    company_info: Dict[str, Any]                         # From input_agent
    search_queries: Dict[str, List[str]]                 # From discovery_agent
    company_aliases: List[str]                           # From entity_resolution
    uploaded_docs: List[Dict[str, Any]]                  # User uploads
    doc_extracted_text: List[Dict[str, Any]]             # From document_processing_agent
    news_data: Annotated[List[Dict], operator.add]       # From news_agent (parallel)
    social_data: Annotated[List[Dict], operator.add]     # From social_agent (parallel)
    review_data: Annotated[List[Dict], operator.add]     # From review_agent (parallel)
    financial_data: Annotated[List[Dict], operator.add]  # From financial_agent (parallel)
    cleaned_data: List[Dict[str, Any]]                   # From data_cleaning_agent
    resolved_entities: Dict[str, Any]                    # From entity_resolution_agent
    extracted_risks: List[Dict[str, Any]]                # From risk_extraction_agent
    extracted_strengths: List[Dict[str, Any]]            # From risk_extraction_agent
    risk_score: Dict[str, Any]                           # From risk_scoring_agent
    explanations: List[Dict[str, Any]]                   # From explainability_agent
    final_report: str                                    # From reviewer_agent
    errors: Annotated[List[str], operator.add]           # Accumulates across agents
```

**GuardedAgentState** extends this with 4 additional fields:
- `industry_context: Dict` — from industry_context_agent
- `press_release_analysis: Dict` — from press_release_agent
- `audit_trail: Dict` — from audit_agent
- `guardrail_warnings: Annotated[List[str], operator.add]` — from guardrail_runner

---

## 12. Pydantic Output Schemas (LLM Structured Output)

These schemas enforce deterministic output structure from LLM calls:

```
RiskSignal:
    type: "Traditional Risk" | "Non-traditional Risk"
    description: str (1-sentence)

StrengthSignal:
    type: "Financial Strength" | "Market Strength"
    description: str (1-sentence)

RiskScoreOutput:
    score: int (0-100, 100 = max insolvency risk)
    max: int (always 100)
    rating: "Low" | "Medium" | "High"

Explanation:
    metric: str (area of concern, e.g. "Financials", "Public Sentiment")
    reason: str (short rationale for risk impact)
```

**Score-rating consistency enforced by output_enforcer.py**: Low=0-33, Medium=34-66, High=67-100.

---

## 13. Pipeline Execution Flow (Guarded Orchestrator)

```
START
  |
  v
[guarded_input] -----> [discovery] ---------> [news]      (parallel)
  |                        |                   [social]     (parallel)
  |                        |                   [review]     (parallel)
  |                        |                   [financial]  (parallel)
  |                        +-----------------> [press_release] (parallel)
  +-----> [document_processor] ----+
                                   |
  [news + social + review + financial + press + doc_processor] (fan-in)
                                   |
                                   v
                          [data_cleaning]
                           /           \
              [source_credibility]  [industry_context]   (parallel)
                           \           /
                        [entity_resolution]              (fan-in)
                                   |
                                   v
                    [guarded_risk_extraction]  <-- guardrail: output_enforcer
                                   |
                    [guarded_risk_scoring]     <-- guardrail: output_enforcer
                                   |
                         [confidence]          <-- 0 LLM tokens
                                   |
                    [guarded_explainability]   <-- guardrail: content_safety
                                   |
                      [guarded_reviewer]       <-- guardrail: hallucination + bias
                                   |
                           [audit]             <-- 0 LLM tokens
                                   |
                                  END
```

**Guardrail wrapping pattern**: Each `guarded_*` function calls `runner.validate_input()` or `runner.validate_agent_output()` before/after the real agent, injecting warnings into `guardrail_warnings`.

**Fan-out/fan-in**: LangGraph's `Annotated[List, operator.add]` reducer accumulates results from parallel agents. The `add_edge([list], target)` syntax creates a synchronization barrier.

---

## 14. Scoring Methodology — 6 Domain Sub-Scores

Each domain produces a sub-score (0-100 where 100 = worst risk). Analyst sets weights, composite = weighted sum.

| Domain | Method | Algorithm |
|--------|--------|-----------|
| **Financial Statements (FSH)** | Modified Altman Z-Score | 5 ratio zones: Liquidity (CR), Leverage (D/E), Profitability (margin), Coverage (IC), Risk Flags. Each zone scores 0-20. Total max 100. |
| **Companies Act (CCA)** | Basel Going-Concern | Binary signals: going concern doubt (+40), can't pay debts (+30), not true & fair (+15). Base 15. Max 100. |
| **News** | KMV Event-Study | Asymmetric sentiment: `50 + 40*(neg*1.5 - pos)/1.5`. Negative events weighted 1.5x (empirical credit literature). |
| **Press Releases** | S&P Competitive Position | Trajectory map: growth=25, stable=45, restructuring=70, contraction=80. Adjusted by event balance (neg vs pos). |
| **Social Sentiment** | Stakeholder Sentiment Index | Volume-adjusted Bayesian regression: `50*(1-confidence) + raw*confidence` where confidence = min(posts/10, 1). Low sample = regress to 50. |
| **Reviews** | Moody's Stakeholder Quality | Employee 60% / Customer 40% blend. `100 - blended_rating * 20`. Rating 5.0 = score 0. Rating 0 = score 100. |

**Presets**:
| Preset | FSH | CCA | News | Press | Social | Reviews |
|--------|-----|-----|------|-------|--------|---------|
| Basel IRB | 40% | 20% | 15% | 10% | 5% | 10% |
| Altman Z-Score | 60% | 15% | 10% | 5% | 5% | 5% |
| S&P Global | 30% | 10% | 15% | 15% | 10% | 20% |
| Moody's KMV | 35% | 10% | 25% | 15% | 10% | 5% |
| MAS FEAT | 25% | 15% | 20% | 15% | 10% | 15% |

---

## 15. Source Credibility Tiers (0 LLM tokens)

Hardcoded credibility weights — deterministic and auditable:

| Tier | Weight | Examples |
|------|--------|---------|
| **Tier 1 — Institutional** | 0.90-0.95 | yfinance, SEC EDGAR, MAS filings, ACRA, annual reports |
| **Tier 2 — Reputable Media** | 0.80-0.85 | Reuters, Bloomberg, FT, WSJ, NewsAPI |
| **Tier 3 — Contextual** | 0.50-0.60 | Glassdoor, LinkedIn, customer reviews |
| **Tier 4 — Low Signal** | 0.35-0.40 | Reddit, Twitter/X, social media |

Domain matching: `sec.gov` → Tier 1 (0.95), `reuters.com` → Tier 2 (0.85), `reddit.com` → Tier 4 (0.35).

---

## 16. Guardrail Runner — Audit Log Structure

Every guardrail check produces a timestamped audit entry:

```json
{
    "timestamp": "2026-04-02T08:30:15.123Z",
    "guardrail_name": "bias_fairness",
    "action": "validated",
    "details": {
        "proxy_terms_found": 0,
        "protected_classes_flagged": [],
        "mas_feat_compliant": true
    }
}
```

**GuardrailRunner methods**:
- `validate_input(company_name)` → (sanitized, is_valid, warnings)
- `validate_agent_output(agent_name, output, state)` → (cleaned, warnings)
- `validate_final_report(report, state)` → (cleaned_report, summary)
- `get_audit_log()` → list of timestamped entries
- `get_summary()` → {checks, warnings, blocks, pass_rate}

---

## 17. UI Function Map (hitl_ui.py — 2652 lines, 35 functions)

### Visual Primitives
| Function | Line | What |
|----------|------|------|
| `_metric()` | 81 | Colored metric card with label/value/delta |
| `_risk_gauge()` | 91 | Horizontal bar gauge (green/orange/red) |
| `_badge()` | 103 | Pass/fail badge |
| `_sentiment_counts()` | 112 | Count pos/neg/neutral from items list |
| `_fmt()` | 122 | Number formatter (1.5B, 200M, 1,500, 0.1234) |

### Phase Functions (main workflow)
| Function | Line | What |
|----------|------|------|
| `_phase_input()` | 246 | Company name input + file uploader + XBRL preview |
| `_phase_collect()` | 284 | Run pipeline or show error. Tracks elapsed time + cost |
| `_phase_review()` | 323 | 6-tab domain review (FSH, CCA, News, Press, Social, Industry) |
| `_phase_weights()` | 682 | 5 preset buttons + 6 weight sliders + normalization |
| `_phase_score()` | 795 | 6 domain sub-scores + weighted composite + bar chart |
| `_phase_report()` | 956 | Executive summary + rationale by category/severity + guardrails |
| `_phase_governance()` | 1538 | IMDA AI Verify + Project Moonshot + MAS FEAT + EU AI Act |
| `_phase_email_report()` | 1626 | Email composer with mailto link |

### Domain Review Tabs (inside _phase_review)
| Function | Line | Data Source |
|----------|------|------------|
| `_tab_financial_statements()` | 364 | XBRL structured / yfinance fallback |
| `_tab_credit_quality()` | 442 | MAS 5-grade classification from XBRL |
| `_tab_companies_act()` | 495 | Going concern, directors assessment |
| `_tab_news_press()` | 540 | News sentiment + corporate events |
| `_tab_social_reviews()` | 591 | Social sentiment + employee/customer reviews |
| `_tab_industry()` | 651 | Industry outlook, drivers |

### Pipeline Trace (8 steps)
| Function | Line | Agent Stage |
|----------|------|------------|
| `_pipeline_view()` | 1061 | Master view with progress bar |
| `_pipe_step_input()` | 1119 | Input validation |
| `_pipe_step_discovery()` | 1140 | Source discovery |
| `_pipe_step_collection()` | 1163 | Parallel data collection (6 agents) |
| `_pipe_step_cleaning()` | 1198 | Data cleaning + credibility |
| `_pipe_step_extraction()` | 1227 | Risk/strength extraction |
| `_pipe_step_scoring()` | 1253 | Risk scoring |
| `_pipe_step_explain()` | 1278 | Explainability |
| `_pipe_step_report()` | 1298 | Final report + compliance |

### Infrastructure
| Function | Line | What |
|----------|------|------|
| `_build_css()` | 1343 | Dark theme CSS with `--fs` variable |
| `_hitl_gate()` | 1722 | Pulsing decision gate (approve/reject/redo) |
| `_loan_simulation()` | 1746 | What-if loan calculator |
| `_dashboard_view()` | 1826 | 4 toggleable metric panels |
| `_render_sidebar()` | 1927 | Compact flat sidebar |
| `_tab_testing()` | 2025 | Guardrail config (6 toggles) + eval suite (6 checkboxes) |
| `_tab_user_guide()` | 2272 | Workflows, settings, scoring, HITL gates, roles |
| `render_hitl()` | 2368 | Main orchestrator — sidebar + ribbon + 9 tabs |

---

## 18. Workflow Modes — Complete Config

```python
"exploratory": {
    "label": "Quick Screen (New Client)",
    "desc": "5-min snapshot for initial client call...",
    "agents_enabled": {news: True, social: False, review: False,
                       financial: True, press: False, xbrl: True},
    "default_model": "gpt-4o-mini",
    "reviewer_rounds": 1,
    "cost_est": "~$0.005",
    "temperature": 0.0,
    "max_tokens_per_agent": 500,
}

"deep_dive": {
    "label": "Full Assessment (Annual Review)",
    "desc": "Comprehensive multi-source analysis for credit committee...",
    "agents_enabled": {ALL: True},
    "default_model": "gpt-4o",
    "reviewer_rounds": 3,
    "cost_est": "~$0.03",
    "temperature": 0.1,
    "max_tokens_per_agent": 1500,
}

"loan_simulation": {
    "label": "Loan Simulation (What-If)",
    "desc": "Enter a loan amount to see how D/E ratio, coverage, and risk score change.",
    "agents_enabled": {news: True, social: False, review: True,
                       financial: True, press: True, xbrl: True},
    "default_model": "gpt-4o-mini",
    "reviewer_rounds": 2,
    "cost_est": "~$0.01",
    "temperature": 0.0,
    "max_tokens_per_agent": 800,
}
```

---

## 19. Explainer Agent — Reasoning Quality Checker

**File**: `src/agents/explainer_agent.py`
**Purpose**: Analyze any agent output text for reasoning quality issues.
**LLM calls**: 1 per invocation (~$0.002)

**Issue categories**:
1. LOGICAL ERROR — flawed reasoning, non-sequiturs, circular logic
2. OVERSIMPLIFICATION — imprecise language losing important nuance
3. EPISTEMIC ERROR — false confidence, missing uncertainty qualifiers
4. FACTUAL CONCERN — claims that may be inaccurate or unverifiable
5. MISSING CONTEXT — important factors not considered

**Output**: `{"explainer_issues": [{category, severity, original_text, correction}], "explainer_summary": str}`

**UI integration**: Text area in Pipeline Trace tab — paste any agent output, click "Analyze Reasoning", see structured issues with severity badges.

---

## 20. Testing Tab — Guardrails & Eval Config

### Guardrail Toggles (6):
| Toggle | Key | Description |
|--------|-----|-------------|
| Input Validation | `guard_input` | Regex injection detection, entity classification |
| Output Enforcement | `guard_output` | Schema validation, score-rating consistency |
| Hallucination Detection | `guard_hallucination` | Entity attribution verification |
| Bias/Fairness | `guard_bias` | 50+ proxy variable detection |
| Cascade Guard | `guard_cascade` | Pipeline abort on too many failures |
| Content Safety | `guard_content` | Report language filtering |

### Eval Suite Checkboxes (6):
| Eval | Key | Library | Time | Default |
|------|-----|---------|------|---------|
| Behavioral Tests | `eval_behavioral` | pytest (open-source) | ~2s | ON |
| Safety Evals | `eval_safety` | pytest (open-source) | ~3s | ON |
| Synthetic Companies | `eval_synthetic` | pytest (domain-specific) | ~5s | ON |
| Distress Backtest | `eval_distress` | pytest (domain-specific) | ~3s | ON |
| Project Moonshot | `eval_moonshot` | IMDA (gov-developed) | Setup required | OFF |
| LLM-as-Judge | `eval_llm_judge` | OpenAI API | ~$0.01/run | OFF |

---

## 21. HITL Decision Gates

| Gate | Location | Options | Auto-run Behavior |
|------|----------|---------|-------------------|
| Collection Review | After `_phase_collect()` | Approve / Re-run / Stop | Skipped (auto-approve) |
| Weight Confirmation | After `_phase_weights()` | Generate Score / Adjust | Skipped (auto-generate) |

**Auto-run toggle**: `sb.checkbox("Auto-run (skip review gates)", key="auto_run")` in sidebar. When checked, both gates auto-approve and pipeline runs straight through to output.

---

## 22. Team Role Mapping

| Role | Member | What They Built | Key Files |
|------|--------|----------------|-----------|
| R1 Product Owner | Marcus | PRD, scope, milestones | — |
| R2 AI Governance | — | Bias checks, explainability spec | — |
| R4 Orchestration | Marcus | LangGraph StateGraph, agent routing | `orchestrator.py`, `state.py` |
| R5 Retrieval | Taz | Tavily search, FinBERT, source discovery | `updated_source_agent.py`, `finbert_tool.py` |
| R6 Budget & Infra | — | API cost tracking, caching | — |
| R7 Analysis | Marcus | Risk extraction prompts, Pydantic schemas | `analysis_agents.py` |
| R8 Guardrails | Vaishnavi | 6 guardrail modules, guarded orchestrator | `src/guardrails/*.py`, `orchestrator_guarded.py` |
| R9 Evaluation | Vaishnavi | 255 tests, 4 datasets, eval framework | `tests/`, `eval/` |
| R10 Demo & Docs | Marcus/Vaishnavi | Streamlit UI, XBRL display, README | `frontend/*.py`, `README.md` |

---

## 23. Dependencies

### Production (`requirements.txt`):
```
streamlit==1.55.0, pydantic, mcp, anthropic, pandas, numpy,
python-dotenv, langgraph, langchain, langchain-openai,
tavily-python, yfinance, requests, httpx, transformers,
torch, torchvision, pypdf, openpyxl
```

### Dev (`requirements-dev.txt`):
```
pytest, pytest-asyncio, freezegun
```

### Runtime Notes:
- `numpy` must be <2.0 (torch/transformers compiled against 1.x). NOTE: requirements.txt still pins `numpy==2.4.3` — this is a known contradiction. Runtime fix was `pip install "numpy<2"` but requirements.txt was not updated.
- `transformers` loads ProsusAI/finbert (~500MB) on first use via HuggingFace Hub. Lazy-loaded and globally cached in module-level globals. Cold start with no cache triggers download.
- `yfinance` requires internet access
- `streamlit==1.55.0` is pinned. Later versions may fix the Material icon ligature bug but could break our CSS selectors.
- `langgraph`, `langchain`, `langchain-openai` are UNPINNED — fan-in syntax `add_edge([list], target)` may change across versions. This is a deployment risk.
- `mcp==1.26.0` and `anthropic==0.84.0` are in requirements.txt but NOT used by the main app pipeline. MCP is for the standalone `social_scraper_mcp/` tool. `anthropic` is not referenced anywhere in app code.

---

## 24. LLM Configuration Details (`src/core/llm.py`)

- **Model is HARDCODED to `gpt-4o-mini`** in `get_llm()`. The `OPENAI_MODEL` env var in AAFS.env is **silently ignored** — never read by any code.
- **Signature**: `get_llm(temperature: float = 0.0) -> Optional[ChatOpenAI]`
- **Returns `None` if `OPENAI_API_KEY` is missing** — does not raise an exception.
- **Every agent must handle `None` return.** Agents that call `get_llm()` degrade gracefully: entity_resolution falls back to basic checks, processing_agents skip FinBERT enrichment.
- **No base_url override, no alternative inference endpoints.** References to HUD endpoints in MEMORY.md are from a different project.
- **Temperature defaults to 0.0** (deterministic). The `temperature` and `max_tokens_per_agent` fields in `_WORKFLOW_MODES` are stored in session_state but NOT passed to `get_llm()` calls. This is a known gap (documented in Section 7.2 Pending).

---

## 25. Standard vs Guarded Orchestrator — Exact Differences

### Standard (`src/core/orchestrator.py`) — 13 nodes:
```
input → discovery → [news, social, review, financial] (fan-out, 4 parallel)
input → document_processor (parallel with discovery)
[news, social, review, financial, document_processor] → data_cleaning (5-way fan-in)
data_cleaning → entity_resolution → risk_extraction → risk_scoring → explainability → reviewer → END
```
- No press_release agent
- No source_credibility, industry_context, confidence, audit agents
- No guardrail wrappers
- No conditional edges (entirely static graph)

### Guarded (`src/core/orchestrator_guarded.py`) — 18+ nodes:
- Adds: `press_release` (parallel with news/social/review/financial)
- Adds: `source_credibility` and `industry_context` (parallel after data_cleaning)
- Adds: `confidence` (after risk_scoring)
- Adds: `audit` (after reviewer, before END)
- Wraps: input, risk_extraction, risk_scoring, explainability, reviewer with guardrail hooks
- Fan-in becomes 6-way: `[news, social, review, financial, press_release, document_processor]`

### Key structural point:
`input_agent` fans out to BOTH `discovery` AND `document_processor` simultaneously. Document processing starts in parallel with search query generation, not after it. This is non-obvious but critical for understanding pipeline latency.

---

## 26. Collection Agent API Dependencies & Data Shapes

| Agent | API | Dependency | Items | Fallback on Missing Key |
|-------|-----|-----------|-------|------------------------|
| `news_agent` | NewsAPI.org `/v2/everything` | `NEWS_API_KEY` | max 5 | Single mock dict |
| `social_agent` | Tavily sync (`TavilyClient`) | `TAVILY_API_KEY` | max 5 | Empty list (silent) |
| `review_agent` | Tavily sync (`TavilyClient`) | `TAVILY_API_KEY` | max 5 | Empty list (silent) |
| `financial_agent` | yfinance + Tavily | `TAVILY_API_KEY` | max 5 | Partial data |

### Data shapes returned:
- **News**: `{"title": str, "description": str, "source": str, "url": str}`
- **Social/Review**: `{"platform": str, "title": str, "snippet": str, "url": str}`
- **Financial**: `{"source": "yfinance", "ticker": str, "metrics": {debtToEquity, currentRatio, operatingMargins, profitMargins, returnOnEquity, totalDebt, totalRevenue, revenueGrowth, ebitda}}`

### Ticker lookup:
`financial_agent` has a 10-company hardcoded ticker map (Apple, Tesla, Microsoft, Google, Alphabet, Amazon, Nvidia, Meta, Facebook, Nike). For unlisted companies, falls back to Yahoo Finance's undocumented search API.

### Query source:
All agents read from `state["search_queries"]` (produced by `discovery_agent`). Key names: `"news"`, `"social"`, `"reviews"`, `"financials"`. Mismatch in key name (e.g., `"review"` vs `"reviews"`) silently falls back to default single-query list.

### Deduplication:
- News: URL-based
- Social/Review: snippet-text-based

---

## 27. FinBERT Enrichment & Entity Resolution Details

### data_cleaning_agent (misleading name — actually FinBERT enrichment):
- Merges all 4 collection outputs + doc text into one list
- Runs `analyze_financial_sentiment()` on each item → `item["finbert_sentiment"]`
- **No actual deduplication or normalization** despite the "cleaning" name
- FinBERT input truncated at **2000 characters** (character-based, not token-based). Pipeline has its own 512-token truncation.
- Items with no extractable text get appended WITHOUT `finbert_sentiment` key — downstream agents must handle missing keys.

### entity_resolution_agent:
- **Mutates `cleaned_data` by filtering** — only items LLM marks `is_relevant: True` survive. This is the ONLY agent that shrinks a state list.
- Uses `with_structured_output(EntityResolutionOutput)` Pydantic model requiring `verifications: List[VerificationResult]`, `primary_name: str`, `discovered_aliases: List[str]`
- **Index-alignment assumption**: `result.verifications[i]` maps to `cleaned_data[i]`. If LLM returns fewer verifications than items, extras are silently dropped. No alignment validation.
- On exception: fallback returns company name as-is with empty aliases.

---

## 28. Industry Inference Algorithm (`social_scraper_mcp/industry.py`)

**Method**: Keyword frequency counting over Tavily search snippets (NOT LLM classification).

1. Run 5 company-profiling queries through Tavily
2. Concatenate all result titles + snippets into one text blob
3. Count keyword hits per industry category (10 categories hardcoded)
4. Industry with most hits wins

**10 industry categories**: energy & utilities, banking & financial services, technology, real estate & property, transport & logistics, consumer & retail, healthcare, telecommunications, industrial & manufacturing, hospitality & travel.

**Confidence formula**: `min(0.95, 0.45 + 0.1 * best_score + 0.05 * max(0, best_score - second_score))`
- Zero hits → confidence 0.2, label "unknown"
- Gap between 1st and 2nd place increases confidence

**Outlook scoring**: 14 positive keywords + 15 negative keywords, each with weight multipliers.
- Strongest negative: "recession" (weight 2.0)
- Strongest positive: "strong demand" (weight 1.8)
- Score: `pos_weight / (pos_weight + neg_weight)`
- Rating thresholds: Positive >= 0.65, Neutral 0.40-0.65, Negative < 0.40

**Known issues**:
- `CURRENT_YEAR = 2026` is hardcoded (not from `datetime.now()`). Queries will be stale in 2027.
- `AsyncTavilyClient` wrapped by `asyncio.run()` — breaks if calling orchestrator is already async.
- Companies in uncovered industries get classified as whichever category has most coincidental keyword matches.

---

## 29. Synthetic Companies Dataset Schema

**30 entries** with this exact field schema:
```json
{
    "company_name": "str",
    "ticker": "str | null",
    "category": "str",
    "expected_risk_range": [min_int, max_int],
    "expected_rating": "str",
    "key_risk_signals": ["str", ...],
    "key_strength_signals": ["str", ...],
    "default_date": "str | null",
    "description": "str"
}
```

**Category breakdown**: `known_default` (8), `distressed_recovered` (6), `healthy_large_cap` (7), `healthy_mid_cap` (5), `ambiguous_mixed` (4).

**Known data quirks**:
- `expected_rating` for AMC and Credit Suisse is `"Medium/High"` (composite string, not one of the standard 3 values)
- `ticker` is `null` for FTX only
- `key_strength_signals` is `[]` for all `known_default` entries

---

## 30. Test Infrastructure (`tests/conftest.py`)

- **`make_state(mock_data, **overrides)`** — factory fixture, NOT pre-built state. Creates AgentState from mock JSON + any overrides. Pre-populates `cleaned_data` as concatenation of all 4 data lists.
- **`guardrail_runner`** — function-scoped fixture (fresh per test, isolated audit log)
- **10 mock fixtures** use exact keys: `apple_inc`, `svb`, `tesla`, `evergrande`, `microsoft`, `credit_suisse`, `grab_holdings`, `wirecard`, `dbs_bank`, `ftx`. Typo in key → `pytest.skip()` (not failure).
- **Dataset fixtures are session-scoped** (loaded once). Mock fixtures and guardrail_runner are function-scoped. Dataset mutations across tests would be a silent bug.
- **`eval_runner.py` CLI**: `python -m tests.eval_runner --mode mock|live --suite all|safety|behavioral --output dir` — not mentioned in Section 8 "How to Run".

---

## 31. Known Contradictions & Risks

| Item | What Docs Say | What Code Does |
|------|-------------|---------------|
| `OPENAI_MODEL` env var | AAFS.env sets it to `gpt-4o-mini` | **Ignored** — `get_llm()` hardcodes `gpt-4o-mini` |
| `requirements.txt` numpy | Bug fix says "pin numpy<2" | requirements.txt has `numpy==2.4.3` — NOT fixed |
| `data_cleaning_agent` name | "Data cleaning" | Actually FinBERT enrichment — no deduplication |
| Collection agent item count | "14+ agents" | Standard graph has 13 nodes, guarded has 18 |
| `mcp` and `anthropic` packages | In requirements.txt | Not used by main app |
| `temperature`/`max_tokens` config | Stored in workflow modes | Never passed to `get_llm()` |
| `reviewer_rounds` slider | UI shows 1-5 rounds | Reviewer agent runs exactly once regardless |

---

## 32. LLM Prompt Templates (Verbatim from Source)

### risk_extraction_agent (analysis_agents.py lines 48-60):
- Role: "objective corporate analyst"
- Key instruction: "Treat `finbert_sentiment` as expert financial sentiment analysis"
- Directive: "Negative finbert_sentiment → risk; Positive → growth/stability"
- Input: `company_name` + full `cleaned_data` as JSON
- Output: `RiskExtractionOutput` (co-extracts both risks AND strengths in single call via `with_structured_output()`)

### risk_scoring_agent (analysis_agents.py lines 92-104):
- Role: "neutral and objective credit analyst"
- Key instruction: "BE NEUTRAL: Use FinBERT sentiment scores as objective anchor points. High confidence positive sentiment should significantly offset risks."
- Input: `extracted_risks` + `extracted_strengths` as JSON
- Output: `RiskScoreOutput` via `with_structured_output()`

### explainability_agent (analysis_agents.py lines 132-145):
- Role: "objective auditor"
- Key instruction: "Generate 2-3 explanations that show BOTH the risks and how they are (or are not) mitigated by strengths"
- Key instruction: "BE BALANCED: Highlight the 'tug-of-war' between positive and negative signals"
- Input: score + risks + strengths
- Output: `ExplainabilityOutput` via `with_structured_output()`

### reviewer_agent (reviewer_agent.py lines 21-37):
- Uses `SystemMessage` + `HumanMessage` pair (NOT `with_structured_output()` — returns free-form Markdown)
- System: "You compile structured data into executive Markdown risk reports."
- Output must have exactly 4 sections: (1) Company + score, (2) Red Flags, (3) Green Flags, (4) Executive Summary
- Only metric logged: character length of generated report

**Architectural distinction**: analysis_agents use `with_structured_output(Pydantic)`. reviewer_agent uses raw `invoke()` for free-form Markdown.

### Fallback behavior (all analysis agents):
All return empty lists/default dicts on exception. Pipeline continues with degraded data — no abort.

---

## 33. Hardcoded Thresholds & Constants

| Constant | File | Value | Purpose |
|----------|------|-------|---------|
| Fuzzy match threshold | hallucination_detector.py | 0.40 | Attribution matching — lower = more permissive |
| Eval fuzzy match threshold | eval/scorer.py | 0.65 | Ground truth signal matching — stricter than runtime |
| Description length limit | output_enforcer.py | 500 chars | Truncates risk/strength descriptions |
| FinBERT confidence floor | output_enforcer.py | 0.30 | Items below this score are filtered out |
| FinBERT text truncation | processing_agents.py | 2000 chars | Character-based (not token-based) |
| Tavily max_results per query | press_release_agent.py | 3 | 5 queries × 3 = 15 max, deduped to 10 |
| Press title truncation | press_release_agent.py | 80 chars | Token budget control |
| Press snippet truncation | press_release_agent.py | 120 chars | Token budget control |
| Max press results for LLM | press_release_agent.py | 8 | Hard cap before LLM call |
| Confidence: High threshold | confidence_agent.py | >= 0.70 | |
| Confidence: Medium threshold | confidence_agent.py | >= 0.40 | |
| Confidence: Low threshold | confidence_agent.py | < 0.40 | |
| High-tier source cutoff | confidence_agent.py | >= 0.80 | credibility_weight threshold for tier 1-2 |
| Export list truncation | ui_export.py | 10 items | Markdown export silently drops items beyond 10 |
| Pipeline version | audit_agent.py | "1.0.0" | Hardcoded in every audit trail |
| Industry hardcoded year | social_scraper_mcp/industry.py | 2026 | NOT from datetime.now() — stale in 2027 |
| Rating ranges | output_enforcer.py | Low=0-33, Med=34-66, High=67-100 | Score is authoritative over LLM rating |

---

## 34. Confidence Calibration Formula (confidence_agent.py)

```
confidence_score = 0.30 * data_coverage
                 + 0.20 * source_diversity
                 + 0.30 * sentiment_agreement
                 + 0.20 * high_tier_ratio

Clamped to [0.0, 1.0]
```

**Component algorithms**:
- `data_coverage`: fraction of 5 fields (`news_data`, `social_data`, `review_data`, `financial_data`, `doc_extracted_text`) that are non-empty
- `source_diversity`: Shannon entropy of `source_type` distribution, normalized by `log2(num_types)`. Returns 0.0 if only 1 source type.
- `sentiment_agreement`: fraction of items matching majority `finbert_label`. Default 0.5 when no data.
- `high_tier_ratio`: fraction of `cleaned_data` items with `credibility_weight >= 0.80`

**Output**: augments `state["risk_score"]` dict with 3 new keys: `confidence_level`, `confidence_score`, `confidence_breakdown`

---

## 35. Hallucination Detector — Attribution Algorithm

### `check_entity_attribution()` (lines 51-101):
1. Extract all string values from `source_data` (nested dict values included)
2. For each risk/strength description, run 3-tier fuzzy matching:
   - **Fast path**: substring containment (`desc in src` or `src in desc`)
   - **Full-text**: `SequenceMatcher.ratio()` against entire source
   - **Sentence-level**: source split on `[.!?]+`, each sentence checked individually
3. Threshold: **0.40** (hardcoded)
4. `attribution_score = grounded_count / (total_risks + total_strengths)`
5. Edge case: returns 1.0 when both lists empty (nothing to hallucinate)

### `flag_fabricated_metrics()` — 3 regex patterns:
- Dollar amounts: `\$[\d,]+\.?\d*`
- Percentages: `-?[\d,]+\.?\d*\s*%`
- Plain numbers: `(?<!\$)(?<!\w)-?[\d,]+\.?\d+(?!\s*%)`

Extracted numbers normalized and checked against known values from `financial_data` (stored in 3 formats: raw, `.1f`, `.2f`).

### `verify_company_in_output()`:
Checks company name AND aliases from `state["company_aliases"]`. If neither appears in report → hallucination warning.

---

## 36. Bias/Fairness — Complete 60-Term Taxonomy

### Demographics (severity: HIGH, 35 terms):
race, racial, ethnicity, ethnic, african american, caucasian, hispanic, latino, latina, asian, white, black, indigenous, native american, gender, male, female, non-binary, transgender, religion, religious, christian, muslim, jewish, hindu, buddhist, sikh, atheist, nationality, national origin, immigrant, citizen, foreigner, alien, refugee

### Geographic Proxy (severity: MEDIUM, 14 terms):
zip code, zipcode, zip-code, postal code, neighborhood, neighbourhood, district, borough, inner city, inner-city, suburb, rural area, urban area, ghetto, barrio

### Personal (severity: LOW, 17 terms):
age, elderly, senior citizen, young adult, marital status, married, divorced, single parent, widowed, separated, family status, pregnant, disability, disabled, handicapped, sexual orientation, gay, lesbian, bisexual

**Enforcement**: MAS FEAT fails only on HIGH severity. MEDIUM/LOW logged but don't fail. EU AI Act fails on ANY term (even LOW) via `no_protected_terms` check.

**Matching**: word-boundary regex (`\b` + `re.escape(term)` + `\b`) — prevents false positives.

---

## 37. Press Release Agent — Complete Event Categories

### CORPORATE_EVENT_CATEGORIES keyword lists:
- `m_and_a`: acquisition, merger, acquired, takeover, divest, sold, purchase
- `workforce`: hiring, layoff, restructuring, headcount, job cuts, expansion, new hires
- `financial_health`: revenue, profit, loss, guidance, earnings, dividend, quarterly results
- `market_position`: market share, partnership, contract, new market, launch, expand
- `leadership`: ceo, appointed, resigned, board, executive, succession, director
- `risk_events`: lawsuit, investigation, recall, breach, sanction, default, fraud

All patterns pre-compiled at module load (regex). Zero LLM tokens for categorization.

### CorporateTrajectory Pydantic schema:
```python
growth_signals: List[str]
contraction_signals: List[str]
trajectory: Literal["expanding", "stable", "contracting", "restructuring"]
key_events: List[str]  # top 3-5
outlook_impact: Literal["positive", "neutral", "negative"]
```

### 5 Tavily query templates:
1. `"{company}" press release newsroom {year}`
2. `"{company}" acquisition merger announcement {year}`
3. `"{company}" restructuring layoffs hiring {year}`
4. `"{company}" earnings quarterly results guidance {year}`
5. `"{company}" partnership expansion new market {year}`

Fallback: if Tavily unavailable, silently uses `state["news_data"]` instead.

---

## 38. Audit Trail — Agent vs Guardrail (Two Different Logs)

**audit_agent output** (`state["audit_trail"]`):
```json
{
  "run_id": "uuid4",
  "timestamp": "ISO 8601 UTC",
  "company": "...",
  "pipeline_version": "1.0.0",
  "agents_executed": ["input_agent", "discovery_agent", ...],
  "data_sources_used": {"news_data": N, "social_data": N, ...},
  "source_tiers_distribution": {"tier1": N, "tier2": N, ...},
  "errors_encountered": [...],
  "compliance": {
    "mas_feat_passed": bool,
    "eu_ai_act_passed": bool,
    "mas_feat_missing": [...],
    "eu_ai_act_missing": [...]
  }
}
```

MAS FEAT requires 5 state fields: `cleaned_data`, `extracted_risks`, `risk_score`, `explanations`, `final_report`.
EU AI Act requires 4 fields (same minus `final_report`).

Agent detection is inference-based: checks if output fields are non-empty. Agent that ran but produced empty output will NOT appear in `agents_executed`.

**guardrail_runner audit log** (separate from above):
```json
{"timestamp": "...", "guardrail_name": "...", "action": "validated", "details": {...}}
```

---

## 39. Output Enforcer — Complete Validation Rules

| Rule | Action | Detail |
|------|--------|--------|
| Risk type not in `["Traditional Risk", "Non-traditional Risk"]` | Corrected to "Traditional Risk" | |
| Strength type not in `["Financial Strength", "Market Strength"]` | Corrected to "Financial Strength" | |
| Description > 500 chars | Truncated | Hard limit |
| Score outside 0-100 | Clamped | `max(0, min(100, score))` |
| `max` field any value | Overwritten to 100 | LLM's value discarded |
| Rating inconsistent with score | Rating corrected from score | Score is authoritative |
| Invalid rating string | Derived from score ranges | Low=0-33, Med=34-66, High=67-100 |
| Zero valid explanations | Placeholder injected | `{"metric": "Overall Assessment", "reason": "Insufficient data..."}` |
| FinBERT score < 0.30 | Item filtered out | `confidence_floor_filter()` |
| Required key missing/None | Returns `False` (hard stop) | `schema_hard_stop()` triggers cascade abort |

---

## 40. Eval Scorer — Ground Truth Algorithm

### `score_against_ground_truth()` weighted formula:
```
overall_score = 0.30 * score_in_range
              + 0.20 * rating_match
              + 0.30 * risk_signal_recall
              + 0.20 * risk_signal_precision
```

**Note**: Strength signals are computed but NOT included in `overall_score`. Only risk signals drive the composite.

### Compound rating handling:
`expected_rating` supports `"Medium/High"` (slash-separated). Check: `actual_rating in expected_parts`.

### `compute_precision_recall()` — greedy bipartite matching:
For each expected signal, find best-matching extracted signal (by SequenceMatcher ratio ≥ 0.65) that hasn't been matched yet. `matched_extracted` set prevents double-counting.

Edge cases:
- Both empty → (1.0, 1.0)
- Extracted only (nothing expected) → precision 0.0, recall 1.0
- Expected only (nothing extracted) → precision 0.0, recall 0.0

---

## 41. Export Section Taxonomy — All 19 Keys

### By Process (7):
`input_validation`, `data_collection`, `data_cleaning`, `risk_extraction`, `risk_scoring`, `explainability`, `final_report`

### By Agent Output (7):
`news_data`, `social_data`, `review_data`, `financial_data`, `press_release`, `xbrl_data`, `industry_context`

### By Risk Factor (5):
`financial_health`, `credit_quality`, `regulatory`, `market_position`, `sentiment`

**Key extraction rules**:
- `xbrl_data`: filters `doc_extracted_text` where `type == "XBRL_STRUCTURED"` only
- `financial_health`: risks where `"financial"` or `"leverage"` in type, explanations where `"financial"` in metric
- `credit_quality`: risks where `"credit"` in type or `"npl"` in description (hardcoded NPL keyword)
- `regulatory`: risks where `"regulatory"` in type or `"mas"` in description (hardcoded MAS keyword)

**Export format details**:
- JSON: sections nested under `"sections"` key. Top-level: `company`, `score`, `rating`, `generated`, `sections`
- CSV: comma-delimited, `---,---` as section separator. Lists show `count=N` only, not items.
- Markdown: lists truncated to **first 10 items** silently
- Score source: `st.session_state["composite_score"]` (analyst-adjusted) takes precedence over `state["risk_score"]["score"]` (raw LLM)
