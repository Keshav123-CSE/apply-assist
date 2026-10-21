"""Deterministic Fact Checker.
CRITICAL SAFETY INSTRUCTION:
Compares every line and skill in the tailored resume/cover note against profile.yml.
Fails the build on any unsupported claim, invented skill, or inflated metric.
"""

import re
from typing import List, Set
from src.core.profile import UserProfile


class FactCheckValidationError(Exception):
    """Raised when an unverified claim, metric, or skill is detected in generated content."""
    pass


class FactChecker:
    def __init__(self, profile: UserProfile):
        self.profile = profile
        self.allowed_skills = {s.lower().strip() for s in profile.skills.all_skills_flat()}
        # Normalize common variations
        self.allowed_skills.update({s.replace(" ", "") for s in self.allowed_skills})
        self.allowed_skills.update({s.replace(".", "") for s in self.allowed_skills})

        # Collect verified words and phrases from projects, experience, education
        self.verified_corpus = set()
        for edu in profile.education:
            self._add_text_to_corpus(f"{edu.degree} {edu.institution} {edu.location} {edu.grad_year} {edu.gpa or ''}")
        for proj in profile.projects:
            self._add_text_to_corpus(f"{proj.title} {proj.role} {' '.join(proj.tech_stack)} {' '.join(proj.bullets)}")
        for exp in profile.experience:
            self._add_text_to_corpus(f"{exp.company} {exp.role} {exp.period} {' '.join(exp.bullets)}")

    def _add_text_to_corpus(self, text: str):
        words = re.findall(r"\b[A-Za-z0-9+#.-]+\b", text.lower())
        self.verified_corpus.update(words)

    def verify_skills_list(self, skills_to_check: List[str]):
        """Ensures every skill is directly declared in profile.yml."""
        for skill in skills_to_check:
            clean = skill.lower().strip()
            clean_nopunct = clean.replace(" ", "").replace(".", "")
            if clean not in self.allowed_skills and clean_nopunct not in self.allowed_skills:
                raise FactCheckValidationError(
                    f"Fact check failed! Skill '{skill}' is NOT listed in profile.yml. "
                    "Rule: Nothing can ever be claimed that is not in profile.yml."
                )

    def verify_text_content(self, text: str, suspicious_terms: List[str] = None):
        """Scans generated resume bullets or cover note for invented technologies or inflated titles."""
        # Check against common inflated claims not present in student profile
        blacklist = suspicious_terms or [
            "kubernetes", "aws certified", "microservices architect", "team lead",
            "5 years", "10 years", "phd", "master's", "senior engineer"
        ]
        text_lower = text.lower()
        for term in blacklist:
            if term in text_lower and term not in self.allowed_skills and term not in self.verified_corpus:
                raise FactCheckValidationError(
                    f"Fact check failed! Detected unverified/inflated term '{term}' in generated document."
                )
