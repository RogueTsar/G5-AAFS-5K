import io
import pandas as pd
from pypdf import PdfReader
from typing import Dict, Any, List
from src.core.state import AgentState
from src.core.logger import log_agent_action

def document_processing_agent(state: AgentState) -> Dict[str, Any]:
    """
    Parses uploaded documents and extracts text for analysis.
    Supported formats: PDF, Excel, Text, XBRL (XML-based).
    """
    uploaded_docs = state.get("uploaded_docs", [])
    if not uploaded_docs:
        log_agent_action("document_processing_agent", "No documents uploaded to process.")
        return {"doc_extracted_text": []}

    log_agent_action("document_processing_agent", f"Processing {len(uploaded_docs)} uploaded documents.")
    extracted_results = []

    for doc in uploaded_docs:
        filename = doc.get("filename", "unknown")
        content = doc.get("content", b"")
        file_ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        try:
            text = ""
            doc_type = ""
            
            if file_ext == "pdf":
                doc_type = "PDF"
                reader = PdfReader(io.BytesIO(content))
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            elif file_ext in ["xlsx", "xls"]:
                doc_type = "Excel"
                df_dict = pd.read_excel(io.BytesIO(content), sheet_name=None)
                for sheet_name, df in df_dict.items():
                    text += f"--- Sheet: {sheet_name} ---\n"
                    text += df.to_csv(index=False) + "\n"
            
            elif file_ext in ["txt", "xbrl", "xml"]:
                doc_type = file_ext.upper()
                text = content.decode("utf-8", errors="ignore")
            
            else:
                doc_type = "Unknown"
                text = content.decode("utf-8", errors="ignore")[:1000] # Partial read for safety
                
            extracted_results.append({
                "filename": filename,
                "text": text,
                "type": doc_type
            })
            log_agent_action("document_processing_agent", f"Successfully processed {filename} ({doc_type})")
            
        except Exception as e:
            log_agent_action("document_processing_agent", f"Error processing {filename}: {str(e)}")
            extracted_results.append({
                "filename": filename,
                "text": f"Error: {str(e)}",
                "type": "Error"
            })

    return {"doc_extracted_text": extracted_results}
