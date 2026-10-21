"""Greenhouse public job board API client."""

import html
import re
from typing import List
from src.discovery.base import BaseATSClient
from src.storage.models import JobPosting


class GreenhouseClient(BaseATSClient):
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    def fetch_jobs(self, company_name: str, board_token: str) -> List[JobPosting]:
        url = f"{self.BASE_URL}/{board_token}/jobs?content=true"
        try:
            resp = self._get(url)
            data = resp.json()
        except Exception as e:
            print(f"[Greenhouse] Failed to fetch {board_token}: {e}")
            return []

        jobs = []
        for item in data.get("jobs", []):
            job_id = f"gh_{board_token}_{item.get('id')}"
            raw_content = item.get("content", "")
            # Clean HTML tags for plain text description
            clean_desc = re.sub(r"<[^>]+>", " ", html.unescape(raw_content))
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            location = item.get("location", {}).get("name", "Unknown")
            posted_date = item.get("updated_at")

            jobs.append(JobPosting(
                id=job_id,
                company=company_name,
                ats_type="greenhouse",
                board_token=board_token,
                title=item.get("title", "").strip(),
                location=location.strip(),
                url=item.get("absolute_url", ""),
                posted_date=posted_date,
                description=clean_desc,
            ))
        return jobs
