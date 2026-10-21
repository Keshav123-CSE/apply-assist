"""Base ATS client with honest User-Agent and polite rate limiting."""

import time
import requests
from abc import ABC, abstractmethod
from typing import List, Optional
from src.storage.models import JobPosting


class BaseATSClient(ABC):
    # Polite User-Agent identifying the personal assistant
    USER_AGENT = "ApplyAssistBot/1.0 (+https://github.com/aarav-sharma/apply-assist; Educational Job Assistant)"
    RATE_LIMIT_DELAY = 1.0  # Respectful 1-second pause between API calls

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        })

    def _get(self, url: str, params: Optional[dict] = None) -> requests.Response:
        """Rate-limited polite GET request."""
        time.sleep(self.RATE_LIMIT_DELAY)
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp

    @abstractmethod
    def fetch_jobs(self, company_name: str, board_token: str) -> List[JobPosting]:
        """Fetches public jobs from the target ATS board."""
        pass
