import yfinance as yf
from typing import Dict, Any, Optional
import os

def get_financial_metrics(ticker_symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetches key financial metrics for a given ticker using Yahoo Finance.
    Returns None if the ticker cannot be found or has no data.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Get standard info dictionary
        info = ticker.info
        
        if not info or 'shortName' not in info:
            return None
            
        metrics = {
            "currency": info.get("financialCurrency", "USD"),
            "debtToEquity": info.get("debtToEquity", None),
            "currentRatio": info.get("currentRatio", None),
            "operatingMargins": info.get("operatingMargins", None),
            "profitMargins": info.get("profitMargins", None),
            "returnOnEquity": info.get("returnOnEquity", None),
            "totalDebt": info.get("totalDebt", None),
            "totalRevenue": info.get("totalRevenue", None),
            "revenueGrowth": info.get("revenueGrowth", None),
            "ebitda": info.get("ebitda", None)
        }
        
        return metrics
        
    except Exception as e:
        print(f"Error fetching financial metrics for {ticker_symbol}: {e}")
        return None

def find_ticker(company_name: str) -> Optional[str]:
    """
    Attempts to map a company name to a stock ticker.
    First checks a known list for speed/accuracy, then falls back to a search via Yahoo Finance.
    """
    known = {
        "apple": "AAPL",
        "apple inc": "AAPL",
        "tesla": "TSLA",
        "microsoft": "MSFT",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "amazon": "AMZN",
        "nvidia": "NVDA",
        "meta": "META",
        "facebook": "META",
        "nike": "NKE"
    }
    
    clean_name = company_name.lower().strip()
    if clean_name in known:
        return known[clean_name]
        
    try:
        # Fallback to search query using internal yfinance undocumented search API
        import urllib.parse
        search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(company_name)}&quotesCount=1&newsCount=0"
        
        # Yahoo requires a user-agent
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        import requests
        response = requests.get(search_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            quotes = data.get('quotes', [])
            if quotes and len(quotes) > 0:
                # Return the first symbol found
                return quotes[0].get('symbol')
                
    except Exception as e:
        print(f"Error searching for ticker {company_name}: {e}")
        
    return None
