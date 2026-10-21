"""Helper script to detect the ATS provider and board token from a careers page URL."""

import re
import requests
from typing import Optional, Tuple
from urllib.parse import urlparse


ATS_PATTERNS = [
    # Greenhouse: boards.greenhouse.io/{board_token} or greenhouse.io/embed/job_board?for={board_token}
    (r"boards\.greenhouse\.io/([^/?#]+)", "greenhouse"),
    (r"greenhouse\.io/embed/job_board\?for=([^&#]+)", "greenhouse"),
    (r"boards-api\.greenhouse\.io/v1/boards/([^/?#]+)", "greenhouse"),

    # Lever: jobs.lever.co/{board_token}
    (r"jobs\.lever\.co/([^/?#]+)", "lever"),

    # Ashby: jobs.ashbyhq.com/{board_token}
    (r"jobs\.ashbyhq\.com/([^/?#]+)", "ashby"),

    # Workable: apply.workable.com/([^/?#]+)
    (r"apply\.workable\.com/([^/?#]+)", "workable"),
]


def detect_ats_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Analyzes a URL or follows redirects to identify (ats_name, board_token)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    # 1. Direct regex check on the provided URL
    for pattern, ats in ATS_PATTERNS:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return ats, match.group(1).lower()

    # 2. Fetch page and inspect redirected URL or embedded links
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        final_url = resp.url
        for pattern, ats in ATS_PATTERNS:
            match = re.search(pattern, final_url, re.IGNORECASE)
            if match:
                return ats, match.group(1).lower()

        # 3. Search HTML body for ATS links / iframes
        body = resp.text
        for pattern, ats in ATS_PATTERNS:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return ats, match.group(1).lower()

    except Exception as e:
        print(f"Error inspecting careers URL: {e}")

    return None, None
