"""One-time: register the five Flicsy characters as Band agents and save their keys to .band/agents.json.

    uv run python scripts/setup_band.py

Band shows each agent API key once, so the file is the only copy. It is gitignored; never commit it.
Re-running skips agents already saved.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: F401  (loads .env)
from app.band import AGENTS_FILE, Band, load_band_agents

ROLES = {
    "miranda": "Lead Stylist at Flicsy. Writes the client brief, delegates to the desk and makes the final selection.",
    "andy": "Fashion Editor at Flicsy. Reports what the fashion establishment suggests for a client's brief.",
    "emily": "Social and Culture Editor at Flicsy. Reports what people are actually wearing and talking about.",
    "serena": "Personal Shopper at Flicsy. Builds complete, purchasable looks from retailer catalogs.",
    "nigel": "Fashion Director at Flicsy. Critiques each look and can send a piece back for revision.",
}


async def main() -> int:
    saved = load_band_agents()
    owner = Band(os.environ["BAND_API_KEY"])
    try:
        for key, desc in ROLES.items():
            if key in saved:
                print(f"{key:<8} {saved[key]['id']}  reused")
                continue
            data = await owner.register_agent(key, desc)
            saved[key] = {"id": data["agent"]["id"], "name": data["agent"]["name"], "api_key": data["credentials"]["api_key"]}
            AGENTS_FILE.parent.mkdir(exist_ok=True)
            AGENTS_FILE.write_text(json.dumps(saved, indent=2), encoding="utf-8")
            print(f"{key:<8} {saved[key]['id']}  registered")
    finally:
        await owner.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
