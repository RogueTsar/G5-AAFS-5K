# G5-AAFS: Automated Anomaly & Financial Screening

Comprehensive risk analysis system for companies using MCP agents, RAG retrieval, and automated data collection.

## 🎯 System Architecture

```
User Input (Company Name)
   ↓
Input Agent
   ↓
Source Discovery Agent
   ↓
Parallel Data Collection Agents
   ├ News Agent
   ├ Social Media Agent
   ├ Review Agent
   └ Financial Filings Agent
   ↓
MCP Tool Layer
   ├ News API
   ├ Social Scraper
   ├ Review Scraper
   └ Legal Lookup
   ↓
Raw Data Storage
   ↓
Embeddings + Vector DB
   ↓
RAG Retrieval
   ↓
Risk Extraction Agent
   ↓
Risk Scoring Agent
   ↓
Reviewer Agent
   ↓
Final Risk Report
```

## 📁 Project Structure

```
G5-AAFS-5K/
│
├── app.py                # Entry point (orchestrates full pipeline)
├── config.py               # API keys, model configs, env variables
│
├── data_collection/
│   ├── news/
│   │   └── news_collector.py
│   ├── social/
│   │   └── social_collector.py
│   ├── forums/
│   │   └── forum_collector.py
│   ├── filings/
│   │   └── filings_collector.py
│   └── __init__.py
│
├── tools/                      # MCP Tool Layer
│   ├── news_search_tool.py
│   ├── social_scraper.py
│   ├── forum_scraper.py
│   ├── legal_lookup_tool.py
│   ├── review_scraper.py
│   ├── finbert_tool.py
│   └── __init__.py
│
├── agents/
│   ├── news_agent.py
│   ├── social_media_agent.py
│   ├── forum_agent.py
│   ├── filings_agent.py
│   ├── reviewer_agent.py
│   └── __init__.py
│
├── guardrails/
│   ├── validation.py           # sanity checks, hallucination detection
│   ├── compliance.py           # regulatory filtering
│   └── __init__.py
│
├── models/
│   ├── llama_interface.py      # LLaMA 3.1 interaction (inference / finetuned)
│   ├── prompts.py              # prompt templates
│   └── __init__.py
│
├── pipeline/
│   ├── orchestrator.py         # connects all layers together
│   └── state_manager.py        # handles intermediate data
│
├── utils/
│   ├── text_cleaning.py
│   ├── scoring.py              # weighting / risk scoring logic
│   └── logger.py
│
├── outputs/
│   ├── reports/
│   └── logs/
│
└── README.md

## 🚀 Quick Start

### 1. Activate Virtual Environment

```powershell
# Windows PowerShell
.\project_venv\Scripts\Activate.ps1

# Or directly with Python
.\project_venv\Scripts\python
```

### 2. Run the Streamlit App

```bash
.\project_venv\Scripts\python -m streamlit run app.py
```

The app will open at `http://localhost:8501`

### 3. Enter Company Name

- Type a company name (e.g., "Apple Inc.", "Tesla", "Microsoft")
- Click "Start Analysis"
- Monitor the analysis pipeline in real-time

## 📦 Installed Packages

- **streamlit** (1.55.0) - Web UI framework
- **pydantic** (2.12.5) - Data validation
- **mcp** (1.26.0) - Model Context Protocol for agent tools
- **anthropic** (0.84.0) - Claude API for agents
- **pandas** (2.3.3) - Data manipulation
- **numpy** (2.4.3) - Numerical computing

## 🔧 Configuration

### API Keys
Add your API keys in the sidebar Settings section:
- News API Key
- Financial Data API Key
- (Additional keys as needed)

### Custom Settings
Edit `config/settings.py` for:
- Data collection parameters
- Risk scoring thresholds
- Report formatting options

## 📊 Features

- ✅ Company name input UI
- ✅ Pipeline visualization
- ✅ Multi-stage analysis workflow
- ✅ Parallel data collection
- ✅ Real-time progress tracking
- 🔄 Risk extraction & scoring (in development)
- 🔄 RAG-based retrieval (in development)
- 🔄 Automated report generation (in development)

## 🤖 Agents Overview

| Agent | Purpose |
|-------|---------|
| **Input Agent** | Validate and parse company information |
| **Source Discovery** | Identify relevant data sources |
| **News Agent** | Collect company news and press releases |
| **Social Media Agent** | Monitor social sentiment and mentions |
| **Review Agent** | Gather customer/employee reviews |
| **Financial Agent** | Analyze SEC filings and financial reports |
| **Risk Extraction** | Identify risk factors from raw data |
| **Risk Scoring** | Calculate risk metrics and ratings |
| **Reviewer Agent** | Validate and review results |

## 🛠️ Development

### Install Development Dependencies

```bash
.\project_venv\Scripts\python -m pip install pytest black flake8
```

### Run Tests

```bash
.\project_venv\Scripts\python -m pytest tests/
```

### Code Formatting

```bash
.\project_venv\Scripts\python -m black src/
```

## 📝 Next Steps

- [ ] Implement input validation agent
- [ ] Set up source discovery agent
- [ ] Integrate news data collection
- [ ] Add social media scraping
- [ ] Implement review aggregation
- [ ] Connect to financial APIs
- [ ] Build embeddings pipeline
- [ ] Set up vector database
- [ ] Implement RAG retriever
- [ ] Create risk extraction logic
- [ ] Add risk scoring algorithm
- [ ] Build report generator
- [ ] Add progress tracking UI
- [ ] Implement error handling
- [ ] Add logging and monitoring

## 📄 License

Internal Use Only
