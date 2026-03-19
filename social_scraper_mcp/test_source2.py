import asyncio
import json
from source2 import discover_best_sources


async def main():
    entity_name = "Sembcorp Industries"
    entity_type = "company"

    result_str = await discover_best_sources(entity_name, entity_type)
    parsed = json.loads(result_str)

    print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    asyncio.run(main())