import asyncio
import json
import os
from datetime import datetime

from source3 import discover_best_sources


OUTPUT_DIR = "test_outputs_sources"


async def run_test(entity_name: str, entity_type: str = ""):
    print(f"\n{'=' * 70}")
    print(f"Testing: {entity_name}")
    print(f"Entity type: {entity_type if entity_type else '[auto-detect]'}")
    print(f"{'=' * 70}")

    try:
        result_str = await discover_best_sources(entity_name, entity_type)
        parsed = json.loads(result_str)

        print("\nResult Summary:")
        print(f"- Entity: {parsed.get('entity_name')}")
        print(f"- Type: {parsed.get('entity_type')}")

        print("\nRecommended Sources:")
        sources = parsed.get("sources", [])
        for i, src in enumerate(sources, start=1):
            print(f"\n{i}. {src.get('source')}")
            print(f"   Reason: {src.get('reason')}")

        # Save output
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in entity_name)

        file_path = os.path.join(
            OUTPUT_DIR,
            f"{safe_name}_{timestamp}.json"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)

        print(f"\nSaved to: {file_path}")

    except Exception as e:
        print(f"\nError testing {entity_name}: {e}")


async def main():
    test_cases = [
        # SME (Singapore context)
        {
            "entity_name": "Sheng Siong Supermarket",
            "entity_type": "company"
        },

        # Large regional company
        {
            "entity_name": "Grab Holdings",
            "entity_type": "company"
        },

        # Global large company
        {
            "entity_name": "Apple Inc",
            "entity_type": "company"
        }
    ]

    for case in test_cases:
        await run_test(case["entity_name"], case["entity_type"])
        print("\n" + "-" * 70)


if __name__ == "__main__":
    asyncio.run(main())