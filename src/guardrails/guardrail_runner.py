"""Unified guardrail runner for the G5-AAFS credit risk pipeline.

Orchestrates all guardrail modules and maintains an audit log of every
check performed. Uses zero LLM tokens -- all checks are deterministic.
"""

from datetime import datetime, timezone
from typing import Tuple

from src.guardrails.input_guardrails import (
    normalize_text,
    sanitize_query,
    run_rule_checks,
    has_suspicious_chars,
)
from src.guardrails.output_enforcer import (
    enforce_risk_extraction,
    enforce_risk_score,
    enforce_explanations,
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
    check_mas_feat_compliance,
    check_eu_ai_act_compliance,
    generate_fairness_disclaimer,
)
from src.guardrails.cascade_guard import (
    validate_agent_output as cascade_validate,
    should_abort_pipeline,
    create_fallback_output,
)
from src.guardrails.content_safety import (
    filter_report_content,
    add_regulatory_footer,
    validate_score_language_consistency,
)


DEFAULT_CONFIG = {
    "input_guardrails": True,
    "output_enforcer": True,
    "hallucination_detector": True,
    "bias_fairness": True,
    "cascade_guard": True,
    "content_safety": True,
}


class GuardrailRunner:
    """Orchestrates all guardrail checks across the credit risk pipeline.

    Config dict allows toggling individual guardrail modules on/off.
    All decisions are logged to an internal audit trail.
    """

    def __init__(self, config: dict = None):
        """Initialize with optional config to toggle guardrails on/off."""
        self.config = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)
        self.audit_log: list = []
        self._total_checks = 0
        self._total_warnings = 0
        self._total_blocks = 0

    def _log(self, guardrail_name: str, action: str, details: dict) -> None:
        """Append an entry to the audit log."""
        self.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrail_name": guardrail_name,
            "action": action,
            "details": details,
        })

    def validate_input(
        self, company_name: str
    ) -> Tuple[str, bool, list]:
        """Run input guardrails on the company name.

        Returns (sanitized_name, is_valid, warnings).
        """
        self._total_checks += 1
        warnings = []

        if not self.config.get("input_guardrails", True):
            self._log("input_guardrails", "skipped", {"reason": "disabled"})
            return company_name, True, []

        normalized = normalize_text(company_name)
        errors, risk_flags = run_rule_checks(normalized)

        if has_suspicious_chars(normalized):
            sanitized = sanitize_query(normalized)
            warnings.append(
                f"Input sanitized: suspicious characters removed."
            )
        else:
            sanitized = normalized

        is_valid = len(errors) == 0

        if errors:
            self._total_blocks += 1
            warnings.extend(errors)

        if risk_flags:
            self._total_warnings += len(risk_flags)
            warnings.extend(
                [f"Risk flag: {flag}" for flag in risk_flags]
            )

        self._log("input_guardrails", "validated", {
            "original": company_name,
            "sanitized": sanitized,
            "is_valid": is_valid,
            "errors": errors,
            "risk_flags": risk_flags,
        })

        return sanitized, is_valid, warnings

    def validate_agent_output(
        self, agent_name: str, output: dict, state: dict
    ) -> Tuple[dict, list]:
        """Run cascade_guard and output_enforcer for a specific agent.

        Returns (validated_output, warnings).
        """
        self._total_checks += 1
        all_warnings = []

        # --- Cascade guard ---
        if self.config.get("cascade_guard", True):
            output, cascade_warnings = cascade_validate(
                agent_name, output, state
            )
            all_warnings.extend(cascade_warnings)
            self._log("cascade_guard", "validated", {
                "agent": agent_name,
                "warnings": cascade_warnings,
            })

        # --- Output enforcer (agent-specific) ---
        if self.config.get("output_enforcer", True):
            if agent_name == "risk_extraction":
                output, enforcer_warnings = enforce_risk_extraction(output)
                all_warnings.extend(enforcer_warnings)
                self._log("output_enforcer", "enforce_risk_extraction", {
                    "agent": agent_name,
                    "warnings": enforcer_warnings,
                })
            elif agent_name == "risk_scoring":
                # risk_scoring_agent returns {"risk_score": {...}} — unwrap for enforcer
                inner = output.get("risk_score", output)
                if isinstance(inner, dict) and "score" in inner:
                    inner, enforcer_warnings = enforce_risk_score(inner)
                    output["risk_score"] = inner
                else:
                    output, enforcer_warnings = enforce_risk_score(output)
                all_warnings.extend(enforcer_warnings)
                self._log("output_enforcer", "enforce_risk_score", {
                    "agent": agent_name,
                    "warnings": enforcer_warnings,
                })
            elif agent_name == "explainability":
                output, enforcer_warnings = enforce_explanations(output)
                all_warnings.extend(enforcer_warnings)
                self._log("output_enforcer", "enforce_explanations", {
                    "agent": agent_name,
                    "warnings": enforcer_warnings,
                })

        self._total_warnings += len(all_warnings)
        return output, all_warnings

    def validate_final_report(
        self, report: str, state: dict
    ) -> Tuple[str, dict]:
        """Run hallucination, bias/fairness, and content safety checks on the final report.

        Returns (cleaned_report, validation_results).
        """
        self._total_checks += 1
        results = {
            "warnings": [],
            "hallucination": {},
            "bias_fairness": {},
            "content_safety": {},
            "compliance": {},
        }

        company_name = state.get("company_name", "")
        risks = state.get("extracted_risks", [])
        strengths = state.get("extracted_strengths", [])
        source_data = state.get("cleaned_data", [])
        financial_data = state.get("financial_data", [])
        score = state.get("risk_score", {})

        # --- Hallucination detection ---
        if self.config.get("hallucination_detector", True):
            # Entity attribution
            if source_data:
                attribution = check_entity_attribution(
                    company_name, risks, strengths, source_data
                )
                results["hallucination"]["attribution"] = attribution
                if attribution["attribution_score"] < 0.5:
                    results["warnings"].append(
                        f"Low attribution score: {attribution['attribution_score']}. "
                        "Many claims may not be grounded in source data."
                    )
                self._log("hallucination_detector", "entity_attribution", {
                    "attribution_score": attribution["attribution_score"],
                    "ungrounded_risks": len(attribution["ungrounded_risks"]),
                    "ungrounded_strengths": len(attribution["ungrounded_strengths"]),
                })

            # Company name in report
            aliases = state.get("aliases", [])
            found, company_warnings = verify_company_in_output(
                company_name, report, aliases
            )
            results["hallucination"]["company_found"] = found
            results["warnings"].extend(company_warnings)
            self._log("hallucination_detector", "verify_company", {
                "company_found": found,
                "warnings": company_warnings,
            })

            # Fabricated metrics
            if financial_data:
                fabrications = flag_fabricated_metrics(report, financial_data)
                results["hallucination"]["fabricated_metrics"] = fabrications
                results["warnings"].extend(fabrications)
                self._log("hallucination_detector", "fabricated_metrics", {
                    "flagged_count": len(fabrications),
                })

        # --- Bias and fairness ---
        if self.config.get("bias_fairness", True):
            proxy_vars = detect_proxy_variables(report)
            results["bias_fairness"]["proxy_variables"] = proxy_vars
            if proxy_vars:
                results["warnings"].append(
                    f"Found {len(proxy_vars)} protected class term(s) in report."
                )
            self._log("bias_fairness", "proxy_detection", {
                "found": len(proxy_vars),
                "terms": [p["term"] for p in proxy_vars],
            })

            # Compliance checks
            mas = check_mas_feat_compliance(report)
            eu = check_eu_ai_act_compliance(report)
            results["compliance"]["mas_feat"] = mas
            results["compliance"]["eu_ai_act"] = eu
            self._log("bias_fairness", "compliance_check", {
                "mas_feat": mas,
                "eu_ai_act": eu,
            })

        # --- Content safety ---
        if self.config.get("content_safety", True):
            report, modifications = filter_report_content(report)
            results["content_safety"]["modifications"] = modifications
            results["warnings"].extend(modifications)
            self._log("content_safety", "filter_report", {
                "modifications_count": len(modifications),
            })

            # Score-language consistency
            if score:
                consistency_warnings = validate_score_language_consistency(
                    score, report
                )
                results["content_safety"]["consistency_warnings"] = consistency_warnings
                results["warnings"].extend(consistency_warnings)
                self._log("content_safety", "score_language_consistency", {
                    "warnings": consistency_warnings,
                })

            # Add regulatory footer
            report = add_regulatory_footer(report)
            self._log("content_safety", "regulatory_footer", {
                "added": True,
            })

        self._total_warnings += len(results["warnings"])
        return report, results

    def get_audit_log(self) -> list:
        """Return the full audit trail of guardrail decisions."""
        return list(self.audit_log)

    def get_summary(self) -> dict:
        """Return summary statistics of guardrail checks.

        Returns dict with total_checks, warnings, blocks, and pass_rate.
        """
        return {
            "total_checks": self._total_checks,
            "warnings": self._total_warnings,
            "blocks": self._total_blocks,
            "pass_rate": (
                round(
                    (self._total_checks - self._total_blocks)
                    / self._total_checks,
                    4,
                )
                if self._total_checks > 0
                else 1.0
            ),
        }
