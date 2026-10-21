"""Tests for Phase 1: Profile Loading and Validation."""

import pytest
from pathlib import Path
from src.core.profile import load_profile, UserProfile, ProfileValidationError
from src.config import PROFILE_EXAMPLE_PATH


def test_load_example_profile():
    """Verify that profile.example.yml passes all schema and integrity checks."""
    assert PROFILE_EXAMPLE_PATH.exists()
    profile = load_profile(PROFILE_EXAMPLE_PATH)
    assert isinstance(profile, UserProfile)
    assert profile.contact.full_name == "Aarav Sharma"
    assert "Python" in profile.skills.languages
    assert len(profile.education) >= 1
    assert len(profile.projects) >= 1
    assert "Immediate (0 days)" in profile.canned_answers.get("notice_period", "")


def test_profile_missing_contact_fails(tmp_path: Path):
    """Verify that a profile missing required contact info raises ProfileValidationError."""
    bad_yaml = tmp_path / "bad_profile.yml"
    bad_yaml.write_text("contact:\n  email: test@example.com\n", encoding="utf-8")

    with pytest.raises(ProfileValidationError) as exc:
        load_profile(bad_yaml)
    assert "Missing required contact field" in str(exc.value)


def test_all_skills_flat():
    """Verify all_skills_flat deduplicates and aggregates across all buckets."""
    profile = load_profile(PROFILE_EXAMPLE_PATH)
    flat_skills = profile.skills.all_skills_flat()
    assert "Python" in flat_skills
    assert "FastAPI" in flat_skills
    assert "PostgreSQL" in flat_skills
    assert "Git" in flat_skills
    assert len(flat_skills) == len(set(flat_skills))  # Unique
