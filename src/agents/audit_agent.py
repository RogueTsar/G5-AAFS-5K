"""
Audit Agent -- compiles a structured JSON audit trail for
MAS FEAT and EU AI Act compliance. Uses ONE focused LLM call
to assess compliance QUALITY beyond simple field-presence checks.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from collections import Counter
from src.core.state import AgentState
from src.core.llm import get_llm
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


def _build_compliance_context(state: AgentState) -> str:
    """Build a concise summary of pipeline outputs for the LLM to evaluate."""
    parts = []

    # Explanations quality
    explanations = state.get("explanations", [])
    if explanations:
        sample = explanations[:3]
        expl_texts = []
        for e in sample:
            if isinstance(e, dict):
                expl_texts.append(e.get("explanation", e.get("text", str(e)))[:120])
            else:
                expl_texts.append(str(e)[:120])
        parts.append(f"EXPLANATIONS ({len(explanations)} total, sample): {'; '.join(expl_texts)}")

    # Risk factors
    risks = state.get("extracted_risks", [])
    if risks:
        risk_cats = []
        for r in risks[:5]:
            if isinstance(r, dict):
                cat = r.get("category", "unknown")
                desc = r.get("description", r.get("text", ""))[:80]
                risk_cats.append(f"{cat}: {desc}")
        parts.append(f"RISKS ({len(risks)} total): {'; '.join(risk_cats)}")

    # Risk score
    risk_score = state.get("risk_score")
    if isinstance(risk_score, dict):
        parts.append(f"RISK SCORE: {risk_score.get('score', '?')}/{risk_score.get('max', 100)} "
                      f"rating={risk_score.get('rating', '?')}")
    elif risk_score is not None:
        parts.append(f"RISK SCORE: {risk_score}")

    # Final report snippet
    report = state.get("final_report", "")
    if report:
        parts.append(f"REPORT SNIPPET: {str(report)[:200]}")

    # Agents executed and data breadth
    agents = _get_agents_executed(state)
    sources = _count_data_sources(state)
    parts.append(f"AGENTS RUN: {', '.join(agents)}")
    parts.append(f"DATA SOURCES: {json.dumps(sources)}")

    # Strengths
    strengths = state.get("extracted_strengths", [])
    if strengths:
        parts.append(f"STRENGTHS IDENTIFIED: {len(strengths)}")

    return "\n".join(parts)


def _run_llm_compliance_assessment(state: AgentState, checklist_compliance: dict) -> dict:
    """
    Single LLM call to assess compliance quality beyond field presence.
    Returns dict with compliance_narrative, compliance_recommendations,
    and regulatory_risk_level. Returns empty defaults on failure.
    """
    llm = get_llm(temperature=0)
    if not llm:
        log_agent_action(AGENT_NAME, "LLM not available, skipping quality assessment")
        return {}

    context = _build_compliance_context(state)
    company = state.get("company_name", "unknown")

    prompt = f"""You are a regulatory compliance auditor. Assess this AI due-diligence pipeline output for {company}.

PIPELINE OUTPUT SUMMARY:
{context}

CHECKLIST STATUS: MAS FEAT passed={checklist_compliance['mas_feat_passed']}, EU AI Act passed={checklist_compliance['eu_ai_act_passed']}

Evaluate against these frameworks concisely:
- MAS FEAT Transparency: Are explanations genuinely transparent or boilerplate?
- MAS FEAT Fairness: Do risk factors reveal potential bias (geographic, sector, demographic)?
- MAS FEAT Accountability: Is the audit trail complete enough for a regulator?
- MAS FEAT Ethics: Are ethical considerations reflected in the analysis?
- EU AI Act Art.6: Is the risk classification appropriate?
- EU AI Act Art.9: Is the risk management approach adequate?
- EU AI Act Art.14: Are there human oversight gaps?

Respond in EXACTLY this JSON format (no markdown):
{{"narrative": "<2-3 sentence compliance quality assessment>", "recommendations": ["<action1>", "<action2>", "<action3>"], "risk_level": "<low|medium|high>"}}"""

    try:
        log_agent_action(AGENT_NAME, "Invoking LLM for compliance quality assessment", {
            "company": company,
            "context_length": len(context),
        })
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Parse the JSON response -- strip markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        parsed = json.loads(content)

        result = {
            "compliance_narrative": parsed.get("narrative", ""),
            "compliance_recommendations": parsed.get("recommendations", []),
            "regulatory_risk_level": parsed.get("risk_level", "medium"),
        }

        # Validate risk_level
        if result["regulatory_risk_level"] not in ("low", "medium", "high"):
            result["regulatory_risk_level"] = "medium"

        log_agent_action(AGENT_NAME, "LLM compliance assessment complete", {
            "risk_level": result["regulatory_risk_level"],
            "recommendations_count": len(result["compliance_recommendations"]),
        })

        return result

    except Exception as e:
        log_agent_action(AGENT_NAME, f"LLM compliance assessment failed: {str(e)}")
        return {}


def audit_agent(state: AgentState) -> Dict[str, Any]:
    """Compile structured audit trail for regulatory compliance with LLM quality assessment."""
    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    company_name = state.get("company_name", "unknown")
    errors = state.get("errors", [])

    log_agent_action(AGENT_NAME, "Starting audit trail compilation", {
        "company": company_name,
    })

    agents_executed = _get_agents_executed(state)
    data_sources_used = _count_data_sources(state)
    tier_distribution = _get_source_tier_distribution(state)

    # --- Checklist-based compliance (structural foundation) ---
    mas_feat_passed = _check_compliance(state, MAS_FEAT_REQUIRED)
    eu_ai_act_passed = _check_compliance(state, EU_AI_ACT_REQUIRED)

    checklist_compliance = {
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
    }

    # --- LLM-powered quality assessment (single call, ~300 tokens) ---
    llm_assessment = _run_llm_compliance_assessment(state, checklist_compliance)

    # Build final audit trail, merging checklist + LLM results
    audit_trail = {
        "run_id": run_id,
        "timestamp": timestamp,
        "company": company_name,
        "pipeline_version": PIPELINE_VERSION,
        "agents_executed": agents_executed,
        "data_sources_used": data_sources_used,
        "source_tiers_distribution": tier_distribution,
        "errors_encountered": errors,
        "compliance": checklist_compliance,
        # New LLM-assessed fields (fall back to defaults if LLM unavailable)
        "compliance_narrative": llm_assessment.get(
            "compliance_narrative",
            "LLM assessment unavailable. Checklist-only compliance reported."
        ),
        "compliance_recommendations": llm_assessment.get(
            "compliance_recommendations",
            []
        ),
        "regulatory_risk_level": llm_assessment.get(
            "regulatory_risk_level",
            "medium" if (mas_feat_passed and eu_ai_act_passed) else "high"
        ),
    }

    log_agent_action(AGENT_NAME, "Audit trail compiled", {
        "run_id": run_id,
        "agents_executed_count": len(agents_executed),
        "total_data_items": sum(data_sources_used.values()),
        "errors_count": len(errors),
        "mas_feat_passed": mas_feat_passed,
        "eu_ai_act_passed": eu_ai_act_passed,
        "llm_assessment_available": bool(llm_assessment),
        "regulatory_risk_level": audit_trail["regulatory_risk_level"],
    })

    return {"audit_trail": audit_trail}
