# regex + deterministic checks
import re
from typing import List, Tuple

MAX_INPUT_LENGTH = 120

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+all\s+prior",
    r"system\s+prompt",
    r"developer\s+message",
    r"reveal\s+prompt",
    r"act\s+as\s+",
    r"bypass\s+rules",
]

CODE_PATTERNS = [
    r"drop\s+table",
    r"delete\s+from",
    r"insert\s+into",
    r"update\s+\w+\s+set",
    r"select\s+.+\s+from",
    r"<script.*?>",
    r"rm\s+-rf",
    r"curl\s+http",
    r"wget\s+http",
]

ACTION_PATTERNS = [
    r"send\s+email",
    r"transfer\s+money",
    r"buy\s+stock",
    r"execute\s+trade",
    r"wire\s+funds",
    r"book\s+meeting",
]

COMPANY_HINTS = {
    "inc", "corp", "corporation", "ltd", "limited", "llc", "plc",
    "pte", "co", "company", "holdings", "group", "bank"
}


def normalize_text(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value


def contains_pattern(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def has_suspicious_chars(text: str) -> bool:
    return bool(re.search(r"[^a-zA-Z0-9\s\.\-&',()/]", text))


def sanitize_query(text: str) -> str:
    cleaned = re.sub(r"[^\w\s\.\-&',()/]", "", text)
    return normalize_text(cleaned)


def classify_entity_heuristic(name: str) -> str:
    lowered = name.lower()
    if any(hint in lowered for hint in COMPANY_HINTS):
        return "company"

    tokens = name.split()
    if 2 <= len(tokens) <= 4 and all(token[:1].isupper() for token in tokens if token):
        return "individual"

    return "unknown"


def run_rule_checks(normalized_input: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    risk_flags: List[str] = []

    if not normalized_input:
        errors.append("No entity name was provided.")

    if len(normalized_input) > MAX_INPUT_LENGTH:
        errors.append(f"Input is too long. Maximum length is {MAX_INPUT_LENGTH} characters.")

    if len(normalized_input) < 2:
        errors.append("Input is too short to identify an entity.")

    if contains_pattern(normalized_input, INJECTION_PATTERNS):
        errors.append("Input contains prompt-injection style instructions.")
        risk_flags.append("prompt_injection")

    if contains_pattern(normalized_input, CODE_PATTERNS):
        errors.append("Input contains code or command-like content.")
        risk_flags.append("code_or_command")

    if contains_pattern(normalized_input, ACTION_PATTERNS):
        errors.append("Input contains action-oriented instructions, not entity lookup.")
        risk_flags.append("unsafe_action_request")

    if has_suspicious_chars(normalized_input):
        risk_flags.append("suspicious_characters")

    if " and " in normalized_input.lower() or "," in normalized_input:
        risk_flags.append("multiple_entities_possible")

    return errors, risk_flags