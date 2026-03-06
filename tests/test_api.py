"""Tests for the FastAPI backend."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.database import init_db

init_db()
client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_get_jobs_empty():
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_start_scrape_returns_job():
    resp = client.post("/api/scrape", json={
        "url": "https://example.com",
        "mode": "html",
        "download_images": False,
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] in ("pending", "running")
    assert data["url"] == "https://example.com"


def test_get_job_not_found():
    resp = client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404


def test_get_items_not_found():
    resp = client.get("/api/jobs/does-not-exist/items")
    assert resp.status_code == 404


def test_quick_scrape():
    resp = client.post("/api/quick-scrape", json={
        "url": "https://example.com",
        "mode": "html",
        "download_images": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "meta" in data
