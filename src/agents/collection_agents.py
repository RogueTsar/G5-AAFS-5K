from typing import Dict, Any, List
from src.core.state import AgentState
from src.mcp_tools.news_api import search_company_news
from src.mcp_tools.financial_lookup import get_financial_metrics, find_ticker
from src.mcp_tools.sentiment_tool import get_sentiment_snippets
from src.core.logger import log_agent_action

def news_agent(state: AgentState) -> Dict[str, Any]:
    """Retrieves news articles and press releases using dynamic queries."""
    company_name = state.get("company_name", "")
    queries = state.get("search_queries", {}).get("news", [company_name])
    
    log_agent_action("news_agent", f"Fetching news using {len(queries)} dynamic queries")
    
    all_news = []
    seen_urls = set()
    
    for q in queries:
        if len(all_news) >= 5: break
        articles = search_company_news(q)
        for art in articles:
            if art.get("url") not in seen_urls:
                all_news.append(art)
                seen_urls.add(art.get("url"))
            if len(all_news) >= 5: break
    
    log_agent_action("news_agent", f"Found {len(all_news)} unique articles")
    return {"news_data": all_news[:5]}

def social_agent(state: AgentState) -> Dict[str, Any]:
    """Monitors public sentiment using dynamic queries across social platforms."""
    company_name = state.get("company_name", "")
    queries = state.get("search_queries", {}).get("social", [f"{company_name} sentiment"])
    
    log_agent_action("social_agent", f"Monitoring social using {len(queries)} dynamic queries")
    
    all_social = []
    seen_snippets = set()
    
    for q in queries:
        if len(all_social) >= 5: break
        # We pass the query directly to the tool now
        snippets = get_sentiment_snippets(q, platform="social media")
        for s in snippets:
            if s.get("snippet") not in seen_snippets:
                all_social.append(s)
                seen_snippets.add(s.get("snippet"))
            if len(all_social) >= 5: break
    
    log_agent_action("social_agent", f"Found {len(all_social)} unique social mentions")
    return {"social_data": all_social[:5]}

def review_agent(state: AgentState) -> Dict[str, Any]:
    """Collects employee/customer reviews using dynamic queries."""
    company_name = state.get("company_name", "")
    queries = state.get("search_queries", {}).get("reviews", [f"{company_name} reviews"])
    
    log_agent_action("review_agent", f"Collecting reviews using {len(queries)} dynamic queries")
    
    all_reviews = []
    seen_snippets = set()
    
    for q in queries:
        if len(all_reviews) >= 5: break
        snippets = get_sentiment_snippets(q, platform="reviews")
        for s in snippets:
            if s.get("snippet") not in seen_snippets:
                all_reviews.append(s)
                seen_snippets.add(s.get("snippet"))
            if len(all_reviews) >= 5: break
    
    log_agent_action("review_agent", f"Found {len(all_reviews)} unique review snippets")
    return {"review_data": all_reviews[:5]}

def financial_agent(state: AgentState) -> Dict[str, Any]:
    """Analyzes financial statements and supplements with dynamic web searches."""
    company_name = state.get("company_name", "")
    queries = state.get("search_queries", {}).get("financials", [f"{company_name} financials"])
    
    log_agent_action("financial_agent", f"Analyzing financials for {company_name}")
    
    # 1. Traditional Ticker Lookup
    ticker = find_ticker(company_name)
    financial_metrics = []
    
    if ticker:
        log_agent_action("financial_agent", f"Resolved ticker to {ticker}")
        metrics = get_financial_metrics(ticker)
        if metrics:
            financial_metrics.append({"source": "yfinance", "ticker": ticker, "metrics": metrics})
            
    # 2. Supplemental Web Search for Financial Context
    financial_news = []
    for q in queries:
        if len(financial_news) >= 5: break
        snippets = get_sentiment_snippets(q, platform="financial news")
        for s in snippets:
            financial_news.append({"source": "web_search", "content": s})
            if len(financial_news) >= 5: break
            
    log_agent_action("financial_agent", f"Gathered {len(financial_metrics)} metrics and {len(financial_news)} news points")
    return {
        "financial_data": financial_metrics,
        "financial_news_data": financial_news
    }
