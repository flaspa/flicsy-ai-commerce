"""Flicsy backend. Holds the ZooWork key server-side; browsers talk only to this app."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config  # noqa: F401  (loads .env)
from app.config import PROJECT_ROOT
from app.checkout import router as checkout_router
from app.live import router as live_router

app = FastAPI(title="Flicsy")
app.include_router(live_router)
app.include_router(checkout_router)


@app.on_event("startup")
async def warm_moss() -> None:
    """Load the Moss index once (~10 s) so customer queries take milliseconds."""
    import asyncio

    from app.research import moss_client
    asyncio.create_task(moss_client())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "flicsy"}


# Phase 1 front end: a static, mock-data customer journey. Mounted last so API routes match first.
app.mount("/characters", StaticFiles(directory=PROJECT_ROOT / "assets" / "characters"), name="characters")
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "app" / "static", html=True), name="site")
