from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.mcp_tools.finbert_tool import analyze_financial_sentiment
from src.core.llm import get_llm
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json

class VerificationResult(BaseModel):
    is_relevant: bool = Field(description="Exactly True if the data refers to the company or its confirmed subsidiaries, otherwise False.")
    company_alias_found: Optional[str] = Field(description="If the data refers to a subsidiary or a different brand name for the company, list it here.")
    reasoning: str = Field(description="Brief 1-sentence explanation of why this is or isn't relevant.")

class EntityResolutionOutput(BaseModel):
    verifications: List[VerificationResult]
    primary_name: str = Field(description="The most official or current name for the company.")
    discovered_aliases: List[str] = Field(description="All discovered brand names, subsidiaries, or abbreviations found in the data.")

def data_cleaning_agent(state: AgentState) -> dict:
    """Enriches data points with FinBERT sentiment scores."""
    company_name = state.get("company_name", "Unknown")
    log_agent_action("data_cleaning_agent", f"Starting data cleaning and sentiment enrichment for {company_name}")
    
    raw_data = []
    if state.get("news_data"):
        for item in state["news_data"]:
            item["source_type"] = "news"
            raw_data.append(item)
    if state.get("social_data"):
        for item in state["social_data"]:
            item["source_type"] = "social"
            raw_data.append(item)
    if state.get("review_data"):
        for item in state["review_data"]:
            item["source_type"] = "review"
            raw_data.append(item)
    if state.get("financial_data"):
        for item in state["financial_data"]:
            item["source_type"] = "financial"
            raw_data.append(item)
    if state.get("financial_news_data"):
        for item in state["financial_news_data"]:
            item["source_type"] = "news"
            raw_data.append(item)
    if state.get("doc_extracted_text"):
        for item in state["doc_extracted_text"]:
            item["source_type"] = "document"
            # Ensure the structure matches what the loop expects for 'text' extraction
            item["snippet"] = item.get("text", "") 
            raw_data.append(item)
            
    enriched_data = []
    for item in raw_data:
        text = ""
        if "title" in item and "snippet" in item:
            text = f"{item['title']} - {item['snippet']}"
        elif "content" in item and isinstance(item["content"], dict):
             c = item["content"]
             text = f"{c.get('title', '')} {c.get('snippet', '')}"
        elif "title" in item:
            text = item["title"]
        elif "snippet" in item:
            text = item["snippet"]
            
        if text:
            sentiment = analyze_financial_sentiment(text)
            item["finbert_sentiment"] = sentiment
        
        enriched_data.append(item)
        
    return {"cleaned_data": enriched_data}

def entity_resolution_agent(state: AgentState) -> dict:
    """
    Agentic AI integration: Uses an LLM to verify data consistency, 
    filter out irrelevant noise, and resolve subsidiaries.
    """
    company_name = state.get("company_name", "Unknown")
    log_agent_action("entity_resolution_agent", f"Performing intelligent entity resolution for {company_name}")
    
    llm = get_llm()
    if not llm:
        log_agent_action("entity_resolution_agent", "LLM not initialized, falling back to basic checks")
        return {"resolved_entities": {"primary_entity": company_name}, "company_aliases": []}
        
    structured_llm = llm.with_structured_output(EntityResolutionOutput)
    
    cleaned_data = state.get("cleaned_data", [])
    if not cleaned_data:
        return {"resolved_entities": {"primary_entity": company_name}, "company_aliases": []}
        
    # 1. Separate trusted data from data that needs verification
    trusted_data = []
    to_verify_data = []
    
    for item in cleaned_data:
        # yfinance is a trusted source retrieved by ticker
        if item.get("source") == "yfinance":
            trusted_data.append(item)
        else:
            to_verify_data.append(item)
            
    if not to_verify_data:
        return {
            "cleaned_data": trusted_data,
            "resolved_entities": {"primary_entity": company_name, "mentions": len(trusted_data)},
            "company_aliases": []
        }
        
    # 2. Prepare only unverified data for the LLM
    data_to_verify = []
    for item in to_verify_data:
        # Handle different nested structures for text extraction
        text = ""
        if "content" in item and isinstance(item["content"], dict):
            c = item["content"]
            text = f"[{c.get('platform', 'news')}] {c.get('title', '')}: {c.get('snippet', '')}"
        else:
            text = f"{item.get('title', '')} {item.get('snippet', '')}"
            
        data_to_verify.append({"id": id(item), "text": text[:300]})
        
    prompt = f"""
    You are an expert corporate genealogist. Your task is to verify if the following data points 
    refers to the company: '{company_name}' or its direct subsidiaries/brands.
    
    Data to verify:
    {json.dumps(data_to_verify, indent=2)}
    
    Identify:
    1. If the data is actually relevant (e.g. filter out 'Apple Records' if searching for 'Apple Inc').
    2. Any subsidiaries (e.g. 'Waymo' belongs to 'Alphabet', 'YouTube' belongs to 'Alphabet').
    3. The official primary name if '{company_name}' is an abbreviation.

    Be strict about relevance to avoid 'hallucinated' data points in the risk report.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        
        # 3. Filter the to_verify_data based on LLM verification
        verified_data = []
        for i, verification in enumerate(result.verifications):
            if i < len(to_verify_data) and verification.is_relevant:
                item = to_verify_data[i]
                item["verified_relevant"] = True
                if verification.company_alias_found:
                    item["resolved_alias"] = verification.company_alias_found
                verified_data.append(item)
        
        # 4. Combine trusted data with verified data
        final_cleaned_data = trusted_data + verified_data
                
        log_agent_action("entity_resolution_agent", f"Verified {len(verified_data)}/{len(to_verify_data)} points. Kept {len(trusted_data)} trusted points. Total: {len(final_cleaned_data)}")
        
        return {
            "cleaned_data": final_cleaned_data,
            "resolved_entities": {
                "primary_entity": result.primary_name,
                "mentions": len(final_cleaned_data)
            },
            "company_aliases": result.discovered_aliases
        }
    except Exception as e:
        log_agent_action("entity_resolution_agent", f"Resolution error: {str(e)}")
        return {
            "resolved_entities": {"primary_entity": company_name, "mentions": len(cleaned_data)},
            "company_aliases": []
        }
