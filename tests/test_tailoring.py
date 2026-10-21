"""Tests for Phase 5: Fact Checker & Tailoring Engine."""

import pytest
from src.core.profile import load_profile
from src.core.fact_checker import FactChecker, FactCheckValidationError
from src.tailoring.resume_generator import ResumeGenerator
from src.tailoring.cover_note import CoverNoteGenerator
from src.adapters.llm import MockLLMAdapter
from src.storage.models import JobPosting
from src.config import PROFILE_EXAMPLE_PATH


@pytest.fixture
def profile():
    return load_profile(PROFILE_EXAMPLE_PATH)


@pytest.fixture
def sample_job():
    return JobPosting(
        id="gh_tailor_1",
        company="Postman",
        ats_type="greenhouse",
        board_token="postman",
        title="Software Engineer Intern",
        location="Bengaluru, India",
        url="https://boards.greenhouse.io/postman/jobs/1",
        posted_date="2026-10-18T00:00:00Z",
        description="Looking for an intern skilled in Python, FastAPI, and Redis to build APIs.",
    )


def test_fact_check_passes_on_valid_skills(profile):
    checker = FactChecker(profile)
    # Python and FastAPI are in profile.example.yml
    checker.verify_skills_list(["Python", "FastAPI", "Docker"])


def test_fact_check_fails_on_unverified_skill(profile):
    checker = FactChecker(profile)
    # Kubernetes is deliberately NOT in profile.example.yml
    with pytest.raises(FactCheckValidationError) as exc:
        checker.verify_skills_list(["Python", "Kubernetes"])
    assert "Kubernetes" in str(exc.value)
    assert "NOT listed in profile.yml" in str(exc.value)


def test_fact_check_fails_on_inflated_term(profile):
    checker = FactChecker(profile)
    with pytest.raises(FactCheckValidationError) as exc:
        checker.verify_text_content("Candidate has 10 years experience as a microservices architect.")
    assert "unverified/inflated term" in str(exc.value)


def test_resume_generation_reorders_relevant_projects(profile, sample_job, tmp_path):
    generator = ResumeGenerator(profile)
    html = generator.generate_html(sample_job)
    assert profile.contact.full_name in html
    assert "DocuSense" in html
    assert "FastAPI" in html

    # Output file test
    out_file = generator.export_pdf_or_html(sample_job, output_dir=tmp_path)
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_cover_note_generator_with_mock_llm(profile, sample_job):
    truthful_note = (
        "Dear Postman Hiring Team,\n\n"
        "I am a 2nd-year B.Tech CSE student passionate about backend systems. "
        "Through my project DocuSense, I have hands-on experience building FastAPI services "
        "and utilizing Python. I would love the opportunity to contribute as an intern."
    )
    generator = CoverNoteGenerator(profile, llm_adapter=MockLLMAdapter(default_response=truthful_note))
    note = generator.generate(sample_job)
    assert "DocuSense" in note
    assert "Postman" in note
