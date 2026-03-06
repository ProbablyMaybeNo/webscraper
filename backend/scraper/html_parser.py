"""Static HTML scraper using BeautifulSoup.

Strategy: attempt to extract structured data from common patterns:
- OpenGraph / schema.org metadata
- Tables (<table>)
- Card-like elements (repeated sibling divs with img + text)
- Definition lists / key-value pairs
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

from .formatter import make_item

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str, timeout: int = 15) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def is_js_rendered(html: str) -> bool:
    """Return True when the page body is essentially empty (SPA shell)."""
    soup = BeautifulSoup(html, "lxml")
    body = soup.body
    if not body:
        return True
    text = body.get_text(separator=" ", strip=True)
    # Less than 200 chars of real text → almost certainly a JS shell
    return len(text) < 200


def resolve_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href)


def scrape_tables(soup: BeautifulSoup, base_url: str) -> list[dict]:
    items = []
    for table in soup.find_all("table"):
        headers: list[str] = []
        for th in table.find_all("th"):
            headers.append(th.get_text(strip=True))
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            row_data: dict[str, Any] = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_data[key] = cell.get_text(strip=True)
            name = row_data.get(headers[0], "") if headers else list(row_data.values())[0]
            desc_key = next(
                (k for k in ("description", "desc", "text", "details") if k.lower() in [h.lower() for h in headers]),
                headers[1] if len(headers) > 1 else None,
            )
            desc = row_data.get(desc_key, "") if desc_key else ""
            img = cell.find("img") if cells else None
            items.append(
                make_item(
                    name=name,
                    description=desc,
                    source_url=base_url,
                    image_url=resolve_url(base_url, img["src"]) if img and img.get("src") else "",
                    extra=row_data,
                )
            )
    return items


def scrape_card_elements(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Find repeated card-like container elements (common UI pattern)."""
    items = []
    # Look for elements with class names hinting at cards/items/tiles
    card_pattern = re.compile(r"card|item|tile|product|result|entry", re.I)
    containers = soup.find_all(class_=card_pattern)
    # De-duplicate by ensuring we take the most-specific container
    seen_ids = set()
    for el in containers:
        el_id = id(el)
        if el_id in seen_ids:
            continue
        # Skip if a parent with the same class is already captured
        parent_match = any(
            id(p) in seen_ids
            for p in el.parents
            if isinstance(p, Tag) and p.get("class")
        )
        if parent_match:
            continue
        seen_ids.add(el_id)

        img_tag = el.find("img")
        heading = el.find(re.compile(r"h[1-6]|strong|b"))
        paras = el.find_all("p")

        name = heading.get_text(strip=True) if heading else ""
        description = " ".join(p.get_text(strip=True) for p in paras)
        image_url = ""
        if img_tag:
            src = img_tag.get("src") or img_tag.get("data-src") or ""
            image_url = resolve_url(base_url, src) if src else ""

        if not name and not description:
            continue

        items.append(make_item(name=name, description=description, source_url=base_url, image_url=image_url))

    return items


def scrape_meta(soup: BeautifulSoup, base_url: str) -> dict:
    """Extract page-level metadata (title, description, og tags)."""
    meta: dict[str, str] = {}
    title = soup.find("title")
    if title:
        meta["title"] = title.get_text(strip=True)
    for tag in soup.find_all("meta"):
        name = tag.get("name") or tag.get("property") or ""
        content = tag.get("content") or ""
        if name and content:
            meta[name] = content
    return meta


def scrape_images(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Return all images on the page as items."""
    items = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        alt = img.get("alt") or ""
        items.append(make_item(name=alt or src, description="", source_url=base_url, image_url=resolve_url(base_url, src)))
    return items


def run(url: str) -> dict:
    """
    Main entry point. Returns:
        {
          "needs_browser": bool,
          "items": list[dict],
          "meta": dict,
          "html": str,
        }
    """
    html = fetch_html(url)

    if is_js_rendered(html):
        return {"needs_browser": True, "items": [], "meta": {}, "html": html}

    soup = BeautifulSoup(html, "lxml")
    meta = scrape_meta(soup, url)

    items = scrape_tables(soup, url)
    if not items:
        items = scrape_card_elements(soup, url)
    if not items:
        items = scrape_images(soup, url)

    return {"needs_browser": False, "items": items, "meta": meta, "html": html}
