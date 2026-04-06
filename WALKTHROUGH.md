# G5-AAFS Feature Walkthrough — Complete Guide

## How to Launch

```bash
cd /path/to/G5-AAFS-5K
pip install -r requirements.txt

# Create AAFS.env with your API keys
cat > AAFS.env << 'EOF'
OPENAI_API_KEY=sk-proj-your-key
NEWS_API_KEY=your-newsapi-key
OPENAI_MODEL=gpt-4o-mini
TAVILY_API_KEY=tvly-dev-your-key
EOF

# Launch
streamlit run app.py
# Opens at http://localhost:8501
```

---

## Workflow 1: Quick Screen (New Client Call Prep)

**Scenario**: RM has a meeting with a new prospect in 30 minutes. Needs a quick risk snapshot.

### Steps:
1. **Sidebar** → Select **Quick Screen (New Client)** under Workflow
2. **Sidebar** → Model stays at `gpt-4o-mini` (fast, cheap)
3. **Sidebar** → Reviewer rounds: 1
4. **Sidebar** → Only News, Financial, XBRL agents checked (Social/Press unchecked)
5. **Main area** → Type company name (e.g. "DBS Group")
6. **Click** → "Collect & Analyse"
7. **Wait** → Pipeline runs (~30s). Status bar shows progress.
8. **HITL Gate** → Click "Approve & Continue" (or check "Auto-run" in sidebar to skip)
9. **Dashboard tab** → See scenario briefing card + collection summary
10. **Credit Assessment tab** → Review Financial Statements + News tabs
11. **Choose preset** → Click "Basel IRB" for conservative weights
12. **HITL Gate** → Click "Generate Score"
13. **Result** → Score, rating, risk/strength signals, rationale by severity
14. **Export** → Go to "Export & Email" tab → Download JSON or Markdown

**Time**: ~2 minutes | **Cost**: ~$0.005

---

## Workflow 2: Full Assessment (Annual Credit Review)

**Scenario**: Annual review for established client. Credit committee needs comprehensive package.

### Steps:
1. **Sidebar** → Select **Full Assessment (Annual Review)**
2. **Sidebar** → Model: `gpt-4o` (stronger reasoning)
3. **Sidebar** → Reviewer rounds: 3
4. **Sidebar** → All 6 agents checked
5. **Upload XBRL** → Drag the company's ACRA BizFinx filing (.xbrl or .xml)
6. **XBRL Preview** → See parsed company name + section count immediately
7. **Type company name** → Must match the XBRL filing entity
8. **Click** → "Collect & Analyse"
9. **Wait** → Full pipeline (~45s). All agents run in parallel.
10. **HITL Gate** → "Approve & Continue"
11. **Dashboard tab** → Review all 4 panels:
    - Collection Agents: item counts per agent
    - Analysis & Scoring: risk/strength counts
    - Guardrails & Safety: compliance badges
    - Data Quality: source coverage chart
12. **Credit Assessment tab** → Review ALL 6 domain tabs:
    - Financial Statements: balance sheet, P&L, ratios from XBRL
    - Credit Quality: MAS 5-grade classification (Pass/Special Mention/Substandard/Doubtful/Loss)
    - Companies Act: going concern, directors assessment
    - News & Press: sentiment analysis + corporate events
    - Social & Reviews: employee/customer sentiment
    - Industry & Market: sector outlook
13. **Set weights** → Choose preset OR manually adjust 6 sliders
14. **Generate Score** → See composite with per-domain sub-scores and methodology attribution
15. **Review rationale** → Expand each risk category (sorted by severity)
16. **Pipeline Trace tab** → Verify agent-by-agent what happened at each step
17. **AI Governance tab** → Check IMDA AI Verify, MAS FEAT, EU AI Act compliance
18. **Export & Email tab** → Select sections to include → Choose format → Download
19. **Email** → Fill recipient, subject auto-populated → Click "Open in Email Client"
20. **History** → Assessment auto-saved. Run again with different weights to compare.

**Time**: ~5 minutes | **Cost**: ~$0.03

---

## Workflow 3: Loan Simulation (Facility What-If)

**Scenario**: Client requesting a $50M loan. Committee needs impact analysis.

