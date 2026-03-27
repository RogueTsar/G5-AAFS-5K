"""Cascade guard for multi-agent pipeline validation.

Provides agent-specific output validation, abort logic, and safe
fallback outputs so downstream agents always receive valid-shaped data.
"""

from typing import Tuple


# --- Agent schema registry ---
# Each entry defines required_keys and their expected types.
AGENT_SCHEMAS = {
    "input": {
        "required_keys": ["company_name"],
        "types": {"company_name": str},
    },
    "discovery": {
        "required_keys": ["discovery_data"],
        "types": {"discovery_data": (list, dict)},
    },
    "news": {
        "required_keys": ["news_data"],
        "types": {"news_data": list},
    },
    "social": {
        "required_keys": ["social_data"],
        "types": {"social_data": list},
    },
    "review": {
        "required_keys": ["review_data"],
        "types": {"review_data": list},
    },
    "financial": {
        "required_keys": ["financial_data"],
        "types": {"financial_data": (list, dict)},
    },
    "document_processor": {
        "required_keys": ["doc_extracted_text"],
        "types": {"doc_extracted_text": list},
    },
    "data_cleaning": {
        "required_keys": ["cleaned_data"],
        "types": {"cleaned_data": (list, dict)},
    },
    "entity_resolution": {
        "required_keys": ["resolved_entities"],
        "types": {"resolved_entities": (list, dict)},
    },
    "risk_extraction": {
        "required_keys": ["extracted_risks", "extracted_strengths"],
        "types": {"extracted_risks": list, "extracted_strengths": list},
    },
    "risk_scoring": {
        "required_keys": ["risk_score"],
        "types": {"risk_score": dict},
    },
    "explainability": {
        "required_keys": ["explanations"],
        "types": {"explanations": list},
    },
    "reviewer": {
        "required_keys": ["final_report"],
        "types": {"final_report": str},
    },
}

# --- Fallback outputs for each agent ---
FALLBACK_OUTPUTS = {
    "input": {"company_name": "Unknown Entity"},
    "discovery": {"discovery_data": []},
    "news": {"news_data": []},
    "social": {"social_data": []},
    "review": {"review_data": []},
    "financial": {"financial_data": []},
    "document_processor": {"doc_extracted_text": []},
    "data_cleaning": {"cleaned_data": []},
    "entity_resolution": {"resolved_entities": []},
    "risk_extraction": {"extracted_risks": [], "extracted_strengths": []},
    "risk_scoring": {"risk_score": {"score": 50, "max": 100, "rating": "Medium"}},
    "explainability": {
        "explanations": [
            {
                "metric": "Overall Assessment",
                "reason": "Insufficient data to generate detailed explanations.",
            }
        ]
    },
    "reviewer": {
        "final_report": "Unable to generate report due to insufficient upstream data."
    },
}


def validate_agent_output(
    agent_name: str, output: dict, state: dict
) -> Tuple[dict, list]:
    """Validate an agent's output against the AGENT_SCHEMAS registry.

    Checks required keys exist, are non-None, have correct types,
    and contain non-empty data where applicable.

    Returns (validated_output, warnings).
    """
    warnings = []

    if agent_name not in AGENT_SCHEMAS:
        warnings.append(f"Unknown agent '{agent_name}', skipping validation.")
        return output, warnings

    schema = AGENT_SCHEMAS[agent_name]
    if not isinstance(output, dict):
        warnings.append(
            f"Agent '{agent_name}' output is not a dict. Using fallback."
        )
        return create_fallback_output(agent_name), warnings

    validated = dict(output)

    for key in schema["required_keys"]:
        if key not in validated or validated[key] is None:
            warnings.append(
                f"Agent '{agent_name}' missing required key '{key}'. "
                "Inserting fallback value."
            )
            fallback = FALLBACK_OUTPUTS.get(agent_name, {})
            validated[key] = fallback.get(key)
            continue

        # Type check
        expected_type = schema["types"].get(key)
        if expected_type and not isinstance(validated[key], expected_type):
            warnings.append(
                f"Agent '{agent_name}' key '{key}' has wrong type "
                f"(expected {expected_type}, got {type(validated[key]).__name__}). "
                "Using fallback value."
            )
            fallback = FALLBACK_OUTPUTS.get(agent_name, {})
            validated[key] = fallback.get(key)
            continue

        # Non-empty check for collections
        value = validated[key]
        if isinstance(value, (list, dict)) and len(value) == 0:
            warnings.append(
                f"Agent '{agent_name}' key '{key}' is empty."
            )
        elif isinstance(value, str) and not value.strip():
            warnings.append(
                f"Agent '{agent_name}' key '{key}' is an empty string. "
                "Using fallback value."
            )
            fallback = FALLBACK_OUTPUTS.get(agent_name, {})
            validated[key] = fallback.get(key)

    return validated, warnings


def should_abort_pipeline(errors: list, threshold: int = 3) -> bool:
    """Return True if the number of errors meets or exceeds the threshold."""
    return len(errors) >= threshold


def create_fallback_output(agent_name: str) -> dict:
    """Return a safe default output for the given agent.

    Ensures downstream agents always receive valid-shaped data.
    """
    if agent_name in FALLBACK_OUTPUTS:
        # Return a copy to prevent mutation
        import copy
        return copy.deepcopy(FALLBACK_OUTPUTS[agent_name])
    return {}
