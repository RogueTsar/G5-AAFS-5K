from tavily import TavilyClient
from typing import List, Dict, Any
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("sentiment_tool")

# Tavily client cache
_tavily_client = None

def get_tavily_client():
    """Lazily initialize the Tavily client."""
    global _tavily_client
    if _tavily_client is None:
        # Re-load dotenv in case it changed
        load_dotenv()
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key:
            _tavily_client = TavilyClient(api_key=api_key)
        else:
            logger.error("TAVILY_API_KEY not found in environment.")
    return _tavily_client

def get_sentiment_snippets(company_name: str, platform: str = "reddit") -> List[Dict[str, Any]]:
    """
    Search for recent mentions of a company on specific platforms using Tavily.
    Optimized for reliability and English results.
    """
    client = get_tavily_client()
    if not client:
        return []

    platform_lower = platform.lower()
    
    # Use quotes only for multi-word company names
    search_term = f'"{company_name}"' if " " in company_name else company_name
    
    # Construct targeted queries
    if platform_lower == "reddit":
        query = f"site:reddit.com {search_term} opinion 2025 2026"
    elif platform_lower == "glassdoor":
        query = f"site:glassdoor.com {search_term} reviews"
    elif platform_lower in ["twitter", "x", "facebook"]:
        query = f"(site:twitter.com OR site:x.com OR site:facebook.com) {search_term} sentiment"
    else:
        query = f"{search_term} {platform} sentiment"

    def is_relevant(company: str, title: str, snippet: str) -> bool:
        """Basic check to see if the company name appears in the result."""
        target = company.lower()
        text = (title + " " + snippet).lower()
        
        # Check for full name
        if target in text: return True
        
        # Check for major parts (at least 3 chars)
        parts = [p.strip() for p in target.split() if len(p.strip()) > 3]
        if any(p in text for p in parts): return True
        
        return False

    def fetch_with_tavily(client, q: str):
        try:
            # Tavily search returns a dictionary with 'results' key
            search_result = client.search(query=q, search_depth="advanced", max_results=5)
            results_list = search_result.get("results", [])
            
            extracted = []
            for r in results_list:
                title = r.get("title", "")
                snippet = r.get("content", "")
                
                if is_relevant(company_name, title, snippet):
                    extracted.append({
                        "platform": platform,
                        "title": title,
                        "snippet": snippet,
                        "url": r.get("url")
                    })
                if len(extracted) >= 5: break
            
            if not results_list:
                logger.warning(f"Tavily returned 0 results for query: {q}")
            return extracted
        except Exception as e:
            logger.error(f"Error fetching snippets with Tavily: {str(e)}")
            return []

    # Attempt 1: Platform specific search
    results = fetch_with_tavily(client, query)
    
    # Fallback: Broad search if specific is empty
    if not results:
        fallback_query = f"{search_term} {platform} news sentiment reviews 2025 2026"
        results = fetch_with_tavily(client, fallback_query)
        
    return results
