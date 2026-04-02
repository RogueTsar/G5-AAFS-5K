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

def evaluate_fact_sentiment(metric: str, value_str: str) -> str:
    """
    Rule-based engine to assign positive/negative sentiment to financial facts
    based on their numerical values.
    """
    m = metric.lower()
    
    # Try to extract a clean number
    # Handles strings like "43% YoY", "1.72x", "SGD 42.50M (+15.5% YoY)"
    import re
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", value_str.replace(",", ""))
    if not numbers:
        return "neutral"
    
    val = float(numbers[0])
    
    # --- Growth Metrics ---
    if "growth" in m or "yoy" in m or "revenue" in m or "profit" in m or "income" in m:
        # Check for growth percentages if it's a YoY string
        if "yoy" in value_str.lower():
            try:
                growth_val = float(re.findall(r"([-+]?\d*\.\d+|\d+)%", value_str)[0])
                if growth_val > 0.1: return "positive"
                if growth_val < -5: return "negative"
            except: pass
        if "loss" in m: return "negative" if val > 0 else "positive"
        if "profit" in m and val > 0: return "positive"
        return "neutral"

    # --- Liquidity Ratios ---
    if "current ratio" in m:
        if val > 1.2: return "positive"
        if val < 1.0: return "negative"
        
    # --- Solvency (Debt-to-Equity) ---
    if "debt-to-equity" in m or "leverage" in m:
        if val < 1.0: return "positive"
        if val > 2.0: return "negative"
        
    # --- Profitability (Margins) ---
    if "margin" in m:
        if val > 5: return "positive"
        if val < 0: return "negative"
        
    if "cash" in m and val > 0: return "positive"
    
    return "neutral"

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

    if state.get("doc_structured_data"):
        for item in state["doc_structured_data"]:
            # These are financial metrics from documents
            item["source_type"] = "financial"
            # Add a snippet for consistency in extraction agents
            snippet = f"{item.get('metric')}: {item.get('value')} ({item.get('period')}) - {item.get('context')}"
            item["snippet"] = snippet
            
            # Use rule-based sentiment for consistency
            label = evaluate_fact_sentiment(item.get("metric", ""), str(item.get("value", "")))
            item["finbert_sentiment"] = {"label": label, "score": 0.99}
            raw_data.append(item)

    if state.get("xbrl_parsed_data"):
        for report in state["xbrl_parsed_data"]:
            period_str = f"FY {report.get('periods', {}).get('current', 'Unknown')}"
            currency = report.get("currency", "SGD")
            
            # Helper to flatten statement rows
            def process_rows(rows, section_name):
                for row in rows:
                    if row.get("current") is not None:
                        label = row.get("label", "Unknown")
                        val = row.get("current")
                        raw_data.append({
                            "metric": label,
                            "value": f"{currency} {val:,.2f}",
                            "period": period_str,
                            "context": section_name,
                            "source_type": "financial",
                            "snippet": f"XBRL {label}: {currency} {val:,.2f} ({period_str}) - {section_name}"
                        })

            # Process all major sections
            bs = report.get("balance_sheet", {})
            income = report.get("income_statement", [])
            
            # --- Extract Key Metrics Specifically ---
            def get_val(concept, source_list):
                for row in source_list:
                    if row.get("concept") == concept:
                        return row.get("current"), row.get("prior")
                return None, None

            # 1. Revenue & YoY
            rev_curr, rev_prior = get_val("Revenue", income)
            if rev_curr:
                yoy_str = ""
                yoy_val = 0
                if rev_prior and rev_prior != 0:
                    yoy_val = ((rev_curr - rev_prior) / abs(rev_prior)) * 100
                    yoy_str = f" ({yoy_val:+.1f}% YoY)"
                
                val_str = f"{currency} {rev_curr:,.2f}{yoy_str}"
                label = evaluate_fact_sentiment("Revenue Growth", yoy_str if yoy_str else str(rev_curr))
                
                raw_data.append({
                    "metric": "Revenue", "value": val_str, "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Revenue: {val_str}",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            # 2. Net Profit & YoY
            prof_curr, prof_prior = get_val("ProfitLoss", income)
            if prof_curr:
                yoy_str = ""
                yoy_val = 0
                if prof_prior and prof_prior != 0:
                    yoy_val = ((prof_curr - prof_prior) / abs(prof_prior)) * 100
                    yoy_str = f" ({yoy_val:+.1f}% YoY)"
                
                val_str = f"{currency} {prof_curr:,.2f}{yoy_str}"
                label = evaluate_fact_sentiment("Net Profit Growth", yoy_str if yoy_str else str(prof_curr))
                
                raw_data.append({
                    "metric": "Net Profit", "value": val_str, "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Net Profit: {val_str}",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            # 3. Total Assets
            assets_curr, _ = get_val("Assets", bs.get("total_assets", []))
            if assets_curr:
                label = evaluate_fact_sentiment("Assets", str(assets_curr))
                raw_data.append({
                    "metric": "Total Assets", "value": f"{currency} {assets_curr:,.2f}", "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Total Assets: {currency} {assets_curr:,.2f}",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            # 4. Cash & Bank
            cash_curr, _ = get_val("CashAndBankBalances", bs.get("current_assets", []))
            if cash_curr:
                label = evaluate_fact_sentiment("Cash", str(cash_curr))
                raw_data.append({
                    "metric": "Cash & Bank", "value": f"{currency} {cash_curr:,.2f}", "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Cash & Bank: {currency} {cash_curr:,.2f}",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            # 5. Ratios & Margins (Calculated if present)
            curr_assets, _ = get_val("CurrentAssets", bs.get("current_assets", []))
            curr_liabs, _ = get_val("CurrentLiabilities", bs.get("current_liabilities", []))
            if curr_assets and curr_liabs and curr_liabs != 0:
                ratio = curr_assets / curr_liabs
                label = evaluate_fact_sentiment("Current Ratio", f"{ratio:.2f}")
                raw_data.append({
                    "metric": "Current Ratio", "value": f"{ratio:.2f}x", "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Current Ratio: {ratio:.2f}x",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            total_liabs, _ = get_val("Liabilities", bs.get("total_liabilities", []))
            total_equity, _ = get_val("Equity", bs.get("equity", []))
            if total_liabs and total_equity and total_equity != 0:
                der = total_liabs / total_equity
                label = evaluate_fact_sentiment("Debt-to-Equity", f"{der:.2f}")
                raw_data.append({
                    "metric": "Debt-to-Equity", "value": f"{der:.2f}x", "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Debt-to-Equity: {der:.2f}x",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            if rev_curr and prof_curr and rev_curr != 0:
                margin = (prof_curr / rev_curr) * 100
                label = evaluate_fact_sentiment("Net Margin", f"{margin:.1f}%")
                raw_data.append({
                    "metric": "Net Margin", "value": f"{margin:.1f}%", "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Net Margin: {margin:.1f}%",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            if total_equity and assets_curr and assets_curr != 0:
                eq_ratio = (total_equity / assets_curr) * 100
                label = evaluate_fact_sentiment("Equity Ratio", f"{eq_ratio:.1f}%")
                raw_data.append({
                    "metric": "Equity Ratio", "value": f"{eq_ratio:.1f}%", "period": period_str,
                    "source_type": "financial", "snippet": f"XBRL Key Metric - Equity Ratio: {eq_ratio:.1f}%",
                    "finbert_sentiment": {"label": label, "score": 0.99}
                })

            # --- Process full statements for comprehensive evidence ---
            def process_rows(rows, section_name):
                for row in rows:
                    if row.get("current") is not None:
                        label = row.get("label", "Unknown")
                        val = row.get("current")
                        sentiment = evaluate_fact_sentiment(label, str(val))
                        raw_data.append({
                            "metric": label,
                            "value": f"{currency} {val:,.2f}",
                            "period": period_str,
                            "context": section_name,
                            "source_type": "financial",
                            "snippet": f"XBRL {label}: {currency} {val:,.2f} ({period_str}) - {section_name}",
                            "finbert_sentiment": {"label": sentiment, "score": 0.99}
                        })

            process_rows(bs.get("current_assets", []), "Balance Sheet - Current Assets")
            process_rows(bs.get("noncurrent_assets", []), "Balance Sheet - Noncurrent Assets")
            process_rows(bs.get("total_assets", []), "Balance Sheet - Total Assets")
            process_rows(bs.get("current_liabilities", []), "Balance Sheet - Current Liabilities")
            process_rows(bs.get("noncurrent_liabilities", []), "Balance Sheet - Noncurrent Liabilities")
            process_rows(bs.get("total_liabilities", []), "Balance Sheet - Total Liabilities")
            process_rows(bs.get("equity", []), "Balance Sheet - Equity")
            
            process_rows(report.get("income_statement", []), "Income Statement")
            process_rows(report.get("cash_flow", []), "Cash Flow Statement")
            
            # Also add key entity info points
            for label, val in report.get("entity_info", {}).items():
                raw_data.append({
                    "metric": label,
                    "value": str(val),
                    "period": period_str,
                    "context": "Entity Information",
                    "source_type": "financial",
                    "snippet": f"XBRL {label}: {val} - Entity Info"
                })
            
    enriched_data = []
    for item in raw_data:
        # Bypass FinBERT if sentiment has already been assigned manually (e.g. via rule-based engine)
        if "finbert_sentiment" in item:
            enriched_data.append(item)
            continue
            
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
