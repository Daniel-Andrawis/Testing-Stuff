# CyberRank Web App — Design Spec

**Date:** 2026-04-15
**Status:** Approved
**Summary:** A web application that lets cybersecurity professionals see how their resume stacks up against live job listings. Builds on the existing `cyber_job_hunter` CLI tool, adding user accounts, persistent profiles, a dashboard portal, and a public "try it" experience.

---

## 1. Goals

- Let Daniel (and any registered user) maintain a profile and see how they match against cybersecurity jobs in a personal portal/dashboard
- Provide a public "try it" page where anyone can check their match score without signing up
- Scrape jobs from existing sources (USAJobs, Indeed, RemoteOK, Jobicy, TheMuse) on a background schedule
- Support pluggable company-specific scrapers (SpaceX, CrowdStrike, etc.) added over time
- Allow on-demand scraping for specific companies ("Check SpaceX now")
- Reuse the existing Python matcher engine and scraper code

## 2. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | **FastAPI** | Python, reuses existing code, async support |
| Templates | **Jinja2 + HTMX** | Server-rendered, dynamic updates without JS framework |
| Database | **SQLite + SQLAlchemy** | Single file, zero config, JSON column support |
| Auth | **FastAPI-Users** | Email/password + magic link, battle-tested |
| Background jobs | **APScheduler** | Runs in-process, no Redis/Celery needed |
| Resume parsing | **pdfplumber + python-docx** | Regex/keyword extraction, no external APIs |

Single FastAPI process serves HTML pages, JSON API, and runs the background scraper. Deployable to a single VPS or PaaS.

## 3. Database Schema

### users
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| email | str | unique |
| hashed_password | str | nullable (magic link users) |
| is_active | bool | |
| is_verified | bool | |
| created_at | datetime | |
| updated_at | datetime | |

### profiles
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users, unique |
| name | str | |
| education | JSON | {degree, major, minor, school, honors} |
| certifications | JSON[] | |
| skills | JSON[] | |
| experience_keywords | JSON[] | |
| years_experience | int | |
| languages | JSON[] | |
| clearance_eligible | bool | |
| target_companies | JSON[] | |
| original_resume_filename | str | |
| created_at | datetime | |
| updated_at | datetime | |

### jobs
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| source | str | "USAJobs", "Indeed", etc. |
| external_id | str | unique per source, dedup key |
| title | str | |
| organization | str | |
| department | str | |
| location | str | |
| salary_min | str | |
| salary_max | str | |
| grade | str | |
| description | text | |
| qualifications | text | |
| url | str | unique |
| open_date | str | |
| close_date | str | |
| fetched_at | datetime | |
| is_active | bool | mark stale jobs inactive |

### match_results
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| job_id | UUID | FK → jobs |
| total_score | float | |
| breakdown | JSON | {skills, keywords, certs, edu, org, lang} |
| matched_skills | JSON[] | |
| matched_keywords | JSON[] | |
| computed_at | datetime | |

**Notes:**
- `match_results` is a cache — recomputed when profile changes or new jobs arrive
- `match_results` has a unique constraint on `(user_id, job_id)` — one score per user per job
- `external_id` on jobs prevents duplicates across scraping runs
- Profile data stored as JSON columns for flexibility

## 4. Pages & User Flow

### 4.1 Landing Page (`/`)
- Public homepage
- Headline: "See how you stack up against cybersecurity jobs"
- Two CTAs: "Try it free" (no account) and "Sign up"
- Brief explanation of how it works

### 4.2 Public Try-It Page (`/try`)
- No account required
- Simple form: paste skills, select certs from checklist, pick education level
- Submit → shows top 10 job matches with scores
- Upsell: "Want to save results and track over time? Create an account"

### 4.3 Auth Pages (`/login`, `/register`)
- Email + password registration
- Magic link option (enter email, receive login link)
- Handled by FastAPI-Users

### 4.4 Profile Setup (`/profile/setup`)
- Step 1: Upload resume (PDF/DOCX) OR skip to manual entry
- Step 2: Review/edit auto-parsed data in a form
  - Skills (multi-select with autocomplete from master list)
  - Certifications (checkbox list of known certs)
  - Education (degree, major, minor, school)
  - Experience keywords (tag input)
  - Years of experience, languages, clearance eligibility
  - Target companies (multi-select)
- Step 3: Save → triggers initial match scoring → redirect to dashboard

### 4.5 Dashboard / Portal (`/dashboard`)
- **Stats row:** Average match score, strong matches count (70+), total jobs tracked, profile strength %
- **Top matches list:** Highest-scoring jobs with title, org, location, salary, score badge
- **Quick actions sidebar:** "Check [company] now" button, update resume, export CSV
- **Skill gaps widget:** Skills frequently in job listings but missing from profile
- **Job sources widget:** Breakdown of jobs per source with counts

### 4.6 Job Browser (`/jobs`)
- Full list of matched jobs, sortable by score, date, salary, source
- Filters: source, min score, location, organization
- Click a job → expanded view with full description, score breakdown, matched skills/keywords
- HTMX-powered filtering (no page reloads)

