"""Live Fashion Desk run: Band carries every handoff, ZooWork does every agent's thinking.

Each agent is a worker polling Band for messages that @mention it (Band delivers by mention). On a message it
reads the room transcript back from Band, takes one ZooWork turn, and replies in Band, @mentioning whoever
acts next. Nothing is routed in-process: if Band does not deliver a message, the next agent never acts.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import traceback
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from zoowork import create_zoowork_client

from app.agents import ask, load_ids
from app.band import Band, load_band_agents
from app.research import clipbook_query, complements, moss_search, tavily_search

router = APIRouter(prefix="/api/live")
RUNS: dict[str, "LiveRun"] = {}
KEYS = ["miranda", "andy", "emily", "serena", "nigel"]
RUN_TIMEOUT_S = 180

# The real Everlane pool the UI already shows (Moss replaces this later).
CATALOG = {
    "halter": ("Textured Halter Midi Dress, Open Air Blue", 101),
    "scarf": ("Wool Cashmere Tie-Front Scarf, Celestial Blue", 78),
    "mule": ("Glove Mule Slipper, Black Leather", 168),
    "blazer": ("The Dream Blazer, Navy", 50),
    "trouser": ("Tropical Wool Trouser (men's), Dark Navy", 198),
    "boot": ("Collegium x Everlane Summit Boot, Navy Suede", 379),
    "slingback": ("The Ballet Slingback Heel, Black", 57),
    "slip": ("Slip Dress in Silk Charmeuse, Black", 50),
    "puffer": ("EverPuff Cloud Short Puffer, Cashmere Blue", 228),
    "pump": ("The Banana Pump, Black Suede", 50),
}
CATALOG_TEXT = "; ".join(f"{k}: {n} ${p}" for k, (n, p) in CATALOG.items())


def brief_text(b: dict) -> str:
    keys = ["occasion", "city", "when", "dressCode", "budget", "silhouette", "palette", "style", "loves", "dislikes"]
    return ", ".join(f"{k}: {b[k]}" for k in keys if b.get(k))


def look_line(i: int, look: dict) -> str:
    items = [x for x in look.get("items", []) if x in CATALOG]
    total = sum(CATALOG[x][1] for x in items)
    names = ", ".join(CATALOG[x][0] for x in items)
    return f"Look {i} · {look.get('name', 'Untitled')} — {names} (${total}). {look.get('why', '')}"


class LiveRun:
    def __init__(self, brief: dict):
        self.id = uuid.uuid4().hex[:10]
        self.brief = brief
        self.status = "starting"
        self.error: str | None = None
        self.room_id: str | None = None
        self.stages = {s: "waiting" for s in ["brief", "andy", "emily", "serena", "nigel", "final"]}
        self.lines: dict[str, str] = {}
        self.kinds: dict[str, str] = {}   # Band message id -> UI kind (reject / revision / approve / handoff)
        self.timing: dict[str, float] = {}
        self.t0 = time.perf_counter()
        self.handles: dict[str, str] = {}  # key -> Band handle, plus "user"
        self.ids: dict[str, str] = {}      # Band participant id -> key
        self.seen: set[str] = set()
        self.serena_inputs: dict[str, str] = {}
        self.nigel_reviews = 0
        self.t_assign = 0.0
        self.failure: Exception | None = None
        self.tools: list[dict] = []
        self.evidence: dict = {}
        self.products: dict[str, dict] = {}
        self.looks: list[dict] = []
        self.looks_draft: list[dict] = []
        self.revision: dict | None = None
        self.notes: list[str] = []
        self.final: list[dict] = []
        self.n = 0
        self.done = asyncio.Event()

    def stage(self, s: str, state: str, line: str = "") -> None:
        self.stages[s] = state
        if line:
            self.lines[s] = line


async def start(brief: dict) -> LiveRun:
    run = LiveRun(brief)
    RUNS[run.id] = run
    asyncio.create_task(_guarded(run))
    return run


async def _guarded(run: LiveRun) -> None:
    try:
        await asyncio.wait_for(_run(run), timeout=RUN_TIMEOUT_S)
        run.status = "done"
    except Exception as exc:  # the UI switches to the rehearsal run on error
        run.status = "error"
        run.error = f"{type(exc).__name__}: {exc}"[:300]
        traceback.print_exc()
    run.timing["total"] = time.perf_counter() - run.t0
    print(f"[live {run.id}] {run.status} room={run.room_id} timing={ {k: round(v, 1) for k, v in run.timing.items()} }")


async def _run(run: LiveRun) -> None:
    band_agents = load_band_agents()
    zw_ids = load_ids()
    owner = Band(os.environ["BAND_API_KEY"])
    agents = {k: Band(band_agents[k]["api_key"]) for k in KEYS}
    try:
        t = time.perf_counter()
        room = await owner.create_room(f"Flicsy · {run.brief.get('occasion', 'Styling')} · {datetime.now():%H:%M:%S}")
        run.room_id = room["id"]
        for k in KEYS:
            await owner.add_participant(run.room_id, band_agents[k]["id"])
        for p in await owner.participants(run.room_id):
            key = next((k for k in KEYS if band_agents[k]["id"] == p["id"]), "user")
            run.handles[key] = p.get("handle") or p["name"]
            run.ids[p["id"]] = key
        run.timing["room_setup"] = time.perf_counter() - t
        run.status = "running"

        async with create_zoowork_client() as zw:
            workers = [asyncio.create_task(_worker(run, k, agents[k], owner, zw, zw_ids[k])) for k in KEYS]
            # The client's brief enters the room addressed to Miranda; everything after is agent-to-agent.
            run.stage("brief", "working", "Reading the client brief…")
            await owner.post_as_user(run.room_id, f"{_at(run, 'miranda')} New client brief — {brief_text(run.brief)}",
                                     [_m(run, "miranda")])
            await run.done.wait()
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            if run.failure:
                raise run.failure
    finally:
        for c in [owner, *agents.values()]:
            await c.close()


def _at(run: LiveRun, key: str) -> str:
    return "@" + run.handles[key]


def _m(run: LiveRun, key: str) -> dict:
    pid = next(i for i, k in run.ids.items() if k == key)
    return {"id": pid, "handle": run.handles[key]}


async def _worker(run: LiveRun, key: str, me: Band, owner: Band, zw, zw_id: str) -> None:
    while not run.done.is_set():
        msg = await me.next_message(run.room_id)
        if not msg:
            await asyncio.sleep(0.4)
            continue
        if msg["id"] + key in run.seen:  # at-least-once delivery: dedupe per agent
            await me.mark(run.room_id, msg["id"], "processing")
            await me.mark(run.room_id, msg["id"], "processed")
            continue
        run.seen.add(msg["id"] + key)
        await me.mark(run.room_id, msg["id"], "processing")
        sender = run.ids.get(msg.get("sender_id"), "user")
        try:
            await HANDLERS[key](run, me, owner, zw, zw_id, sender, msg)
            await me.mark(run.room_id, msg["id"], "processed")
        except Exception as exc:  # fail the whole run now, so the UI falls back immediately
            run.failure = exc
            run.done.set()
            try:
                await me.mark(run.room_id, msg["id"], "failed")
            except Exception:
                pass
            return


def _readable(run: LiveRun, text: str) -> str:
    """Band stores mentions as @[[participant-id]]; show them as @handle."""
    for pid, key in run.ids.items():
        text = text.replace(f"@[[{pid}]]", "@" + ("client" if key == "user" else key))
    return text


async def _transcript(owner: Band, run: LiveRun) -> str:
    """The room as Band has it — the shared context every agent reasons over."""
    lines = []
    for m in await owner.room_messages(run.room_id):
        if m.get("message_type", "text") == "text":
            lines.append(f"{m.get('sender_name')}: {_readable(run, m.get('content', ''))}")
    return "\n".join(lines)


async def _turn(run: LiveRun, owner: Band, zw, zw_id: str, label: str, task: str) -> dict:
    room = await _transcript(owner, run)
    out, secs = await ask(zw, zw_id, f"Band room so far:\n{room}\n\nYour task: {task}", timeout=60)
    run.timing[label] = secs
    return out if isinstance(out, dict) else {"say": str(out)[:400]}  # tolerate a plain-text reply


async def _say(run: LiveRun, me: Band, to: list[str], text: str, kind: str = "handoff") -> None:
    mentions = " ".join(_at(run, k) for k in to)
    text = re.sub(r"^(\s*@[\w/.-]+[,:]?\s*)+", "", str(text))  # the agent sometimes writes its own @mention
    sent = await me.post_as_agent(run.room_id, f"{mentions} {text}", [_m(run, k) for k in to])
    run.kinds[sent["id"]] = kind


async def _miranda(run, me, owner, zw, zw_id, sender, msg):
    if sender == "user":
        out = await _turn(run, owner, zw, zw_id, "miranda_brief",
            'Brief your desk. Return JSON {"to_andy": "...", "to_emily": "..."}, each max 30 words. Ask Andy for an '
            "editorial direction (blue is a preference, not an instruction; nothing predictable). Ask Emily for the "
            "social/cultural direction (current without being trendy for its own sake).")
        run.stage("brief", "done", "Brief sent to the desk")
        run.t_assign = time.perf_counter()
        run.stage("andy", "working", "Reading the fashion press…")
        run.stage("emily", "working", "Reading social culture…")
        await asyncio.gather(_say(run, me, ["andy"], out["to_andy"], "assign"), _say(run, me, ["emily"], out["to_emily"], "assign"))
    elif sender == "nigel":
        run.stage("final", "working", "Making the final selection…")
        names = [l["name"] for l in run.looks]
        out = await _turn(run, owner, zw, zw_id, "miranda_final",
            f"Make the final choice from Serena's current looks {names}, following or overruling Nigel. Return JSON "
            '{"present": ["exact look names"], "alternative": "exact look name or null", '
            '"why": {"look name": "max 25 words, to the client"}, "say": "max 35 words, to the client"}.')
        run.final = _final_looks(run, out)
        present = f" Presenting: {', '.join(l['name'] for l in run.final if not l['alt'])}" if run.final else ""
        alt = next((f"; alternative: {l['name']}." for l in run.final if l["alt"]), ".")
        await _say(run, me, ["user"], f"FINAL APPROVAL — {out.get('say', '')}{present}{alt}", "approve")
        run.stage("final", "done", "Looks selected")
        run.done.set()


def _final_looks(run: LiveRun, out: dict) -> list[dict]:
    by = {l["name"].lower(): l for l in run.looks}
    pick = lambda n: by.get(str(n).lower()) or next((l for k, l in by.items() if str(n).lower()[:12] in k), None)
    chosen = [pick(n) for n in out.get("present") or []]
    alt = pick(out.get("alternative")) if out.get("alternative") else None
    looks = [l for l in chosen if l] or run.looks[:2]
    why = out.get("why") or {}
    res = []
    for l in looks + ([alt] if alt and alt not in looks else []):
        res.append({**l, "alt": l is alt and l not in looks, "rationale": why.get(l["name"]) or l.get("why", "")})
    return res[:3]


def _tool(run: LiveRun, agent: str, tool: str, args: str, result: str) -> None:
    run.tools.append({"from": agent, "tool": tool, "args": args, "result": result,
                      "at": datetime.now(timezone.utc).isoformat()})


async def _andy(run, me, owner, zw, zw_id, sender, msg):
    b = run.brief
    q = f"{b.get('dressCode', 'black tie')} unconventional evening dressing {b.get('palette', '').replace('always', '')} tailoring flats 2026"
    res = await tavily_search(re.sub(r"[,\s]+", " ", q).strip())
    _tool(run, "andy", "tavily.search", res["query"], f"{len(res['sources'])} sources · {res.get('ms', '–')} ms · {res['status']}")
    srcs = res["sources"]
    listing = "\n".join(f"[{i + 1}] {s['publication']} — {s['title']}: {s['snippet']}" for i, s in enumerate(srcs)) or "(no live results)"
    out = await _turn(run, owner, zw, zw_id, "andy",
        f"Answer Miranda using ONLY these real search results:\n{listing}\nReturn JSON "
        '{"direction": "max 35 words", "insights": [{"n": source number, "insight": "max 15 words: why it matters for this client"}]}.')
    for it in out.get("insights") or []:
        if isinstance(it, dict) and str(it.get("n", "")).isdigit() and 0 < int(it["n"]) <= len(srcs):
            srcs[int(it["n"]) - 1]["insight"] = it.get("insight", "")
    res["direction"] = out.get("direction") or out.get("say", "")
    run.evidence["press"] = res
    cites = "; ".join(f"{s['publication']}, “{s['title']}”" for s in srcs[:3])
    await _say(run, me, ["serena"], f"{res['direction']} Sources: {cites or 'none (FALLBACK)'}.")
    run.stage("andy", "done", f"{len(srcs)} real sources · {res['status']}")


async def _emily(run, me, owner, zw, zw_id, sender, msg):
    res = clipbook_query(run.brief)
    _tool(run, "emily", "brightdata.clipbook.query", "; ".join(res.get("concepts", [])),
          f"{res['matched']} of {res['searched']} clips relevant · {res['status']}")
    clips = res["clips"]
    if not clips:
        res["say"] = "Social evidence is limited for this brief."
    else:
        listing = "\n".join(f"[{i + 1}] ({c['trend']}) {c['plays'] or 0:,} plays · {c['text']}" for i, c in enumerate(clips))
        out = await _turn(run, owner, zw, zw_id, "emily",
            "Summarise ONLY what these real TikTok clips (collected via Bright Data) show. Do not claim trends they do "
            "not show; if the evidence is thin, say so.\n" + listing + '\nReturn JSON {"say": "max 40 words"}.')
        res["say"] = out.get("say", "")
    run.evidence["clips"] = res
    await _say(run, me, ["serena"], f"{res['say']} (from {res['matched']} relevant clips in the Mira Picks clipping book)")
    run.stage("emily", "done", f"{res['matched']} relevant clips · {res['status']}")


async def _shop(run: LiveRun, query: str) -> str:
    """Moss for garments (the index holds Everlane dresses) + real Everlane catalog for shoes/outerwear/tailoring."""
    moss = await moss_search(query)
    _tool(run, "serena", "moss.search", f"{query} {{index: everlane-com}}",
          f"{len(moss['products'])} products · {moss.get('moss_ms', '–')} ms · {moss['status']}")
    comps = complements(query)
    _tool(run, "serena", "everlane.catalog.lookup", query[:80], f"{len(comps)} shoes/outerwear/tailoring/bags")
    lines = []
    for p in moss["products"] + comps:
        run.n += 1
        pid = f"p{run.n}"
        run.products[pid] = p
        lines.append(f"{pid}: {p['name']}{' — ' + p['color'] if p.get('color') else ''} · {p.get('slot', 'dress')} · ${p['price']:g}")
    run.evidence.setdefault("moss", []).append({k: moss.get(k) for k in ("status", "query", "moss_ms", "error")})
    return "\n".join(lines)


def _look(run: LiveRun, l: dict) -> dict:
    items = [i for i in l.get("items", []) if i in run.products]
    return {"name": l.get("name", "Untitled"), "items": items, "why": l.get("why", ""),
            "total": round(sum(run.products[i]["price"] for i in items), 2)}


def _look_text(run: LiveRun, l: dict) -> str:
    return f"{l['name']} — " + ", ".join(f"{run.products[i]['name']} ${run.products[i]['price']:g}" for i in l["items"]) + f" (${l['total']:g})"


async def _serena(run, me, owner, zw, zw_id, sender, msg):
    if sender in ("andy", "emily"):
        run.serena_inputs[sender] = msg["content"]
        if len(run.serena_inputs) < 2:  # Band delivers each editor separately; build once both are in
            run.stage("serena", "waiting", f"Has {sender.title()}'s direction, waiting for the other")
            return
        run.timing["andy_emily_parallel"] = time.perf_counter() - run.t_assign
        run.stage("serena", "working", "Searching Moss for real products…")
        b = run.brief
        catalog = await _shop(run, f"elegant {b.get('dressCode', '')} evening dress {b.get('palette', '').replace('always', '')} unconventional")
        out = await _turn(run, owner, zw, zw_id, "serena",
            f"Build 3 complete looks for the client from these REAL products only (use ids; respect the budget and footwear "
            f"constraints; each look needs shoes):\n{catalog}\nReturn JSON "
            '{"looks": [{"name": "...", "items": ["id", "id", "id"], "why": "max 15 words"}]}.')
        run.looks = [_look(run, l) for l in (out.get("looks") or [])[:3]]
        run.looks_draft = [dict(l) for l in run.looks]
        await _say(run, me, ["nigel"], "Candidate looks: " + " | ".join(f"Look {i + 1} · {_look_text(run, l)}" for i, l in enumerate(run.looks)))
        run.stage("serena", "done", f"{len(run.looks)} looks from real products")
    elif sender == "nigel":
        run.stage("serena", "working", "Revising per Nigel — searching Moss again…")
        catalog = await _shop(run, re.sub(r"@\[\[[^\]]+\]\]", "", msg.get("content", ""))[:160])
        out = await _turn(run, owner, zw, zw_id, "serena_revision",
            f"Make Nigel's change using the earlier products or these new REAL products (use ids):\n{catalog}\nReturn JSON "
            '{"replaces": "exact name of the look you revised", "look": {"name": "...", "items": ["id", "id", "id"], "why": "max 15 words"}, '
            '"changed": "max 12 words"}.')
        new = _look(run, out.get("look") or {})
        idx = next((i for i, l in enumerate(run.looks) if l["name"].lower() == str(out.get("replaces", "")).lower()), None)
        if idx is None:
            idx = next((i for i, l in enumerate(run.looks) if str(out.get("replaces", "")).lower()[:10] in l["name"].lower()), len(run.looks) - 1)
        if new["items"]:
            run.revision = {"replaces": run.looks[idx]["name"], "changed": out.get("changed", ""), "look": new}
            run.looks[idx] = new
        await _say(run, me, ["nigel"], f"Revised — {out.get('changed', '')}. {_look_text(run, new)}", "revision")
        run.stage("serena", "done", "Revision sent to Nigel")


async def _nigel(run, me, owner, zw, zw_id, sender, msg):
    run.nigel_reviews += 1
    if run.nigel_reviews == 1:
        run.stage("nigel", "working", "Reviewing the looks…")
        out = await _turn(run, owner, zw, zw_id, "nigel",
            "Critique Serena's looks (real products, real prices) honestly against the brief, Andy's sources and Emily's "
            "clips: occasion, coherence, budget, footwear, use of evidence. Do not approve "
            "everything: find the weakest piece and demand one concrete replacement. Return JSON "
            '{"say": "max 45 words: verdict on each look plus the concrete change you want from Serena"}.')
        run.notes.append(out["say"])
        await _say(run, me, ["serena"], out["say"], "reject")
        run.stage("nigel", "blocked", "Change requested from Serena")
    else:
        run.stage("nigel", "working", "Reviewing the revision…")
        out = await _turn(run, owner, zw, zw_id, "nigel_final",
            'Review Serena\'s revision, then recommend to Miranda which looks to present. Return JSON '
            '{"say": "max 40 words"}.')
        run.notes.append(out["say"])
        await _say(run, me, ["miranda"], out["say"])
        run.stage("nigel", "done", "Recommendation sent to Miranda")


HANDLERS = {"miranda": _miranda, "andy": _andy, "emily": _emily, "serena": _serena, "nigel": _nigel}


# ------------------------------- HTTP API for the UI -------------------------------

@router.post("/runs")
async def create_run(brief: dict) -> dict:
    run = await start(brief)
    return {"run_id": run.id}


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "unknown run")
    events = []
    if run.room_id:
        owner = Band(os.environ["BAND_API_KEY"])
        try:
            msgs = await owner.room_messages(run.room_id)
        finally:
            await owner.close()
        for m in msgs:
            if m.get("message_type", "text") != "text":
                continue
            text = _readable(run, m.get("content", ""))
            events.append({"id": m["id"], "from": run.ids.get(m.get("sender_id"), "client"), "text": text,
                           "at": m.get("inserted_at"), "kind": run.kinds.get(m["id"], "")})
    return {"status": run.status, "error": run.error, "room_id": run.room_id, "stages": run.stages,
            "lines": run.lines, "events": events, "tools": run.tools, "timing": {k: round(v, 1) for k, v in run.timing.items()},
            "evidence": {"press": run.evidence.get("press"), "clips": run.evidence.get("clips"), "moss": run.evidence.get("moss"),
                         "products": run.products, "draft": run.looks_draft, "looks": run.looks, "revision": run.revision,
                         "notes": run.notes, "final": run.final}}
