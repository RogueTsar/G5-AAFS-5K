from typing import Any

from src.core.state import AgentState
from src.core.logger import log_agent_action

from src.agents.input_models import InputRequest, InputValidationResult
from src.guardrails.input_guardrails import (
    normalize_text,
    sanitize_query,
    classify_entity_heuristic,
    run_rule_checks,
)
# Optional: enable later if needed
# from src.agents.input_llm import classify_input_with_llm


def input_agent(state: AgentState) -> AgentState:
    """
    First-stage input validation and sanitisation agent.

    Responsibilities:
    1. Validate raw input structure with Pydantic
    2. Apply deterministic guardrails (regex/rule-based)
    3. Normalise and sanitise query
    4. Classify likely entity type (company / individual / unknown)
    5. Return only safe, structured fields for downstream agents

    Downstream contract for source discovery agent:
    - state["source_query"]
    - state["source_entity_type"]
    - state["entity_input"]
    """

    raw_input = (
        state.get("entity_name")
        or state.get("company_name")
        or state.get("person_name")
        or state.get("input")
        or ""
    )

    raw_input = str(raw_input)

    log_agent_action(
        "input_agent",
        "Received raw input",
        {"raw_input": raw_input},
    )

    try:
        request = InputRequest(raw_input=raw_input)
    except Exception as e:
        error_message = str(e)

        result = InputValidationResult(
            raw_input=raw_input,
            normalized_input="",
            safe_query="",
            entity_type="unknown",
            intent="unsafe",
            is_safe=False,
            is_valid=False,
            risk_flags=["schema_validation_failed"],
            rationale=error_message,
        )

        log_agent_action(
            "input_agent",
            "Pydantic validation failed",
            {"error": error_message, "result": result.model_dump()},
        )

        return {
            "entity_input": result.model_dump(),
            "errors": [error_message],
            "source_query": "",
            "source_entity_type": "unknown",
        }  # type: ignore

    normalized_input = normalize_text(request.raw_input)
    safe_query = sanitize_query(normalized_input)

    errors, risk_flags = run_rule_checks(normalized_input)

    if errors:
        result = InputValidationResult(
            raw_input=request.raw_input,
            normalized_input=normalized_input,
            safe_query=safe_query,
            entity_type="unknown",
            intent="unsafe",
            is_safe=False,
            is_valid=False,
            risk_flags=risk_flags,
            rationale="Rejected by deterministic input guardrails.",
        )

        log_agent_action(
            "input_agent",
            "Rejected by rule-based checks",
            {
                "result": result.model_dump(),
                "errors": errors,
            },
        )

        return {
            "entity_input": result.model_dump(),
            "errors": errors,
            "source_query": "",
            "source_entity_type": "unknown",
        }  # type: ignore

    heuristic_entity_type = classify_entity_heuristic(normalized_input)
    entity_type = heuristic_entity_type
    intent = "entity_lookup"
    rationale = "Classified by heuristic."

    # Optional LLM fallback for ambiguous cases
    # if heuristic_entity_type == "unknown":
    #     try:
    #         llm_result = classify_input_with_llm(normalized_input)
    #         entity_type = llm_result.entity_type
    #         intent = llm_result.intent
    #         rationale = llm_result.rationale
    #
    #         if intent == "unsafe":
    #             risk_flags.append("llm_marked_unsafe")
    #
    #         if intent == "broad_search":
    #             risk_flags.append("broad_query")
    #
    #     except Exception as e:
    #         entity_type = "unknown"
    #         intent = "entity_lookup"
    #         rationale = f"LLM classification unavailable; fallback used. Error: {str(e)}"
    #         risk_flags.append("llm_classification_fallback")

    is_safe = intent != "unsafe"
    is_valid = bool(safe_query) and is_safe

    result = InputValidationResult(
        raw_input=request.raw_input,
        normalized_input=normalized_input,
        safe_query=safe_query,
        entity_type=entity_type,
        intent=intent,
        is_safe=is_safe,
        is_valid=is_valid,
        risk_flags=risk_flags,
        rationale=rationale,
    )

    if not is_valid:
        log_agent_action(
            "input_agent",
            "Validation failed after classification",
            {"result": result.model_dump()},
        )

        return {
            "entity_input": result.model_dump(),
            "errors": ["Input could not be safely validated."],
            "source_query": "",
            "source_entity_type": "unknown",
        }  # type: ignore

    output: dict[str, Any] = {
        "entity_input": result.model_dump(),
        "entity_name": result.safe_query,
        "source_query": result.safe_query,
        "source_entity_type": result.entity_type,
        "errors": [],
    }

    if result.entity_type == "company":
        output["company_name"] = result.safe_query
        output["person_name"] = None
    elif result.entity_type == "individual":
        output["company_name"] = None
        output["person_name"] = result.safe_query
    else:
        output["company_name"] = None
        output["person_name"] = None

    log_agent_action(
        "input_agent",
        "Validation successful",
        {"result": result.model_dump(), "output_keys": list(output.keys())},
    )

    return output  # type: ignore