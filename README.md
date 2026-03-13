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
├── app.py                 # Main Streamlit UI application
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── project_venv/          # Python virtual environment
├── src/
│   ├── agents/           # Agent implementations
│   │   ├── input_agent.py
│   │   ├── discovery_agent.py
│   │   ├── news_agent.py
│   │   ├── social_agent.py
│   │   ├── review_agent.py
│   │   ├── financial_agent.py
│   │   ├── risk_extraction_agent.py
│   │   ├── risk_scoring_agent.py
│   │   └── reviewer_agent.py
│   ├── mcp_tools/        # MCP tool integrations
│   │   ├── news_api.py
│   │   ├── social_scraper.py
│   │   ├── review_scraper.py
│   │   └── financial_lookup.py
│   ├── storage/          # Data storage
│   │   ├── vector_db.py
│   │   └── raw_data_store.py
│   ├── embeddings/       # Embedding generation
│   │   └── embedder.py
│   ├── rag/              # RAG retrieval
│   │   └── retriever.py
│   └── reporter/         # Report generation
│       └── report_generator.py
├── tests/                # Unit tests
└── config/               # Configuration files
    └── settings.py
```

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