"""Normalises raw scraped data into standard ScrapedItem dicts."""
import re
from typing import Any


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def make_item(
    name: str | None = None,
    description: str | None = None,
    source_url: str | None = None,
    image_url: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict:
    return {
        "name": clean_text(name),
        "description": clean_text(description),
        "source_url": source_url or "",
        "image_url": image_url or "",
        "extra_data": extra or {},
    }
