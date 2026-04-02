from src.core.state import AgentState
from src.core.logger import log_agent_action

def input_agent(state: AgentState) -> AgentState:
    """Validates company information."""
    company_name = state.get("company_name", "")
    
    log_agent_action("input_agent", f"Processing input for company: {company_name}")
    
    # Basic validation logic
    validated_info = {
        "name": company_name,
        "ticker": None, # Can be resolved via API
        "valid": bool(company_name.strip())
    }
    
    if not validated_info["valid"]:
        log_agent_action("input_agent", "Validation failed - invalid name", {"validated_info": validated_info})
        return {"company_info": validated_info, "errors": ["Invalid company name provided."]} # type: ignore
        
    log_agent_action("input_agent", "Validation successful", {"validated_info": validated_info})
    return {"company_info": validated_info} # type: ignore
