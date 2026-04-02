import pytest
from unittest.mock import patch

from src.agents.updated_input_agent import input_agent
from src.agents.updated_source_agent import source_discovery_agent


@pytest.mark.asyncio
async def test_input_to_source_integration_valid():
    """
    Simulates the LangGraph step where the output of input_agent 
    is passed directly as the state to source_discovery_agent.
    """
    # 1. Define initial user input state
    initial_state = {"input": "Apple Inc"}
    
    # 2. Execute input_agent
    input_result = input_agent(initial_state)
    
    # Verify input agent populated the expected upstream fields
    assert "entity_input" in input_result
    assert input_result["source_query"] == "Apple Inc"
    assert input_result["source_entity_type"] == "company"
    assert len(input_result["errors"]) == 0
    
    # 3. Execute source_discovery_agent with the state from input_agent.
    # We patch the external API calls (Tavily/OpenAI) to avoid real network requests in unit tests.
    with patch("src.agents.updated_source_agent.run_queries") as mock_run_queries, \
         patch("src.agents.updated_source_agent.choose_sources_with_llm") as mock_choose_sources:
        
        # Fake search candidates
        mock_run_queries.return_value = [
            {"title": "Tesla", "url": "https://www.tesla.com", "snippet": "Electric cars"}
        ]
        
        # Fake LLM source selection
        mock_choose_sources.return_value = (
            [{"source": "tesla.com", "tier": 1, "score": 0.99, "allowed_for_scoring": True, "reason": "Official site"}],
            False # insufficient_source_confidence
        )
        
        # Run agent
        source_result = await source_discovery_agent(input_result)
        
        # 4. Verify source agent correctly consumed and enriched the state
        assert source_result["source_query"] == "Apple Inc"
        assert source_result["source_entity_type"] == "company"
        assert len(source_result["source_candidates"]) == 1
        assert len(source_result["selected_sources"]) == 1
        assert source_result["insufficient_source_confidence"] is False
        assert len(source_result["errors"]) == 0


@pytest.mark.asyncio
async def test_input_to_source_integration_invalid():
    """
    Tests that if the input_agent flags the input as unsafe/invalid, 
    the source_discovery_agent safely bails out without executing searches.
    """
    # 1. Define a malicious/invalid input state
    initial_state = {"input": "DROP TABLE users; --"}
    
    # 2. Execute input_agent
    input_result = input_agent(initial_state)
    
    # Verify input agent rejected it
    assert input_result["entity_input"]["is_valid"] is False
    
    # 3. Pass to source_discovery_agent
    # No patching required because the agent should return early due to upstream errors.
    source_result = await source_discovery_agent(input_result)
    
    # 4. Verify source agent gracefully cascaded the failure
    assert source_result["source_candidates"] == []
    assert source_result["selected_sources"] == []
    assert source_result["insufficient_source_confidence"] is True
    assert len(source_result["errors"]) > 0
    assert "Input agent marked the input as invalid" in source_result["errors"][0] or len(input_result["errors"]) > 0