### Steps:
1. **Run Full Assessment first** (Workflow 2 above) — need baseline data
2. **Sidebar** → Switch to **Loan Simulation (What-If)**
3. **Loan Simulation tab** → Enter loan amount: $50,000,000
4. **Set interest rate** → Slider to assumed rate (e.g. 5%)
5. **See impact table**:
   - Debt/Equity ratio: before vs after
   - Current Ratio: before vs after
   - Interest Coverage: before vs after
   - New annual interest cost
   - Total liabilities change
6. **See score shift** → Original score vs simulated score with delta
7. **Risk gauge** → Visual bar showing new risk level
8. **Decision** → If score stays below threshold, recommend approval

**Time**: ~30 seconds (no re-run needed) | **Cost**: $0

---

## Feature: Run History & Comparison

### Save an assessment:
- Assessments auto-save after scoring (in Credit Assessment tab)
- History count shown in top ribbon

### Compare two runs:
1. Go to **History & Compare** tab
2. See table of all saved runs (company, score, rating, mode, model)
3. Filter by company name using search box
4. Click any run to expand full details
5. **Comparison tool** below:
   - Select Assessment A and Assessment B from dropdowns
   - See side-by-side: score delta, weight diff, risk signal diff, config diff
   - Green = improvement (lower risk), Red = deterioration

### Use case: "How did changing weights affect the score?"
1. Run company with Basel IRB weights → save
2. Run same company with MAS FEAT weights → save
3. Compare the two → see exactly which domain weight changes drove the score difference

---

## Feature: Selective Export

1. Go to **Export & Email** tab
2. **Choose grouping**: By Process / By Agent Output / By Risk Factor
3. **Check/uncheck sections** to include:
   - By Process: Input Validation, Data Collection, Cleaning, Risk Extraction, Scoring, Explainability, Report
   - By Agent: News, Social, Reviews, Financial, Press, XBRL, Industry
   - By Risk Factor: Financial Health, Credit Quality, Regulatory, Market Position, Sentiment
4. **Select All / Deselect All** buttons
5. **Choose format**: Markdown, JSON, or CSV
6. **Preview** → Expand to see what the export will look like
7. **Download** → Click download button

---

## Feature: Guardrails Testing (In-App)

1. Go to **Testing** tab
2. **Guardrail Config section**:
   - 6 checkboxes to toggle guardrails (Input, Output, Hallucination, Bias, Cascade, Content)
   - Click "Run All Guardrails (pytest)" → runs 74 guardrail tests in-app
   - Click "Run Live Check" → runs guardrails on current assessment data
   - See flagged warnings with severity
3. **Eval Suite section**:
   - 6 checkboxes with descriptions:
     - Behavioral Tests (pytest, ~2s)
     - Safety Evals (pytest, ~3s)
     - Synthetic Companies (30 companies, ~5s)
     - Distress Backtest (10 historical defaults, ~3s)
     - Project Moonshot (IMDA gov toolkit)
     - LLM-as-Judge (~$0.01/run)
   - Click "Run Selected Evals" → runs only checked suites
   - See pass/fail counts per suite

---

## Feature: Explainer Agent (Reasoning Quality Check)

1. Go to **Pipeline Trace** tab
2. Scroll to bottom → "Explain Agent Output" section
3. **Paste any agent output text** into the text area
4. Click **"Analyze Reasoning"**
5. LLM analyzes for:
   - Logical errors (flawed reasoning, non-sequiturs)
   - Oversimplification (imprecise language)
   - Epistemic errors (false confidence)
   - Factual concerns (unverifiable claims)
   - Missing context (important factors not considered)
6. Each issue shows: category, severity (HIGH/MEDIUM/LOW), original text, correction
7. **Cost**: ~$0.002 per analysis

---

## Feature: Pipeline Trace (Agent Traceability)

1. Go to **Pipeline Trace** tab
2. See **progress bar** (X/8 stages completed)
3. **8 expandable steps**:
   - Step 1: Input Validation — company name, entity type, docs uploaded
   - Step 2: Source Discovery — search queries generated
   - Step 3: Data Collection — item counts per agent, sentiment overview
   - Step 4: Data Cleaning — cleaned records, source credibility
   - Step 5: Risk Extraction — risk signals + strength signals with type distribution chart
   - Step 6: Risk Scoring — score, rating, confidence, methodology
   - Step 7: Explainability — per-factor reasoning cards
   - Step 8: Final Report — compliance badges, guardrail warnings, report preview, audit trail
