"""Unified Command Line Interface for Apply-Assist."""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.config import get_app_config, get_companies_file, PROFILE_PATH, RESUME_DIR
from src.core.profile import load_profile, bootstrap_profile_from_pdf
from src.core.genuineness import GenuinenessChecker, RiskLevel
from src.storage.database import Database
from src.storage.tracker import ApplicationTracker
from src.discovery.engine import DiscoveryEngine
from src.discovery.detector import detect_ats_from_url
from src.matching.filters import passes_hard_filters
from src.matching.scorer import JobScorer
from src.tailoring.resume_generator import ResumeGenerator
from src.tailoring.cover_note import CoverNoteGenerator
from src.browser.automation import ApplicationManager

console = Console()


def cmd_bootstrap_profile(args):
    pdf = Path(args.pdf) if args.pdf else (RESUME_DIR / "resume.pdf")
    try:
        dest = bootstrap_profile_from_pdf(pdf)
        console.print(f"[bold green][OK] Profile successfully bootstrapped to:[/bold green] {dest}")
        console.print("[yellow]Please open profile.yml now to review, correct, and add any missing projects/skills![/yellow]")
    except Exception as e:
        console.print(f"[bold red][FAIL] Error bootstrapping profile:[/bold red] {e}")


def cmd_detect_ats(args):
    url = args.url
    console.print(f"[*] Inspecting careers URL: [cyan]{url}[/cyan]")
    ats, token = detect_ats_from_url(url)
    if ats and token:
        console.print(f"[bold green][OK] Detected ATS:[/bold green] {ats.upper()}")
        console.print(f"[bold green][OK] Board Token:[/bold green] {token}")
        console.print("\nAdd this entry to your [bold]companies.yml[/bold]:")
        console.print(f"  - name: \"Company Name\"\n    ats: \"{ats}\"\n    board_token: \"{token}\"")
    else:
        console.print("[yellow][-] Could not automatically identify supported ATS from URL.[/yellow]")


def cmd_discover(args):
    db = Database()
    engine = DiscoveryEngine(db)
    jobs = engine.run_discovery()
    console.print(f"[bold green][OK] Discovery complete. Total jobs in DB: {len(db.get_all_jobs())}[/bold green]")
    ApplicationTracker(db).export_markdown()


def cmd_match(args):
    db = Database()
    config = get_app_config()
    profile = load_profile()
    scorer = JobScorer()
    genuineness = GenuinenessChecker()

    jobs = db.get_jobs_by_status("DISCOVERED")
    console.print(f"[*] Filtering & Matching {len(jobs)} unreviewed jobs against profile.yml...")

    passed_count = 0
    for job in jobs:
        # Step 1: Hard filters
        passed, filter_reason = passes_hard_filters(job, config)
        if not passed:
            db.update_job_status(job.id, "FILTERED_OUT", fit_reason=filter_reason)
            continue

        # Step 2: Genuineness Check
        risk_level, risk_reasons = genuineness.evaluate(job)
        risk_str = "; ".join(risk_reasons)

        if risk_level == RiskLevel.HIGH:
            db.update_job_status(job.id, "FILTERED_OUT", risk_level=risk_level, risk_reasons=risk_str, fit_reason="High risk scam flag")
            continue

        # Step 3: LLM Fit Scoring
        try:
            eval_data = scorer.evaluate_fit(profile, job)
            score = eval_data.get("score", 1)
            reason = eval_data.get("honest_reason", "")
            gaps = ", ".join(eval_data.get("missing_requirements", []))
            full_reason = f"{reason} | Gaps: {gaps}" if gaps else reason

            status = "MATCHED" if score >= 3 else "LOW_FIT"
            db.update_job_status(job.id, status, fit_score=score, fit_reason=full_reason, risk_level=risk_level, risk_reasons=risk_str)
            if score >= 3:
                passed_count += 1
                console.print(f"  [green]Score [{score}/5][/green] [bold]{job.company}[/bold] - {job.title} ([dim]{risk_level} risk[/dim])")
        except Exception as e:
            console.print(f"  [red][-] Failed to score {job.id}: {e}[/red]")

    console.print(f"[bold green][OK] Matching finished. {passed_count} high-fit jobs matched.[/bold green]")
    ApplicationTracker(db).export_markdown()


