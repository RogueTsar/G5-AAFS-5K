"""
G5-AAFS: Credit Risk Assessment Application
Main entry point — launches the Streamlit application.

Usage:
    streamlit run app.py              # Main analysis UI
    streamlit run frontend/hitl_ui.py # Enhanced HITL workstation
"""

from dotenv import load_dotenv
import os

# Load from AAFS.env (shared team keys) then fallback to .env
load_dotenv("AAFS.env")
load_dotenv()  # fallback

from frontend import render

if __name__ == "__main__":
    render()
