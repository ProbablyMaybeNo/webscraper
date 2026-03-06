"""Tests for the core scraping engine and HTML parser."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import asyncio
from backend.scraper.html_parser import is_js_rendered, scrape_tables, scrape_card_elements
from backend.scraper.formatter import make_item, clean_text
from bs4 import BeautifulSoup


# ── Formatter ────────────────────────────────────────────────────────────────

def test_make_item_defaults():
    item = make_item()
    assert item["name"] == ""
    assert item["description"] == ""
    assert item["source_url"] == ""
    assert item["image_url"] == ""
    assert item["extra_data"] == {}


def test_make_item_cleans_whitespace():
    item = make_item(name="  Hello   World  ", description="\nFoo  Bar\n")
    assert item["name"] == "Hello World"
    assert item["description"] == "Foo Bar"


def test_clean_text_handles_none():
    assert clean_text(None) == ""
    assert clean_text("") == ""
    assert clean_text("  hello  ") == "hello"


# ── JS detection ─────────────────────────────────────────────────────────────

def test_is_js_rendered_spa_shell():
    html = '<html><body><app-root></app-root></body></html>'
    assert is_js_rendered(html) is True


def test_is_js_rendered_real_content():
    html = '<html><body>' + '<p>Real content goes here with lots of text. ' * 20 + '</p></body></html>'
    assert is_js_rendered(html) is False


# ── Table scraping ────────────────────────────────────────────────────────────

def test_scrape_tables_basic():
    html = """
    <table>
        <tr><th>Name</th><th>Description</th></tr>
        <tr><td>Item A</td><td>Description A</td></tr>
        <tr><td>Item B</td><td>Description B</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    items = scrape_tables(soup, "http://example.com")
    assert len(items) == 2
    assert items[0]["name"] == "Item A"


def test_scrape_tables_empty():
    soup = BeautifulSoup("<div>No tables here</div>", "lxml")
    items = scrape_tables(soup, "http://example.com")
    assert items == []


# ── Card element scraping ─────────────────────────────────────────────────────

def test_scrape_card_elements():
    html = """
    <div>
        <div class="card">
            <h3>Card One</h3>
            <p>First card description</p>
        </div>
        <div class="card">
            <h3>Card Two</h3>
            <p>Second card description</p>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    items = scrape_card_elements(soup, "http://example.com")
    assert len(items) >= 2
    names = [it["name"] for it in items]
    assert "Card One" in names
    assert "Card Two" in names


# ── Engine integration ────────────────────────────────────────────────────────

def test_engine_import():
    from backend.scraper import engine
    assert hasattr(engine, 'run_scrape')


@pytest.mark.asyncio
@pytest.mark.integration
async def test_engine_html_mode_reachable_site():
    """Light integration test — scrape a simple static page."""
    from backend.scraper.engine import run_scrape
    result = await run_scrape(
        url="https://example.com",
        mode="html",
        download_images=False,
        job_id="test",
    )
    assert "items" in result
    assert "meta" in result
    # example.com is static HTML
    assert result.get("items") is not None