def cmd_review(args):
    db = Database()
    jobs = [j for j in db.get_all_jobs() if (j.fit_score or 0) >= 3]

    table = Table(title="Shortlisted Jobs for Review (Score >= 3)")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Company", style="bold")
    table.add_column("Title")
    table.add_column("Location")
    table.add_column("Score", justify="center")
    table.add_column("Risk", justify="center")
    table.add_column("Status", justify="center")

    for j in jobs:
        score_color = "green" if (j.fit_score or 0) >= 4 else "yellow"
        risk_color = "green" if j.risk_level == "LOW" else "yellow" if j.risk_level == "MEDIUM" else "red"
        table.add_row(
            j.id,
            j.company,
            j.title,
            j.location,
            f"[{score_color}]{j.fit_score}/5[/{score_color}]",
            f"[{risk_color}]{j.risk_level}[/{risk_color}]",
            j.status,
        )

    console.print(table)


def cmd_tailor(args):
    db = Database()
    job = db.get_job(args.job_id)
    if not job:
        console.print(f"[red][FAIL] Job '{args.job_id}' not found in database.[/red]")
        sys.exit(1)

    profile = load_profile()
    resume_gen = ResumeGenerator(profile)
    cover_gen = CoverNoteGenerator(profile)

    console.print(f"[*] Tailoring application materials for: [bold]{job.company}[/bold] - {job.title}")

    try:
        resume_file = resume_gen.export_pdf_or_html(job)
        console.print(f"[bold green][OK] Generated tailored resume:[/bold green] {resume_file}")

        cover_note = cover_gen.generate(job)
        console.print("\n[bold]Generated Cover Note (Fact-Checked):[/bold]")
        console.print("-" * 50)
        console.print(cover_note)
        console.print("-" * 50)

        db.update_job_status(job.id, "TAILORED")
    except Exception as e:
        console.print(f"[bold red][FAIL] Fact check or tailoring error:[/bold red] {e}")


def cmd_apply(args):
    db = Database()
    job = db.get_job(args.job_id)
    if not job:
        console.print(f"[red][FAIL] Job '{args.job_id}' not found in database.[/red]")
        sys.exit(1)

    profile = load_profile()
    resume_gen = ResumeGenerator(profile)
    resume_path = resume_gen.export_pdf_or_html(job)

    dry_run = not args.live
    manager = ApplicationManager(profile, db)
    manager.prefill_and_review(job, resume_path=resume_path, dry_run=dry_run)
    ApplicationTracker(db).export_markdown()


def cmd_tracker(args):
    db = Database()
    tracker = ApplicationTracker(db)
    md_file = tracker.export_markdown()
    console.print(f"[bold green][OK] Exported applications tracker to:[/bold green] {md_file}")
    cmd_review(args)


def main():
    parser = argparse.ArgumentParser(
        prog="apply-assist",
        description="A transparent, safe, personal job application assistant for SDE & AI internships."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # bootstrap-profile
    p_boot = subparsers.add_parser("bootstrap-profile", help="Generate profile.yml from resume/resume.pdf")
    p_boot.add_argument("--pdf", help="Path to resume PDF (default: resume/resume.pdf)")

    # detect-ats
    p_det = subparsers.add_parser("detect-ats", help="Find ATS provider & board token from a careers URL")
    p_det.add_argument("url", help="Careers page URL")

    # discover
    subparsers.add_parser("discover", help="Fetch public jobs from configured ATS boards")

    # match
    subparsers.add_parser("match", help="Filter and score discovered jobs against profile.yml")

    # review
    subparsers.add_parser("review", help="Display shortlisted jobs in a formatted terminal table")

    # tailor
    p_tailor = subparsers.add_parser("tailor", help="Generate tailored resume & cover note with fact-check")
    p_tailor.add_argument("--job-id", required=True, help="Job ID to tailor for")

    # apply
    p_apply = subparsers.add_parser("apply", help="Prefill application using Playwright (dry-run by default)")
    p_apply.add_argument("--job-id", required=True, help="Job ID to apply to")
    p_apply.add_argument("--live", action="store_true", help="Submit live after explicit user terminal confirmation")

    # tracker
    subparsers.add_parser("tracker", help="Export status to applications.md and print summary")

    args = parser.parse_args()

    commands = {
        "bootstrap-profile": cmd_bootstrap_profile,
        "detect-ats": cmd_detect_ats,
        "discover": cmd_discover,
        "match": cmd_match,
        "review": cmd_review,
        "tailor": cmd_tailor,
        "apply": cmd_apply,
        "tracker": cmd_tracker,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
