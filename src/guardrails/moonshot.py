"""
Mini Moonshot: A lightweight implementation of key AI safety checks.
Inspired by Singapore's Project Moonshot for AI safety.
"""

import re
from typing import List, Dict, Tuple

# common prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"disregard all previous instructions",
    r"system override",
    r"you are now a",
    r"forget what you were told",
    r"bypass safety",
]

# basic PII patterns (email, phone)
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone": r"\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
}

def check_prompt_injection(text: str) -> List[str]:
    """Search for common prompt injection patterns."""
    found = []
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            found.append(f"Potential injection detected: '{pattern}'")
    return found

def check_pii(text: str) -> List[str]:
    """Search for PII like emails and phone numbers."""
    found = []
    for label, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            # We don't list all matches to avoid leaking them in logs, just a count/flag
            found.append(f"Potential PII detected ({label}): found {len(matches)} occurrence(s).")
    return found

def run_mini_moonshot(text: str) -> Dict[str, List[str]]:
    """Run all Mini Moonshot safety checks."""
    return {
        "injection_warnings": check_prompt_injection(text),
        "pii_warnings": check_pii(text),
    }
