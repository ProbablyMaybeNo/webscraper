"""Smart scraping orchestrator.

Decision tree:
1. Fetch HTML via requests
2. If page is JS-rendered → use Playwright browser scraper
3. Otherwise → use BeautifulSoup HTML parser
4. After items collected → download images
5. Return normalised result
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncGenerator

from . import html_parser, browser as browser_scraper, image_fetcher


async def run_scrape(
    url: str,
    mode: str = "auto",
    download_images: bool = True,
    job_id: str = "default",
    progress_cb=None,
) -> dict:
    """
    mode: "auto" | "html" | "browser"

    progress_cb: optional async callable(message: str, count: int)

    Returns {items, meta, screenshot, api_responses, image_map}
    """

    async def emit(msg: str, count: int = 0):
        if progress_cb:
            await progress_cb(msg, count)

    await emit("Starting scrape…", 0)

    screenshot = None
    api_responses = []
    items = []
    meta = {}

    if mode == "html":
        await emit("Parsing HTML…")
        result = html_parser.run(url)
        items = result["items"]
        meta = result["meta"]

    elif mode == "browser":
        await emit("Launching browser…")
        result = await browser_scraper.run(url)
        items = result["items"]
        meta = result["meta"]
        screenshot = result["screenshot"]
        api_responses = result["api_responses"]

    else:  # auto
        await emit("Fetching page…")
        try:
            html_result = html_parser.run(url)
        except Exception as exc:
            html_result = {"needs_browser": True, "items": [], "meta": {}, "html": ""}

        if html_result["needs_browser"]:
            await emit("JS-rendered page detected — launching browser…")
            browser_result = await browser_scraper.run(url)
            items = browser_result["items"]
            meta = browser_result["meta"]
            screenshot = browser_result["screenshot"]
            api_responses = browser_result["api_responses"]
        else:
            items = html_result["items"]
            meta = html_result["meta"]

    await emit(f"Extracted {len(items)} items", len(items))

    image_map: dict[str, str] = {}
    if download_images and items:
        image_urls = [it["image_url"] for it in items if it.get("image_url")]
        if image_urls:
            await emit(f"Downloading {len(image_urls)} images…")
            image_map = await image_fetcher.download_all(image_urls, job_id)
            # Attach local paths to items
            for item in items:
                if item.get("image_url") and item["image_url"] in image_map:
                    item["image_path"] = image_map[item["image_url"]]

    await emit("Done", len(items))

    return {
        "items": items,
        "meta": meta,
        "screenshot": screenshot,
        "api_responses": api_responses,
        "image_map": image_map,
    }
