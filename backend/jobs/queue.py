"""In-process job queue with SSE progress streaming.

Each job runs in a background asyncio task. Progress events are published
to a per-job asyncio.Queue so the SSE endpoint can stream them to the UI.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..db.database import get_db
from ..scraper.engine import run_scrape
from ..scrapers import fww_library

# {job_id: asyncio.Queue}
_progress_queues: dict[str, asyncio.Queue] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(url: str, label: str | None, mode: str, auth_token: str | None = None) -> str:
    job_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO jobs (id, url, label, mode, status, created_at, updated_at, auth_token) VALUES (?,?,?,?,?,?,?,?)",
        (job_id, url, label or url, mode, "pending", _now(), _now(), auth_token),
    )
    conn.commit()
    conn.close()
    return job_id


def get_job(job_id: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_jobs() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_items(job_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM items WHERE job_id=? ORDER BY id", (job_id,)).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        if d.get("extra_data"):
            try:
                d["extra_data"] = json.loads(d["extra_data"])
            except Exception:
                pass
        items.append(d)
    return items


def _update_job(job_id: str, **kwargs):
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    conn = get_db()
    conn.execute(f"UPDATE jobs SET {sets} WHERE id=?", values)
    conn.commit()
    conn.close()


def _save_items(job_id: str, items: list[dict]):
    conn = get_db()
    for item in items:
        conn.execute(
            """INSERT INTO items
               (job_id, name, description, source_url, image_url, image_path, extra_data, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                job_id,
                item.get("name", ""),
                item.get("description", ""),
                item.get("source_url", ""),
                item.get("image_url", ""),
                item.get("image_path", ""),
                json.dumps(item.get("extra_data") or {}),
                _now(),
            ),
        )
    conn.execute("UPDATE jobs SET item_count=?, updated_at=? WHERE id=?", (len(items), _now(), job_id))
    conn.commit()
    conn.close()


async def _publish(job_id: str, event: str, data: Any):
    q = _progress_queues.get(job_id)
    if q:
        await q.put({"event": event, "data": data})


async def run_job(job_id: str):
    """Execute a scrape job. Called as a background task."""
    job = get_job(job_id)
    if not job:
        return

    _progress_queues[job_id] = asyncio.Queue()
    _update_job(job_id, status="running")
    await _publish(job_id, "status", {"status": "running"})

    try:
        async def progress_cb(message: str, count: int = 0):
            await _publish(job_id, "progress", {"message": message, "count": count})

        url = job["url"]
        mode = job["mode"]

        # Route to specialist scrapers
        if "fallout.maloric.com" in url and "/fww/library" in url:
            result = await fww_library.scrape(auth_token=job.get("auth_token"), progress_cb=progress_cb)
        else:
            result = await run_scrape(url=url, mode=mode, job_id=job_id, progress_cb=progress_cb)

        items = result["items"]
        _save_items(job_id, items)
        _update_job(job_id, status="done", item_count=len(items))
        await _publish(job_id, "done", {"count": len(items), "status": "done"})

    except Exception as exc:
        error_msg = str(exc)
        _update_job(job_id, status="error", error=error_msg)
        await _publish(job_id, "error", {"message": error_msg})

    finally:
        # Drain queue sentinel
        q = _progress_queues.get(job_id)
        if q:
            await q.put(None)


def subscribe(job_id: str) -> asyncio.Queue | None:
    return _progress_queues.get(job_id)
