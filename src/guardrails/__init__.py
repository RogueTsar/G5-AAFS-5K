"""Guardrails package for the G5-AAFS credit risk assessment pipeline.

Exports all guardrail modules for input validation, output enforcement,
hallucination detection, bias/fairness checks, cascade control,
content safety, and the unified GuardrailRunner.
"""

from src.guardrails.input_guardrails import (
    normalize_text,
    contains_pattern,
    has_suspicious_chars,
    sanitize_query,
    classify_entity_heuristic,
    run_rule_checks,
)

from src.guardrails.output_enforcer import (
    enforce_risk_extraction,
    enforce_risk_score,
    enforce_explanations,
    confidence_floor_filter,
    schema_hard_stop,
)

from src.guardrails.hallucination_detector import (
    check_entity_attribution,
    verify_company_in_output,
    flag_fabricated_metrics,
)

from src.guardrails.bias_fairness import (
    detect_proxy_variables,
    filter_protected_class_references,
    generate_fairness_disclaimer,
    check_mas_feat_compliance,
    check_eu_ai_act_compliance,
)

from src.guardrails.cascade_guard import (
    validate_agent_output,
    should_abort_pipeline,
    create_fallback_output,
)

from src.guardrails.content_safety import (
    filter_report_content,
    add_regulatory_footer,
    validate_score_language_consistency,
)

from src.guardrails.guardrail_runner import GuardrailRunner
