"""Read-only ZooWork check: verify the API key and list the model catalog.

Calls only list_models(). It creates no Agents, Sessions, or other resources.

    uv run python scripts/list_models.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zoowork import ZooworkError, create_zoowork_client

from app.config import require_zoowork_key


def pick_default_model(models: list[dict]) -> str | None:
    """The platform's primary chat default: selectable, with 'model' in default_for."""
    for row in models:
        if row.get("selectable") is not False and "model" in (row.get("default_for") or []):
            return row.get("model")
    return None


async def main() -> int:
    require_zoowork_key()
    try:
        async with create_zoowork_client() as client:
            models = await client.list_models()
    except ZooworkError as e:
        print(f"ZooWork error: status={e.status} type={e.type}", file=sys.stderr)
        if e.status in (401, 403):
            print("The API key was rejected; check ZOOWORK_API_KEY.", file=sys.stderr)
        return 1

    print(f"Authenticated. {len(models)} model(s) in the catalog:\n")
    print(f"{'model':<45} {'selectable':<11} {'api':<20} {'lifecycle':<12} default_for")
    for row in models:
        print(
            f"{str(row.get('model')):<45} "
            f"{str(row.get('selectable', True)):<11} "
            f"{str(row.get('api', '')):<20} "
            f"{str(row.get('lifecycle_status', '')):<12} "
            f"{','.join(row.get('default_for') or [])}"
        )

    default = pick_default_model(models)
    print(f"\nPrimary chat default: {default or 'none found'}")

    if "--json" in sys.argv:
        print(json.dumps(models, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
