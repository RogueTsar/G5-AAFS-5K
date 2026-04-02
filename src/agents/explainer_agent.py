"""Explainer Agent — finds reasoning errors and clarifies agent outputs."""

from typing import Any, Dict, List
from src.core.llm import get_llm
from src.core.logger import log_agent_action

def explainer_agent(state: dict, excerpt: str = "") -> Dict[str, Any]:
    """Analyze agent output for reasoning quality. Returns structured issues list."""
    llm = get_llm()

    # Build context from state
    company = state.get("company_name", "Unknown")
    risks = state.get("extracted_risks", [])
    strengths = state.get("extracted_strengths", [])
    report = state.get("final_report", "")
    explanations = state.get("explanations", [])

    # If no specific excerpt, analyze the full report
    target = excerpt if excerpt else report

    if not target:
        return {"explainer_issues": [], "explainer_summary": "No content to analyze."}

    prompt = f"""You are a senior credit risk analyst reviewing AI-generated analysis for {company}.

Analyze this text for reasoning quality issues:

---
{target[:3000]}
---

Context - Risks found: {[r.get('description','') for r in risks[:5]]}
Context - Strengths found: {[s.get('description','') for s in strengths[:5]]}

Find ALL issues in these categories:
1. LOGICAL ERROR - flawed reasoning, non-sequiturs, circular logic
2. OVERSIMPLIFICATION - imprecise language that loses important nuance
3. EPISTEMIC ERROR - false confidence, missing uncertainty qualifiers
4. FACTUAL CONCERN - claims that may be inaccurate or unverifiable
5. MISSING CONTEXT - important factors not considered

For each issue, respond in this exact format (one per line):
ISSUE|<category>|<severity:HIGH/MEDIUM/LOW>|<original_text_snippet>|<correction_or_clarification>

If no issues found, respond with: NO_ISSUES_FOUND"""

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        log_agent_action("explainer_agent", f"Analyzed {len(target)} chars for {company}")

        issues = []
        for line in content.strip().split("\n"):
            if line.startswith("ISSUE|"):
                parts = line.split("|")
                if len(parts) >= 5:
                    issues.append({
                        "category": parts[1].strip(),
                        "severity": parts[2].strip(),
                        "original_text": parts[3].strip(),
                        "correction": parts[4].strip(),
                    })

        summary = f"Found {len(issues)} reasoning issues" if issues else "No issues found"
        return {"explainer_issues": issues, "explainer_summary": summary}
    except Exception as e:
        log_agent_action("explainer_agent", f"Error: {e}")
        return {"explainer_issues": [], "explainer_summary": f"Analysis failed: {e}"}
