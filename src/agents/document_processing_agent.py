import io
import pandas as pd
from pypdf import PdfReader
from typing import Dict, Any, List
from src.core.state import AgentState
from src.core.logger import log_agent_action
from src.mcp_tools.xbrl_parser import parse_xbrl

_xbrl_cache: list = []

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
            
            elif file_ext in ["xbrl", "xml"]:
                doc_type = "XBRL"
                raw_xml = content.decode("utf-8", errors="ignore")
                try:
                    xbrl_data = parse_xbrl(raw_xml)
                    # Build a plain text summary for downstream agents (must be str, not dict)
                    summary_parts = []
                    ei = xbrl_data.get("entity_info", {})
                    if ei.get("company_name"):
                        summary_parts.append(f"Company: {ei['company_name']}")
                    for section in ["balance_sheet", "income_statement", "cash_flow", "ratios"]:
                        sect_data = xbrl_data.get(section, {})
                        if isinstance(sect_data, dict):
                            for k, v in sect_data.items():
                                if v is not None and not isinstance(v, dict):
                                    summary_parts.append(f"{k}: {v}")
                    text_summary = "\n".join(summary_parts) if summary_parts else raw_xml[:2000]
                    # Store text only in doc_extracted_text (no nested dicts)
                    extracted_results.append({
                        "filename": filename,
                        "text": text_summary,
                        "type": "XBRL_STRUCTURED",
                    })
                    _xbrl_cache.append(xbrl_data)
                    log_agent_action("document_processing_agent", f"Successfully parsed XBRL: {filename} ({len(raw_xml)} chars)")
                    continue
                except Exception as parse_err:
                    log_agent_action("document_processing_agent", f"XBRL parse failed for {filename}, falling back to raw text: {parse_err}")
                    text = raw_xml

            elif file_ext in ["txt"]:
                doc_type = "TXT"
                text = content.decode("utf-8", errors="ignore")

            elif file_ext == "xsd":
                doc_type = "XSD_SCHEMA"
                text = content.decode("utf-8", errors="ignore")[:2000]
            
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

    return {"doc_extracted_text": extracted_results, "xbrl_parsed_data": _xbrl_cache}
