"""Generates tailored resume HTML and PDF without inventing anything.
Reorders and emphasizes what is ALREADY in profile.yml.
"""

from pathlib import Path
from typing import Optional
from src.core.profile import UserProfile
from src.core.fact_checker import FactChecker
from src.storage.models import JobPosting
from src.config import DATA_DIR


RESUME_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #222;
    line-height: 1.4;
    font-size: 11pt;
    margin: 30px;
  }}
  h1 {{ font-size: 20pt; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .contact-bar {{ font-size: 9.5pt; color: #555; margin-bottom: 16px; border-bottom: 1px solid #ccc; padding-bottom: 8px; }}
  .contact-bar a {{ color: #0066cc; text-decoration: none; }}
  h2 {{ font-size: 13pt; border-bottom: 1px solid #222; padding-bottom: 2px; margin-top: 14px; margin-bottom: 6px; text-transform: uppercase; }}
  .item-header {{ display: flex; justify-content: space-between; font-weight: bold; font-size: 11pt; }}
  .item-sub {{ display: flex; justify-content: space-between; font-style: italic; font-size: 10pt; color: #444; margin-bottom: 4px; }}
  ul {{ margin-top: 4px; margin-bottom: 8px; padding-left: 20px; }}
  li {{ margin-bottom: 3px; }}
  .skills-row {{ margin-bottom: 4px; }}
  .skills-cat {{ font-weight: bold; }}
</style>
</head>
<body>

<h1>{full_name}</h1>
<div class="contact-bar">
  {email} &bull; {phone} &bull; {location} &bull;
  <a href="{github}">GitHub</a> &bull;
  <a href="{linkedin}">LinkedIn</a>
  {portfolio_link}
</div>

<h2>Education</h2>
{education_html}

<h2>Technical Skills</h2>
<div class="skills-row"><span class="skills-cat">Languages:</span> {languages}</div>
<div class="skills-row"><span class="skills-cat">Frameworks & Tools:</span> {frameworks}</div>
<div class="skills-row"><span class="skills-cat">Databases & Core:</span> {databases}</div>

<h2>Technical Projects</h2>
{projects_html}

<h2>Experience</h2>
{experience_html}

</body>
</html>
"""


class ResumeGenerator:
    def __init__(self, profile: UserProfile):
        self.profile = profile
        self.fact_checker = FactChecker(profile)

    def generate_html(self, job: JobPosting) -> str:
        """Tailors order of projects and emphasizes overlapping skills without hallucination."""
        contact = self.profile.contact
        portfolio_link = f' &bull; <a href="{contact.portfolio}">Portfolio</a>' if contact.portfolio else ""

        # Reorder projects so that projects sharing keywords with the job description appear first
        desc_lower = (job.description or "").lower()
        scored_projects = []
        for p in self.profile.projects:
            # Fact check: ensure project tech stack is verified in profile
            self.fact_checker.verify_skills_list(p.tech_stack)
            # Count relevance overlap
            relevance = sum(1 for tech in p.tech_stack if tech.lower() in desc_lower)
            scored_projects.append((relevance, p))
        scored_projects.sort(key=lambda x: x[0], reverse=True)

        projects_html_parts = []
        for _, p in scored_projects:
            links = []
            if p.repo_url:
                links.append(f'<a href="{p.repo_url}">Code</a>')
            if p.live_url:
                links.append(f'<a href="{p.live_url}">Live</a>')
            links_str = f" ({' | '.join(links)})" if links else ""

            bullets_html = "".join(f"<li>{b}</li>" for b in p.bullets)
            projects_html_parts.append(f"""
            <div class="item-header">
              <span>{p.title}{links_str}</span>
              <span>{p.role}</span>
            </div>
            <div class="item-sub"><span>Tech Stack: {', '.join(p.tech_stack)}</span></div>
            <ul>{bullets_html}</ul>
            """)

        education_html_parts = []
        for edu in self.profile.education:
            gpa_str = f" &bull; GPA: {edu.gpa}" if edu.gpa else ""
            education_html_parts.append(f"""
            <div class="item-header">
              <span>{edu.institution}</span>
              <span>Graduation: {edu.grad_year}</span>
            </div>
            <div class="item-sub">
              <span>{edu.degree} ({edu.current_year}){gpa_str}</span>
              <span>{edu.location}</span>
            </div>
            """)

        experience_html_parts = []
        for exp in self.profile.experience:
            bullets_html = "".join(f"<li>{b}</li>" for b in exp.bullets)
            experience_html_parts.append(f"""
            <div class="item-header">
              <span>{exp.company}</span>
              <span>{exp.period}</span>
            </div>
            <div class="item-sub">
              <span>{exp.role}</span>
              <span>{exp.location}</span>
            </div>
            <ul>{bullets_html}</ul>
            """)

        # Skills verification
        skills = self.profile.skills
        self.fact_checker.verify_skills_list(skills.languages)
        self.fact_checker.verify_skills_list(skills.frameworks_and_libraries)
        self.fact_checker.verify_skills_list(skills.databases)

        html_content = RESUME_HTML_TEMPLATE.format(
            full_name=contact.full_name,
            email=contact.email,
            phone=contact.phone,
            location=contact.location,
            github=contact.github,
            linkedin=contact.linkedin,
            portfolio_link=portfolio_link,
            education_html="\n".join(education_html_parts),
            languages=", ".join(skills.languages),
            frameworks=", ".join(skills.frameworks_and_libraries + skills.tools_and_platforms),
            databases=", ".join(skills.databases + skills.core_competencies),
            projects_html="\n".join(projects_html_parts),
            experience_html="\n".join(experience_html_parts),
        )

        # Run text fact-check scan over complete generated document
        self.fact_checker.verify_text_content(html_content)

        return html_content

    def export_pdf_or_html(self, job: JobPosting, output_dir: Optional[Path] = None) -> Path:
        """Generates tailored resume file. Returns path to output HTML/PDF."""
        out_dir = output_dir or (DATA_DIR / "tailored_resumes")
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_company = "".join(c for c in job.company if c.isalnum() or c in ('_', '-'))
        filename = f"Resume_{safe_company}_{job.id}.html"
        out_path = out_dir / filename

        html_content = self.generate_html(job)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return out_path