4. Each step shows **what the agent produced** with visual diagnostics

---

## Feature: AI Governance Compliance

1. Go to **AI Governance** tab
2. **IMDA AI Verify** — 7 principles with pass/fail badges:
   - Transparency, Fairness, Safety, Accountability, Human Agency, Data Governance, Inclusiveness
3. **Project Moonshot** — Red-teaming results:
   - Prompt Injection: 15 tested, 15 blocked
   - Entity Spoofing: 10 tested, 10 blocked
   - Hallucination Detection, Output Schema, Cascade Prevention
4. **MAS FEAT** — 4 principles with descriptions
5. **EU AI Act** — 7 high-risk AI requirements

---

## Feature: Scoring Weight Presets

In the **Credit Assessment** tab, after reviewing data:

| Preset | Best For | FSH | CCA | News | Press | Social | Reviews |
|--------|----------|-----|-----|------|-------|--------|---------|
| **Basel IRB** | Regulatory capital | 40% | 20% | 15% | 10% | 5% | 10% |
| **Altman Z-Score** | Distress screening | 60% | 15% | 10% | 5% | 5% | 5% |
| **S&P Global** | Corporate rating | 30% | 10% | 15% | 15% | 10% | 20% |
| **Moody's KMV** | Market-implied risk | 35% | 10% | 25% | 15% | 10% | 5% |
| **MAS FEAT** | SG regulatory | 25% | 15% | 20% | 15% | 10% | 15% |

Click any preset → sliders auto-adjust → see normalized weights table.

---

## Feature: Auto-Run (Skip HITL Gates)

For batch processing or when you trust the pipeline:

1. **Sidebar** → Check **"Auto-run (skip review gates)"**
2. Enter company name → Click "Collect & Analyse"
3. Pipeline runs → skips both HITL gates → goes straight to scoring and report
4. All tabs populate automatically
5. Assessment auto-saves to history

---

## Feature: Font Scaling

- **Top bar** → Click `A-` to decrease, `A+` to increase (12px to 22px)
- All text scales proportionally via CSS rem units
- Layout never breaks at any size

---

## Sidebar Controls Reference

| Control | What It Does |
|---------|-------------|
| **Workflow** | Quick Screen / Full Assessment / Loan Simulation |
| **Model** | gpt-4o-mini (fast) / gpt-4o (stronger) / gpt-4-turbo / claude-sonnet-4-5 |
| **Rounds** | How many times reviewer critiques the report (1-5) |
| **Auto-run** | Skip HITL approval gates |
| **Agent checkboxes** | Toggle News / Social / Reviews / Financial / Press / XBRL |
| **Reset** | Clear current assessment, start fresh |
| **Re-run** | Re-run pipeline with current settings |

---

## Tab Reference

| Tab | What | When to Use |
|-----|------|-------------|
| **Dashboard** | Scenario briefing + 4 metric panels | Quick overview |
| **Credit Assessment** | 6 domain tabs + weight sliders + scoring | Main workflow |
| **Pipeline Trace** | 8-step agent trace + explainer | Audit trail |
| **Loan Simulation** | What-if loan calculator | Facility requests |
| **AI Governance** | IMDA / MAS / EU compliance | Regulatory review |
| **History & Compare** | Saved runs + side-by-side diff | Compare configs |
| **Export & Email** | Selective export + email composer | Final deliverable |
| **Testing** | Guardrail + eval run buttons | Quality assurance |
| **User Guide** | Workflows, settings, scoring, roles | Onboarding |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| App won't start | `pip install -r requirements.txt` then `streamlit run app.py` |
| "No module named X" | `pip install X` or check requirements.txt |
| XBRL upload crashes | Make sure file is `.xbrl` or `.xml`, not `.xsd` |
| Pipeline fails | Check AAFS.env has valid API keys |
| Slow first run | FinBERT downloads ~500MB model on first use |
| Port 8501 busy | `lsof -ti :8501 | xargs kill -9` |
| Font overlaps | Click `A-` in topbar to reduce font size |
| numpy error | `pip install "numpy<2"` |
