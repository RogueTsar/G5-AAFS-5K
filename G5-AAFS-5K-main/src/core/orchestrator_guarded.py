"""Guarded orchestrator for the G5-AAFS credit-risk pipeline.

This module is **additive-only** -- it does NOT modify the original
``orchestrator.py``, ``state.py``, or any existing agent files.  Instead it:

1. Defines ``GuardedAgentState``, which extends ``AgentState`` with the extra
   fields required by the new agents (industry_context, press_release_analysis,
   audit_trail, guardrail_warnings).
2. Creates thin wrapper functions that apply ``GuardrailRunner`` checks
   before and/or after the relevant agents.
3. Wires everything into a new LangGraph ``StateGraph`` via
   ``create_guarded_workflow()``.

Graph flow
----------
START -> guarded_input -> discovery
                       -> document_processor
discovery -> news, social, review, financial, press_release  (fan-out)
[news, social, review, financial, press_release, document_processor] -> data_cleaning  (fan-in)
data_cleaning -> source_credibility  (parallel branch A)
data_cleaning -> industry_context    (parallel branch B)
[source_credibility, industry_context] -> entity_resolution
entity_resolution -> guarded_risk_extraction
guarded_risk_extraction -> guarded_risk_scoring
guarded_risk_scoring -> confidence
confidence -> guarded_explainability
guarded_explainability -> guarded_reviewer
guarded_reviewer -> audit
audit -> END
"""

from __future__ import annotations

import operator
from typing import Any, Dict, List

from typing_extensions import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END

# -- Existing state & agents ------------------------------------------------
from src.core.state import AgentState
from src.agents.input_agent import input_agent
from src.agents.discovery_agent import discovery_agent
from src.agents.collection_agents import (
    news_agent,
    social_agent,
    review_agent,
    financial_agent,
)
from src.agents.document_processing_agent import document_processing_agent
from src.agents.processing_agents import (
    data_cleaning_agent,
    entity_resolution_agent,
)
from src.agents.analysis_agents import (
    risk_extraction_agent,
    risk_scoring_agent,
    explainability_agent,
)
from src.agents.reviewer_agent import reviewer_agent

# -- New agents --------------------------------------------------------------
from src.agents.source_credibility_agent import source_credibility_agent
from src.agents.confidence_agent import confidence_agent
from src.agents.audit_agent import audit_agent
from src.agents.industry_context_agent import industry_context_agent
from src.agents.press_release_agent import press_release_agent

# -- Guardrails --------------------------------------------------------------
from src.guardrails.guardrail_runner import GuardrailRunner

__all__ = ["create_guarded_workflow"]

# ---------------------------------------------------------------------------
# Extended state
# ---------------------------------------------------------------------------


class GuardedAgentState(TypedDict):
    """Flattened state that includes all AgentState fields plus new agent fields.

    We explicitly re-declare every field from AgentState rather than using
    TypedDict inheritance because LangGraph's StateGraph introspects
    ``__annotations__`` on the immediate class only — Annotated reducers
    from parent TypedDicts may not be visible, causing fan-in to silently
    overwrite instead of accumulate.
    """

    # -- Original AgentState fields (copied verbatim) -----------------------
    company_name: str
    company_info: Dict[str, Any]
    search_queries: Dict[str, List[str]]
    company_aliases: List[str]
    uploaded_docs: List[Dict[str, Any]]
    doc_extracted_text: List[Dict[str, Any]]
    news_data: Annotated[List[Dict[str, Any]], operator.add]
    social_data: Annotated[List[Dict[str, Any]], operator.add]
    review_data: Annotated[List[Dict[str, Any]], operator.add]
    financial_data: Annotated[List[Dict[str, Any]], operator.add]
    cleaned_data: List[Dict[str, Any]]
    resolved_entities: Dict[str, Any]
    extracted_risks: List[Dict[str, Any]]
    extracted_strengths: List[Dict[str, Any]]
    risk_score: Dict[str, Any]
    explanations: List[Dict[str, Any]]
    final_report: str
    errors: Annotated[List[str], operator.add]

    # -- New fields for augmented pipeline ----------------------------------
    industry_context: Dict[str, Any]
    press_release_analysis: Dict[str, Any]
    audit_trail: Dict[str, Any]
    guardrail_warnings: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Guarded wrapper factory
# ---------------------------------------------------------------------------


