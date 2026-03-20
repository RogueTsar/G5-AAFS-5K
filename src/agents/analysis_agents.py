from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.core.llm import get_llm
from pydantic import BaseModel, Field
from typing import List, Optional
import json

# Define Pydantic models for structured LLM parsing
class RiskSignal(BaseModel):
    type: str = Field(description="Category. Strictly either 'Traditional Risk' or 'Non-traditional Risk'")
    description: str = Field(description="A concise, 1-sentence description of the risk factor found in the data")

class StrengthSignal(BaseModel):
    type: str = Field(description="Category. Strictly either 'Financial Strength' or 'Market Strength'")
    description: str = Field(description="A concise, 1-sentence description of a positive or mitigating factor found in the data")

class RiskExtractionOutput(BaseModel):
    extracted_risks: List[RiskSignal]
    extracted_strengths: List[StrengthSignal]

class RiskScoreOutput(BaseModel):
    score: int = Field(description="A calculated risk score strictly between 0 and 100, where 100 is maximum risk.")
    max: int = Field(description="Always 100")
    rating: str = Field(description="Strictly one of: 'Low', 'Medium', or 'High'")

class Explanation(BaseModel):
    metric: str = Field(description="The specific area of concern or strength (e.g. 'Financials', 'Public Sentiment')")
    reason: str = Field(description="Short rationale for why this impacts the overall risk profile positively or negatively.")

class ExplainabilityOutput(BaseModel):
    explanations: List[Explanation]


def risk_extraction_agent(state: AgentState) -> dict:
    """Extracts both risk and strength signals from unstructured data dynamically using an LLM."""
    log_agent_action("risk_extraction_agent", "Extracting balanced signals (risks and strengths) from processed data")
    
    llm = get_llm()
    if not llm:
        return {"extracted_risks": [], "extracted_strengths": []}
        
    structured_llm = llm.with_structured_output(RiskExtractionOutput)
    
    # Prepare context
    company = state.get("company_name", "Unknown")
    data_context = json.dumps(state.get("cleaned_data", []), indent=2)
    
    prompt = f"""
    You are an objective corporate analyst analyzing data for {company}.
    Review the following processed data, which includes specialized 'finbert_sentiment' scores (expert financial sentiment analysis).
    
    Your goal is to provide a BALANCED view:
    1. Extract potential RISK factors (Traditional or Non-traditional). 
       - Pay close attention to items with 'Negative' finbert_sentiment.
    2. Extract STRENGTHS or mitigating factors.
       - Items with 'Positive' finbert_sentiment are strong indicators of growth and stability.
    
    Data:
    {data_context}
    """
    
    try:
        result = structured_llm.invoke(prompt)
        extracted_risks = [risk.model_dump() for risk in result.extracted_risks]
        extracted_strengths = [s.model_dump() for s in result.extracted_strengths]
    except Exception as e:
        log_agent_action("risk_extraction_agent", f"LLM error: {str(e)}")
        extracted_risks = []
        extracted_strengths = []
    
    log_agent_action("risk_extraction_agent", "Finished balanced extraction", {
        "extracted_risks": extracted_risks,
        "extracted_strengths": extracted_strengths
    })
    return {"extracted_risks": extracted_risks, "extracted_strengths": extracted_strengths}


def risk_scoring_agent(state: AgentState) -> dict:
    """Combines risks and strengths into a neutral, objective risk score."""
    log_agent_action("risk_scoring_agent", "Calculating balanced risk score")
    
    llm = get_llm()
    if not llm:
        return {"risk_score": {"score": 0, "max": 100, "rating": "Unknown"}}
        
    structured_llm = llm.with_structured_output(RiskScoreOutput)
    
    company = state.get("company_name", "Unknown")
    risks_context = json.dumps(state.get("extracted_risks", []), indent=2)
    strengths_context = json.dumps(state.get("extracted_strengths", []), indent=2)
    
    prompt = f"""
    You are a neutral and objective credit analyst assessing {company}.
    Review the list of Risks and Strengths, which incorporate specialized FinBERT sentiment signals.
    
    Calculate a final risk score (0-100) where 100 is maximum insolvency risk.
    BE NEUTRAL: Use the FinBERT sentiment scores as objective anchor points. High confidence positive sentiment should significantly offset risks.
    
    Risks:
    {risks_context}
    
    Strengths:
    {strengths_context}
    """
    
    try:
        result = structured_llm.invoke(prompt)
        risk_score = result.model_dump()
    except Exception as e:
        log_agent_action("risk_scoring_agent", f"LLM error: {str(e)}")
        risk_score = {"score": 0, "max": 100, "rating": "Unknown"}
        
    log_agent_action("risk_scoring_agent", "Finished balanced risk scoring", {"risk_score": risk_score})
    return {"risk_score": risk_score}


def explainability_agent(state: AgentState) -> dict:
    """Explains why a company received a risk score, highlighting the balance of factors."""
    log_agent_action("explainability_agent", "Generating balanced explanations for the risk score")
    
    llm = get_llm()
    if not llm:
        return {"explanations": []}
        
    structured_llm = llm.with_structured_output(ExplainabilityOutput)
    
    company = state.get("company_name", "Unknown")
    score_context = json.dumps(state.get("risk_score", {}))
    risks = json.dumps(state.get("extracted_risks", []), indent=2)
    strengths = json.dumps(state.get("extracted_strengths", []), indent=2)
    
    prompt = f"""
    You are an objective auditor explaining the risk profile for {company}.
    The score is: {score_context}.
    
    Generate 2-3 explanations that show BOTH the risks and how they are (or are not) mitigated by the strengths.
    BE BALANCED: Highlight the "tug-of-war" between the positive and negative signals.
    
    Risks:
    {risks}
    
    Strengths:
    {strengths}
    """
    
    try:
        result = structured_llm.invoke(prompt)
        explanations = [exp.model_dump() for exp in result.explanations]
    except Exception as e:
        log_agent_action("explainability_agent", f"LLM error: {str(e)}")
        explanations = []
        
    log_agent_action("explainability_agent", "Finished balanced explanations", {"explanations": explanations})
    return {"explanations": explanations}
