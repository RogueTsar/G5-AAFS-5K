from typing import TypedDict, Annotated, List, Dict, Any
import operator

class AgentState(TypedDict):
    """
    State representing the data passed between agents in the LangGraph workflow.
    """
    company_name: str
    company_info: Dict[str, Any]  # Validated details
    
    # Raw data collection (Annotated with operator.add to accumulate parallel outputs)
    news_data: Annotated[List[Dict[str, Any]], operator.add]
    social_data: Annotated[List[Dict[str, Any]], operator.add]
    review_data: Annotated[List[Dict[str, Any]], operator.add]
    financial_data: Annotated[List[Dict[str, Any]], operator.add]
    
    # Processed data
    cleaned_data: List[Dict[str, Any]]
    resolved_entities: Dict[str, Any]
    
    # Analysis results
    extracted_risks: List[Dict[str, Any]]
    extracted_strengths: List[Dict[str, Any]]
    risk_score: Dict[str, Any]
    explanations: List[Dict[str, Any]]
    
    # Final Output
    final_report: str
    errors: Annotated[List[str], operator.add]
