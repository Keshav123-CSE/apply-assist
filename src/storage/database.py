"""SQLite Database manager for job postings and applications."""

import sqlite3
from pathlib import Path
from typing import List, Optional
from src.config import DB_PATH, DATA_DIR
from src.storage.models import JobPosting, ApplicationRecord


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        """Creates tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_postings (
                    id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    ats_type TEXT NOT NULL,
                    board_token TEXT NOT NULL,
                    title TEXT NOT NULL,
                    location TEXT NOT NULL,
                    url TEXT NOT NULL,
                    posted_date TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    fit_score INTEGER,
                    fit_reason TEXT,
                    risk_level TEXT,
                    risk_reasons TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    job_id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    role_title TEXT NOT NULL,
                    applied_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tailored_resume_path TEXT,
                    notes TEXT,
                    FOREIGN KEY(job_id) REFERENCES job_postings(id)
                )
            """)
            conn.commit()

    def upsert_job(self, job: JobPosting) -> bool:
        """Inserts or updates a job posting. Returns True if inserted, False if updated."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM job_postings WHERE id = ?", (job.id,))
            exists = cursor.fetchone() is not None

            cursor.execute("""
                INSERT INTO job_postings (
                    id, company, ats_type, board_token, title, location, url,
                    posted_date, description, created_at, status, fit_score,
                    fit_reason, risk_level, risk_reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    location=excluded.location,
                    url=excluded.url,
                    posted_date=excluded.posted_date,
                    description=excluded.description
            """, (
                job.id, job.company, job.ats_type, job.board_token, job.title,
                job.location, job.url, job.posted_date, job.description,
                job.created_at, job.status, job.fit_score, job.fit_reason,
                job.risk_level, job.risk_reasons
            ))
            conn.commit()
            return not exists

    def get_job(self, job_id: str) -> Optional[JobPosting]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM job_postings WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return JobPosting(**dict(row))

    def get_jobs_by_status(self, status: str) -> List[JobPosting]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM job_postings WHERE status = ? ORDER BY created_at DESC", (status,))
            return [JobPosting(**dict(row)) for row in cursor.fetchall()]

    def get_all_jobs(self) -> List[JobPosting]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM job_postings ORDER BY created_at DESC")
            return [JobPosting(**dict(row)) for row in cursor.fetchall()]

    def update_job_status(self, job_id: str, status: str, **kwargs):
        """Updates status and optional evaluation fields for a job."""
        fields = ["status = ?"]
        values = [status]
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            values.append(v)
        values.append(job_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE job_postings SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

    def record_application(self, app: ApplicationRecord):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO applications (job_id, company, role_title, applied_date, status, tailored_resume_path, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    applied_date=excluded.applied_date,
                    status=excluded.status,
                    tailored_resume_path=excluded.tailored_resume_path,
                    notes=excluded.notes
            """, (app.job_id, app.company, app.role_title, app.applied_date, app.status, app.tailored_resume_path, app.notes))
            conn.commit()

    def get_applications_today_count(self, date_str: str) -> int:
        """Returns the count of applications submitted today for daily cap enforcement."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM applications WHERE applied_date LIKE ? AND status = 'SUBMITTED'", (f"{date_str}%",))
            return cursor.fetchone()[0]
