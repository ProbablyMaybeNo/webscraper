from pydantic import BaseModel
from typing import Any


class ScrapeRequest(BaseModel):
    url: str
    label: str | None = None
    mode: str = "auto"          # auto | html | browser
    download_images: bool = True
    auth_token: str | None = None  # bearer token for auth-required sites


class JobResponse(BaseModel):
    id: str
    url: str
    label: str | None
    mode: str
    status: str
    created_at: str
    updated_at: str
    item_count: int
    error: str | None


class ItemResponse(BaseModel):
    id: int
    job_id: str
    name: str
    description: str
    source_url: str
    image_url: str
    image_path: str
    extra_data: Any
    created_at: str
