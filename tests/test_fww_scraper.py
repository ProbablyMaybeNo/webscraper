"""Live integration test for the FWW card library scraper.

Run with: py -3.13 -m pytest tests/test_fww_scraper.py -v -s

This test hits the real website — requires internet access and Playwright Chromium.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
import pytest

from backend.scrapers.fww_library import scrape, _normalise_card


# ── Unit tests (no network) ───────────────────────────────────────────────────

def test_normalise_card_basic():
    record = {
        "name": "Super Mutant Suicider",
        "description": "Charges at enemies and explodes.",
        "image": "https://example.com/card.jpg",
        "type": "creature",
        "faction": "Super Mutants",
    }
    item = _normalise_card(record, "sm_suicider")
    assert item["name"] == "Super Mutant Suicider"
    assert item["description"] == "Charges at enemies and explodes."
    assert item["image_url"] == "https://example.com/card.jpg"
    assert "#sm_suicider" in item["source_url"]


def test_normalise_card_missing_fields():
    item = _normalise_card({}, "key123")
    assert item["name"] == "key123"
    assert item["description"] == ""


def test_normalise_card_nested_name():
    """name can be a {en: ...} dict (common Firebase pattern)."""
    record = {"name": {"en": "Vault Dweller"}, "description": "Survivor."}
    item = _normalise_card(record, "vd1")
    assert item["name"] == "Vault Dweller"


def test_normalise_card_description_list():
    """description can be a list of strings."""
    record = {"name": "Super Mutant", "keywords": ["mutant", "hostile"]}
    item = _normalise_card(record, "sm1")
    assert "mutant" in item["description"]


def test_normalise_card_extra_data():
    """Fields not in the standard set go to extra_data."""
    record = {"name": "Raider", "faction": "Raiders", "cost": 5}
    item = _normalise_card(record, "r1")
    assert item["extra_data"].get("faction") == "Raiders"
    assert item["extra_data"].get("cost") == 5


# ── Live integration test ─────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_fww_live_scrape():
    """
    Full live scrape of https://fallout.maloric.com/fww/library.
    Asserts at minimum 10 cards are found.
    Tagged 'integration' so it can be skipped in CI with: pytest -m "not integration"
    """
    messages = []

    async def log(msg, count=0):
        messages.append(msg)
        print(f"  [{count:>4}] {msg}")

    result = await scrape(progress_cb=log)

    items = result["items"]
    print(f"\n=== FWW Scrape Results ===")
    print(f"Total cards found: {len(items)}")
    if items:
        print(f"\nFirst 5 cards:")
        for card in items[:5]:
            print(f"  - {card['name']!r}")
            if card['description']:
                print(f"    {card['description'][:80]}")
            if card['image_url']:
                print(f"    img: {card['image_url'][:60]}")

    assert len(items) >= 1, f"Expected at least 1 card, got {len(items)}"
    assert all("name" in it for it in items), "Every item must have a 'name' key"
    assert all("source_url" in it for it in items), "Every item must have a 'source_url' key"

    # Save results for inspection
    out_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fww_test_results.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {out_path}")
