from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.core.llm import get_llm
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json

class DocMetric(BaseModel):
    metric: str = Field(description="Name of the financial metric (e.g. Revenue, Net Income, Current Ratio, Debt-to-Equity)")
    value: str = Field(description="The numerical value or ratio (e.g. '10.5B', '1.8', '15.2%')")
    period: str = Field(description="The financial period this metric refers to (e.g. 'FY 2023', 'Q3 2024')")
    context: str = Field(description="The specific context or table this was found in (e.g. 'Income Statement', 'Key Highlights')")

class DocMetricsExtraction(BaseModel):
    extracted_metrics: List[DocMetric]

def document_metrics_agent(state: AgentState) -> dict:
    """
    Uses an LLM to 'read' the extracted text from uploaded documents and 
    identify specific numerical financial metrics.
    """
    extracted_docs = state.get("doc_extracted_text", [])
    if not extracted_docs:
        return {"doc_structured_data": []}
        
    log_agent_action("document_metrics_agent", f"Scanning {len(extracted_docs)} documents for structured financial metrics.")
    
    llm = get_llm()
    if not llm:
        return {"doc_structured_data": []}
        
    structured_llm = llm.with_structured_output(DocMetricsExtraction)
    
    all_extracted_metrics = []
    
    for doc in extracted_docs:
        filename = doc.get("filename", "unknown")
        text = doc.get("text", "")
        
        if len(text) < 50: # Skip empty/near-empty docs
            continue
            
        prompt = f"""
        You are a financial data specialist. Your goal is to extract key numerical financial metrics 
        from the following text extracted from the file '{filename}'.
        
        Focus on:
        - Revenue, Gross Margin, Net Income
        - Ratios (Current Ratio, Debt-to-Equity, Operating Margins)
        - Growth percentages (YoY, QoQ)
        - Debt levels and Cash positions
        
        Text to analyze:
        ---
        {text[:8000]} # Limit context for performance
        ---
        
        Extract these into a structured format. If no clear metrics are found, return an empty list.
        """
        
        try:
            result = structured_llm.invoke(prompt)
            for m in result.extracted_metrics:
                metric_dict = m.dict()
                metric_dict["source_file"] = filename
                all_extracted_metrics.append(metric_dict)
                
        except Exception as e:
            log_agent_action("document_metrics_agent", f"Error extracting from {filename}: {str(e)}")
            
    log_agent_action("document_metrics_agent", f"Extracted {len(all_extracted_metrics)} structured metrics from docs.")
    return {"doc_structured_data": all_extracted_metrics}
