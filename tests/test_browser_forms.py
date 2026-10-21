"""Tests for Phase 6: Form Field Detection and Approval Safety Guards."""

from unittest.mock import patch
from src.core.profile import load_profile
from src.browser.forms import FormHandler
from src.config import PROFILE_EXAMPLE_PATH


def test_form_handler_maps_standard_fields():
    profile = load_profile(PROFILE_EXAMPLE_PATH)
    handler = FormHandler(profile)

    assert handler.get_standard_value("first_name") == "Aarav"
    assert handler.get_standard_value("last_name") == "Sharma"
    assert handler.get_standard_value("email") == "aarav.sharma@example.com"
    assert handler.get_standard_value("linkedin") == "https://linkedin.com/in/aaravsharma"


def test_form_handler_resolves_canned_answers():
    profile = load_profile(PROFILE_EXAMPLE_PATH)
    handler = FormHandler(profile)

    ans, source = handler.answer_custom_question("What is your notice period?")
    assert source == "from_canned_answers"
    assert "Immediate" in ans

    ans, source = handler.answer_custom_question("Are you legally authorized to work in India?")
    assert source == "from_canned_answers"
    assert "citizen of India" in ans


def test_form_handler_stops_and_asks_on_unmapped_question():
    profile = load_profile(PROFILE_EXAMPLE_PATH)
    handler = FormHandler(profile)

    # Mock user terminal typing for unmapped question
    with patch("builtins.input", return_value="I built an open source RAG search engine."):
        ans, source = handler.answer_custom_question("Describe a difficult bug you solved recently?")
        assert source == "user_prompted"
        assert ans == "I built an open source RAG search engine."
