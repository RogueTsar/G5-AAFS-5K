import sys
import os
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.orchestrator import create_workflow

def test_full_graph_execution():
    """Test the full execution of the LangGraph workflow with a mock company."""
    app = create_workflow()
    
    # Initial state
    initial_state = {"company_name": "Apple"}
    
    # Run the graph
    final_state = app.invoke(initial_state)
    
    # Assertions
    assert "company_info" in final_state
    assert final_state["company_info"]["name"] == "Apple"
    
    # Check that parallel data collection appended properly
    assert len(final_state.get("news_data", [])) > 0
    assert len(final_state.get("social_data", [])) > 0
    assert len(final_state.get("financial_data", [])) > 0
    assert len(final_state.get("review_data", [])) > 0
    
    # Check that processing cleaned and resolved entities
    assert len(final_state.get("cleaned_data", [])) > 0
    assert "resolved_entities" in final_state
    
    # Check risk scoring and report formatting
    assert "extracted_risks" in final_state
    assert "risk_score" in final_state
    assert "final_report" in final_state
    
    # Assert specific text from the final report format requirement
    report = final_state["final_report"]
    assert "Apple" in report
    
    # Just assert the report was successfully generated and is a decent length
    assert len(report) > 50

if __name__ == "__main__":
    test_full_graph_execution()
    print("Graph execution test passed successfully!")
