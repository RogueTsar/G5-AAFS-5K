import asyncio
import json
import os
from datetime import datetime

from industry import research_company_industry_outlook


OUTPUT_DIR = "test_outputs_industry"


async def run_test(company_name: str):
    print(f"\n{'=' * 70}")
    print(f"Testing research_company_industry_outlook")
    print(f"Company: {company_name}")
    print(f"{'=' * 70}")

    try:
        result_str = await research_company_industry_outlook(company_name)
        parsed = json.loads(result_str)

        metadata = parsed.get("metadata", {})
        industry_research = parsed.get("industry_research", {})
        outlook_analysis = industry_research.get("outlook_analysis", {})
        debug = parsed.get("debug", {})

        print("\nSummary:")
        print(f"- Company: {metadata.get('company_name')}")
        print(f"- Inferred industry: {industry_research.get('inferred_industry')}")
        print(f"- Industry confidence: {industry_research.get('industry_confidence')}")
        print(f"- Outlook score: {outlook_analysis.get('industry_outlook_score')}")
        print(f"- Outlook rating: {outlook_analysis.get('outlook_rating')}")
        print(f"- Outlook confidence: {outlook_analysis.get('outlook_confidence')}")

        drivers = outlook_analysis.get("drivers", {})
        print(f"- Positive drivers: {drivers.get('positive_drivers', [])}")
        print(f"- Negative drivers: {drivers.get('negative_drivers', [])}")

        print(f"- Completed in: {debug.get('completed_in_seconds')}s")
        print(
            f"- Estimated payload tokens: "
            f"{debug.get('token_usage_estimate', {}).get('final_payload_tokens')}"
        )

        print("\nSteps:")
        for step in debug.get("steps", []):
            print(
                f"  - {step.get('step')} "
                f"[{step.get('status')}] "
                f"at {step.get('elapsed_seconds')}s"
            )

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in company_name).strip("_")
        output_path = os.path.join(OUTPUT_DIR, f"{safe_name}_{timestamp}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)

        print(f"\nFull result saved to: {output_path}")

    except Exception as e:
        print(f"\nError while testing '{company_name}': {e}")


async def main():
    test_cases = [
        "Sembcorp Industries",
        "Grab Holdings",
        "DBS Bank",
    ]

    for company in test_cases:
        await run_test(company)
        print("\n" + "-" * 70)


if __name__ == "__main__":
    asyncio.run(main())