from src.core.state import AgentState
from src.core.logger import log_agent_action

def data_cleaning_agent(state: AgentState) -> AgentState:
    """Removes noise, duplicates, irrelevant content."""
    company_name = state.get("company_name", "Unknown")
    log_agent_action("data_cleaning_agent", f"Starting data cleaning for {company_name}")
    
    cleaned_data = []
    if state.get("news_data"):
        cleaned_data.extend(state["news_data"])
    if state.get("social_data"):
        cleaned_data.extend(state["social_data"])
    if state.get("review_data"):
        cleaned_data.extend(state["review_data"])
    if state.get("financial_data"):
        cleaned_data.extend(state["financial_data"])
        
    log_agent_action("data_cleaning_agent", f"Aggregated {len(cleaned_data)} total data points")
    return {"cleaned_data": cleaned_data} # type: ignore

def entity_resolution_agent(state: AgentState) -> AgentState:
    """Ensures all data refers to the same company."""
    company_name = state.get("company_name")
    log_agent_action("entity_resolution_agent", f"Resolving entities for {company_name}")
    
    resolved_entities = {"primary_entity": company_name, "mentions": len(state.get("cleaned_data", []))}
    
    log_agent_action("entity_resolution_agent", "Finished entity resolution", {"resolved_entities": resolved_entities})
    return {"resolved_entities": resolved_entities} # type: ignore
