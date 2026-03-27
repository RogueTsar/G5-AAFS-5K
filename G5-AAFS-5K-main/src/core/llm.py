import os
from langchain_openai import ChatOpenAI
from typing import Optional

def get_llm(temperature: float = 0.0) -> Optional[ChatOpenAI]:
    """
    Returns an instance of ChatOpenAI configured with gpt-4o-mini.
    Returns None if the API key is not found.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found in environment variables.")
        return None
        
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
        api_key=api_key
    )
