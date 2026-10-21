"""Tests for Phase 2: ATS Clients, Storage, and Detector."""

from pathlib import Path
from unittest.mock import MagicMock
from src.storage.database import Database
from src.storage.models import JobPosting
from src.discovery.greenhouse import GreenhouseClient
from src.discovery.lever import LeverClient
from src.discovery.detector import detect_ats_from_url


def test_database_upsert_and_fetch(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = Database(db_file)

    job = JobPosting(
        id="gh_postman_12345",
        company="Postman",
        ats_type="greenhouse",
        board_token="postman",
        title="Software Engineer Intern",
        location="Bengaluru, India",
        url="https://boards.greenhouse.io/postman/jobs/12345",
        posted_date="2026-10-01T00:00:00Z",
        description="Great internship role for undergraduates.",
    )

    is_new = db.upsert_job(job)
    assert is_new is True

    fetched = db.get_job("gh_postman_12345")
    assert fetched is not None
    assert fetched.title == "Software Engineer Intern"
    assert fetched.company == "Postman"

    # Second upsert should update, not re-insert as new
    job.title = "Software Engineer Intern (Updated)"
    is_new_again = db.upsert_job(job)
    assert is_new_again is False

    refetched = db.get_job("gh_postman_12345")
    assert refetched.title == "Software Engineer Intern (Updated)"


def test_greenhouse_client_parser():
    client = GreenhouseClient()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "jobs": [
            {
                "id": 999,
                "title": "Backend Engineering Intern",
                "location": {"name": "Remote, India"},
                "absolute_url": "https://boards.greenhouse.io/test/jobs/999",
                "updated_at": "2026-10-15T12:00:00Z",
                "content": "<p>Python and FastAPI required.</p>",
            }
        ]
    }
    client._get = MagicMock(return_value=mock_resp)

    jobs = client.fetch_jobs(company_name="TestCorp", board_token="testcorp")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "gh_testcorp_999"
    assert job.title == "Backend Engineering Intern"
    assert "Python and FastAPI required." in job.description
    assert job.location == "Remote, India"


def test_detector_regex():
    ats, token = detect_ats_from_url("https://boards.greenhouse.io/postman")
    assert ats == "greenhouse"
    assert token == "postman"

    ats, token = detect_ats_from_url("https://jobs.lever.co/docker")
    assert ats == "lever"
    assert token == "docker"

    ats, token = detect_ats_from_url("https://jobs.ashbyhq.com/ramp")
    assert ats == "ashby"
    assert token == "ramp"
