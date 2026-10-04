"""Stripe TEST-MODE Checkout for the Flicsy bag. Demonstration only: no retailer order is placed.

The client sends product URLs only. Prices are looked up server-side from products the app itself served
(live-run Moss/catalog results, the Everlane catalog snapshot, and the rehearsal looks); unknown items are refused.
"""

from __future__ import annotations

import json
import os
import re

import stripe
from fastapi import APIRouter, HTTPException

from app.config import PROJECT_ROOT
from app.live import RUNS

router = APIRouter(prefix="/api")
BASE_URL = "http://127.0.0.1:8010/"


def _known_prices() -> dict[str, tuple[str, float]]:
    known: dict[str, tuple[str, float]] = {}
    snapshot = json.loads((PROJECT_ROOT / "data" / "catalog" / "everlane_complements.json").read_text(encoding="utf-8"))
    for p in snapshot:
        known[p["url"]] = (p["name"], p["price"])
    # Rehearsal looks (app/static/data.js): name, price and Everlane handle per product.
    js = (PROJECT_ROOT / "app" / "static" / "data.js").read_text(encoding="utf-8")
    js = js[js.index("export const PRODUCTS"): js.index("export const LOOKS")]
    for name, price, handle in re.findall(r'name: "([^"]+)".*?price: (\d+(?:\.\d+)?).*?url: EVERLANE\("([^"]+)"\)', js, re.S):
        known[f"https://www.everlane.com/products/{handle}"] = (name, float(price))
    for run in RUNS.values():  # products served during live runs (Moss + catalog)
        for p in run.products.values():
            known[p["url"]] = (p["name"], float(p["price"]))
    return known


@router.post("/checkout")
async def create_checkout(body: dict) -> dict:
    items = body.get("items") or []
    if not items or len(items) > 20:
        raise HTTPException(400, "Bag is empty")
    known = _known_prices()
    line_items = []
    for it in items:
        hit = known.get(str(it.get("url", "")))
        if not hit:
            raise HTTPException(400, f"Unknown product: {str(it.get('name', ''))[:60]}")
        name, price = hit
        line_items.append({"quantity": 1, "price_data": {
            "currency": "usd", "unit_amount": int(round(price * 100)),
            "product_data": {"name": f"{name} · Everlane", "description": "Flicsy demo · Stripe test mode · no retailer order is placed"}}})
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_test_"):
        raise HTTPException(503, "Stripe test mode is not configured")
    try:
        session = stripe.checkout.Session.create(
            api_key=key, mode="payment", line_items=line_items,
            success_url=BASE_URL + "?checkout=success", cancel_url=BASE_URL + "?checkout=cancelled",
            metadata={"app": "flicsy", "note": "hackathon test transaction"})
    except stripe.StripeError as exc:
        print(f"[checkout] Stripe error: {type(exc).__name__} {getattr(exc, 'code', '')}")  # never logs the key
        raise HTTPException(502, "Stripe is unavailable right now")
    total = sum(li["price_data"]["unit_amount"] for li in line_items) / 100
    return {"url": session.url, "id": session.id, "total": total}
