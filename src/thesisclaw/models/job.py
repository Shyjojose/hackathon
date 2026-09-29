from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanJob(BaseModel):
    """Tracking model for an async literature evaluation job."""

    job_id: str
    status: JobStatus = JobStatus.QUEUED
    target_url: str
    created_at: str
    completed_at: str | None = None
    error: str | None = None
    verdict: str | None = None
