"""Flicsy backend. Holds the ZooWork key server-side; browsers talk only to this app."""

from fastapi import FastAPI

from app import config  # noqa: F401  (loads .env)

app = FastAPI(title="Flicsy")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "flicsy"}
