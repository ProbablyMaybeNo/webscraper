import asyncio
import csv
import io
import json
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from .models import ScrapeRequest, JobResponse, ItemResponse
from ..jobs.queue import (
    create_job, get_job, list_jobs, get_items, run_job, subscribe
)

router = APIRouter(prefix="/api")


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.post("/scrape", response_model=JobResponse, status_code=202)
async def start_scrape(req: ScrapeRequest, background: BackgroundTasks):
    job_id = create_job(req.url, req.label, req.mode, auth_token=req.auth_token)
    background.add_task(run_job, job_id)
    job = get_job(job_id)
    return job


@router.get("/jobs", response_model=list[JobResponse])
def get_jobs():
    return list_jobs()


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_one_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/jobs/{job_id}/items", response_model=list[ItemResponse])
def get_job_items(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return get_items(job_id)


# ── SSE progress stream ───────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        # Poll until queue is registered (job may just be starting)
        for _ in range(20):
            q = subscribe(job_id)
            if q is not None:
                break
            await asyncio.sleep(0.1)

        q = subscribe(job_id)
        if not q:
            yield _sse("error", {"message": "Job queue not available"})
            return

        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
                continue

            if msg is None:
                yield _sse("done", {"status": "finished"})
                break

            yield _sse(msg["event"], msg["data"])

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/export/json")
def export_json(job_id: str):
    items = get_items(job_id)
    if not items:
        raise HTTPException(404, "No items for this job")
    return JSONResponse(content=items)


@router.get("/jobs/{job_id}/export/csv")
def export_csv(job_id: str):
    items = get_items(job_id)
    if not items:
        raise HTTPException(404, "No items for this job")

    output = io.StringIO()
    fieldnames = ["id", "name", "description", "source_url", "image_url", "image_path", "extra_data"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        row = {k: item.get(k, "") for k in fieldnames}
        if isinstance(row.get("extra_data"), dict):
            row["extra_data"] = json.dumps(row["extra_data"])
        writer.writerow(row)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="job_{job_id}.csv"'},
    )


# ── Quick scrape (no storage) ─────────────────────────────────────────────────

@router.post("/quick-scrape")
async def quick_scrape(req: ScrapeRequest):
    """Synchronous scrape — blocks until complete, returns items directly."""
    from ..scraper.engine import run_scrape
    result = await run_scrape(url=req.url, mode=req.mode, download_images=False)
    return {"items": result["items"], "meta": result["meta"]}
