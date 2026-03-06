"""Downloads and saves images from scraped URLs."""
from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import re
import urllib.parse
from pathlib import Path

import aiohttp

IMAGES_DIR = Path(__file__).parent.parent.parent / "data" / "images"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _url_to_filename(url: str, ext: str = ".jpg") -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    # Try to preserve original filename
    parsed = urllib.parse.urlparse(url)
    basename = Path(parsed.path).name
    # Remove query strings and sanitize
    basename = re.sub(r"[^\w\-.]", "_", basename)[:40]
    if "." not in basename:
        basename = f"{basename}{ext}"
    return f"{h}_{basename}"


def _guess_ext(content_type: str, url: str) -> str:
    ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ""
    if not ext:
        parsed = urllib.parse.urlparse(url)
        ext = Path(parsed.path).suffix or ".jpg"
    # Normalize common aliases
    return {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)


async def download_image(session: aiohttp.ClientSession, url: str, job_id: str) -> str | None:
    """Download a single image and return its local path (relative to data/)."""
    if not url or not url.startswith("http"):
        return None
    dest_dir = IMAGES_DIR / job_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                return None
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            ext = _guess_ext(content_type, url)
            filename = _url_to_filename(url, ext)
            dest = dest_dir / filename
            data = await resp.read()
            dest.write_bytes(data)
            return str(dest.relative_to(IMAGES_DIR.parent))
    except Exception:
        return None


async def download_all(image_urls: list[str], job_id: str, concurrency: int = 5) -> dict[str, str]:
    """Download multiple images concurrently. Returns {url: local_path}."""
    results: dict[str, str] = {}
    sem = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession() as session:
        async def fetch(url: str):
            async with sem:
                path = await download_image(session, url, job_id)
                if path:
                    results[url] = path

        await asyncio.gather(*[fetch(u) for u in image_urls if u])

    return results
