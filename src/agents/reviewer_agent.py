from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.core.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
import json

def reviewer_agent(state: AgentState) -> dict:
    """Validates results and outputs final report format using an LLM."""
    company = state.get("company_name", "Unknown Company")
    log_agent_action("reviewer_agent", f"Reviewing final output for {company}")
    
    llm = get_llm()
    if not llm:
        return {"final_report": "Error: Could not generate report. LLM uninitialized."}
        
    score_info = state.get("risk_score", {"rating": "Unknown", "score": 0, "max": 100})
    risks = state.get("extracted_risks", [])
    strengths = state.get("extracted_strengths", [])
    explanations = state.get("explanations", [])
    
    prompt = f"""
    You are a Senior Risk Analyst formatting a final executive report for {company}.
    
    Use the following analytics output to write a professional, concise Markdown report:
    Risk Score: {json.dumps(score_info, indent=2)}
    Extracted Risks: {json.dumps(risks, indent=2)}
    Strengths & Mitigating Factors: {json.dumps(strengths, indent=2)}
    Explanations: {json.dumps(explanations, indent=2)}
    
    The report should:
    1. Start with the company name and primary score (0-100).
    2. Provide a section for 'Red Flags (Risks)'.
    3. Provide a section for 'Green Flags (Strengths & Mitigations)'.
    4. Finish with a balanced 'Executive Summary' that explains how the strengths offset some of the risks.
    
    Make it sleek, neutral, and easy for executives to digest.
    """
    
    messages = [
        SystemMessage(content="You compile structured data into executive Markdown risk reports."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        report = response.content
    except Exception as e:
        log_agent_action("reviewer_agent", f"LLM error: {str(e)}")
        report = f"Error generating markdown report: {str(e)}"
    
    log_agent_action("reviewer_agent", "Finished composing report", {"final_report_length": len(report)})
    return {"final_report": report}
