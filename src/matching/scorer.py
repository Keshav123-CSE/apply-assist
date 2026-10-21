"""Objective job-fit scoring engine (1 to 5) using LLM.
Strict rule: Never inflate scores. Honestly highlight gaps and missing requirements.
"""

import json
import re
from typing import Dict, Any, Optional
from src.core.profile import UserProfile
from src.storage.models import JobPosting
from src.adapters.llm import BaseLLMAdapter, GeminiAdapter


SCORING_SYSTEM_PROMPT = """You are an objective, honest technical recruiter evaluating an applicant's fit for a job posting.
The applicant is a 2nd-year B.Tech CSE student.

STRICT EVALUATION RULES:
1. Score strictly on a 1 to 5 integer scale:
   - 5: Exceptional fit (meets all core skills, seniority is an exact match for 2nd year / intern).
   - 4: Strong fit (matches majority of core technologies, minor gaps easily bridgeable).
   - 3: Moderate fit (knows fundamental language/concepts, but lacks specific framework or domain experience).
   - 2: Weak fit (significant mismatches in tech stack or unfeasible experience expectations).
   - 1: Poor / Unsuitable fit (completely different domain, unrealistic seniority requirement).
2. NEVER inflate scores. Be uncompromisingly candid.
3. If the role requires 3+ years experience or skills the candidate doesn't have, list them explicitly under `missing_requirements`.
4. Output MUST be valid JSON with the exact keys:
   {
     "score": int,
     "skills_overlap": [str],
     "missing_requirements": [str],
     "seniority_fit": str,
     "honest_reason": str
   }
"""


class JobScorer:
    def __init__(self, llm_adapter: Optional[BaseLLMAdapter] = None):
        self.llm = llm_adapter or GeminiAdapter()

    def evaluate_fit(self, profile: UserProfile, job: JobPosting) -> Dict[str, Any]:
        """Evaluates candidate profile against the job posting and returns honest score breakdown."""
        flat_skills = profile.skills.all_skills_flat()
        projects_summary = "\n".join(
            f"- {p.title}: {', '.join(p.tech_stack)} | Bullets: {' '.join(p.bullets[:2])}"
            for p in profile.projects
        )

        prompt = f"""
CANDIDATE PROFILE:
Education: {profile.education[0].degree} at {profile.education[0].institution} ({profile.education[0].current_year}, Grad: {profile.education[0].grad_year})
Verified Skills: {', '.join(flat_skills)}
Projects:
{projects_summary}

JOB POSTING:
Company: {job.company}
Role Title: {job.title}
Location: {job.location}
Description:
{job.description[:3000]}

Evaluate fit honestly and return strictly the JSON schema requested.
"""
        response_text = self.llm.generate(prompt=prompt, system_instruction=SCORING_SYSTEM_PROMPT)

        # Extract JSON from code blocks or raw response
        try:
            clean_json = response_text.strip()
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                clean_json = match.group(0)
            data = json.loads(clean_json)
            # Ensure score is clamped between 1 and 5
            data["score"] = max(1, min(5, int(data.get("score", 1))))
            return data
        except Exception as e:
            # Fallback if LLM returned non-JSON
            return {
                "score": 1,
                "skills_overlap": [],
                "missing_requirements": ["Parsing error or invalid LLM response"],
                "seniority_fit": "Unknown",
                "honest_reason": f"Failed to parse LLM evaluation: {e}",
            }
