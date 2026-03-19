"""
G5-AAFS: Credit Risk Assessment Application
Main entry point for the Streamlit application
"""

from frontend import render
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


if __name__ == "__main__":
    render()
