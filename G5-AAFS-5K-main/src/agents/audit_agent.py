"""
Audit Agent — compiles a structured JSON audit trail for
MAS FEAT and EU AI Act compliance. Uses 0 LLM tokens.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from collections import Counter
from src.core.state import AgentState
from src.core.logger import log_agent_action

AGENT_NAME = "audit_agent"
PIPELINE_VERSION = "1.0.0"

# Map state fields to the agent that produces them
AGENT_OUTPUT_FIELDS = {
    "company_info": "input_agent",
    "search_queries": "discovery_agent",
    "company_aliases": "discovery_agent",
    "doc_extracted_text": "document_processing_agent",
    "news_data": "news_agent",
    "social_data": "social_agent",
    "review_data": "review_agent",
    "financial_data": "financial_agent",
    "cleaned_data": "processing_agents",
    "resolved_entities": "entity_resolution_agent",
    "extracted_risks": "risk_extraction_agent",
    "extracted_strengths": "strength_extraction_agent",
    "risk_score": "risk_scoring_agent",
    "explanations": "explanation_agent",
    "final_report": "reviewer_agent",
}

# Fields required for MAS FEAT compliance
MAS_FEAT_REQUIRED = [
    "cleaned_data",
    "extracted_risks",
    "risk_score",
    "explanations",
    "final_report",
]

# Fields required for EU AI Act compliance
EU_AI_ACT_REQUIRED = [
    "cleaned_data",
    "extracted_risks",
    "risk_score",
    "explanations",
]


def _count_data_sources(state: AgentState) -> Dict[str, int]:
    """Count items in each data collection field."""
    source_fields = ["news_data", "social_data", "review_data",
                     "financial_data", "doc_extracted_text"]
    counts = {}
    for field in source_fields:
        data = state.get(field)
        if data and isinstance(data, list):
            counts[field] = len(data)
        else:
            counts[field] = 0
    return counts


def _get_agents_executed(state: AgentState) -> List[str]:
    """Determine which agents produced output by checking state fields."""
    executed = []
    for field, agent_name in AGENT_OUTPUT_FIELDS.items():
        value = state.get(field)
        if value is not None:
            if isinstance(value, (list, dict, str)):
                if len(value) > 0:
                    executed.append(agent_name)
            else:
                executed.append(agent_name)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for name in executed:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def _get_source_tier_distribution(state: AgentState) -> Dict[str, int]:
    """Count items per source_tier in cleaned_data."""
    cleaned_data = state.get("cleaned_data", [])
    tiers = [item.get("source_tier", "unclassified") for item in cleaned_data]
    return dict(Counter(tiers))


def _check_compliance(state: AgentState, required_fields: List[str]) -> bool:
    """Check if all required fields have non-empty data."""
    for field in required_fields:
        value = state.get(field)
        if not value:
            return False
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            return False
    return True


def audit_agent(state: AgentState) -> Dict[str, Any]:
    """Compile structured audit trail for regulatory compliance."""
    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    company_name = state.get("company_name", "unknown")
    errors = state.get("errors", [])

    agents_executed = _get_agents_executed(state)
    data_sources_used = _count_data_sources(state)
    tier_distribution = _get_source_tier_distribution(state)

    mas_feat_passed = _check_compliance(state, MAS_FEAT_REQUIRED)
    eu_ai_act_passed = _check_compliance(state, EU_AI_ACT_REQUIRED)

    audit_trail = {
        "run_id": run_id,
        "timestamp": timestamp,
        "company": company_name,
        "pipeline_version": PIPELINE_VERSION,
        "agents_executed": agents_executed,
        "data_sources_used": data_sources_used,
        "source_tiers_distribution": tier_distribution,
        "errors_encountered": errors,
        "compliance": {
            "mas_feat_passed": mas_feat_passed,
            "eu_ai_act_passed": eu_ai_act_passed,
            "mas_feat_missing": [
                f for f in MAS_FEAT_REQUIRED
                if not state.get(f) or (isinstance(state.get(f), (list, dict, str)) and len(state.get(f)) == 0)
            ] if not mas_feat_passed else [],
            "eu_ai_act_missing": [
                f for f in EU_AI_ACT_REQUIRED
                if not state.get(f) or (isinstance(state.get(f), (list, dict, str)) and len(state.get(f)) == 0)
            ] if not eu_ai_act_passed else [],
        },
    }

    log_agent_action(AGENT_NAME, "Audit trail compiled", {
        "run_id": run_id,
        "agents_executed_count": len(agents_executed),
        "total_data_items": sum(data_sources_used.values()),
        "errors_count": len(errors),
        "mas_feat_passed": mas_feat_passed,
        "eu_ai_act_passed": eu_ai_act_passed,
    })

    return {"audit_trail": audit_trail}
