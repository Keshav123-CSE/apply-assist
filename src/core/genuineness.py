"""Genuineness and Scam Risk Analyzer.
Flags suspicious patterns (domain, fees, WhatsApp/Telegram/Gmail recruiters, expired posts).
Risk levels:
- LOW: Legitimate, safe to proceed.
- MEDIUM: Suspicious flags present, requires explicit manual review.
- HIGH: Scam indicators detected, BLOCKED from auto-applying.
"""

import re
import socket
from datetime import datetime, timezone
from typing import List, Tuple
from urllib.parse import urlparse
from src.storage.models import JobPosting


KNOWN_ATS_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
]

SUSPICIOUS_FEE_KEYWORDS = [
    "training fee",
    "registration fee",
    "security deposit",
    "caution money",
    "processing fee",
    "laptop deposit",
    "pay first",
    "charges applicable",
    "refundable fee",
    "stipend after paying",
]

SUSPICIOUS_COMMUNICATION_CHANNELS = [
    r"\bwhatsapp\b",
    r"\btelegram\b",
    r"@gmail\.com\b",
    r"@yahoo\.com\b",
    r"@outlook\.com\b",
    r"@hotmail\.com\b",
]


class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GenuinenessChecker:
    @staticmethod
    def domain_resolves(domain: str) -> bool:
        """Verifies if domain has a valid DNS record."""
        try:
            socket.gethostbyname(domain)
            return True
        except Exception:
            return False

    def evaluate(self, job: JobPosting) -> Tuple[str, List[str]]:
        """Evaluates a job posting for legitimacy and flags risks without silent rejection.
        Returns (risk_level, list_of_reasons).
        """
        reasons: List[str] = []
        is_high_risk = False
        is_medium_risk = False

        desc_lower = (job.description or "").lower()
        url_lower = (job.url or "").lower()

        # 1. Ask for Money / Training Fee (HIGH RISK - Definite Scam)
        for fee_kw in SUSPICIOUS_FEE_KEYWORDS:
            if fee_kw in desc_lower:
                reasons.append(f"SCAM FLAG: Mentions fee/deposit ('{fee_kw}')")
                is_high_risk = True

        # 2. Suspicious Contact Channels (WhatsApp/Telegram/Free webmail)
        for pattern in SUSPICIOUS_COMMUNICATION_CHANNELS:
            match = re.search(pattern, desc_lower)
            if match:
                channel = match.group(0)
                reasons.append(f"Suspicious informal contact channel detected: '{channel}'")
                is_high_risk = True

        # 3. Domain Check (Is it hosted on official ATS or known resolvable domain?)
        try:
            parsed = urlparse(job.url)
            domain = parsed.netloc.lower()
            if ":" in domain:
                domain = domain.split(":")[0]

            is_known_ats = any(domain.endswith(ats_dom) for ats_dom in KNOWN_ATS_DOMAINS)
            if not is_known_ats:
                # Check if company domain resolves
                if domain and not self.domain_resolves(domain):
                    reasons.append(f"Unresolvable or invalid host domain: '{domain}'")
                    is_high_risk = True
                else:
                    reasons.append(f"Job is hosted outside known major ATS portals: '{domain}'")
                    is_medium_risk = True
        except Exception as e:
            reasons.append(f"Malformed job URL: {e}")
            is_medium_risk = True

        # 4. Posting Age (> 30 days)
        if job.posted_date:
            try:
                clean_date = job.posted_date.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_date)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - dt).days
                if age_days > 30:
                    reasons.append(f"Posting is {age_days} days old (> 30 days)")
                    is_medium_risk = True
            except Exception:
                pass

        # 5. Vague description check
        if len(job.description.strip()) < 120:
            reasons.append("Very short or vague job description (< 120 characters)")
            is_medium_risk = True

        # Compute final risk level
        if is_high_risk:
            return RiskLevel.HIGH, reasons
        elif is_medium_risk:
            return RiskLevel.MEDIUM, reasons
        else:
            return RiskLevel.LOW, ["Legitimate verified posting on trusted ATS domain"]
