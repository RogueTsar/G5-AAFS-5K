"""
Frontend UI components for G5-AAFS Risk Assessment Application
"""

import streamlit as st
from typing import Optional
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.orchestrator import create_workflow


def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="G5-AAFS Risk Analyzer",
        page_icon="G5",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def setup_custom_css():
    """Apply custom CSS styling based on the selected theme."""
    theme = st.session_state.get("theme", "Light")
    
    if theme == "Purple Galaxy":
        st.markdown("""
            <style>
                /* Global Font Configuration */
                html, body, p, label, li, td, th, [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"] {
                    font-family: Arial, sans-serif !important;
                }
                h1, h2, h3, h4, h5, h6, h1 *, h2 *, h3 *, h4 *, h5 *, h6 * {
                    font-family: "Times New Roman", Times, serif !important;
                }
                
                .stApp {
                    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                    background-attachment: fixed;
                    color: white !important;
                }
                .main {
                    max-width: 1200px;
                }
                /* Glassmorphism containers */
                .flow-diagram, .step-container, [data-testid="stExpander"], .stMetric {
                    background: rgba(255, 255, 255, 0.08) !important;
                    backdrop-filter: blur(12px) !important;
                    border: 1px solid rgba(255, 255, 255, 0.15) !important;
                    border-radius: 12px !important;
                    padding: 20px !important;
                    color: white !important;
                }
                /* Header and text colors */
                h1, h2, h3, h4, h5, h6, b, p, label, .stMarkdown {
                    color: #e0d1ff !important;
                }
                /* Metric values */
                [data-testid="stMetricValue"] {
                    color: #ffffff !important;
                }
                /* Tabs */
                .stTabs [data-baseweb="tab-list"] button {
                    font-size: 16px;
                    color: #d8c4ff !important;
                }
                .stTabs [data-baseweb="tab-highlight"] {
                    background-color: #9d50bb !important;
                }
                /* Sidebar fix */
                [data-testid="stSidebar"] {
                    background-color: #1a1525 !important;
                }
                /* Buttons */
                .stButton > button {
                    background: linear-gradient(90deg, #9d50bb, #6e48aa) !important;
                    border: none !important;
                    color: white !important;
                    transition: all 0.3s ease;
                }
                .stButton > button:hover {
                    box-shadow: 0 0 15px rgba(157, 80, 187, 0.6);
                    transform: translateY(-2px);
                }
                /* Print styles */
                @media print {
                    * {
                        background: transparent !important;
                        color: black !important;
                        text-shadow: none !important;
                        box-shadow: none !important;
                    }
                    body, .stApp, .main, .block-container, [data-testid="stAppViewContainer"], [data-testid="stVerticalBlock"] {
                        background: white !important;
                        background-color: white !important;
                    }
                    /* Hide everything non-report */
                    [data-testid="stSidebar"], 
                    [data-testid="stHeader"],
                    .stTabs [data-baseweb="tab-list"],
                    [data-testid="stHorizontalBlock"],
                    .stButton,
                    .stAlert,
                    [data-testid="stMetric"],
                    [data-testid="stExpander"],
                    footer,
                    .stApp > header,
                    h2, h3, hr {
                        display: none !important;
                    }
                    /* Ensure only the report content is visible */
                    .printable-report {
                        display: block !important;
                        visibility: visible !important;
                        width: 100% !important;
                    }
                    .printable-report h2, .printable-report h3, .printable-report hr {
                        display: block !important;
                    }
                    .main {
                        max-width: 100% !important;
                        padding: 0 !important;
                    }
                }
            </style>
        """, unsafe_allow_html=True)
    elif theme == "UBS Corporate":
        st.markdown("""
            <style>
                /* Global Font Configuration */
                html, body, p, label, li, td, th, [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"] {
                    font-family: Arial, sans-serif !important;
                    color: #000000 !important;
                }
                h1, h2, h3, h4, h5, h6, h1 *, h2 *, h3 *, h4 *, h5 *, h6 * {
                    font-family: "Times New Roman", Times, serif !important;
                    color: #1a1a1a !important;
                }
                
                .stApp {
                    background: linear-gradient(to bottom right, #ffffff, #f2f2f2) !important;
                    background-attachment: fixed !important;
                }
                .main {
                    max-width: 1200px;
                }
                /* Sidebar fix */
                [data-testid="stSidebar"] {
                    background-color: #1a1a1a !important;
                }
                [data-testid="stSidebar"] [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
                    color: #ffffff !important;
                }
                /* Selectbox styling */
                [data-testid="stSidebar"] [data-baseweb="select"] > div {
                    background-color: #2a2a2a !important;
                    border-color: #444 !important;
                }
                [data-testid="stSidebar"] [data-baseweb="select"] span {
                    color: #ffffff !important;
                }
                div[data-baseweb="popover"] ul {
                    background-color: #2a2a2a !important;
                }
                div[data-baseweb="popover"] ul li {
                    color: #ffffff !important;
                }
                div[data-baseweb="popover"] ul li:hover {
                    background-color: #e60000 !important;
                }
                /* Top Header Accent */
                [data-testid="stHeader"] {
                    background-color: #1a1a1a !important;
                    border-bottom: 4px solid #e60000 !important;
                }
                [data-testid="stHeader"] * {
                    color: #ffffff !important;
                }
                /* Clean Corporate containers */
                .flow-diagram, .step-container, [data-testid="stExpander"], .stMetric {
                    background-color: #fcfcfc !important;
                    border: 1px solid #e8e8e8 !important;
                    border-left: 4px solid #e60000 !important;
                    border-radius: 0px !important;
                    padding: 20px !important;
                    color: #000000 !important;
                }
                [data-testid="stSidebar"] [data-testid="stExpander"] {
                    background-color: #2a2a2a !important;
                    border: 1px solid #444 !important;
                    border-left: 4px solid #e60000 !important;
                }
                [data-testid="stSidebar"] [data-testid="stExpander"] * {
                    color: #ffffff !important;
                }
                /* Metric values */
                [data-testid="stMetricValue"] {
                    color: #e60000 !important;
                }
                /* Tabs */
                .stTabs [data-baseweb="tab-list"] button {
                    font-size: 16px;
                    color: #555555 !important;
                }
                .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
                    color: #e60000 !important;
                    font-weight: bold;
                }
                .stTabs [data-baseweb="tab-highlight"] {
                    background-color: #e60000 !important;
                }
                /* Buttons */
                button[kind="primary"], button[kind="secondary"] {
                    background-color: #e60000 !important;
                    border: none !important;
                    color: white !important;
                    border-radius: 0px !important;
                    text-transform: uppercase;
                    font-weight: bold;
                    letter-spacing: 0.5px;
                    transition: all 0.2s ease;
                }
                button[kind="primary"] *, button[kind="secondary"] * {
                    color: white !important;
                }
                button[kind="primary"]:hover, button[kind="secondary"]:hover {
                    background-color: #b30000 !important;
                    box-shadow: none !important;
                }
                /* Uploaded File Texts */
                [data-testid="stUploadedFile"] * {
                    color: #1a1a1a !important;
                }
                /* Tooltips */
                [data-baseweb="tooltip"] * {
                    color: #ffffff !important;
                }
                /* Print styles */
                @media print {
                    * {
                        background: transparent !important;
                        color: black !important;
                        text-shadow: none !important;
                        box-shadow: none !important;
                    }
                    body, .stApp, .main, .block-container, [data-testid="stAppViewContainer"], [data-testid="stVerticalBlock"] {
                        background: white !important;
                        background-color: white !important;
                    }
                    /* Hide everything non-report */
                    [data-testid="stSidebar"], 
                    [data-testid="stHeader"],
                    .stTabs [data-baseweb="tab-list"],
                    [data-testid="stHorizontalBlock"],
                    .stButton,
                    .stAlert,
                    [data-testid="stMetric"],
                    [data-testid="stExpander"],
                    footer,
                    .stApp > header,
                    h2, h3, hr {
                        display: none !important;
                    }
                    /* Ensure only the report content is visible */
                    .printable-report {
                        display: block !important;
                        visibility: visible !important;
                        width: 100% !important;
                    }
                    .printable-report h2, .printable-report h3, .printable-report hr {
                        display: block !important;
                    }
                    .main {
                        max-width: 100% !important;
                        padding: 0 !important;
                    }
                }
            </style>
        """, unsafe_allow_html=True)
    else:
        # Standard Light/Corporate theme
        st.markdown("""
            <style>
                /* Global Font Configuration */
                html, body, p, label, li, td, th, [data-testid="stMarkdownContainer"], [data-testid="stMetricValue"] {
                    font-family: Arial, sans-serif !important;
                }
                h1, h2, h3, h4, h5, h6, h1 *, h2 *, h3 *, h4 *, h5 *, h6 * {
                    font-family: "Times New Roman", Times, serif !important;
                }
                
                .main {
                    max-width: 1200px;
                }
                .stTabs [data-baseweb="tab-list"] button {
                    font-size: 16px;
                }
                .flow-diagram {
                    background-color: #f0f2f6;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }
                .step-container {
                    background-color: #e8f4f8;
                    padding: 15px;
                    border-left: 4px solid #0066cc;
                    margin: 10px 0;
                    border-radius: 5px;
                }
                .success-message {
                    background-color: #d4edda;
                    padding: 15px;
                    border-radius: 5px;
                    border: 1px solid #c3e6cb;
                }
                /* Print styles */
                @media print {
                    * {
                        background: transparent !important;
                        color: black !important;
                        text-shadow: none !important;
                        box-shadow: none !important;
                    }
                    body, .stApp, .main, .block-container, [data-testid="stAppViewContainer"], [data-testid="stVerticalBlock"] {
                        background: white !important;
                        background-color: white !important;
                    }
                    [data-testid="stSidebar"], 
                    [data-testid="stHeader"],
                    .stTabs [data-baseweb="tab-list"],
                    [data-testid="stHorizontalBlock"],
                    .stButton,
                    .stAlert,
                    [data-testid="stMetric"],
                    [data-testid="stExpander"],
                    footer,
                    .stApp > header,
                    h2, h3, hr {
                        display: none !important;
                    }
                    .printable-report {
                        display: block !important;
                        visibility: visible !important;
                        width: 100% !important;
                    }
                    .printable-report h2, .printable-report h3, .printable-report hr {
                        display: block !important;
                    }
                    .main {
                        max-width: 100% !important;
                        padding: 0 !important;
                    }
                }
            </style>
        """, unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "company_name" not in st.session_state:
        st.session_state.company_name = ""
    if "theme" not in st.session_state:
        st.session_state.theme = "Light"
    if "analysis_started" not in st.session_state:
        st.session_state.analysis_started = False
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = None
    if "ready_for_review" not in st.session_state:
        st.session_state.ready_for_review = False
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
    if "edited_risks" not in st.session_state:
        st.session_state.edited_risks = []
    if "edited_strengths" not in st.session_state:
        st.session_state.edited_strengths = []


def render_sidebar():
    """Render sidebar with configuration options."""
    with st.sidebar:
        st.header("Configuration")
        
        with st.expander("API Keys & Settings", expanded=False):
            st.info("Configure your API keys and settings here")
            st.text_input("News API Key", type="password", placeholder="Enter your News API key")
            st.text_input("Financial API Key", type="password", placeholder="Enter your Financial API key")
            
        st.markdown("---")
        st.subheader("Appearance")
        options = ["Light", "Purple Galaxy", "UBS Corporate"]
        st.selectbox(
            "Select UI Theme",
            options=["Light", "Purple Galaxy", "UBS Corporate"],
            key="theme",
            help="Switch between standard, premium gallery, and corporate themes."
        )


def render_company_input() -> tuple[str, bool]:
    """
    Render company input section.
    
    Returns:
        tuple: (company_name, submit_button_clicked)
    """
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## Company Analysis")
        
        with st.container():
            st.markdown('<div class="flow-diagram">', unsafe_allow_html=True)
            st.subheader("Step 1: Enter Company Information")
            
            company_input = st.text_input(
                "Company Name",
                value=st.session_state.company_name,
                placeholder="e.g., Apple Inc., Tesla, Microsoft...",
                help="Enter the company name to analyze"
            )
            
            uploaded_files = st.file_uploader(
                "Enhance Analysis with Documents (Optional)",
                type=["pdf", "xlsx", "xls", "txt", "xbrl", "xml", "xsd", "html"],
                accept_multiple_files=True,
                help="Upload financial reports, news transcripts, or spreadsheets to improve risk assessment accuracy."
            )
            
            submit_button = st.button(
                "Start Analysis",
                width="stretch",
                type="primary"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if submit_button and company_input.strip():
                # Reset analysis state for a fresh run
                st.session_state.company_name = company_input.strip()
                st.session_state.analysis_started = True
                st.session_state.ready_for_review = False
                st.session_state.analysis_complete = False
                st.session_state.edited_risks = []
                st.session_state.edited_strengths = []
                st.session_state.final_report = ""
                
                st.success(f"Analysis started for: **{st.session_state.company_name}**")
                
                # Prepare uploaded docs for the graph
                docs_for_graph = []
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        docs_for_graph.append({
                            "filename": uploaded_file.name,
                            "content": uploaded_file.getvalue()
                        })
                
                # Execute LangGraph Pipeline with streaming progress
                progress_bar = st.progress(0, text="Initializing Multi-Agent Analysis Pipeline...")
                
                # Map nodes to progress percentage and status labels
                node_progress = {
                    "input": (10, "Parsing company information..."),
                    "discovery": (20, "Discovering data search queries..."),
                    "news": (40, "Collecting news data from NewsAPI..."),
                    "social": (45, "Gathering social sentiment (X/Reddit)..."),
                    "review": (50, "Analyzing employee and customer reviews..."),
                    "financial": (55, "Fetching structured financial ratios..."),
                    "document_processor": (60, "Extracting text from uploaded docs..."),
                    "document_metrics": (70, "Identifying structured metrics in documents..."),
                    "data_cleaning": (80, "Consolidating and cleaning data points..."),
                    "entity_resolution": (85, "Resolving corporate entities and aliases..."),
                    "risk_extraction": (90, "Extracting risk and strength signals..."),
                    "risk_scoring": (93, "Calculating weighted risk scores..."),
                    "explainability": (96, "Generating metric-level justifications..."),
                    "reviewer": (100, "Composing final executive report...")
                }

                try:
                    app = create_workflow()
                    initial_state = {
                        "company_name": st.session_state.company_name,
                        "uploaded_docs": docs_for_graph
                    }
                    
                    final_state = initial_state
                    # Use streaming to update the progress bar as nodes finish
                    for event in app.stream(initial_state):
                        # Each event contains one or more completed nodes
                        for node_name in event.keys():
                            # STOP before the reviewer node to allow manual intervention
                            if node_name == "reviewer":
                                continue
                                
                            if node_name in node_progress:
                                prg, label = node_progress[node_name]
                                progress_bar.progress(prg, text=label)
                            
                            # Accumulate the state changes from each node
                            final_state.update(event[node_name])
                    
                    # Store the results for human review
                    st.session_state.final_state = final_state
                    
                    # Initialize editable lists with a template row if empty
                    risks = final_state.get("extracted_risks", [])
                    if not risks:
                        risks = [{"type": "Traditional Risk", "impact": "Medium", "description": "Type to add a new risk...", "Exclude?": False}]
                    else:
                        for r in risks: r["Exclude?"] = False
                    st.session_state.edited_risks = risks
                    
                    strengths = final_state.get("extracted_strengths", [])
                    if not strengths:
                        strengths = [{"type": "Financial Strength", "impact": "Medium", "description": "Type to add a new strength...", "Exclude?": False}]
                    else:
                        for s in strengths: s["Exclude?"] = False
                    st.session_state.edited_strengths = strengths
                    
                    st.session_state.ready_for_review = True
                    st.success("Analysis Phase Complete. Please review the findings below.")
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
                    st.session_state.ready_for_review = False
    
    return company_input.strip() if company_input else "", submit_button




def render_data_collection():
    """Render the detailed analysis data points tab."""
    st.markdown("### Raw API Data")
    
    if st.session_state.get("analysis_complete", False) or st.session_state.get("ready_for_review", False):
        final_state = st.session_state.get("final_state", {})
        
        with st.expander("View Financial Data (Yahoo Finance)", expanded=False):
            st.json(final_state.get("financial_data", []))
            
        with st.expander("View News Data (General Web Search)", expanded=False):
            st.json(final_state.get("news_data", []))

        with st.expander("View Targeted Financial News (NewsAPI/Tavily)", expanded=False):
            st.json(final_state.get("financial_news_data", []))

        with st.expander("View Social Sentiment Data (Tavily)", expanded=False):
            st.json(final_state.get("social_data", []))

        with st.expander("View Review Data (Tavily)", expanded=False):
            st.json(final_state.get("review_data", []))

        # Visual XBRL Financial Statements Display
        xbrl_data = final_state.get("xbrl_parsed_data", [])
        if xbrl_data:
            st.markdown("### XBRL Financial Statements")
            from frontend.xbrl_display import render_xbrl_financials
            render_xbrl_financials(xbrl_data)

        with st.expander("View Uploaded Document Data (Processed)", expanded=False):
            st.json(final_state.get("doc_extracted_text", []))

        with st.expander("View Uploaded Document Data (Structured)", expanded=False):
            st.json(final_state.get("doc_structured_data", []))
            
        st.markdown(f"**Company:** {st.session_state.company_name}")
    else:
        st.info("Raw data will be available once the analysis phase completes.")




def render_data_points():
    """Render the detailed analysis data points tab."""
    st.markdown("### Analysis Data Points")
    st.write("These are the specific data points extracted, cleaned, and analyzed to generate the risk score.")
    
    if st.session_state.get("analysis_complete", False) or st.session_state.get("ready_for_review", False):
        final_state = st.session_state.get("final_state", {})
        cleaned_data = final_state.get("cleaned_data", [])
        
        if cleaned_data:
            # Flatten data for the dataframe
            display_data = []
            for item in cleaned_data:
                sentiment_info = item.get("finbert_sentiment", {})
                display_data.append({
                    "Source Type": item.get("source_type", "Unknown").title(),
                    "Sentiment": sentiment_info.get("label", "neutral").upper(),
                    "Confidence": f"{sentiment_info.get('score', 0):.2f}",
                    "Evidence Snippet": item.get("snippet", item.get("text", ""))[:500]
                })
            
            import pandas as pd
            df = pd.DataFrame(display_data)
            
            # Show searchable table
            st.dataframe(
                df,
                width="stretch",
                column_config={
                    "Sentiment": st.column_config.TextColumn("Sentiment", width="small"),
                    "Confidence": st.column_config.TextColumn("Conf.", width="small"),
                    "Source Type": st.column_config.TextColumn("Source", width="small"),
                    "Evidence Snippet": st.column_config.TextColumn("Evidence Snippet", width="large")
                }
            )
        else:
            st.warning("No processed data points found.")
    else:
        st.info("Data points will be available once the analysis phase completes.")


def render_results():
    """Render results and report tab."""
    st.markdown("### Results & Report")
    
    if st.session_state.get("analysis_complete", False):
        # Print Button
        col_p1, col_p2 = st.columns([4, 1])
        with col_p1:
            st.success("Analysis Complete!")
        with col_p2:
            if st.button("Save as PDF", width="stretch", help="Open browser print dialog to save as PDF"):
                import time
                # Trigger window.parent.print() via a tiny HTML component
                # Adding a timestamp ensures Streamlit treats this as a new component on every click
                st.components.v1.html(f"""
                    <script>
                        window.parent.print();
                        // {time.time()}
                    </script>
                """, height=0, width=0)

        final_state = st.session_state.get("final_state", {})
        risk_info = final_state.get("risk_score", {"score": 0, "rating": "Unknown"})
        
        # Prominent Summary Metrics
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Risk Score", f"{risk_info.get('score', 0)}/100")
        with m_col2:
            rating = risk_info.get("rating", "Unknown")
            color = "green" if rating == "Low" else "orange" if rating == "Medium" else "red"
            st.markdown(f"**Risk Rating:** <span style='color:{color}; font-size:24px;'>{rating}</span>", unsafe_allow_html=True)
        with m_col3:
            st.metric("Data Points", len(final_state.get("cleaned_data", [])))
            
        breakdown = risk_info.get("breakdown", {})
        if breakdown:
            with st.expander("View Weighted Score Breakdown", expanded=False):
                st.markdown("This score is calculated using a **60/20/12/8** weighted distribution (re-normalized if data is missing).")
                cols = st.columns(len(breakdown))
                for i, (cat, cat_score) in enumerate(breakdown.items()):
                    cat_name = cat.capitalize()
                    if cat == "structured":
                        cat_name = "Financial/Docs"
                    with cols[i]:
                        st.metric(cat_name, f"{cat_score:.1f}")
            
        st.markdown("---")
        
        # Render the actual report
        st.markdown(f'<div class="printable-report">\n\n{st.session_state.get("final_report", "")}\n\n</div>', unsafe_allow_html=True)
        
            
    elif st.session_state.get("ready_for_review", False):
        st.info("AI has completed its initial scan. Review and refine the findings below.")
        
        from src.agents.reviewer_agent import reviewer_agent
        
        st.markdown("### Analyst Review Stage")
        st.write("Modify AI-detected risks and strengths, or add your own expert notes. Check **'Exclude?'** to remove a finding.")

        # Editable Dataframes for HITL
        impact_options = ["High", "Medium", "Low"]
        risk_type_options = ["Traditional Risk", "Non-traditional Risk"]
        strength_type_options = ["Financial Strength", "Market Strength"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Risks")
            edited_risks = st.data_editor(
                st.session_state.edited_risks,
                num_rows="dynamic",
                width="stretch",
                column_config={
                    "Exclude?": st.column_config.CheckboxColumn("Exclude?", default=False, help="Check to remove this risk"),
                    "type": st.column_config.SelectboxColumn("Category", options=risk_type_options, required=True),
                    "impact": st.column_config.SelectboxColumn("Severity", options=impact_options, required=True),
                    "description": st.column_config.TextColumn("Risk Factor Description", required=True)
                },
                key="risk_editor"
            )
            
        with col2:
            st.subheader("Strengths")
            edited_strengths = st.data_editor(
                st.session_state.edited_strengths,
                num_rows="dynamic",
                width="stretch",
                column_config={
                    "Exclude?": st.column_config.CheckboxColumn("Exclude?", default=False, help="Check to remove this strength"),
                    "type": st.column_config.SelectboxColumn("Category", options=strength_type_options, required=True),
                    "impact": st.column_config.SelectboxColumn("Significance", options=impact_options, required=True),
                    "description": st.column_config.TextColumn("Strength Description", required=True)
                },
                key="strength_editor"
            )

        if st.button("Finalize & Generate Report", type="primary", width="stretch"):
            with st.spinner("Composing final executive report with your expert edits..."):
                try:
                    # Filter out excluded rows and empty templates
                    final_risks = [r for r in edited_risks if not r.get("Exclude?", False) and "Type to add" not in r.get("description", "")]
                    final_strengths = [s for s in edited_strengths if not s.get("Exclude?", False) and "Type to add" not in s.get("description", "")]
                    
                    # Update state with human edits
                    final_state = st.session_state.final_state
                    
                    # Mark as priority if they were edited or added by the user
                    original_risks = final_state.get("extracted_risks", [])
                    original_strengths = final_state.get("extracted_strengths", [])
                    
                    def mark_priority(current_list, original_list):
                        orig_desc = {r.get("description") for r in original_list}
                        for item in current_list:
                            if item.get("description") not in orig_desc:
                                item["priority"] = True
                                item["source"] = "Analyst Input"
                            else:
                                item["priority"] = False
                        return current_list

                    final_state["extracted_risks"] = mark_priority(final_risks, original_risks)
                    final_state["extracted_strengths"] = mark_priority(final_strengths, original_strengths)
                    
                    # Call reviewer agent manually
                    output = reviewer_agent(final_state)
                    
                    # Update session state with final results
                    st.session_state.final_report = output.get("final_report", "Report generation failed.")
                    st.session_state.analysis_complete = True
                    st.session_state.ready_for_review = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during report generation: {str(e)}")
    else:
        st.info("Final report will be displayed here once analysis completes")
        
        st.markdown("""
            **Report will include:**
            - Executive Summary
            - Key Risk Factors
            - Risk Scores & Ratings
            - Data Source Attribution
            - Recommendations
        """)


def render_analysis_pipeline():
    """Render the full analysis pipeline with tabs."""
    st.markdown("---")
    st.markdown("## Analysis Pipeline")
    
    tab1, tab2, tab3 = st.tabs([
        "Results",
        "Data Collection",
        "Analysis Data Points"
    ])
    
    with tab1:
        render_results()
    
    with tab2:
        render_data_collection()
    
    with tab3:
        render_data_points()


def render_quick_start():
    """Render welcome section when no analysis has started."""
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div class="flow-diagram">', unsafe_allow_html=True)
        st.markdown("### Quick Start")
        st.markdown("""
            1. Enter a company name
            2. Click "Start Analysis"
            3. Monitor the analysis pipeline
            4. View comprehensive risk report
        """)
        st.markdown('</div>', unsafe_allow_html=True)


def render_footer():
    """Render application footer."""
    st.markdown("---")
    st.markdown("""
    <small>
    G5-AAFS: Credit Risk Assessment | 
    Powered by MCP Agents & Streamlit
    </small>
    """, unsafe_allow_html=True)


def render():
    """Main render function - orchestrates all UI components."""
    setup_page_config()
    setup_custom_css()
    initialize_session_state()
    
    st.title("G5-AAFS: Credit Risk Assessment")
    
    render_sidebar()
    render_quick_start()
    render_company_input()
    
    if st.session_state.analysis_started:
        render_analysis_pipeline()
        
    
    render_footer()
