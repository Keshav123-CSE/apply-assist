"""Ashby public job board API client."""

import html
import re
from typing import List
from src.discovery.base import BaseATSClient
from src.storage.models import JobPosting


class AshbyClient(BaseATSClient):
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"

    def fetch_jobs(self, company_name: str, board_token: str) -> List[JobPosting]:
        url = f"{self.BASE_URL}/{board_token}"
        try:
            resp = self._get(url)
            data = resp.json()
        except Exception as e:
            print(f"[Ashby] Failed to fetch {board_token}: {e}")
            return []

        jobs = []
        for item in data.get("jobs", []):
            job_id = f"ashby_{board_token}_{item.get('id')}"
            location = item.get("location", "Remote")
            if item.get("secondaryLocations"):
                location += ", " + ", ".join(loc.get("location", "") for loc in item.get("secondaryLocations"))

            raw_desc = item.get("descriptionHtml", "")
            clean_desc = re.sub(r"<[^>]+>", " ", html.unescape(raw_desc))
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            jobs.append(JobPosting(
                id=job_id,
                company=company_name,
                ats_type="ashby",
                board_token=board_token,
                title=item.get("title", "").strip(),
                location=location.strip(),
                url=item.get("jobUrl", f"https://jobs.ashbyhq.com/{board_token}/{item.get('id')}"),
                posted_date=item.get("publishedAt"),
                description=clean_desc,
            ))
        return jobs
