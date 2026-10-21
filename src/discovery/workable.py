"""Workable public job widget API client."""

import html
import re
from typing import List
from src.discovery.base import BaseATSClient
from src.storage.models import JobPosting


class WorkableClient(BaseATSClient):
    BASE_URL = "https://apply.workable.com/api/v1/widget/accounts"

    def fetch_jobs(self, company_name: str, board_token: str) -> List[JobPosting]:
        url = f"{self.BASE_URL}/{board_token}"
        try:
            resp = self._get(url)
            data = resp.json()
        except Exception as e:
            print(f"[Workable] Failed to fetch {board_token}: {e}")
            return []

        jobs = []
        for item in data.get("jobs", []):
            shortcode = item.get("shortcode", item.get("id"))
            job_id = f"workable_{board_token}_{shortcode}"

            city = item.get("city") or ""
            country = item.get("country") or ""
            location = f"{city}, {country}".strip(", ")
            if item.get("telecommuting"):
                location += " (Remote)" if location else "Remote"

            clean_desc = item.get("description", "")
            clean_desc = re.sub(r"<[^>]+>", " ", html.unescape(clean_desc))
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            jobs.append(JobPosting(
                id=job_id,
                company=company_name,
                ats_type="workable",
                board_token=board_token,
                title=item.get("title", "").strip(),
                location=location or "Not specified",
                url=item.get("url", f"https://apply.workable.com/{board_token}/j/{shortcode}/"),
                posted_date=item.get("published_on"),
                description=clean_desc,
            ))
        return jobs
