"""Profile model and validation engine.
Single Source of Truth: Nothing is ever claimed that is not in this profile.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pypdf import PdfReader

from src.config import PROFILE_PATH, PROFILE_EXAMPLE_PATH, RESUME_DIR


class ProfileValidationError(Exception):
    """Raised when profile.yml fails schema integrity or required fields."""
    pass


@dataclass
class ContactInfo:
    full_name: str
    email: str
    phone: str
    location: str
    github: str
    linkedin: str
    portfolio: Optional[str] = None


@dataclass
class EducationItem:
    degree: str
    institution: str
    location: str
    current_year: str
    grad_year: int
    gpa: Optional[str] = None


@dataclass
class SkillsInfo:
    languages: List[str] = field(default_factory=list)
    frameworks_and_libraries: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    tools_and_platforms: List[str] = field(default_factory=list)
    core_competencies: List[str] = field(default_factory=list)

    def all_skills_flat(self) -> List[str]:
        """Returns a flat, deduplicated list of all skills/keywords."""
        items = (
            self.languages
            + self.frameworks_and_libraries
            + self.databases
            + self.tools_and_platforms
            + self.core_competencies
        )
        return list(dict.fromkeys(items))


@dataclass
class ProjectItem:
    title: str
    role: str
    tech_stack: List[str]
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    bullets: List[str] = field(default_factory=list)


@dataclass
class ExperienceItem:
    company: str
    role: str
    period: str
    location: str
    bullets: List[str] = field(default_factory=list)


@dataclass
class UserProfile:
    contact: ContactInfo
    education: List[EducationItem]
    skills: SkillsInfo
    projects: List[ProjectItem]
    experience: List[ExperienceItem]
    canned_answers: Dict[str, str] = field(default_factory=dict)

    def get_canned_answer(self, key: str) -> Optional[str]:
        return self.canned_answers.get(key)


def load_profile(path: Optional[Path] = None) -> UserProfile:
    """Loads and validates profile.yml. Falls back to example profile if specified."""
    target_path = path or PROFILE_PATH
    if not target_path.exists():
        if target_path == PROFILE_PATH and PROFILE_EXAMPLE_PATH.exists():
            target_path = PROFILE_EXAMPLE_PATH
        else:
            raise FileNotFoundError(f"Profile file not found at: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ProfileValidationError("Profile YAML must be a mapping/dictionary.")

    # Validate Contact
    contact_data = data.get("contact")
    if not contact_data or not isinstance(contact_data, dict):
        raise ProfileValidationError("Missing or invalid 'contact' section in profile.")
    
    for req in ("full_name", "email", "phone", "location", "github", "linkedin"):
        if not contact_data.get(req):
            raise ProfileValidationError(f"Missing required contact field: '{req}'")

    contact = ContactInfo(
        full_name=contact_data["full_name"],
        email=contact_data["email"],
        phone=contact_data["phone"],
        location=contact_data["location"],
        github=contact_data["github"],
        linkedin=contact_data["linkedin"],
        portfolio=contact_data.get("portfolio"),
    )

    # Validate Education
    edu_list = []
    for item in data.get("education", []):
        edu_list.append(EducationItem(
            degree=item.get("degree", ""),
            institution=item.get("institution", ""),
            location=item.get("location", ""),
            current_year=item.get("current_year", ""),
            grad_year=int(item.get("grad_year", 0)),
            gpa=item.get("gpa"),
        ))
    if not edu_list:
        raise ProfileValidationError("Profile must contain at least one education entry.")

    # Validate Skills
    skills_data = data.get("skills", {})
    skills = SkillsInfo(
        languages=skills_data.get("languages", []),
        frameworks_and_libraries=skills_data.get("frameworks_and_libraries", []),
        databases=skills_data.get("databases", []),
        tools_and_platforms=skills_data.get("tools_and_platforms", []),
        core_competencies=skills_data.get("core_competencies", []),
    )

    # Validate Projects
    proj_list = []
    for p in data.get("projects", []):
        proj_list.append(ProjectItem(
            title=p.get("title", ""),
            role=p.get("role", ""),
            tech_stack=p.get("tech_stack", []),
            repo_url=p.get("repo_url"),
            live_url=p.get("live_url"),
            bullets=p.get("bullets", []),
        ))

    # Validate Experience
    exp_list = []
    for e in data.get("experience", []):
        exp_list.append(ExperienceItem(
            company=e.get("company", ""),
            role=e.get("role", ""),
            period=e.get("period", ""),
            location=e.get("location", ""),
            bullets=e.get("bullets", []),
        ))

    canned = data.get("canned_answers", {})

    return UserProfile(
        contact=contact,
        education=edu_list,
        skills=skills,
        projects=proj_list,
        experience=exp_list,
        canned_answers=canned,
    )


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts raw text from a PDF resume."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {pdf_path}")
    reader = PdfReader(str(pdf_path))
    text_parts = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            text_parts.append(txt)
    return "\n".join(text_parts)


def bootstrap_profile_from_pdf(pdf_path: Optional[Path] = None, output_path: Optional[Path] = None) -> Path:
    """Reads resume/resume.pdf, extracts text, and generates a scaffolded profile.yml for user review."""
    source_pdf = pdf_path or (RESUME_DIR / "resume.pdf")
    dest_path = output_path or PROFILE_PATH

    if not source_pdf.exists():
        raise FileNotFoundError(
            f"Cannot bootstrap profile: '{source_pdf}' not found. Please place your resume at resume/resume.pdf"
        )

    text = extract_text_from_pdf(source_pdf)
    # Read the example template
    if not PROFILE_EXAMPLE_PATH.exists():
        raise FileNotFoundError(f"Example profile template not found at {PROFILE_EXAMPLE_PATH}")

    with open(PROFILE_EXAMPLE_PATH, "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)

    # Attach raw extracted text in a comment or field for user reference
    template["_extracted_resume_raw_preview"] = text[:500] + "... (truncated)"

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write("# Generated from your resume/resume.pdf. Review and update every field carefully!\n")
        f.write("# Single source of truth: No skill or experience unlisted here will ever be claimed.\n\n")
        yaml.safe_dump(template, f, sort_keys=False)

    return dest_path
