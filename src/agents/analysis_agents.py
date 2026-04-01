from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.core.llm import get_llm
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json

# Define Pydantic models for structured LLM parsing
class RiskSignal(BaseModel):
    type: str = Field(description="Category. Strictly either 'Traditional Risk' or 'Non-traditional Risk'")
    description: str = Field(description="A concise, 1-sentence description of the risk factor found in the data")
    impact: str = Field(description="The significance of the risk factor. Strictly one of: 'High', 'Medium', or 'Low'")

class StrengthSignal(BaseModel):
    type: str = Field(description="Category. Strictly either 'Financial Strength' or 'Market Strength'")
    description: str = Field(description="A concise, 1-sentence description of a positive or mitigating factor found in the data")
    impact: str = Field(description="The significance of the factor. Strictly one of: 'High', 'Medium', or 'Low'")

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
    Review the following processed data, which includes specialized 'finbert_sentiment' scores (expert financial sentiment analysis) and raw metrics.
    
    Your goal is to provide a BALANCED view:
    1. Extract potential RISK factors (Traditional or Non-traditional). 
       - Pay close attention to items with 'Negative' finbert_sentiment.
       - Assign an 'impact' (High, Medium, Low) to each risk. Factors impacting core revenue, solvency, or major leadership stability are 'High' impact.
    2. Extract STRENGTHS or mitigating factors.
       - Items with 'Positive' finbert_sentiment are strong indicators of growth and stability.
       - Assign an 'impact' (High, Medium, Low) to each strength. Major revenue growth, strong liquidity, or significant strategic wins are 'High' impact.
    
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


def evaluate_financial_metrics(metrics: Dict[str, Any]) -> str:
    """
    Rule-based engine to evaluate raw financial ratios.
    Returns "positive", "neutral", or "negative".
    """
    if not metrics:
        return "neutral"
        
    # Extract key ratios (handling potential missing keys)
    de = metrics.get("debtToEquity", 0)
    cr = metrics.get("currentRatio", 1.0)
    rg = metrics.get("revenueGrowth", 0)
    pm = metrics.get("profitMargins", 0)
    
    # 1. Red Flags (Negative)
    if cr < 1.0: return "negative" # Liquidity risk: Can't pay short-term debts
    if de > 100: return "negative" # High leverage: Over 100% debt-to-equity
    if rg < -0.05: return "negative" # Significant revenue decline
    
    # 2. Green Flags (Positive)
    if cr > 1.5 and rg > 0.05 and pm > 0.05:
        return "positive" # Healthy balance of liquidity, growth, and margins
    
    return "neutral"

def calculate_source_score(items: List[Dict[str, Any]]) -> Optional[float]:
    """Calculates a 0-100 risk score based on average FinBERT sentiment or raw metrics."""
    if not items:
        return None
        
    scores = []
    for item in items:
        # Check for yfinance metrics first (threshold-based scoring)
        if "metrics" in item:
            label = evaluate_financial_metrics(item["metrics"])
        else:
            # Fallback to textual sentiment (FinBERT)
            sentiment = item.get("finbert_sentiment", {})
            label = sentiment.get("label", "neutral").lower()
            
        # Mapping: Positive -> 0, Neutral -> 50, Negative -> 100
        if label == "positive":
            scores.append(0.0)
        elif label == "negative":
            scores.append(100.0)
        else: # Neutral or Error
            scores.append(50.0)
            
    return sum(scores) / len(scores)

def risk_scoring_agent(state: AgentState) -> dict:
    """Calculates a deterministic risk score using weighted categories and LLM refinement."""
    company = state.get("company_name", "Unknown")
    log_agent_action("risk_scoring_agent", f"Calculating weighted risk score for {company}")
    
    # 1. Rules: 60/20/12/8 distribution
    base_weights = {
        "structured": 0.60, # financial + document
        "news": 0.20,
        "review": 0.12,
        "social": 0.08
    }
    
    # 2. Group items from cleaned_data
    grouped_data = {
        "structured": [],
        "news": [],
        "review": [],
        "social": []
    }
    
    for item in state.get("cleaned_data", []):
        stype = item.get("source_type")
        if stype in ["financial", "document"]:
            grouped_data["structured"].append(item)
        elif stype in grouped_data:
            grouped_data[stype].append(item)
            
    # 3. Calculate category scores and re-normalize weights
    category_scores = {}
    active_weights = {}
    total_active_weight = 0.0
    
    for category, weight in base_weights.items():
        score = calculate_source_score(grouped_data[category])
        if score is not None:
            category_scores[category] = score
            active_weights[category] = weight
            total_active_weight += weight
            
    # 4. Final Weighted Calculation with Re-normalization
    if total_active_weight == 0:
        base_score = 50.0 # Default to neutral if no data
    else:
        # Re-normalize weights so they sum to 1.0 (deterministic math)
        weighted_sum = 0.0
        normalized_weights = {cat: w/total_active_weight for cat, w in active_weights.items()}
        for category, score in category_scores.items():
            weighted_sum += score * normalized_weights[category]
        base_score = weighted_sum

    # 5. LLM refinement for Rating and Justification
    llm = get_llm()
    if not llm:
        # Qualitative fallback if LLM is unavailable
        rating = "Low" if base_score < 40 else "Medium" if base_score < 70 else "High"
        return {"risk_score": {"score": int(base_score), "max": 100, "rating": rating, "breakdown": category_scores}}

    structured_llm = llm.with_structured_output(RiskScoreOutput)
    
    prompt = f"""
    You are a Senior Risk Analyst. We have calculated a rule-based risk score for {company} weighting sources as follows:
    - Structured/Financial: 60%
    - News: 20%
    - Reviews: 12%
    - Social Media: 8% (Adjusted weights sum to 100% when data is missing).
    
    The calculated base score is: {base_score:.1f}/100.
    
    Categorized Risk Scores (Average Risk):
    {json.dumps(category_scores, indent=2)}
    
    Your Task:
    1. Verify if the calculated 'base_score' matches the appropriate 'rating' (Low, Medium, or High).
    2. Suggest any final small adjustment (+/- 5 points) if the qualitative context suggests something the math missed.
    3. Output the final score and rating.
    
    Rating Guide:
    - < 40: Low
    - 40 - 70: Medium
    - > 70: High
    """
    
    try:
        result = structured_llm.invoke(prompt)
        risk_score = result.model_dump()
        risk_score["breakdown"] = category_scores # Pass breakdown to UI for transparency
    except Exception as e:
        log_agent_action("risk_scoring_agent", f"Error in LLM refinement: {str(e)}")
        # Use calculated score as final if LLM fails
        rating = "Low" if base_score < 40 else "Medium" if base_score < 70 else "High"
        risk_score = {"score": int(base_score), "max": 100, "rating": rating, "breakdown": category_scores}
        
    log_agent_action("risk_scoring_agent", "Finished weighted risk scoring", {"final_score": risk_score["score"]})
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
