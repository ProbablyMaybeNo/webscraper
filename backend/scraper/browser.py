"""Playwright-based browser scraper.

Handles:
- JS-rendered SPAs
- Network request interception (captures XHR/fetch JSON responses)
- DOM extraction after full render
- Image collection
"""
from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

from playwright.async_api import async_playwright, Page, Response

from .formatter import make_item


async def _intercept_responses(page: Page) -> list[dict]:
    """Collect all JSON API responses made during page load."""
    captured: list[dict] = []

    async def on_response(response: Response):
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            return
        try:
            data = await response.json()
            captured.append({"url": response.url, "data": data})
        except Exception:
            pass

    page.on("response", on_response)
    return captured


async def _extract_dom_items(page: Page, base_url: str) -> list[dict]:
    """Extract card/item elements from rendered DOM."""
    items = []

    # Try to find repeated structural elements
    result = await page.evaluate("""() => {
        const candidates = [];

        // Look for common card/item selectors
        const selectors = [
            '[class*="card"]', '[class*="item"]', '[class*="tile"]',
            '[class*="product"]', '[class*="result"]', 'li', 'article',
            '.card', '.item', '.tile'
        ];

        let elements = [];
        for (const sel of selectors) {
            const found = Array.from(document.querySelectorAll(sel));
            if (found.length > 3) {
                elements = found;
                break;
            }
        }

        for (const el of elements.slice(0, 500)) {
            const img = el.querySelector('img');
            const heading = el.querySelector('h1,h2,h3,h4,h5,h6,strong,b,[class*="title"],[class*="name"]');
            const paras = el.querySelectorAll('p,[class*="desc"],[class*="text"]');

            const name = heading ? heading.textContent.trim() : '';
            const description = Array.from(paras).map(p => p.textContent.trim()).join(' ').trim();
            const imageUrl = img ? (img.src || img.dataset.src || '') : '';
            const linkEl = el.querySelector('a');
            const link = linkEl ? linkEl.href : '';

            if (!name && !description) continue;

            candidates.push({ name, description, image_url: imageUrl, source_url: link || window.location.href });
        }
        return candidates;
    }""")

    for r in (result or []):
        items.append(make_item(
            name=r.get("name"),
            description=r.get("description"),
            source_url=r.get("source_url") or base_url,
            image_url=r.get("image_url"),
        ))

    return items


def _parse_api_responses(captured: list[dict], base_url: str) -> list[dict]:
    """Try to interpret intercepted API responses as item lists."""
    items = []
    for entry in captured:
        data = entry["data"]
        if not data:
            continue

        # Firebase Realtime DB returns a dict of {key: object}
        if isinstance(data, dict):
            # Skip tiny utility responses
            if len(data) < 2:
                continue
            records = list(data.values())
        elif isinstance(data, list):
            records = data
        else:
            continue

        if not records or not isinstance(records[0], dict):
            continue

        for record in records:
            if not isinstance(record, dict):
                continue

            name = (
                record.get("name")
                or record.get("title")
                or record.get("card_name")
                or record.get("cardName")
                or record.get("label")
                or ""
            )
            description = (
                record.get("description")
                or record.get("desc")
                or record.get("text")
                or record.get("flavour_text")
                or record.get("flavourText")
                or record.get("rules_text")
                or record.get("rulesText")
                or ""
            )
            image_url = (
                record.get("image")
                or record.get("image_url")
                or record.get("imageUrl")
                or record.get("img")
                or record.get("thumbnail")
                or ""
            )

            if not name and not description:
                continue

            items.append(make_item(
                name=str(name),
                description=str(description),
                source_url=base_url,
                image_url=str(image_url) if image_url else "",
                extra={k: v for k, v in record.items() if k not in ("name", "description", "image_url")},
            ))

    return items


async def run(url: str, wait_selector: str | None = None, timeout: int = 30000) -> dict:
    """
    Navigate to url with a real browser, capture network + DOM.

    Returns:
        {
          "items": list[dict],
          "api_responses": list[dict],
          "meta": dict,
          "screenshot": bytes | None,
        }
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # Start intercepting before navigation
        captured: list[dict] = []

        async def on_response(response: Response):
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                return
            try:
                data = await response.json()
                captured.append({"url": response.url, "data": data})
            except Exception:
                pass

        page.on("response", on_response)

        await page.goto(url, wait_until="networkidle", timeout=timeout)

        if wait_selector:
            try:
                await page.wait_for_selector(wait_selector, timeout=10000)
            except Exception:
                pass

        # Extra wait for dynamic content
        await page.wait_for_timeout(2000)

        # Try API responses first (higher quality data)
        items = _parse_api_responses(captured, url)

        # Fall back to DOM extraction
        if not items:
            items = await _extract_dom_items(page, url)

        # Page metadata
        title = await page.title()
        meta = {"title": title, "url": page.url}

        screenshot = await page.screenshot(full_page=False)

        await browser.close()

    return {
        "items": items,
        "api_responses": captured,
        "meta": meta,
        "screenshot": screenshot,
    }
