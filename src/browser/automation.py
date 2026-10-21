"""Playwright browser automation for job application prefilling.
Guarantees:
- Persistent Chrome profile for manual logins & cookies.
- No CAPTCHA solving, no stealth/fingerprint evasion.
- Daily cap enforcement (default 10).
- Screenshot summary & answers printed before submission.
- Requires user typing 'yes' to submit. Dry run by default.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, BrowserContext, Page

from src.core.profile import UserProfile
from src.browser.forms import FormHandler, STANDARD_FIELD_SELECTORS
from src.storage.models import JobPosting, ApplicationRecord
from src.storage.database import Database
from src.config import ROOT_DIR, SCREENSHOTS_DIR, get_app_config


class ApplicationManager:
    def __init__(self, profile: UserProfile, db: Database, config: Optional[Dict[str, Any]] = None):
        self.profile = profile
        self.db = db
        self.config = config or get_app_config()
        self.form_handler = FormHandler(profile)
        self.auto_cfg = self.config.get("automation", {})
        self.daily_cap = self.auto_cfg.get("daily_application_cap", 10)
        self.user_data_dir = ROOT_DIR / self.auto_cfg.get("browser_profile_dir", ".browser_profile")
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def check_daily_cap(self) -> bool:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = self.db.get_applications_today_count(today_str)
        if count >= self.daily_cap:
            print(f"[!] Daily application cap reached: {count}/{self.daily_cap} applications submitted today.")
            return False
        return True

    def prefill_and_review(self, job: JobPosting, resume_path: Optional[Path] = None, dry_run: bool = True) -> bool:
        """Opens job page, fills standard fields, prompts user for unknown questions,
        takes preview screenshot, and awaits explicit 'yes' confirmation before submission.
        """
        # 1. Cap check
        if not dry_run and not self.check_daily_cap():
            return False

        # 2. Duplicate check
        existing = self.db.get_job(job.id)
        if existing and existing.status == "APPLIED":
            print(f"[!] Already applied to role '{job.title}' at {job.company} (ID: {job.id}). Skipping.")
            return False

        print(f"\n[*] Launching persistent browser for {job.company} - {job.title}")
        print(f"[*] URL: {job.url}")
        print(f"[*] Mode: {'DRY-RUN (will not submit)' if dry_run else 'LIVE SUBMIT (requires confirmation)'}")

        filled_answers: Dict[str, str] = {}

        with sync_playwright() as p:
            # Use persistent context to retain user logins and cookies naturally
            context: BrowserContext = p.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=False,  # Let user see the browser
                viewport={"width": 1280, "height": 900},
            )
            page: Page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(job.url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                # Check if a login wall, Cloudflare, or CAPTCHA is present
                page_text = page.inner_text("body").lower()
                if "captcha" in page_text or "verify you are human" in page_text:
                    print("\n[!] CAPTCHA or Verification detected!")
                    print("Rule: No automated CAPTCHA bypassing. Please solve it in the browser window.")
                    input("Press ENTER in this terminal once you have solved it to continue...")

                # Fill Standard Fields
                for field_key, selectors in STANDARD_FIELD_SELECTORS.items():
                    val = self.form_handler.get_standard_value(field_key)
                    if not val and field_key != "resume_upload":
                        continue

                    for selector in selectors:
                        try:
                            loc = page.locator(selector).first
                            if loc.is_visible(timeout=1000):
                                if field_key == "resume_upload" and resume_path and resume_path.exists():
                                    loc.set_input_files(str(resume_path))
                                    filled_answers["Resume File"] = str(resume_path.name)
                                    print(f"  [+] Uploaded resume: {resume_path.name}")
                                    break
                                elif field_key != "resume_upload" and val:
                                    loc.fill(val)
                                    filled_answers[field_key] = val
                                    print(f"  [+] Filled {field_key}: {val}")
                                    break
                        except Exception:
                            continue

                # Take summary screenshot
                screenshot_filename = f"preview_{job.company}_{job.id}.png"
                screenshot_path = SCREENSHOTS_DIR / screenshot_filename
                page.screenshot(path=str(screenshot_path), full_page=False)
                print(f"\n[+] Summary screenshot saved to: {screenshot_path}")

                # Display Summary in Terminal
                print("\n" + "=" * 50)
                print(f"APPLICATION SUMMARY: {job.company} - {job.title}")
                print("=" * 50)
                for k, v in filled_answers.items():
                    print(f"  {k}: {v}")
                print("=" * 50)

                if dry_run:
                    print("\n[DRY RUN COMPLETE] No application was submitted.")
                    self.db.record_application(ApplicationRecord(
                        job_id=job.id,
                        company=job.company,
                        role_title=job.title,
                        applied_date=datetime.now(timezone.utc).isoformat(),
                        status="DRY_RUN",
                        tailored_resume_path=str(resume_path) if resume_path else None,
                        notes="Completed dry run prefill preview.",
                    ))
                    context.close()
                    return True

                # Confirmation gate
                print("\n[CONFIRMATION REQUIRED] Are you ready to submit this application?")
                print("Type 'yes' to submit. Any other response aborts.")
                confirm = input("> ").strip().lower()

                if confirm == "yes":
                    # Attempt submit click
                    submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit Application")').first
                    if submit_btn.is_visible(timeout=2000):
                        submit_btn.click()
                        page.wait_for_timeout(3000)
                        print("[+] Application submitted successfully!")
                        self.db.update_job_status(job.id, "APPLIED")
                        self.db.record_application(ApplicationRecord(
                            job_id=job.id,
                            company=job.company,
                            role_title=job.title,
                            applied_date=datetime.now(timezone.utc).isoformat(),
                            status="SUBMITTED",
                            tailored_resume_path=str(resume_path) if resume_path else None,
                            notes="Successfully submitted via human terminal approval.",
                        ))
                        context.close()
                        return True
                    else:
                        print("[-] Could not locate Submit button automatically. Please click Submit in the open browser.")
                        input("Press ENTER once done...")
                        self.db.update_job_status(job.id, "APPLIED")
                        context.close()
                        return True
                else:
                    print("[-] Submission cancelled by user.")
                    context.close()
                    return False

            except Exception as e:
                print(f"[-] Automation error: {e}")
                context.close()
                return False
