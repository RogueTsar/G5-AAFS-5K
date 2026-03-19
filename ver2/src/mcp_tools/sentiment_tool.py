from duckduckgo_search import DDGS
from typing import List, Dict, Any
import logging

logger = logging.getLogger("sentiment_tool")

def get_sentiment_snippets(company_name: str, platform: str = "reddit") -> List[Dict[str, Any]]:
    """
    Search for recent mentions of a company on specific platforms.
    Optimized for reliability and English results.
    """
    platform_lower = platform.lower()
    
    # Use quotes only for multi-word company names to prevent over-filtering on common words
    search_term = f'"{company_name}"' if " " in company_name else company_name
    
    # Use a wider 2025-2026 window
    year_filter = "2025 2026"
    
    # Construct targeted queries
    if platform_lower == "reddit":
        query = f"site:reddit.com {search_term} opinion {year_filter}"
    elif platform_lower == "glassdoor":
        query = f"site:glassdoor.com {search_term} reviews"
    elif platform_lower in ["twitter", "x", "facebook"]:
        query = f"(site:twitter.com OR site:x.com OR site:facebook.com) {search_term} sentiment"
    else:
        query = f"{search_term} {platform} sentiment lang:en"

    def is_relevant(company: str, title: str, snippet: str) -> bool:
        """Basic check to see if the company name appears in the result."""
        target = company.lower()
        text = (title + " " + snippet).lower()
        
        # Check for full name
        if target in text: return True
        
        # Check for major parts (at least 3 chars)
        parts = [p.strip() for p in target.split() if len(p.strip()) > 3]
        if any(p in text for p in parts): return True
        
        # Special case: If it's a very common 1-word company (Apple, Tesla, Nike), 
        # allow product-based context or just be more lenient
        common_tech = ["apple", "tesla", "nike", "nvidia", "meta", "google"]
        if target in common_tech and any(word in text for word in ["company", "product", "stock", "review", "price"]):
            return True
            
        return False

    def fetch_with_query(q: str, region: str = "us-en", time_limit: str = None):
        try:
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(q, region=region, safesearch="off", timelimit=time_limit)
                extracted = []
                raw_count = 0
                for i, r in enumerate(ddgs_gen):
                    raw_count += 1
                    if i >= 15: break 
                    title = r.get("title", "")
                    snippet = r.get("body", "")
                    
                    if is_relevant(company_name, title, snippet):
                        extracted.append({
                            "platform": platform,
                            "title": title,
                            "snippet": snippet,
                            "url": r.get("href")
                        })
                    if len(extracted) >= 5: break
                
                if raw_count == 0:
                    logger.warning(f"DuckDuckGo returned 0 RAW results for query: {q}")
                return extracted
        except Exception as e:
            if "Ratelimit" in str(e) or "403" in str(e):
                logger.error(f"DuckDuckGo Rate Limit Hit for query {q}")
            else:
                logger.error(f"Error fetching snippets: {str(e)}")
            return []

    # Attempt 1: Platform specific search
    results = fetch_with_query(query, region="us-en")
    
    # Fallback 1: Broad search if specific is empty or failed relevance
    if not results:
        fallback_query = f"{search_term} {platform} news sentiment reviews {year_filter}"
        results = fetch_with_query(fallback_query, region="us-en")
        
    # Fallback 2: General global attempt without site restricts
    if not results:
        results = fetch_with_query(f"{search_term} {platform} sentiment", region="wt-wt")
        
    return results
