"""Minimal Band REST client (https://docs.band.ai/openapi.json). Owner = Human API key; agents = Agent API keys."""

from __future__ import annotations

import json

import httpx

from app.config import PROJECT_ROOT

BASE = "https://api.band.ai/api/v1"
AGENTS_FILE = PROJECT_ROOT / ".band" / "agents.json"  # SECRET: per-agent API keys (gitignored)


def load_band_agents() -> dict:
    return json.loads(AGENTS_FILE.read_text(encoding="utf-8")) if AGENTS_FILE.exists() else {}


class Band:
    def __init__(self, api_key: str):
        self.http = httpx.AsyncClient(base_url=BASE, headers={"X-API-Key": api_key}, timeout=30)

    async def close(self) -> None:
        await self.http.aclose()

    async def _req(self, method: str, path: str, **kw) -> dict | None:
        r = await self.http.request(method, path, **kw)
        if r.status_code == 204:
            return None
        if r.status_code >= 400:
            raise RuntimeError(f"Band {method} {path} -> {r.status_code}: {r.text[:200]}")
        return r.json()

    # ---- Human (owner) API ----
    async def register_agent(self, name: str, description: str) -> dict:
        return (await self._req("POST", "/me/agents/register", json={"agent": {"name": name, "description": description}}))["data"]

    async def create_room(self, title: str) -> dict:
        return (await self._req("POST", "/me/chats", json={"chat": {"title": title}}))["data"]

    async def add_participant(self, chat_id: str, participant_id: str) -> None:
        await self._req("POST", f"/me/chats/{chat_id}/participants", json={"participant": {"participant_id": participant_id}})

    async def participants(self, chat_id: str) -> list[dict]:
        return (await self._req("GET", f"/me/chats/{chat_id}/participants", params={"limit": 50}))["data"]

    async def room_messages(self, chat_id: str) -> list[dict]:
        """All messages in the room, oldest first (the API returns newest first)."""
        data = (await self._req("GET", f"/me/chats/{chat_id}/messages", params={"limit": 100}))["data"]
        return list(reversed(data))

    async def post_as_user(self, chat_id: str, content: str, mentions: list[dict]) -> dict:
        return (await self._req("POST", f"/me/chats/{chat_id}/messages", json={"message": {"content": content, "mentions": mentions}}))["data"]

    # ---- Agent API ----
    async def next_message(self, chat_id: str) -> dict | None:
        res = await self._req("GET", f"/agent/chats/{chat_id}/messages/next")
        return res["data"] if res else None

    async def mark(self, chat_id: str, message_id: str, status: str) -> None:
        await self._req("POST", f"/agent/chats/{chat_id}/messages/{message_id}/{status}")

    async def post_as_agent(self, chat_id: str, content: str, mentions: list[dict]) -> dict:
        return (await self._req("POST", f"/agent/chats/{chat_id}/messages", json={"message": {"content": content, "mentions": mentions}}))["data"]
