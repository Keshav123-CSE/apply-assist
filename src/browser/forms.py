"""Form field detection, mapping, and interactive question handler."""

import re
from typing import Dict, Optional, Tuple
from src.core.profile import UserProfile


STANDARD_FIELD_SELECTORS = {
    "first_name": [
        'input[name*="first_name" i]',
        'input[id*="first_name" i]',
        'input[placeholder*="first name" i]',
        'input[aria-label*="first name" i]'
    ],
    "last_name": [
        'input[name*="last_name" i]',
        'input[id*="last_name" i]',
        'input[placeholder*="last name" i]',
        'input[aria-label*="last name" i]'
    ],
    "full_name": [
        'input[name*="name" i]:not([name*="first"]):not([name*="last"])',
        'input[id*="name" i]:not([id*="first"]):not([id*="last"])',
        'input[placeholder*="full name" i]',
        'input[aria-label*="full name" i]'
    ],
    "email": [
        'input[type="email"]',
        'input[name*="email" i]',
        'input[id*="email" i]',
        'input[placeholder*="email" i]'
    ],
    "phone": [
        'input[type="tel"]',
        'input[name*="phone" i]',
        'input[id*="phone" i]',
        'input[placeholder*="phone" i]'
    ],
    "linkedin": [
        'input[name*="linkedin" i]',
        'input[id*="linkedin" i]',
        'input[placeholder*="linkedin" i]'
    ],
    "github": [
        'input[name*="github" i]',
        'input[id*="github" i]',
        'input[placeholder*="github" i]'
    ],
    "portfolio": [
        'input[name*="portfolio" i]',
        'input[name*="website" i]',
        'input[id*="portfolio" i]',
        'input[placeholder*="portfolio" i]'
    ],
    "resume_upload": [
        'input[type="file"][name*="resume" i]',
        'input[type="file"][id*="resume" i]',
        'input[type="file"][data-testid*="resume" i]',
        'input[type="file"]'
    ],
}


class FormHandler:
    def __init__(self, profile: UserProfile):
        self.profile = profile

    def get_standard_value(self, field_key: str) -> Optional[str]:
        contact = self.profile.contact
        name_parts = contact.full_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        mapping = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": contact.full_name,
            "email": contact.email,
            "phone": contact.phone,
            "linkedin": contact.linkedin,
            "github": contact.github,
            "portfolio": contact.portfolio or "",
        }
        return mapping.get(field_key)

    def answer_custom_question(self, question_text: str) -> Tuple[Optional[str], str]:
        """Tries to answer a custom question from profile.canned_answers.
        If unknown or sensitive, STOP and ask user in terminal.
        NEVER guess answers for work authorization, demographic, or salary questions.
        """
        q_lower = question_text.lower()

        # Check canned answers
        if "notice period" in q_lower:
            ans = self.profile.canned_answers.get("notice_period")
            if ans:
                return ans, "from_canned_answers"

        if "relocate" in q_lower or "location" in q_lower:
            ans = self.profile.canned_answers.get("willing_to_relocate")
            if ans:
                return ans, "from_canned_answers"

        if "authorized to work" in q_lower or "sponsorship" in q_lower or "work authorization" in q_lower:
            ans = self.profile.canned_answers.get("work_authorization_india")
            if ans:
                return ans, "from_canned_answers"

        if "salary" in q_lower or "stipend" in q_lower or "compensation" in q_lower:
            ans = self.profile.canned_answers.get("salary_expectations")
            if ans:
                return ans, "from_canned_answers"

        # Not mapped in profile: Must prompt user explicitly
        print("\n" + "=" * 60)
        print("[!] PAUSE: Form requires an unmapped / custom answer.")
        print(f"QUESTION: '{question_text.strip()}'")
        print("Never guessing. Please provide your answer (or press enter to skip):")
        user_input = input("> ").strip()
        print("=" * 60 + "\n")
        return user_input or None, "user_prompted"
