from langgraph.graph import StateGraph, START, END
from src.core.state import AgentState
from src.agents.input_agent import input_agent
from src.agents.discovery_agent import discovery_agent
from src.agents.collection_agents import news_agent, social_agent, review_agent, financial_agent
from src.agents.document_processing_agent import document_processing_agent
from src.agents.document_metrics_agent import document_metrics_agent
from src.agents.processing_agents import data_cleaning_agent, entity_resolution_agent
from src.agents.analysis_agents import risk_extraction_agent, risk_scoring_agent, explainability_agent
from src.agents.reviewer_agent import reviewer_agent

def create_workflow():
    """Creates and compiles the LangGraph standard workflow."""
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("input", input_agent)
    workflow.add_node("discovery", discovery_agent)
    
    # Parallel collection nodes
    workflow.add_node("news", news_agent)
    workflow.add_node("social", social_agent)
    workflow.add_node("review", review_agent)
    workflow.add_node("financial", financial_agent)
    workflow.add_node("document_processor", document_processing_agent)
    workflow.add_node("document_metrics", document_metrics_agent)
    
    # Processing and Analysis nodes
    workflow.add_node("data_cleaning", data_cleaning_agent)
    workflow.add_node("entity_resolution", entity_resolution_agent)
    workflow.add_node("risk_extraction", risk_extraction_agent)
    workflow.add_node("risk_scoring", risk_scoring_agent)
    workflow.add_node("explainability", explainability_agent)
    workflow.add_node("reviewer", reviewer_agent)
    
    # Define Edges (Routing)
    workflow.add_edge(START, "input")
    workflow.add_edge("input", "discovery")
    workflow.add_edge("input", "document_processor")
    workflow.add_edge("document_processor", "document_metrics")
    
    # Fan-out
    workflow.add_edge("discovery", "news")
    workflow.add_edge("discovery", "social")
    workflow.add_edge("discovery", "review")
    workflow.add_edge("discovery", "financial")
    
    # Fan-in
    workflow.add_edge(["news", "social", "review", "financial", "document_metrics"], "data_cleaning")
    
    # Sequential processing
    workflow.add_edge("data_cleaning", "entity_resolution")
    workflow.add_edge("entity_resolution", "risk_extraction")
    workflow.add_edge("risk_extraction", "risk_scoring")
    workflow.add_edge("risk_scoring", "explainability")
    workflow.add_edge("explainability", "reviewer")
    workflow.add_edge("reviewer", END)
    
    # Compile the graph
    app = workflow.compile()
    return app
