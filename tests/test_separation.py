import os
import sys
from dotenv import load_dotenv

# Add src to python path
sys.path.append(os.getcwd())

from src.core.orchestrator import create_workflow
from src.core.state import AgentState

def test_data_separation():
    load_dotenv()
    
    # Initialize workflow
    app = create_workflow()
    
    # Initial state
    initial_state = {
        "company_name": "Tesla",
        "uploaded_docs": [],
        "doc_extracted_text": [],
        "news_data": [],
        "social_data": [],
        "review_data": [],
        "financial_data": [],
        "financial_news_data": [],
        "errors": []
    }
    
    print("--- Starting Workflow ---")
    
    # Run the workflow and capture intermediate states
    # We'll run it and look at the state after financial_agent and data_cleaning_agent
    try:
        # Run the full graph for Tesla
        result = app.invoke(initial_state)
        
        print("\n--- Verification ---")
        
        # 1. Check if financial_data and financial_news_data are separate keys in the final state
        # (Note: LangGraph merges results into the state)
        
        fin_metrics = result.get("financial_data", [])
        fin_news = result.get("financial_news_data", [])
        
        print(f"Items in financial_data (metrics): {len(fin_metrics)}")
        for idx, item in enumerate(fin_metrics):
             print(f"  {idx}: Source: {item.get('source')}, Type: {item.get('source_type', 'Not Set')}")
             
        print(f"Items in financial_news_data: {len(fin_news)}")
        for idx, item in enumerate(fin_news):
             print(f"  {idx}: Source: {item.get('source')}, Type: {item.get('source_type', 'Not Set')}")

        # 2. Check cleaned_data in the final state to see if source_type was correctly assigned
        cleaned = result.get("cleaned_data", [])
        print(f"\nItems in cleaned_data: {len(cleaned)}")
        
        for idx, item in enumerate(cleaned):
            source = item.get("source", "unknown")
            stype = item.get("source_type", "unknown")
            # If it's a financial snippet (has 'content' and not yfinance)
            is_newsapi = "content" in item and source == "web_search"
            is_yfinance = source == "yfinance"
            
            if is_yfinance:
                # Metrics should have a synthetic label used by the scoring agent
                # (Note: data_cleaning_agent doesn't set it, calculate_source_score does it on the fly)
                # But we can verify metrics exist
                print(f"  Item {idx}: Source: {source}, Metrics Count: {len(item.get('metrics', {}))}")
            elif is_newsapi:
                 print(f"  Item {idx}: Source: {source}, Assigned Source Type: {stype}")

        # 3. Check the breakdown in risk_score
        risk_score = result.get("risk_score", {})
        breakdown = risk_score.get("breakdown", {})
        print(f"\n--- Risk Score Breakdown ---")
        for cat, score in breakdown.items():
            print(f"  {cat}: {score}")
        
        # Verify yfinance (structured) is not just 50 if metrics are clear
        # For Tesla in the previous run, metrics were:
        # debtToEquity: 17.76% (<100) -> Not Negative
        # currentRatio: 2.164 (>1.5) -> Positive? 
        # revenueGrowth: -0.031 (>-0.05) -> Neutral
        # 4. Verify extracted risks and strengths have impact
        risks = result.get("extracted_risks", [])
        strengths = result.get("extracted_strengths", [])
        
        print(f"\n--- Extracted Risks (Prioritized) ---")
        for r in risks:
            print(f"  [{r.get('impact')}] {r.get('type')}: {r.get('description')}")
            
        print(f"\n--- Extracted Strengths (Prioritized) ---")
        for s in strengths:
            print(f"  [{s.get('impact')}] {s.get('type')}: {s.get('description')}")

        # 5. Check the final report
        print(f"\n--- Final Report (First 500 chars) ---")
        print(result.get("final_report", "")[:500])

    except Exception as e:
        print(f"Error during execution: {str(e)}")

if __name__ == "__main__":
    test_data_separation()
