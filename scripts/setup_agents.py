"""One-time setup: create (or reuse) the five Flicsy ZooWork agents, start them, save their IDs.

    uv run python scripts/setup_agents.py

Re-running reuses saved agents. A saved ID that no longer resolves is recreated; a changed model in .env is
updated in place. Agents are created one at a time (concurrent creates can 503).
"""

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zoowork import ZooworkError, create_zoowork_client

from app.agents import SPECS, agent_resource, load_ids, save_ids
from app.config import require_zoowork_key


async def ensure(client, key: str, ids: dict[str, str]) -> tuple[str, str]:
    want = os.environ[SPECS[key]["env"]]
    agent_id = ids.get(key)
    if agent_id:
        try:
            agent = await client.get_agent(agent_id)
            have = ((agent.get("declared") or {}).get("model") or {}).get("primary")
            if have and have != want:
                await client.update_agent(agent_id, {"model": agent_resource(key)["model"]})
                return agent_id, f"reused, model updated {have} -> {want}"
            return agent_id, "reused"
        except ZooworkError as e:
            if e.status != 404:
                raise
    for attempt in range(4):
        try:
            created = await client.create_agent(agent_resource(key), idempotency_key=f"flicsy-{key}-v1")
            ids[key] = created["agent_id"]
            save_ids(ids)
            return ids[key], "created"
        except ZooworkError as e:
            if e.status == 503 and attempt < 3:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


async def main() -> int:
    require_zoowork_key()
    t0 = time.perf_counter()
    ids = load_ids()
    async with create_zoowork_client() as client:
        for key in SPECS:  # serial creates
            agent_id, how = await ensure(client, key, ids)
            print(f"{key:<8} {agent_id}  {os.environ[SPECS[key]['env']]:<28} {how}")
        save_ids(ids)
        t_start = time.perf_counter()
        await asyncio.gather(*(client.start_agent(ids[k]) for k in SPECS))
        await asyncio.gather(*(client.wait_until_running(ids[k], timeout=120) for k in SPECS))
        print(f"\nall running · start+wait {time.perf_counter() - t_start:.1f}s · total setup {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
