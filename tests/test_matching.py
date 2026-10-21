"""Tests for Phase 3: Hard Filters and LLM Fit Scorer."""

import json
from src.storage.models import JobPosting
from src.matching.filters import passes_hard_filters
from src.matching.scorer import JobScorer
from src.adapters.llm import MockLLMAdapter
from src.core.profile import load_profile
from src.config import PROFILE_EXAMPLE_PATH


def test_hard_filters_rejects_senior():
    job = JobPosting(
        id="gh_1",
        company="TechCorp",
        ats_type="greenhouse",
        board_token="techcorp",
        title="Senior Backend Engineer",
        location="Bengaluru, India",
        url="https://example.com/job/1",
        posted_date="2026-10-10T00:00:00Z",
        description="Looking for senior backend architect with 8+ years.",
    )
    config = {"filters": {"disallowed_levels": ["senior", "lead"]}}
    passed, reason = passes_hard_filters(job, config)
    assert not passed
    assert "Disallowed seniority" in reason


def test_hard_filters_accepts_valid_intern():
    job = JobPosting(
        id="gh_2",
        company="TechCorp",
        ats_type="greenhouse",
        board_token="techcorp",
        title="Software Engineer Intern",
        location="Remote, India",
        url="https://example.com/job/2",
        posted_date="2026-10-10T00:00:00Z",
        description="Great summer internship for 2026/2027 graduates.",
    )
    config = {
        "filters": {
            "allowed_locations": ["remote", "india"],
            "allowed_levels": ["intern"],
            "disallowed_levels": ["senior"],
            "target_role_keywords": ["software", "sde"],
            "max_posting_age_days": 30,
        }
    }
    passed, reason = passes_hard_filters(job, config)
    assert passed
    assert "Passed all hard filters" in reason


def test_scorer_with_mock_llm():
    profile = load_profile(PROFILE_EXAMPLE_PATH)
    job = JobPosting(
        id="gh_3",
        company="Acme",
        ats_type="greenhouse",
        board_token="acme",
        title="Gen AI / SDE Intern",
        location="Bengaluru",
        url="https://example.com",
        posted_date="2026-10-10T00:00:00Z",
        description="Build RAG pipelines with Python and FastAPI.",
    )

    mock_response = json.dumps({
        "score": 4,
        "skills_overlap": ["Python", "FastAPI", "RAG Architectures"],
        "missing_requirements": ["Production Kubernetes experience"],
        "seniority_fit": "Exact match for undergraduate intern",
        "honest_reason": "Candidate has direct project experience with RAG and FastAPI. Lacks cloud infrastructure experience."
    })
    scorer = JobScorer(llm_adapter=MockLLMAdapter(default_response=mock_response))
    result = scorer.evaluate_fit(profile, job)

    assert result["score"] == 4
    assert "Python" in result["skills_overlap"]
    assert "Production Kubernetes experience" in result["missing_requirements"]
    assert "Candidate has direct project experience" in result["honest_reason"]
