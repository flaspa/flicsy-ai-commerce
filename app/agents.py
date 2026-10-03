"""The five Flicsy ZooWork agents: specs, saved IDs, and one call per agent turn.

Agents are created once by scripts/setup_agents.py and reused; their IDs live in
config/zoowork_agents.json (non-secret). Nothing here creates an agent on the request path.
"""

from __future__ import annotations

import asyncio
import json
import os
import time

from zoowork import assistant_text, is_run_finished, run_outcome

from app.config import PROJECT_ROOT

STATE_FILE = PROJECT_ROOT / "config" / "zoowork_agents.json"

COMMON = (
    "You are part of Flicsy, the AI personal-styling desk launched by the fashion magazine Mira Picks. "
    "Answer directly from your own knowledge: do not use tools, browse, or write files. "
    "Be concise. Reply with ONLY one compact JSON object, no prose before or after it."
)

SPECS = {
    "miranda": {
        "name": "flicsy-miranda", "env": "MIRANDA_MODEL", "title": "Miranda — Lead Stylist",
        "prompt": "You are Miranda, Lead Stylist. You turn a client's request into a styling brief, and at the end you "
                  "make the final selection from your desk's work. You are exacting and decisive.",
    },
    "andy": {
        "name": "flicsy-andy", "env": "ANDY_MODEL", "title": "Andy — Fashion Editor",
        "prompt": "You are Andy, Fashion Editor. You answer: what does the fashion establishment suggest? "
                  "Report editorial direction (silhouettes, colour, materials). Never pick products.",
    },
    "emily": {
        "name": "flicsy-emily", "env": "EMILY_MODEL", "title": "Emily — Social & Culture Editor",
        "prompt": "You are Emily, Social & Culture Editor. You answer: what are people actually wearing and talking "
                  "about? Report social styling signals and aesthetics. Never pick products.",
    },
    "serena": {
        "name": "flicsy-serena", "env": "SERENA_MODEL", "title": "Serena — Personal Shopper",
        "prompt": "You are Serena, Personal Shopper. You answer: what can the client actually buy? You assemble "
                  "complete looks only from the catalog items you are given, and revise them when Nigel objects.",
    },
    "nigel": {
        "name": "flicsy-nigel", "env": "NIGEL_MODEL", "title": "Nigel — Fashion Director",
        "prompt": "You are Nigel, Fashion Director and critic. You judge whether each look works for this client: "
                  "occasion, budget, coherence, evidence. You may reject one piece. You never make the final decision.",
    },
}


def agent_resource(key: str) -> dict:
    spec = SPECS[key]
    return {
        "name": spec["name"],
        "model": {"primary": os.environ[spec["env"]], "max_tokens": 1200},
        "persona": {"docs": [{"name": "ROLE.md", "content": f"{spec['prompt']}\n\n{COMMON}"}]},
        "include_global_skills": False,  # fewer tools to consider -> faster, more predictable turns
        "labels": {"app": "flicsy", "role": key},
        "userTimezone": "America/Los_Angeles",
    }


def load_ids() -> dict[str, str]:
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}


def save_ids(ids: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")


def _json(text: str) -> dict | str:
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return text.strip()


async def ask(client, agent_id: str, message: str, timeout: float = 90.0) -> tuple[dict | str, float]:
    """One turn in a fresh Session. Returns (parsed reply, seconds)."""
    t0 = time.perf_counter()

    async def turn() -> str:
        session = await client.create_session(agent_id, {"initial_events": [{"type": "user.message", "content": message}]})
        parts: list[str] = []
        async for event in client.stream_events(agent_id, session["session_id"]):
            parts.append(assistant_text(event))
            if is_run_finished(event):
                if run_outcome(event) != "succeeded":
                    raise RuntimeError(f"run {run_outcome(event)}")
                break
        return "".join(parts)

    text = await asyncio.wait_for(turn(), timeout=timeout)
    return _json(text), time.perf_counter() - t0


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False)


async def run_pipeline(client, ids: dict[str, str], request: str, catalog: list[dict]) -> dict:
    """Miranda brief -> Andy + Emily (parallel) -> Serena -> Nigel -> Miranda final. Returns outputs + timings."""
    out, timing = {}, {}
    t_all = time.perf_counter()

    out["brief"], timing["miranda_brief"] = await ask(client, ids["miranda"],
        f"Client request: {request}\nWrite the styling brief as JSON: "
        '{"occasion","dress_code","budget","palette","style","avoid","question_for_andy","question_for_emily"}. Max 12 words per field.')

    t_par = time.perf_counter()
    (out["andy"], timing["andy"]), (out["emily"], timing["emily"]) = await asyncio.gather(
        ask(client, ids["andy"], f"Brief: {_j(out['brief'])}\nReturn JSON: "
            '{"direction":"one sentence","signals":[3 short strings]}.'),
        ask(client, ids["emily"], f"Brief: {_j(out['brief'])}\nReturn JSON: "
            '{"observation":"one sentence","signals":[3 short strings]}.'),
    )
    timing["andy_emily_parallel"] = time.perf_counter() - t_par

    out["serena"], timing["serena"] = await ask(client, ids["serena"],
        f"Brief: {_j(out['brief'])}\nAndy: {_j(out['andy'])}\nEmily: {_j(out['emily'])}\n"
        f"Catalog (use only these ids): {_j(catalog)}\n"
        'Return JSON: {"looks":[{"name","items":[ids],"total":number,"why":"one sentence"}]} with exactly 3 looks of 3 items.')

    out["nigel"], timing["nigel"] = await ask(client, ids["nigel"],
        f"Brief: {_j(out['brief'])}\nSerena's looks: {_j(out['serena'])}\nCatalog: {_j(catalog)}\n"
        'Return JSON: {"verdicts":[{"look","ok":bool,"note":"max 15 words"}],"reject":{"look","item","reason"} or null}.')

    out["final"], timing["miranda_final"] = await ask(client, ids["miranda"],
        f"Brief: {_j(out['brief'])}\nLooks: {_j(out['serena'])}\nNigel: {_j(out['nigel'])}\n"
        'Make the final selection. Return JSON: {"present":[look names],"alternative":look name or null,"note":"one sentence to the client"}.')

    timing["total"] = time.perf_counter() - t_all
    return {"outputs": out, "timing": timing}
