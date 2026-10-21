# apply-assist

A personal, transparent, and safe job-application assistant tailored for undergraduate computer science students targeting **SDE, Full-Stack, and Gen AI internships in India (remote preferred)**.

---

## 🎯 Guiding Principles

1. **Single Source of Truth (`profile.yml`)**:
   - Nothing is ever claimed that is not in `profile.yml`.
   - Automated fact-checking runs before every output: if any skill, tool, or metric is not declared in your profile, the build **fails immediately**.
   - If a form asks a question not covered by `profile.yml`, the tool **stops and asks you in the terminal**. It never guesses.
2. **Public APIs Only (Zero ToS Violations)**:
   - Queries official, publicly exposed job board APIs: **Greenhouse**, **Lever**, **Ashby**, and **Workable**.
   - **No scraping** of LinkedIn, Indeed, or login-walled job boards. Respects `robots.txt` and rate limits all requests with an honest, identified `User-Agent`.
3. **Genuineness & Anti-Scam Protection**:
   - Flags training fees, laptop deposits, informal recruiter channels (WhatsApp, Telegram, `@gmail.com`), unresolvable host domains, and stale postings (> 30 days).
   - High risk is **never applied to**; Medium risk requires explicit review.
4. **Prefill with Human Approval**:
   - Persistent Chrome profile so you can log into your own accounts naturally.
   - Summarizes filled answers and displays a preview screenshot.
   - **Dry-run by default**. Lives submissions require explicit terminal confirmation (`yes`).
   - Daily cap of 10 applications (configurable) and duplicate prevention.
5. **Privacy First**:
   - `.gitignore` strictly protects your `resume/`, `profile.yml`, `.env`, database, and browser profiles.

---

## 🚀 Quickstart

### 1. Installation & Environment

Clone the repository and set up a Python 3.11+ virtual environment:

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

Copy the example environment file and add your Gemini API key:
```bash
cp .env.example .env
```
*(Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/)).*

---

### 2. Configure Your Profile

Place your current resume at `resume/resume.pdf` and run:

```bash
python -m src.cli bootstrap-profile
```

This extracts raw text from your PDF and creates `profile.yml`. Open `profile.yml` and verify every section:
- Contact details
- Education & GPA
- Languages, frameworks, databases, and tools
- Projects with tech stacks and quantifiable bullet points
- Canned answers (notice period, location preference, work authorization)

> **Remember:** Whatever is not in `profile.yml` will never exist to this tool.

---

### 3. Configure Monitored Companies

Copy `companies.example.yml` to `companies.yml`:
```bash
cp companies.example.yml companies.yml
```

To find any company's ATS board from their career link:
```bash
python -m src.cli detect-ats https://boards.greenhouse.io/postman
```

---

## 🛠️ CLI Commands & Workflow

### Phase-by-Phase Workflow

```bash
# 1. Discover jobs from all configured ATS boards
python -m src.cli discover

# 2. Filter & Match: Run hard filters and honest LLM scoring against profile.yml
python -m src.cli match

# 3. Review shortlisted roles (Score >= 3/5)
python -m src.cli review

# 4. Tailor resume & cover note for a specific job (runs strict fact-check)
python -m src.cli tailor --job-id gh_postman_12345

# 5. Prefill application in browser (dry-run preview with screenshot)
python -m src.cli apply --job-id gh_postman_12345

# 6. Submit live application (requires explicit 'yes' confirmation)
python -m src.cli apply --job-id gh_postman_12345 --live

# 7. Export markdown summary tracker
python -m src.cli tracker
```

---

## 🧪 Testing

The repository includes a comprehensive 21-test suite verifying all safety guarantees, hard filters, scam checkers, and fact-checking validations:

```bash
pytest
```

---

## 🛡️ Safety & Ethical Limits

- **No CAPTCHA Solving**: The tool does not use fingerprint evasion or CAPTCHA bypassers. If Cloudflare or a CAPTCHA appears, the browser pauses and invites you to complete it manually.
- **Never Guesses Demographic / Salary Data**: Form fields regarding gender, ethnicity, disability, or visa status will only ever be filled if explicitly provided in `profile.yml` or typed by you in terminal.
- **Strict Fact Check**: Injects no unearned keywords or hallucinated experience.
