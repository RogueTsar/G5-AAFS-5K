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
    
    Use the following analytics output to write a professional, high-impact Markdown report:
    - Risk Score: {json.dumps(score_info, indent=2)}
    - Extracted Risks: {json.dumps(risks, indent=2)}
    - Strengths & Mitigations: {json.dumps(strengths, indent=2)}
    - Detailed Explanations: {json.dumps(explanations, indent=2)}
    
    REPORT STRUCTURE REQUIREMENTS:
    1. **Title**: Main heading with company name.
    2. **Executive Summary**: A high-level overview of the risk profile. Includes the 'Overall Risk Score'.
    3. **Key Metrics Table**: Create a Markdown table with 'Metric', 'Rating', and 'Score'.
       **CRITICAL: STICK TO THE NUMERICAL SCORES (0-100) FROM THE BREAKDOWN.** 
       Do NOT use raw metrics (like 2.164 or 25%) here. Only use the 0-100 values.
       
       MAPPING FOR CATEGORIES:
       - 'Overall Risk Score' ➔ use the main 'score' and 'rating'.
       - 'Financial Metrics & Docs' ➔ use 'structured' score.
       - 'Market News & Sentiment' ➔ use 'news' score.
       - 'Employee/Customer Feedback' ➔ use 'review' score.
       - 'Social Media Momentum' ➔ use 'social' score.
       
       RATING LOGIC (IF NOT PROVIDED):
       - < 40: Low
       - 40 - 70: Medium
       - > 70: High
       
    4. **Risk Profile Details**:
        - Use `### 🚩 Red Flags (Risks)` for potential issues. 
          **CRITICAL: Order these by 'impact', placing 'High' significance risks at the top.**
          Include the impact label (e.g., "[High] Traditional Risk: ...") in the bullet point.
        - Use `### ✅ Green Flags (Strengths)` for positive/mitigating factors. 
          **CRITICAL: Order these by 'impact', placing 'High' significance strengths at the top.**
          Include the impact label in the bullet point.
    5. **Analyst Conclusion**: A final synthesized view on the outlook.
    
    STYLING:
    - Use bold text for key terms.
    - Keep it professional, data-driven, and objective.
    - Avoid flowery language; focus on clarity.
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
