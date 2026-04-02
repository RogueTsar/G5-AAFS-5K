"""
G5-AAFS: Credit Risk Assessment Application
Main entry point — streamlit run app.py
"""

from dotenv import load_dotenv
import os

load_dotenv("AAFS.env")
load_dotenv()

from frontend.hitl_ui import render_hitl

if __name__ == "__main__":
    render_hitl()
