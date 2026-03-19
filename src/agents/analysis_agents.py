from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.core.llm import get_llm
from pydantic import BaseModel, Field
from typing import List
import json

# Define Pydantic models for structured LLM parsing
class RiskSignal(BaseModel):
    type: str = Field(description="Category. Strictly either 'Traditional Risk' or 'Non-traditional Risk'")
    description: str = Field(description="A concise, 1-sentence description of the risk factor found in the data")

class RiskExtractionOutput(BaseModel):
    extracted_risks: List[RiskSignal]

class RiskScoreOutput(BaseModel):
    score: int = Field(description="A calculated risk score strictly between 0 and 100, where 100 is maximum risk.")
    max: int = Field(description="Always 100")
    rating: str = Field(description="Strictly one of: 'Low', 'Medium', or 'High'")

class Explanation(BaseModel):
    metric: str = Field(description="The specific area of concern (e.g. 'Financials', 'Public Sentiment')")
    reason: str = Field(description="Short rationale for why this contributes to the overall risk.")

class ExplainabilityOutput(BaseModel):
    explanations: List[Explanation]


def risk_extraction_agent(state: AgentState) -> dict:
    """Extracts risk signals from unstructured data dynamically using an LLM."""
    log_agent_action("risk_extraction_agent", "Extracting risk signals from processed data")
    
    llm = get_llm()
    if not llm:
        log_agent_action("risk_extraction_agent", "No LLM available, falling back to empty")
        return {"extracted_risks": []}
        
    structured_llm = llm.with_structured_output(RiskExtractionOutput)
    
    # Prepare context
    company = state.get("company_name", "Unknown")
    data_context = json.dumps(state.get("cleaned_data", []), indent=2)
    
    prompt = f"""
    You are an expert corporate risk analyst analyzing data for {company}.
    Review the following raw data collected from financial databases and news APIs.
    Extract any potential risk factors facing this company. Classify them as either 'Traditional Risk' (financials, debt, margins) or 'Non-traditional Risk' (social, news, legal, reputation).
    
    Data:
    {data_context}
    """
    
    try:
        result = structured_llm.invoke(prompt)
        extracted_risks = [risk.model_dump() for risk in result.extracted_risks]
    except Exception as e:
        log_agent_action("risk_extraction_agent", f"LLM error: {str(e)}")
        extracted_risks = []
    
    log_agent_action("risk_extraction_agent", "Finished risk extraction", {"extracted_risks": extracted_risks})
    return {"extracted_risks": extracted_risks}


def risk_scoring_agent(state: AgentState) -> dict:
    """Combines signals into risk scores dynamically using an LLM."""
    log_agent_action("risk_scoring_agent", "Calculating overall risk score")
    
    llm = get_llm()
    if not llm:
        return {"risk_score": {"score": 0, "max": 100, "rating": "Unknown"}}
        
    structured_llm = llm.with_structured_output(RiskScoreOutput)
    
    company = state.get("company_name", "Unknown")
    risks_context = json.dumps(state.get("extracted_risks", []), indent=2)
    
    prompt = f"""
    You are an expert corporate actuary assessing risk for {company}.
    Review the following list of extracted risk signals and calculate a definitive risk score.
    Higher scores indicate higher risk.
    
    Risks:
    {risks_context}
    """
    
    try:
        result = structured_llm.invoke(prompt)
        risk_score = result.model_dump()
    except Exception as e:
        log_agent_action("risk_scoring_agent", f"LLM error: {str(e)}")
        risk_score = {"score": 0, "max": 100, "rating": "Unknown"}
        
    log_agent_action("risk_scoring_agent", "Finished risk scoring", {"risk_score": risk_score})
    return {"risk_score": risk_score}


def explainability_agent(state: AgentState) -> dict:
    """Explains why a company received a risk score using an LLM."""
    log_agent_action("explainability_agent", "Generating explanations for the risk score")
    
    llm = get_llm()
    if not llm:
        return {"explanations": []}
        
    structured_llm = llm.with_structured_output(ExplainabilityOutput)
    
    company = state.get("company_name", "Unknown")
    score_context = json.dumps(state.get("risk_score", {}))
    risks_context = json.dumps(state.get("extracted_risks", []), indent=2)
    
    prompt = f"""
    You are an audit explainer analyzing the risk profile for {company}.
    The company has received an overall risk configuration of: {score_context}.
    Based on the following extracted risks, generate 1-3 high-level explanations for why this score is justified.
    
    Extracted Risks:
    {risks_context}
    """
    
    try:
        result = structured_llm.invoke(prompt)
        explanations = [exp.model_dump() for exp in result.explanations]
    except Exception as e:
        log_agent_action("explainability_agent", f"LLM error: {str(e)}")
        explanations = []
        
    log_agent_action("explainability_agent", "Finished explainability generation", {"explanations": explanations})
    return {"explanations": explanations}
