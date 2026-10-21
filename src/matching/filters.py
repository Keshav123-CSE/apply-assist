"""Deterministic rule filtering based on config.yml."""

from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from src.storage.models import JobPosting


def passes_hard_filters(job: JobPosting, config: Dict[str, Any]) -> Tuple[bool, str]:
    """Applies strict hard filters:
    - Excludes senior/lead/manager levels
    - Requires intern/entry-level or early career indicators
    - Requires India or Remote location
    - Requires posting date within max_posting_age_days (default: 30)
    - Matches relevant software engineering / AI title keywords
    Returns (passes: bool, reason: str).
    """
    filter_cfg = config.get("filters", {})
    title_lower = job.title.lower()
    location_lower = job.location.lower()
    desc_lower = (job.description or "").lower()

    # 1. Seniority Check: Reject senior/lead/manager titles
    disallowed_levels = filter_cfg.get("disallowed_levels", [
        "senior", "sr.", "lead", "principal", "staff", "director", "manager", "vp", "head of"
    ])
    for dis in disallowed_levels:
        # Check title only to avoid rejecting job descriptions that say "reports to senior manager"
        if dis in title_lower:
            return False, f"Disallowed seniority in title: '{dis}'"

    # 2. Level Check: Must be intern, trainee, entry, fresher, sde-1, etc.
    allowed_levels = filter_cfg.get("allowed_levels", [
        "intern", "internship", "trainee", "entry", "fresher", "junior", "graduate", "sde-1", "sde 1", "software engineer 1"
    ])
    level_matched = any(lvl in title_lower for lvl in allowed_levels)
    # If not in title, check if description indicates university grad / student / 2026 / 2027
    if not level_matched:
        if any(term in desc_lower for term in ["internship", "intern", "2026", "2027", "b.tech", "undergraduate"]):
            level_matched = True

    if not level_matched:
        return False, "Not identified as internship, trainee, or entry-level"

    # 3. Location Check: India or Remote
    allowed_locations = filter_cfg.get("allowed_locations", [
        "remote", "india", "bengaluru", "bangalore", "hyderabad", "pune", "gurgaon", "gurugram", "noida", "mumbai", "delhi", "chennai"
    ])
    location_matched = any(loc in location_lower for loc in allowed_locations)
    if not location_matched:
        return False, f"Location '{job.location}' not matching allowed India/Remote locations"

    # 4. Posting Age Check
    max_days = filter_cfg.get("max_posting_age_days", 30)
    if job.posted_date:
        try:
            # Parse ISO or standard timestamps
            clean_date = job.posted_date.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_date)
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_days = (now - dt).days
            if age_days > max_days:
                return False, f"Posting is {age_days} days old (> {max_days} days limit)"
        except Exception:
            # If date format is non-standard, we don't reject purely on date parsing failure
            pass

    # 5. Role Keyword Check
    target_keywords = filter_cfg.get("target_role_keywords", [
        "software", "sde", "full stack", "fullstack", "backend", "frontend", "gen ai", "generative ai", "ai engineer", "python developer"
    ])
    role_matched = any(kw in title_lower for kw in target_keywords)
    if not role_matched:
        return False, "Title does not match target SDE / Full-stack / AI keywords"

    return True, "Passed all hard filters"