def _make_guarded_wrappers(runner: GuardrailRunner):
    """Create guarded wrapper functions that share a single GuardrailRunner.

    Each call to ``create_guarded_workflow()`` gets its own runner instance
    so concurrent pipelines don't pollute each other's audit logs.
    """

    def guarded_input(state: GuardedAgentState) -> dict:
        company_name = state.get("company_name", "")
        sanitized, is_valid, warnings = runner.validate_input(company_name)
        if not is_valid:
            return {
                "company_name": sanitized,
                "errors": [f"Input guardrail blocked: {'; '.join(warnings)}"],
                "guardrail_warnings": warnings,
            }
        patched_state = dict(state)
        patched_state["company_name"] = sanitized
        result = input_agent(patched_state)
        out = dict(result) if isinstance(result, dict) else {"company_name": sanitized}
        if warnings:
            out["guardrail_warnings"] = warnings
        return out

    def guarded_risk_extraction(state: GuardedAgentState) -> dict:
        result = risk_extraction_agent(state)
        validated, warnings = runner.validate_agent_output(
            "risk_extraction", result, dict(state)
        )
        if warnings:
            validated["guardrail_warnings"] = warnings
        return validated

    def guarded_risk_scoring(state: GuardedAgentState) -> dict:
        result = risk_scoring_agent(state)
        validated, warnings = runner.validate_agent_output(
            "risk_scoring", result, dict(state)
        )
        if warnings:
            validated["guardrail_warnings"] = warnings
        return validated

    def guarded_explainability(state: GuardedAgentState) -> dict:
        result = explainability_agent(state)
        validated, warnings = runner.validate_agent_output(
            "explainability", result, dict(state)
        )
        if warnings:
            validated["guardrail_warnings"] = warnings
        return validated

    def guarded_reviewer(state: GuardedAgentState) -> dict:
        result = reviewer_agent(state)
        report = result.get("final_report", "") if isinstance(result, dict) else ""
        cleaned_report, validation_results = runner.validate_final_report(
            report, dict(state)
        )
        out = dict(result) if isinstance(result, dict) else {}
        out["final_report"] = cleaned_report
        all_warnings = validation_results.get("warnings", [])
        if all_warnings:
            out["guardrail_warnings"] = all_warnings
        return out

    return guarded_input, guarded_risk_extraction, guarded_risk_scoring, guarded_explainability, guarded_reviewer


# ---------------------------------------------------------------------------
# Workflow factory
# ---------------------------------------------------------------------------


def create_guarded_workflow():
    """Build and compile the guarded LangGraph workflow.

    Returns a compiled LangGraph application with guardrail wrappers
    around the input, risk-extraction, risk-scoring, explainability,
    and reviewer agents, plus the five new agents wired into the graph.

    Each call creates a fresh GuardrailRunner so concurrent pipelines
    maintain isolated audit logs.
    """
    runner = GuardrailRunner()
    (
        guarded_input,
        guarded_risk_extraction,
        guarded_risk_scoring,
        guarded_explainability,
        guarded_reviewer,
    ) = _make_guarded_wrappers(runner)

    workflow = StateGraph(GuardedAgentState)

    # -- Nodes ---------------------------------------------------------------
    # Guarded wrappers
    workflow.add_node("guarded_input", guarded_input)
    workflow.add_node("guarded_risk_extraction", guarded_risk_extraction)
    workflow.add_node("guarded_risk_scoring", guarded_risk_scoring)
    workflow.add_node("guarded_explainability", guarded_explainability)
    workflow.add_node("guarded_reviewer", guarded_reviewer)

    # Existing agents (unwrapped)
    workflow.add_node("discovery", discovery_agent)
    workflow.add_node("document_processor", document_processing_agent)
    workflow.add_node("news", news_agent)
    workflow.add_node("social", social_agent)
    workflow.add_node("review", review_agent)
    workflow.add_node("financial", financial_agent)
    workflow.add_node("data_cleaning", data_cleaning_agent)
    workflow.add_node("entity_resolution", entity_resolution_agent)

    # New agents
    workflow.add_node("press_release", press_release_agent)
    workflow.add_node("source_credibility", source_credibility_agent)
    workflow.add_node("confidence", confidence_agent)
    workflow.add_node("audit", audit_agent)
    workflow.add_node("industry_context", industry_context_agent)

    # -- Edges ---------------------------------------------------------------
    # Entry
    workflow.add_edge(START, "guarded_input")

    # Fan-out from guarded_input
    workflow.add_edge("guarded_input", "discovery")
    workflow.add_edge("guarded_input", "document_processor")

    # Fan-out from discovery (includes new press_release agent)
    workflow.add_edge("discovery", "news")
    workflow.add_edge("discovery", "social")
    workflow.add_edge("discovery", "review")
    workflow.add_edge("discovery", "financial")
    workflow.add_edge("discovery", "press_release")

    # Fan-in to data_cleaning
    workflow.add_edge(
        ["news", "social", "review", "financial", "press_release", "document_processor"],
        "data_cleaning",
    )

    # Parallel branches after data_cleaning
    workflow.add_edge("data_cleaning", "source_credibility")
    workflow.add_edge("data_cleaning", "industry_context")

    # Fan-in to entity_resolution
    workflow.add_edge(
        ["source_credibility", "industry_context"],
        "entity_resolution",
    )

    # Sequential tail
    workflow.add_edge("entity_resolution", "guarded_risk_extraction")
    workflow.add_edge("guarded_risk_extraction", "guarded_risk_scoring")
    workflow.add_edge("guarded_risk_scoring", "confidence")
    workflow.add_edge("confidence", "guarded_explainability")
    workflow.add_edge("guarded_explainability", "guarded_reviewer")
    workflow.add_edge("guarded_reviewer", "audit")
    workflow.add_edge("audit", END)

    # -- Compile -------------------------------------------------------------
    app = workflow.compile()
    return app
