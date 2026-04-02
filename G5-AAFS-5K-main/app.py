"""
G5-AAFS: Credit Risk Assessment Application
Unified entry point — launches the HITL credit assessment workstation.
Run: streamlit run app.py
"""

from dotenv import load_dotenv
import os

load_dotenv()

# Import the unified UI (sidebar-driven, dual-view)
from frontend.hitl_ui import render_hitl

if __name__ == "__main__":
    render_hitl()
