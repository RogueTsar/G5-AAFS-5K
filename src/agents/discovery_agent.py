from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.core.llm import get_llm
from pydantic import BaseModel, Field
from typing import List, Dict

class SearchQueriesOutput(BaseModel):
    news: List[str] = Field(description="3-5 optimized search queries for news, press releases, and outlook reports.")
    social: List[str] = Field(description="2-3 optimized search queries for social media sentiment (Reddit, Twitter, etc.).")
    reviews: List[str] = Field(description="2-3 optimized search queries for employee and customer reviews (Glassdoor, Trustpilot, etc.).")
    financials: List[str] = Field(description="2-3 optimized search queries for financial metrics and filings.")

def discovery_agent(state: AgentState) -> Dict[str, List[str]]:
    """
    Agentic AI integration: Uses an LLM to discover and plan a search strategy 
    tailored to the specific company.
    """
    company_name = state.get("company_name", "Unknown")
    log_agent_action("discovery_agent", f"Generating optimized search strategy for {company_name}")
    
    llm = get_llm()
    if not llm:
        log_agent_action("discovery_agent", "LLM not initialized, using default empty strategy")
        return {"search_queries": {"news": [], "social": [], "reviews": [], "financials": []}}
        
    structured_llm = llm.with_structured_output(SearchQueriesOutput)
    
    prompt = f"""
    You are a strategic intelligence analyst planning a deep-dive risk assessment for the company: {company_name}.
    
    Your goal is to generate HIGHLY SPECIFIC search queries to uncover risks, strengths, and future outlook.
    
    Guidelines:
    1. NEWS: Focus on real events and outlook. Use terms like "{company_name} outlook", "{company_name} future plans", "{company_name} expansion". Avoid "report" or "analysis" in news queries.
    2. SOCIAL: Target RAW conversations and unfiltered feedback. Use "{company_name} reddit", "{company_name} twitter", "{company_name} complaints", "{company_name} issues". 
       CRITICAL: Avoid words like "sentiment analysis", "public opinion", or "research" in social queries, as they lead to blog posts ABOUT the company instead of real user posts.
    3. REVIEWS: Target direct feedback. Use "{company_name} employee reviews", "{company_name} glassdoor", "{company_name} trustpilot", "{company_name} customer complaints".
    4. FINANCIALS: Focus on raw data and filings. Use "{company_name} stock", "{company_name} debt", "{company_name} revenue", "{company_name} balance sheet".

    Be aggressive in hunting for raw, unvarnished data.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        search_queries = {
            "news": result.news,
            "social": result.social,
            "reviews": result.reviews,
            "financials": result.financials
        }
        log_agent_action("discovery_agent", "Successfully generated tailored search strategy", search_queries)
        return {"search_queries": search_queries}
    except Exception as e:
        log_agent_action("discovery_agent", f"Error generating queries: {str(e)}")
        # Fallback to basic queries
        fallback = {
            "news": [f"{company_name} latest news 2025", f"{company_name} company outlook 2026"],
            "social": [f"{company_name} reddit sentiment", f"{company_name} twitter opinion"],
            "reviews": [f"{company_name} glassdoor reviews", f"{company_name} customer feedback"],
            "financials": [f"{company_name} financial reports", f"{company_name} stock performance"]
        }
        return {"search_queries": fallback}
