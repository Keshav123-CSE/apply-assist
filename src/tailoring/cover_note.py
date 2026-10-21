"""Generates concise, factual cover notes for job applications.
Guaranteed to only reference verified experiences from profile.yml.
"""

from typing import Optional
from src.core.profile import UserProfile
from src.core.fact_checker import FactChecker
from src.storage.models import JobPosting
from src.adapters.llm import BaseLLMAdapter, GeminiAdapter


COVER_NOTE_SYSTEM_PROMPT = """You are drafting a short, punchy, honest 2-paragraph cover note for a 2nd-year CSE undergraduate applicant.
RULES:
1. Under NO circumstances invent projects, frameworks, or past internships.
2. Only reference facts provided in the candidate's profile.
3. Keep it crisp: ~120 words maximum.
4. Express genuine curiosity and enthusiasm for learning and contributing.
5. End politely with availability and contact info.
"""


class CoverNoteGenerator:
    def __init__(self, profile: UserProfile, llm_adapter: Optional[BaseLLMAdapter] = None):
        self.profile = profile
        self.llm = llm_adapter or GeminiAdapter()
        self.fact_checker = FactChecker(profile)

    def generate(self, job: JobPosting) -> str:
        prompt = f"""
CANDIDATE:
Name: {self.profile.contact.full_name}
Degree: {self.profile.education[0].degree} ({self.profile.education[0].current_year}) at {self.profile.education[0].institution}
Key verified skills: {', '.join(self.profile.skills.all_skills_flat()[:10])}
Featured Project: {self.profile.projects[0].title} - {', '.join(self.profile.projects[0].tech_stack)}

JOB TARGET:
Company: {job.company}
Role: {job.title}
Key details: {job.description[:800]}

Draft a truthful, direct cover note.
"""
        note = self.llm.generate(prompt=prompt, system_instruction=COVER_NOTE_SYSTEM_PROMPT).strip()

        # Deterministic fact-check verification
        self.fact_checker.verify_text_content(note)
        return note
