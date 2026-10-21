"""Orchestrates job discovery across configured companies."""

from typing import List
from src.config import get_companies_file, load_yaml
from src.discovery.greenhouse import GreenhouseClient
from src.discovery.lever import LeverClient
from src.discovery.ashby import AshbyClient
from src.discovery.workable import WorkableClient
from src.storage.database import Database
from src.storage.models import JobPosting


class DiscoveryEngine:
    def __init__(self, db: Database):
        self.db = db
        self.clients = {
            "greenhouse": GreenhouseClient(),
            "lever": LeverClient(),
            "ashby": AshbyClient(),
            "workable": WorkableClient(),
        }

    def run_discovery(self) -> List[JobPosting]:
        companies_file = get_companies_file()
        config_data = load_yaml(companies_file)
        company_list = config_data.get("companies", [])

        discovered_jobs: List[JobPosting] = []

        print(f"[*] Starting job discovery for {len(company_list)} companies...")

        for comp in company_list:
            name = comp.get("name")
            ats = (comp.get("ats") or "").lower()
            token = comp.get("board_token")

            if not name or not ats or not token:
                continue

            client = self.clients.get(ats)
            if not client:
                print(f"[-] Unsupported ATS '{ats}' for {name}")
                continue

            print(f"[*] Fetching {name} ({ats} / {token})...")
            try:
                jobs = client.fetch_jobs(company_name=name, board_token=token)
                new_count = 0
                for job in jobs:
                    is_new = self.db.upsert_job(job)
                    if is_new:
                        new_count += 1
                    discovered_jobs.append(job)
                print(f"[+] Found {len(jobs)} total jobs for {name} ({new_count} newly inserted).")
            except Exception as e:
                print(f"[-] Error querying {name}: {e}")

        return discovered_jobs
