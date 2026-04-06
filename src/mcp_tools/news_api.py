import os
import requests
from typing import List, Dict, Any

def search_company_news(company_name: str, api_key: str = None) -> List[Dict[str, Any]]:
    """
    Fetches recent news articles for a company using NewsAPI.
    If no API key is provided, falls back to mock data.
    """
    key = api_key or os.environ.get("NEWS_API_KEY")
    
    if not key or key.strip() == "":
        print(f"No News API key provided. Using mock data for {company_name}")
        return [{"title": f"Mock: Recent news indicates steady growth for {company_name}", "source": "MockNews"}]
        
    try:
        # Use a more inclusive query: keywords are good, but don't over-restrict
        query_suffix = ' (business OR financial OR earnings OR market)'
        if any(kw in company_name.lower() for kw in ["news", "outlook", "financial", "stock", "report"]):
            q = company_name
        else:
            q = f'{company_name}{query_suffix}'
            
        params = {
            "q": q,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 30,
            "apiKey": key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        if data.get("status") == "ok":
            for item in data.get("articles", []):
                articles.append({
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "source": item.get("source", {}).get("name"),
                    "url": item.get("url")
                })
        return articles
        
    except Exception as e:
        print(f"Error fetching news for {company_name}: {e}")
        return []
