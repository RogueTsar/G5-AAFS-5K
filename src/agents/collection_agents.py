from typing import Dict, Any
from src.core.state import AgentState
from src.mcp_tools.news_api import search_company_news
from src.mcp_tools.financial_lookup import get_financial_metrics, find_ticker
from src.core.logger import log_agent_action

def news_agent(state: AgentState) -> Dict[str, Any]:
    """Retrieves news articles and press releases."""
    company_name = state.get("company_name", "")
    log_agent_action("news_agent", f"Fetching news for {company_name}")
    
    # Fetch real news
    news_articles = search_company_news(company_name)
    
    log_agent_action("news_agent", f"Found {len(news_articles)} articles", {"news_data": news_articles})
    return {"news_data": news_articles}

def social_agent(state: AgentState) -> Dict[str, Any]:
    """Monitors public sentiment and mentions."""
    company_name = state.get("company_name", "")
    log_agent_action("social_agent", f"Monitoring social sentiment for {company_name}")
    
    mock_social = [{"platform": "X", "content": "Social media complaints rising regarding " + company_name}]
    
    log_agent_action("social_agent", "Finished social gathering (mocked)", {"social_data": mock_social})
    return {"social_data": mock_social}

def review_agent(state: AgentState) -> Dict[str, Any]:
    """Collects employee/customer reviews."""
    company_name = state.get("company_name", "")
    log_agent_action("review_agent", f"Collecting reviews for {company_name}")
    
    mock_reviews = [{"platform": "Glassdoor", "content": "Negative employee sentiment on Glassdoor regarding " + company_name}]
    
    log_agent_action("review_agent", "Finished review gathering (mocked)", {"review_data": mock_reviews})
    return {"review_data": mock_reviews}

def financial_agent(state: AgentState) -> Dict[str, Any]:
    """Analyzes financial statements and filings."""
    company_name = state.get("company_name", "")
    log_agent_action("financial_agent", f"Analyzing financials for {company_name}")
    
    # Try to find a ticker for the company
    ticker = find_ticker(company_name)
    financial_data = []
    
    if ticker:
        log_agent_action("financial_agent", f"Resolved ticker to {ticker}")
        metrics = get_financial_metrics(ticker)
        if metrics:
            financial_data.append({"ticker": ticker, "metrics": metrics})
        else:
            financial_data.append({"error": f"Could not retrieve metrics for ticker {ticker}"})
    else:
        financial_data.append({"error": f"Could not find a stock ticker for {company_name}"})
        
    log_agent_action("financial_agent", "Finished financial gathering", {"financial_data": financial_data})
    return {"financial_data": financial_data}
