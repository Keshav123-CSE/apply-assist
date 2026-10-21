"""Tests for Phase 4: Genuineness and Scam Detection."""

from src.storage.models import JobPosting
from src.core.genuineness import GenuinenessChecker, RiskLevel


def test_genuineness_valid_posting():
    job = JobPosting(
        id="gh_10",
        company="GitLab",
        ats_type="greenhouse",
        board_token="gitlab",
        title="Software Engineer Intern",
        location="Remote, India",
        url="https://boards.greenhouse.io/gitlab/jobs/10",
        posted_date="2026-10-18T00:00:00Z",
        description="We are looking for a passionate software engineering intern to join our engineering division. Responsibilities include building backend services, testing, and collaboration with our open source community.",
    )
    checker = GenuinenessChecker()
    risk, reasons = checker.evaluate(job)
    assert risk == RiskLevel.LOW
    assert "trusted ATS domain" in reasons[0]


def test_genuineness_detects_training_fee_scam():
    job = JobPosting(
        id="gh_scam_1",
        company="FakeTech",
        ats_type="greenhouse",
        board_token="faketech",
        title="Python Intern",
        location="Bengaluru",
        url="https://boards.greenhouse.io/faketech/jobs/1",
        posted_date="2026-10-18T00:00:00Z",
        description="Selected candidates must pay a refundable training fee of Rs 5000 before onboarding.",
    )
    checker = GenuinenessChecker()
    risk, reasons = checker.evaluate(job)
    assert risk == RiskLevel.HIGH
    assert any("training fee" in r for r in reasons)


def test_genuineness_detects_whatsapp_contact():
    job = JobPosting(
        id="gh_scam_2",
        company="SketchyCorp",
        ats_type="greenhouse",
        board_token="sketchy",
        title="Web Developer Intern",
        location="Remote",
        url="https://boards.greenhouse.io/sketchy/jobs/2",
        posted_date="2026-10-18T00:00:00Z",
        description="Send your resume directly to our HR team on WhatsApp at +91 9999999999.",
    )
    checker = GenuinenessChecker()
    risk, reasons = checker.evaluate(job)
    assert risk == RiskLevel.HIGH
    assert any("whatsapp" in r.lower() for r in reasons)


def test_genuineness_medium_risk_for_old_posting():
    job = JobPosting(
        id="gh_old",
        company="StaleCorp",
        ats_type="greenhouse",
        board_token="stalecorp",
        title="SDE Intern",
        location="Pune",
        url="https://boards.greenhouse.io/stalecorp/jobs/3",
        posted_date="2026-08-01T00:00:00Z",  # Over 2 months old
        description="A great job description with plenty of detailed requirements and responsibilities.",
    )
    checker = GenuinenessChecker()
    risk, reasons = checker.evaluate(job)
    assert risk == RiskLevel.MEDIUM
    assert any("days old" in r for r in reasons)
