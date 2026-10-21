"""Lever public postings API client."""

import html
import re
from typing import List
from datetime import datetime
from src.discovery.base import BaseATSClient
from src.storage.models import JobPosting


class LeverClient(BaseATSClient):
    BASE_URL = "https://api.lever.co/v0/postings"

    def fetch_jobs(self, company_name: str, board_token: str) -> List[JobPosting]:
        url = f"{self.BASE_URL}/{board_token}?mode=json"
        try:
            resp = self._get(url)
            data = resp.json()
        except Exception as e:
            print(f"[Lever] Failed to fetch {board_token}: {e}")
            return []

        jobs = []
        for item in data:
            job_id = f"lever_{board_token}_{item.get('id')}"
            categories = item.get("categories", {})
            location = categories.get("location") or "Remote"

            # Parse timestamp in milliseconds
            created_at_ms = item.get("createdAt")
            posted_date = None
            if created_at_ms:
                try:
                    posted_date = datetime.utcfromtimestamp(created_at_ms / 1000.0).isoformat()
                except Exception:
                    pass

            desc_parts = [item.get("descriptionPlain", "")]
            for list_item in item.get("lists", []):
                desc_parts.append(list_item.get("text", "") + ":")
                desc_parts.append(list_item.get("content", ""))
            
            clean_desc = "\n".join(filter(None, desc_parts))
            clean_desc = re.sub(r"<[^>]+>", " ", html.unescape(clean_desc))
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            jobs.append(JobPosting(
                id=job_id,
                company=company_name,
                ats_type="lever",
                board_token=board_token,
                title=item.get("text", "").strip(),
                location=location.strip(),
                url=item.get("hostedUrl", ""),
                posted_date=posted_date,
                description=clean_desc,
            ))
        return jobs
