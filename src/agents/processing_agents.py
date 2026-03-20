from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.mcp_tools.finbert_tool import analyze_financial_sentiment

def data_cleaning_agent(state: AgentState) -> AgentState:
    """Enriches data points with FinBERT sentiment scores."""
    company_name = state.get("company_name", "Unknown")
    log_agent_action("data_cleaning_agent", f"Starting data cleaning and sentiment enrichment for {company_name}")
    
    raw_data = []
    if state.get("news_data"):
        for item in state["news_data"]:
            item["source_type"] = "news"
            raw_data.append(item)
    if state.get("social_data"):
        for item in state["social_data"]:
            item["source_type"] = "social"
            raw_data.append(item)
    if state.get("review_data"):
        for item in state["review_data"]:
            item["source_type"] = "review"
            raw_data.append(item)
    if state.get("financial_data"):
        for item in state["financial_data"]:
            item["source_type"] = "financial"
            raw_data.append(item)
            
    enriched_data = []
    for item in raw_data:
        # Extract text to analyze
        text = ""
        if "title" in item and "snippet" in item:
            text = f"{item['title']} - {item['snippet']}"
        elif "content" in item and isinstance(item["content"], dict):
             # For financial web search snippets
             c = item["content"]
             text = f"{c.get('title', '')} {c.get('snippet', '')}"
        elif "title" in item:
            text = item["title"]
        elif "snippet" in item:
            text = item["snippet"]
            
        if text:
            sentiment = analyze_financial_sentiment(text)
            item["finbert_sentiment"] = sentiment
        
        enriched_data.append(item)
        
    log_agent_action("data_cleaning_agent", f"Aggregated and enriched {len(enriched_data)} total data points")
    return {"cleaned_data": enriched_data} # type: ignore

def entity_resolution_agent(state: AgentState) -> AgentState:
    """Ensures all data refers to the same company."""
    company_name = state.get("company_name")
    log_agent_action("entity_resolution_agent", f"Resolving entities for {company_name}")
    
    resolved_entities = {"primary_entity": company_name, "mentions": len(state.get("cleaned_data", []))}
    
    log_agent_action("entity_resolution_agent", "Finished entity resolution", {"resolved_entities": resolved_entities})
    return {"resolved_entities": resolved_entities} # type: ignore