### 4.7 Profile Editor (`/profile`)
- Same form as setup, pre-filled with current data
- Save → recomputes all match scores in background
- Re-upload resume option

## 5. Resume Parsing

**Pipeline:**
1. Extract text — `pdfplumber` for PDFs, `python-docx` for DOCX
2. Section detection — regex for Education, Experience, Skills, Certifications headers
3. Skill extraction — match against master list of ~200 cybersecurity skills/tools
4. Cert extraction — match against known cert names (Security+, CISSP, CEH, OSCP, GIAC, etc.)
5. Education extraction — regex for degree patterns ("Bachelor of", "B.S.", "Master of")
6. Output — structured dict that pre-fills the profile form

Parser interface is designed so an LLM-based parser can be swapped in later without changing the rest of the system. The function signature is: `parse_resume(file_bytes, filename) -> dict` returning the same profile structure.

## 6. Pluggable Scraper System

```
scrapers/
├── base.py              # CompanyScraper base class
├── spacex.py            # future
├── crowdstrike.py       # future
└── ...
```

**Base class interface:**
- `name: str` — company name
- `careers_url: str` — base careers page URL
- `fetch_jobs() -> list[dict]` — returns standard job dicts (same format as existing scrapers)
- `is_available() -> bool` — health check

**Integration:**
- Background scheduler runs all registered scrapers every 4 hours
- On-demand endpoint (`POST /api/scrape/{company}`) triggers a single company scraper
- Dashboard "Check [company] now" button calls this endpoint via HTMX
- New scrapers auto-register when added to the scrapers directory

**Existing sources** (USAJobs, Indeed, RemoteOK, Jobicy, TheMuse) are refactored into this same interface so all job fetching is consistent.

## 7. Background Job Fetcher

- **APScheduler** runs inside the FastAPI process
- Default interval: every 4 hours
- On each run: execute all registered scrapers, upsert jobs into DB, mark jobs not seen in 7 days as inactive
- After new jobs are inserted: recompute match_results for all users with profiles
- On-demand scraping: triggered per-company via API endpoint, same upsert logic

## 8. Project Structure

```
cyber_job_hunter/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, startup, scheduler
│   ├── config.py            # settings, env vars
│   ├── database.py          # SQLAlchemy engine, session
│   ├── models.py            # SQLAlchemy models
│   ├── auth.py              # FastAPI-Users setup
│   ├── routes/
│   │   ├── pages.py         # Jinja2 page routes (landing, dashboard, etc.)
│   │   ├── api.py           # JSON API routes (scrape, match, profile)
│   │   └── auth_routes.py   # login, register, magic link
│   ├── services/
│   │   ├── matcher.py       # scoring engine (migrated from existing)
│   │   ├── resume_parser.py # PDF/DOCX → structured profile
│   │   └── scheduler.py     # APScheduler job fetcher
│   ├── scrapers/
│   │   ├── base.py          # CompanyScraper base class
│   │   ├── usajobs.py       # migrated from existing
│   │   ├── indeed.py        # migrated from existing
│   │   ├── remoteok.py      # migrated from existing
│   │   ├── jobicy.py        # migrated from existing
│   │   └── themuse.py       # migrated from existing
│   └── templates/
│       ├── base.html        # base layout with nav, HTMX script
│       ├── landing.html
│       ├── try_it.html
│       ├── login.html
│       ├── register.html
│       ├── profile_setup.html
│       ├── dashboard.html
│       ├── jobs.html
│       ├── job_detail.html
│       └── profile.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js           # minimal JS (autocomplete, tag inputs)
├── data/
│   └── skills_master.json   # master list of cybersecurity skills/certs
├── main.py                  # existing CLI (preserved, still works)
├── matcher.py               # existing (preserved, web app imports from services/)
├── resume_profile.py        # existing (preserved)
├── private_jobs.py          # existing (preserved)
├── usajobs_client.py        # existing (preserved)
├── requirements.txt         # updated with web dependencies
└── README.md                # existing
```

**Key decisions:**
- Web app lives in `app/` — existing CLI code is untouched and still works
- Matcher and scrapers are migrated (not copied) into `app/services/` and `app/scrapers/`, with the originals preserved for CLI use
- Static files (CSS/JS) are minimal — HTMX handles most interactivity

## 9. Future Enhancements (Not in v1)

- **LLM resume parsing** — swap regex parser for Claude Haiku when accuracy needs improvement
- **Monetization tiers** — Free (top 10, 24hr refresh) / Pro $9-15/mo (unlimited, 4hr, exports, alerts) / Premium $25-30/mo (optimization suggestions, multiple profiles, API)
- **Affiliate links** — cert training recommendations in skill gaps widget
- **Email alerts** — notify users when new high-match jobs appear
- **Company-specific scrapers** — SpaceX, CrowdStrike, Palo Alto Networks careers pages
