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
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def setup_custom_css():
    """Apply custom CSS styling."""
    st.markdown("""
        <style>
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
        </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "company_name" not in st.session_state:
        st.session_state.company_name = ""
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


def render_company_input() -> tuple[str, bool]:
    """
    Render company input section.
    
    Returns:
        tuple: (company_name, submit_button_clicked)
    """
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("## 📋 Company Analysis")
        
        with st.container():
            st.markdown('<div class="flow-diagram">', unsafe_allow_html=True)
            st.subheader("Step 1: Enter Company Information")
            
            col_input1, col_input2 = st.columns([3, 1])
            
            with col_input1:
                company_input = st.text_input(
                    "Company Name",
                    value=st.session_state.company_name,
                    placeholder="e.g., Apple Inc., Tesla, Microsoft...",
                    help="Enter the company name to analyze"
                )
            
            with col_input2:
                st.write("")  # Spacing to align with input field
                submit_button = st.button(
                    "🚀 Start Analysis",
                    use_container_width=True,
                    type="primary"
                )
            
            uploaded_files = st.file_uploader(
                "Enhance Analysis with Documents (Optional)",
                type=["pdf", "xlsx", "xls", "txt", "xbrl", "xml"],
                accept_multiple_files=True,
                help="Upload financial reports, news transcripts, or spreadsheets to improve risk assessment accuracy."
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            if submit_button and company_input.strip():
                st.session_state.company_name = company_input.strip()
                st.session_state.analysis_started = True
                st.success(f"✅ Analysis started for: **{st.session_state.company_name}**")
                
                # Prepare uploaded docs for the graph
                docs_for_graph = []
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        docs_for_graph.append({
                            "filename": uploaded_file.name,
                            "content": uploaded_file.read()
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
                    st.session_state.edited_risks = final_state.get("extracted_risks", [])
                    st.session_state.edited_strengths = final_state.get("extracted_strengths", [])
                    st.session_state.ready_for_review = True
                    st.success("✅ AI Analysis Phase Complete. Please review the findings below.")
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
                    st.session_state.ready_for_review = False
    
    return company_input.strip() if company_input else "", submit_button


def render_pipeline_overview():
    """Render pipeline overview tab."""
    st.markdown("### Complete Analysis Flow")
    
    stages = [
        ("1. Input Processing", "Parsing company information"),
        ("2. Source Discovery", "Identifying relevant data sources"),
        ("3. Data Collection (Parallel)", "Gathering data from multiple sources"),
        ("4. Data Aggregation", "Combining raw data"),
        ("5. Embeddings & Vector Storage", "Processing data for RAG"),
        ("6. Risk Extraction", "Identifying risk factors"),
        ("7. Risk Scoring", "Calculating risk metrics"),
        ("8. Review & Validation", "Human review of results"),
        ("9. Report Generation", "Creating final analysis")
    ]
    
    for stage, description in stages:
        st.markdown(
            f'<div class="step-container"><b>{stage}</b><br><small>{description}</small></div>',
            unsafe_allow_html=True
        )


def render_data_collection():
    """Render data collection agents tab."""
    st.markdown("### Data Collection Agents")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Data Sources")
        st.info("📰 **News Agent**\nCollects company news and press releases")
        st.info("📱 **Social Media Agent**\nMonitors social media mentions and sentiment")
    
    with col2:
        st.markdown("#### ⠀")  # Spacing
        st.info("⭐ **Review Agent**\nGathers customer/employee reviews")
        st.info("📑 **Financial Agent**\nAnalyzes SEC filings and financial reports")


def render_analysis_scoring():
    """Render analysis and scoring tab."""
    st.markdown("### Analysis & Scoring")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Risk Extraction", "Ready", delta="In Progress")
    
    with col2:
        st.metric("Risk Scoring", "Pending", delta="-")
    
    st.markdown("---")
    st.info("🤖 **RAG Retrieval** - Context-aware information retrieval using embeddings")


def render_results():
    """Render results and report tab."""
    st.markdown("### Results & Report")
    
    if st.session_state.get("analysis_complete", False):
        st.success("Analysis Complete!")
        
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
            
        # Display Weighted Breakdown
        breakdown = risk_info.get("breakdown", {})
        if breakdown:
            with st.expander("📊 View Weighted Score Breakdown", expanded=False):
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
        st.markdown(st.session_state.get("final_report", ""))
        
        st.markdown("### 🔍 Raw API Data")
        with st.expander("View Financial Data (Yahoo Finance)", expanded=False):
            st.json(st.session_state.final_state.get("financial_data", []))
            
        with st.expander("View News Data (General Web Search)", expanded=False):
            st.json(st.session_state.final_state.get("news_data", []))

        with st.expander("View Targeted Financial News (NewsAPI/Tavily)", expanded=False):
            st.json(st.session_state.final_state.get("financial_news_data", []))

        with st.expander("View Social Sentiment Data (Tavily)", expanded=False):
            st.json(st.session_state.final_state.get("social_data", []))

        with st.expander("View Review Data (Tavily)", expanded=False):
            st.json(st.session_state.final_state.get("review_data", []))

        # Visual XBRL Financial Statements Display
        xbrl_data = st.session_state.final_state.get("xbrl_parsed_data", [])
        if xbrl_data:
            st.markdown("### XBRL Financial Statements")
            from frontend.xbrl_display import render_xbrl_financials
            render_xbrl_financials(xbrl_data)

        with st.expander("View Uploaded Document Data (Processed)", expanded=False):
            st.json(st.session_state.final_state.get("doc_extracted_text", []))

        with st.expander("View Uploaded Document Data (Structured)", expanded=False):
            st.json(st.session_state.final_state.get("doc_structured_data", []))
            
    elif st.session_state.get("ready_for_review", False):
        st.info("👋 AI has completed its initial scan. Review and refine the findings below.")
        
        from src.agents.reviewer_agent import reviewer_agent
        
        st.markdown("### ✍️ Analyst Review Stage")
        st.write("Modify AI-detected risks and strengths, or add your own expert notes.")

        # Editable Dataframes for HITL
        impact_options = ["High", "Medium", "Low"]
        risk_type_options = ["Traditional Risk", "Non-traditional Risk"]
        strength_type_options = ["Financial Strength", "Market Strength"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚩 Red Flags")
            edited_risks = st.data_editor(
                st.session_state.edited_risks,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "type": st.column_config.SelectboxColumn("Category", options=risk_type_options, required=True),
                    "impact": st.column_config.SelectboxColumn("Severity", options=impact_options, required=True),
                    "description": st.column_config.TextColumn("Risk Factor Description", required=True)
                },
                key="risk_editor"
            )
            
        with col2:
            st.subheader("✅ Green Flags")
            edited_strengths = st.data_editor(
                st.session_state.edited_strengths,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "type": st.column_config.SelectboxColumn("Category", options=strength_type_options, required=True),
                    "impact": st.column_config.SelectboxColumn("Significance", options=impact_options, required=True),
                    "description": st.column_config.TextColumn("Strength Description", required=True)
                },
                key="strength_editor"
            )

        if st.button("📝 Finalize & Generate Report", type="primary", use_container_width=True):
            with st.spinner("Composing final executive report with your expert edits..."):
                try:
                    # Update state with human edits
                    final_state = st.session_state.final_state
                    final_state["extracted_risks"] = edited_risks
                    final_state["extracted_strengths"] = edited_strengths
                    
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
    st.markdown("## 🔄 Analysis Pipeline")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Results",
        "🔍 Data Collection",
        "🎯 Analysis & Scoring",
        "📊 Pipeline Overview"
    ])
    
    with tab1:
        render_results()
    
    with tab2:
        render_data_collection()
    
    with tab3:
        render_analysis_scoring()
    
    with tab4:
        render_pipeline_overview()
    
    # Progress section
    st.markdown("---")
    st.markdown("### 📊 Progress Tracking")
    st.progress(0)
    
    stages_list = [
        "Input Processing",
        "Source Discovery",
        "News Collection",
        "Social Media Scraping",
        "Reviews Collection",
        "Financial Data Gathering",
        "Data Aggregation",
        "Embedding Generation",
        "RAG Retrieval",
        "Risk Extraction",
        "Risk Scoring",
        "Review & Validation",
        "Report Generation"
    ]
    
    st.markdown(f"**Company:** {st.session_state.company_name}")


def render_quick_start():
    """Render welcome section when no analysis has started."""
    st.markdown('<div class="flow-diagram">', unsafe_allow_html=True)
    st.markdown("### 🎯 Quick Start")
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
    
    st.title("🔍 G5-AAFS: Credit Risk Assessment")
    
    render_sidebar()
    render_quick_start()
    render_company_input()
    
    if st.session_state.analysis_started:
        render_analysis_pipeline()
        
    
    render_footer()
