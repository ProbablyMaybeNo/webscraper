"""Fallout: Wasteland Warfare — Card Library Scraper.

The FWW library app (fallout.maloric.com) requires Google/Apple OAuth login.
Card data is served from:  GET /api/library/fww/entries  (requires Authorization header)

Two modes:
  1. REST API mode (fast, preferred): provide an auth_token from your browser session
  2. Browser mode (auto-login not possible): navigates, tries to capture token from
     localStorage, then hits the REST API.

To get your auth token:
  1. Open https://fallout.maloric.com in Chrome and log in
  2. Open DevTools (F12) → Application → Local Storage → fallout.maloric.com
  3. Find key starting with "firebase:authUser:" and copy the "stsTokenManager.accessToken" value
  OR open DevTools Console and run:
     Object.values(localStorage).map(v=>{try{return JSON.parse(v)}catch{return null}}).filter(Boolean).find(v=>v.stsTokenManager)?.stsTokenManager?.accessToken
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from playwright.async_api import async_playwright, Page

from ..scraper.formatter import make_item

BASE_URL = "https://fallout.maloric.com/fww/library"
API_BASE = "https://fallout.maloric.com/api"
DEFAULT_PAGE_SIZE = 100
HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://fallout.maloric.com",
    "Referer": "https://fallout.maloric.com/fww/library",
}


def _normalise_card(record: dict, card_id: str) -> dict:
    name = (
        record.get("name") or record.get("title") or record.get("card_name")
        or (record.get("name_en") if isinstance(record.get("name_en"), str) else None)
        or card_id or "Unknown"
    )
    # name may be a nested {en: ...} object
    if isinstance(name, dict):
        name = name.get("en") or name.get("value") or str(name)

    description = ""
    for field in ("description", "rules_text", "flavour_text", "special", "ability", "keywords", "text"):
        val = record.get(field)
        if val:
            if isinstance(val, dict):
                val = val.get("en") or val.get("value") or ""
            if isinstance(val, list):
                val = " | ".join(str(v) for v in val)
            description = str(val)
            break

    image_url = (
        record.get("image") or record.get("image_url") or record.get("imageUrl")
        or record.get("img") or record.get("front_image") or record.get("cardImage")
        or record.get("thumbnail") or ""
    )
    if isinstance(image_url, dict):
        image_url = image_url.get("url") or ""

    # Build extra_data with all remaining fields
    skip = {"name", "description", "image", "image_url", "imageUrl", "img", "front_image", "cardImage", "thumbnail"}
    extra = {k: v for k, v in record.items() if k not in skip}

    return make_item(
        name=str(name).strip(),
        description=str(description).strip(),
        source_url=f"{BASE_URL}#{card_id}",
        image_url=str(image_url) if image_url else "",
        extra=extra,
    )


def _fetch_all_entries(auth_token: str) -> list[dict]:
    """Paginate through the FWW library entries API."""
    headers = {**HEADERS_BASE, "Authorization": f"Bearer {auth_token}"}
    items: list[dict] = []
    skip = 0
    page_size = DEFAULT_PAGE_SIZE

    while True:
        params: dict[str, Any] = {"skip": skip, "pageSize": page_size}
        resp = requests.get(f"{API_BASE}/library/fww/entries", headers=headers, params=params, timeout=30)

        if resp.status_code == 401:
            raise PermissionError(
                "Auth token is invalid or expired. "
                "Please get a fresh token from your browser (see module docstring)."
            )
        resp.raise_for_status()

        data = resp.json()
        batch = data.get("items") or data.get("entries") or (data if isinstance(data, list) else [])

        if not batch:
            break

        for record in batch:
            card_id = record.get("_id") or record.get("id") or str(skip + len(items))
            items.append(_normalise_card(record, str(card_id)))

        skip += len(batch)
        page_count = data.get("pageCount")
        item_count = data.get("itemCount", 0)

        if page_count is not None and skip >= page_count * page_size:
            break
        if item_count and skip >= item_count:
            break
        if len(batch) < page_size:
            break

    return items


async def _capture_token_from_browser() -> str | None:
    """Launch a browser, let the JS app run, and try to extract the Firebase auth token."""
    token = None
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
        )
        page = await context.new_page()

        # Watch for authenticated API calls — the app will send the bearer token
        async def on_request(request):
            nonlocal token
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer ") and not token:
                token = auth_header.split("Bearer ", 1)[1].strip()

        page.on("request", on_request)
        await page.goto("https://fallout.maloric.com/fww/library", wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(3000)

        # Also try localStorage
        if not token:
            token = await page.evaluate("""() => {
                try {
                    const vals = Object.values(localStorage);
                    for (const v of vals) {
                        try {
                            const parsed = JSON.parse(v);
                            if (parsed?.stsTokenManager?.accessToken) {
                                return parsed.stsTokenManager.accessToken;
                            }
                        } catch {}
                    }
                } catch {}
                return null;
            }""")

        await browser.close()
    return token


async def scrape(auth_token: str | None = None, progress_cb=None) -> dict:
    """
    Scrape the FWW card library.

    auth_token: Firebase ID token (Bearer). If not provided, tries env var
                FWW_AUTH_TOKEN, then attempts to extract from browser session.

    Returns {items, raw_responses, screenshot}
    """

    async def emit(msg: str, count: int = 0):
        if progress_cb:
            await progress_cb(msg, count)

    # Resolve token: explicit arg → env var → .fww_token file
    token = auth_token or os.environ.get("FWW_AUTH_TOKEN")
    if not token:
        token_file = Path(__file__).parent.parent.parent / ".fww_token"
        if token_file.exists():
            token = token_file.read_text().strip() or None

    if not token:
        await emit("No auth token — attempting to capture from browser session…")
        token = await _capture_token_from_browser()

    if not token:
        await emit(
            "No auth token available. To scrape the FWW library:\n"
            "  1. Log in at https://fallout.maloric.com in Chrome\n"
            "  2. Open DevTools Console and run:\n"
            "     Object.values(localStorage).map(v=>{try{return JSON.parse(v)}catch{return null}})"
            ".filter(Boolean).find(v=>v.stsTokenManager)?.stsTokenManager?.accessToken\n"
            "  3. Set the result as env var FWW_AUTH_TOKEN=<token>\n"
            "  4. Or pass it as auth_token parameter in the API request"
        )
        return {"items": [], "raw_responses": [], "screenshot": None, "error": "auth_required"}

    await emit("Auth token found — fetching card library via REST API…")

    try:
        items = _fetch_all_entries(token)
        await emit(f"Fetched {len(items)} cards from FWW library", len(items))
        return {"items": items, "raw_responses": [], "screenshot": None}

    except PermissionError as e:
        await emit(f"Auth error: {e}")
        return {"items": [], "raw_responses": [], "screenshot": None, "error": str(e)}

    except Exception as e:
        await emit(f"Error: {e}")
        raise
