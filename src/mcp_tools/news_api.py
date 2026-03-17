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
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": f'+"{company_name}" AND (business OR financial OR stock OR earnings OR market)',
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 5,
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
        return [{"title": f"Error fetching news for {company_name}", "source": "SystemError"}]
