"""Data models for job postings and applications."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class JobPosting:
    id: str  # Format: {ats}_{board_token}_{job_id}
    company: str
    ats_type: str  # greenhouse, lever, ashby, workable
    board_token: str
    title: str
    location: str
    url: str
    posted_date: Optional[str]
    description: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "DISCOVERED"  # DISCOVERED, FILTERED_OUT, MATCHED, REVIEWED, TAILORED, APPLIED, REJECTED
    fit_score: Optional[int] = None
    fit_reason: Optional[str] = None
    risk_level: Optional[str] = None  # LOW, MEDIUM, HIGH
    risk_reasons: Optional[str] = None


@dataclass
class ApplicationRecord:
    job_id: str
    company: str
    role_title: str
    applied_date: str
    status: str  # DRY_RUN, SUBMITTED, INTERVIEW, REJECTED
    tailored_resume_path: Optional[str] = None
    notes: Optional[str] = None
