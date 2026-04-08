import os
import re
from langchain_openai import ChatOpenAI
from typing import Optional

# Default timeout for LLM calls (seconds)
LLM_TIMEOUT = 30


def get_llm(temperature: float = 0.0) -> Optional[ChatOpenAI]:
    """
    Returns an instance of ChatOpenAI configured with gpt-4o-mini.
    Returns None if the API key is not found.
    Includes a 30-second request timeout to prevent indefinite hangs.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found in environment variables.")
        return None

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        request_timeout=LLM_TIMEOUT,
    )


def sanitize_for_prompt(text: str, max_length: int = 200) -> str:
    """Sanitize user-provided text before interpolating into LLM prompts.

    Strips control characters, newlines, and limits length to prevent
    prompt injection via company names, titles, or other user inputs.
    """
    if not text:
        return ""
    # Strip control chars (except space)
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(text))
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Truncate
    return cleaned[:max_length]


def extract_json_from_llm(content: str) -> str:
    """Extract JSON from LLM response, handling markdown fences robustly.

    Handles: bare JSON, ```json fenced, ``` fenced, JSON with preamble text.
    Returns the extracted string (still needs json.loads).
    """
    if not content:
        return "{}"
    content = content.strip()
    # Try to find JSON inside markdown fences
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    # Try to find a JSON object directly
    obj_match = re.search(r'\{.*\}', content, re.DOTALL)
    if obj_match:
        return obj_match.group(0)
    return content
