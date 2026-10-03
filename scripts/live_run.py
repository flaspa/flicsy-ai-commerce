"""One timed end-to-end run of the five saved ZooWork agents (no Tavily/Bright Data/Moss/Band yet).

    uv run python scripts/live_run.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zoowork import create_zoowork_client

from app.agents import load_ids, run_pipeline
from app.config import require_zoowork_key

REQUEST = ("I'm going to a gala dinner in San Francisco next month. I love skiing, I wear a lot of blue, and I'd like "
           "something elegant but not conventional. Black tie, up to $600, open to dress or suit, no stilettos.")

# A small slice of the Everlane snapshot the UI already uses.
CATALOG = [
    {"id": "halter", "name": "Textured Halter Midi Dress, Open Air Blue", "price": 101},
    {"id": "scarf", "name": "Wool Cashmere Tie-Front Scarf, Celestial Blue", "price": 78},
    {"id": "mule", "name": "Glove Mule Slipper, Black Leather", "price": 168},
    {"id": "blazer", "name": "The Dream Blazer, Navy", "price": 50},
    {"id": "trouser", "name": "Tropical Wool Trouser (men's), Dark Navy", "price": 198},
    {"id": "boot", "name": "Collegium x Everlane Summit Boot, Navy Suede", "price": 379},
    {"id": "slingback", "name": "The Ballet Slingback Heel, Black", "price": 57},
    {"id": "slip", "name": "Slip Dress in Silk Charmeuse, Black", "price": 50},
    {"id": "puffer", "name": "EverPuff Cloud Short Puffer, Cashmere Blue", "price": 228},
    {"id": "pump", "name": "The Banana Pump, Black Suede", "price": 50},
]


async def main() -> int:
    require_zoowork_key()
    ids = load_ids()
    async with create_zoowork_client() as client:
        result = await run_pipeline(client, ids, REQUEST, CATALOG)
    for k, v in result["timing"].items():
        print(f"{k:<22} {v:6.1f}s")
    print(json.dumps(result["outputs"], indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
