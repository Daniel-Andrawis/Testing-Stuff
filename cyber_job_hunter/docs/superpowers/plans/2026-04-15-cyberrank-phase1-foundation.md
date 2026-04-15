# CyberRank Phase 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the FastAPI app with database, auth (email/password), base template, and landing page — a working skeleton that serves HTML and handles user registration/login. Magic link auth is configured but deferred to Phase 2 when SMTP is set up.

**Architecture:** Single FastAPI process with Jinja2 templates, SQLAlchemy + SQLite, FastAPI-Users for auth. HTMX included in base template for future dynamic pages.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, FastAPI-Users, Jinja2, HTMX, python-dotenv

---

### Task 1: Project scaffold and dependencies

**Files:**
- Create: `app/__init__.py`
- Create: `app/config.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Create app package**

```python
# app/__init__.py
```

Empty file — just marks `app/` as a package.

- [ ] **Step 2: Create config module**

```python
# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cyberrank.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
MAIL_ENABLED = os.getenv("MAIL_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
```

- [ ] **Step 3: Update requirements.txt**

```
requests>=2.31.0
beautifulsoup4>=4.12.0
python-dotenv>=1.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.20.0
fastapi-users[sqlalchemy]>=14.0.0
jinja2>=3.1.0
python-multipart>=0.0.9
httpx>=0.27.0
```

- [ ] **Step 4: Install dependencies**

Run: `cd /root/Testing-Stuff/cyber_job_hunter && pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 5: Commit**

```bash
git add app/__init__.py app/config.py requirements.txt
git commit -m "Scaffold app package with config and web dependencies"
```

---

### Task 2: Database models

**Files:**
- Create: `app/database.py`
- Create: `app/models.py`
- Test: manual — verify tables create on startup

- [ ] **Step 1: Create database engine module**

```python
# app/database.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: Create SQLAlchemy models**

```python
# app/models.py
import uuid
from datetime import datetime

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Column, String, Boolean, Integer, Float, Text, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship

from app.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, default="")
    education = Column(SQLiteJSON, default=dict)
    certifications = Column(SQLiteJSON, default=list)
    skills = Column(SQLiteJSON, default=list)
    experience_keywords = Column(SQLiteJSON, default=list)
    years_experience = Column(Integer, default=0)
    languages = Column(SQLiteJSON, default=list)
    clearance_eligible = Column(Boolean, default=False)
    target_companies = Column(SQLiteJSON, default=list)
    original_resume_filename = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)
    external_id = Column(String, default="")
    title = Column(String, nullable=False)
    organization = Column(String, default="")
    department = Column(String, default="")
    location = Column(String, default="")
    salary_min = Column(String, default="N/A")
    salary_max = Column(String, default="N/A")
    grade = Column(String, default="N/A")
    description = Column(Text, default="")
    qualifications = Column(Text, default="")
    url = Column(String, unique=True, nullable=False)
    open_date = Column(String, default="N/A")
    close_date = Column(String, default="N/A")
    fetched_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    total_score = Column(Float, nullable=False)
    breakdown = Column(SQLiteJSON, default=dict)
    matched_skills = Column(SQLiteJSON, default=list)
    matched_keywords = Column(SQLiteJSON, default=list)
    computed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job"),
    )
```

- [ ] **Step 3: Verify models import cleanly**

Run: `cd /root/Testing-Stuff/cyber_job_hunter && python -c "from app.models import User, Profile, Job, MatchResult; print('Models OK')"`
Expected: `Models OK`

- [ ] **Step 4: Commit**

```bash
git add app/database.py app/models.py
git commit -m "Add SQLAlchemy models for users, profiles, jobs, match results"
```

---

### Task 3: FastAPI-Users auth setup

**Files:**
- Create: `app/auth.py`
- Create: `app/routes/__init__.py`
- Create: `app/routes/auth_routes.py`

- [ ] **Step 1: Create auth configuration**

```python
# app/auth.py
import uuid
from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SECRET_KEY
from app.database import get_session
from app.models import User


async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)


cookie_transport = CookieTransport(cookie_name="cyberrank", cookie_max_age=3600 * 24 * 7)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=3600 * 24 * 7)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_db, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_optional_user = fastapi_users.current_user(active=True, optional=True)
```

- [ ] **Step 2: Create routes package**

```python
# app/routes/__init__.py
```

- [ ] **Step 3: Create auth routes**

```python
# app/routes/auth_routes.py
from fastapi import APIRouter

from app.auth import fastapi_users, auth_backend
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate
import uuid


class UserRead(BaseUser[uuid.UUID]):
    pass


class UserCreate(BaseUserCreate):
    pass


class UserUpdate(BaseUserUpdate):
    pass


router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
```

- [ ] **Step 4: Commit**

```bash
git add app/auth.py app/routes/__init__.py app/routes/auth_routes.py
git commit -m "Add FastAPI-Users auth with cookie/JWT and registration routes"
```

---

### Task 4: FastAPI app entrypoint

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Create the FastAPI app**

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import create_tables
from app.routes.auth_routes import router as auth_router


BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="CyberRank", lifespan=lifespan)

# Static files
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
(static_dir / "css").mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

# Routes
app.include_router(auth_router)
```

- [ ] **Step 2: Verify the app starts**

Run: `cd /root/Testing-Stuff/cyber_job_hunter && timeout 5 python -c "from app.main import app; print(f'App loaded: {app.title}')" || true`
Expected: `App loaded: CyberRank`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "Add FastAPI app entrypoint with lifespan, static files, and auth"
```

---

### Task 5: Base template and static assets

**Files:**
- Create: `app/templates/base.html`
- Create: `static/css/style.css`
- Create: `static/js/app.js`

- [ ] **Step 1: Create base HTML template**

```html
<!-- app/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}CyberRank{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
</head>
<body>
    <nav class="nav">
        <div class="nav-inner">
            <a href="/" class="nav-brand">⚡ CyberRank</a>
            <div class="nav-links">
                {% if user %}
                    <a href="/dashboard">Dashboard</a>
                    <a href="/jobs">Jobs</a>
                    <a href="/profile">Profile</a>
                    <span class="nav-user">{{ user.email }}</span>
                    <form action="/auth/logout" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-sm">Logout</button>
                    </form>
                {% else %}
                    <a href="/try">Try It</a>
                    <a href="/login">Login</a>
                    <a href="/register" class="btn btn-primary btn-sm">Sign Up</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <script src="/static/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create base CSS**

```css
/* static/css/style.css */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg: #0f172a;
    --bg-card: #1e293b;
    --border: #334155;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: #6366f1;
    --green: #22c55e;
    --yellow: #eab308;
    --red: #ef4444;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}

/* Nav */
.nav {
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    padding: 0 1.5rem;
}
.nav-inner {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 56px;
}
.nav-brand {
    color: var(--accent);
    font-weight: 700;
    font-size: 1.1rem;
    text-decoration: none;
}
.nav-links { display: flex; align-items: center; gap: 1.25rem; }
.nav-links a { color: var(--text-dim); text-decoration: none; font-size: 0.875rem; }
.nav-links a:hover { color: var(--text); }
.nav-user { color: var(--text-dim); font-size: 0.875rem; }

/* Container */
.container { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }

/* Buttons */
.btn {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg-card);
    color: var(--text);
    font-size: 0.875rem;
    cursor: pointer;
    text-decoration: none;
}
.btn:hover { border-color: var(--accent); }
.btn-primary { background: var(--accent); border-color: var(--accent); color: white; }
.btn-primary:hover { opacity: 0.9; }
.btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }
.btn-lg { padding: 0.75rem 1.5rem; font-size: 1rem; }

/* Cards */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
}

/* Forms */
.form-group { margin-bottom: 1rem; }
.form-group label {
    display: block;
    margin-bottom: 0.375rem;
    font-size: 0.875rem;
    color: var(--text-dim);
}
.form-input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 0.875rem;
}
.form-input:focus { outline: none; border-color: var(--accent); }

/* Score badges */
.score-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
}
.score-high { background: #166534; color: var(--green); }
.score-mid { background: #854d0e; color: var(--yellow); }
.score-low { background: #991b1b; color: var(--red); }

/* Stats grid */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
.stat-card { text-align: left; }
.stat-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); }
.stat-value { font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; }
.stat-sub { font-size: 0.75rem; color: var(--text-dim); }

/* Utility */
.text-dim { color: var(--text-dim); }
.text-accent { color: var(--accent); }
.text-green { color: var(--green); }
.mt-1 { margin-top: 0.5rem; }
.mt-2 { margin-top: 1rem; }
.mt-3 { margin-top: 1.5rem; }
.mb-2 { margin-bottom: 1rem; }
.flex { display: flex; }
.gap-1 { gap: 0.5rem; }
.gap-2 { gap: 1rem; }
```

- [ ] **Step 3: Create minimal JS file**

```javascript
// static/js/app.js
// Minimal JS — HTMX handles most interactivity.
// This file is for autocomplete, tag inputs, and other small UI helpers added later.

document.addEventListener('DOMContentLoaded', function() {
    // Flash message auto-dismiss
    document.querySelectorAll('.flash').forEach(function(el) {
        setTimeout(function() { el.remove(); }, 5000);
    });
});
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/base.html static/css/style.css static/js/app.js
git commit -m "Add base template with dark theme, HTMX, and core CSS"
```

---

### Task 6: Landing page

**Files:**
- Create: `app/templates/landing.html`
- Create: `app/routes/pages.py`
- Modify: `app/main.py` — register page routes

- [ ] **Step 1: Create landing page template**

```html
<!-- app/templates/landing.html -->
{% extends "base.html" %}
{% block title %}CyberRank — See How You Stack Up{% endblock %}

{% block content %}
<div style="text-align:center; padding:4rem 0 2rem;">
    <h1 style="font-size:2.5rem; margin-bottom:0.75rem;">See how you stack up against<br>cybersecurity jobs</h1>
    <p class="text-dim" style="font-size:1.1rem; max-width:600px; margin:0 auto 2rem;">
        Upload your resume or enter your skills, and instantly see how you match
        against hundreds of live cybersecurity job listings.
    </p>
    <div class="flex gap-2" style="justify-content:center;">
        <a href="/try" class="btn btn-lg btn-primary">Try It Free</a>
        <a href="/register" class="btn btn-lg">Create Account</a>
    </div>
</div>

<div class="stats-grid mt-3" style="max-width:800px; margin-left:auto; margin-right:auto;">
    <div class="card stat-card" style="text-align:center;">
        <div class="stat-value text-accent">{{ job_count }}</div>
        <div class="stat-sub">Active job listings</div>
    </div>
    <div class="card stat-card" style="text-align:center;">
        <div class="stat-value text-green">{{ source_count }}</div>
        <div class="stat-sub">Job sources</div>
    </div>
    <div class="card stat-card" style="text-align:center;">
        <div class="stat-value" style="color:var(--yellow);">{{ user_count }}</div>
        <div class="stat-sub">Users matched</div>
    </div>
</div>

<div class="mt-3" style="text-align:center; max-width:700px; margin-left:auto; margin-right:auto;">
    <h2 style="font-size:1.3rem; margin-bottom:1rem;">How it works</h2>
    <div class="stats-grid">
        <div class="card">
            <div style="font-size:1.5rem; margin-bottom:0.5rem;">📄</div>
            <h3 style="font-size:0.95rem; margin-bottom:0.25rem;">1. Add your profile</h3>
            <p class="text-dim" style="font-size:0.85rem;">Upload a resume or manually enter your skills, certs, and experience.</p>
        </div>
        <div class="card">
            <div style="font-size:1.5rem; margin-bottom:0.5rem;">🔍</div>
            <h3 style="font-size:0.95rem; margin-bottom:0.25rem;">2. We scan job boards</h3>
            <p class="text-dim" style="font-size:0.85rem;">USAJobs, Indeed, RemoteOK, and more — refreshed every few hours.</p>
        </div>
        <div class="card">
            <div style="font-size:1.5rem; margin-bottom:0.5rem;">📊</div>
            <h3 style="font-size:0.95rem; margin-bottom:0.25rem;">3. See your match scores</h3>
            <p class="text-dim" style="font-size:0.85rem;">Each job is scored against your profile. Find where you're the strongest fit.</p>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Create page routes**

```python
# app/routes/pages.py
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_optional_user
from app.database import get_session
from app.models import User, Job

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter()


@router.get("/")
async def landing(
    request: Request,
    user=Depends(current_optional_user),
    session: AsyncSession = Depends(get_session),
):
    job_count_result = await session.execute(select(func.count(Job.id)).where(Job.is_active == True))
    job_count = job_count_result.scalar() or 0

    user_count_result = await session.execute(select(func.count(User.id)))
    user_count = user_count_result.scalar() or 0

    source_count_result = await session.execute(select(func.count(func.distinct(Job.source))))
    source_count = source_count_result.scalar() or 0

    return templates.TemplateResponse("landing.html", {
        "request": request,
        "user": user,
        "job_count": job_count,
        "source_count": source_count,
        "user_count": user_count,
    })
```

- [ ] **Step 3: Register page routes in app**

Add to `app/main.py` after the auth router import:

```python
from app.routes.pages import router as pages_router
```

Add after `app.include_router(auth_router)`:

```python
app.include_router(pages_router)
```

- [ ] **Step 4: Test the landing page**

Run: `cd /root/Testing-Stuff/cyber_job_hunter && timeout 5 uvicorn app.main:app --host 0.0.0.0 --port 8000 &`
Then: `sleep 2 && curl -s http://localhost:8000/ | head -20`
Expected: HTML output containing "CyberRank" and "See how you stack up"
Cleanup: `kill %1 2>/dev/null`

- [ ] **Step 5: Commit**

```bash
git add app/templates/landing.html app/routes/pages.py app/main.py
git commit -m "Add landing page with live job/user stats"
```

---

### Task 7: Auth pages (login + register)

**Files:**
- Create: `app/templates/login.html`
- Create: `app/templates/register.html`
- Modify: `app/routes/pages.py` — add login/register page routes

- [ ] **Step 1: Create login template**

```html
<!-- app/templates/login.html -->
{% extends "base.html" %}
{% block title %}Login — CyberRank{% endblock %}

{% block content %}
<div style="max-width:400px; margin:3rem auto;">
    <h1 style="font-size:1.5rem; margin-bottom:0.5rem;">Welcome back</h1>
    <p class="text-dim mb-2">Log in to your CyberRank portal.</p>

    {% if error %}
    <div class="card" style="border-color:var(--red); margin-bottom:1rem;">
        <p style="color:var(--red); font-size:0.875rem;">{{ error }}</p>
    </div>
    {% endif %}

    <form method="POST" action="/auth/login" class="card">
        <div class="form-group">
            <label for="username">Email</label>
            <input type="email" id="username" name="username" class="form-input" required>
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" class="form-input" required>
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%;">Log In</button>
    </form>

    <p class="text-dim mt-2" style="text-align:center; font-size:0.85rem;">
        Don't have an account? <a href="/register" class="text-accent">Sign up</a>
    </p>
</div>
{% endblock %}
```

- [ ] **Step 2: Create register template**

```html
<!-- app/templates/register.html -->
{% extends "base.html" %}
{% block title %}Sign Up — CyberRank{% endblock %}

{% block content %}
<div style="max-width:400px; margin:3rem auto;">
    <h1 style="font-size:1.5rem; margin-bottom:0.5rem;">Create your account</h1>
    <p class="text-dim mb-2">Start matching against cybersecurity jobs.</p>

    {% if error %}
    <div class="card" style="border-color:var(--red); margin-bottom:1rem;">
        <p style="color:var(--red); font-size:0.875rem;">{{ error }}</p>
    </div>
    {% endif %}

    <form id="register-form" class="card">
        <div class="form-group">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" class="form-input" required>
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" class="form-input" minlength="8" required>
        </div>
        <div class="form-group">
            <label for="password_confirm">Confirm Password</label>
            <input type="password" id="password_confirm" class="form-input" minlength="8" required>
        </div>
        <div id="register-error" style="display:none; color:var(--red); font-size:0.85rem; margin-bottom:0.75rem;"></div>
        <button type="submit" class="btn btn-primary" style="width:100%;">Create Account</button>
    </form>

    <p class="text-dim mt-2" style="text-align:center; font-size:0.85rem;">
        Already have an account? <a href="/login" class="text-accent">Log in</a>
    </p>
</div>

<script>
document.getElementById('register-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const errEl = document.getElementById('register-error');
    errEl.style.display = 'none';

    const pw = document.getElementById('password').value;
    if (pw !== document.getElementById('password_confirm').value) {
        errEl.textContent = 'Passwords do not match.';
        errEl.style.display = 'block';
        return;
    }

    const resp = await fetch('/auth/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            email: document.getElementById('email').value,
            password: pw,
        }),
    });

    if (resp.ok) {
        // Auto-login after registration
        const formData = new FormData();
        formData.append('username', document.getElementById('email').value);
        formData.append('password', pw);
        const loginResp = await fetch('/auth/login', { method: 'POST', body: formData });
        if (loginResp.ok) {
            window.location.href = '/profile/setup';
        } else {
            window.location.href = '/login';
        }
    } else {
        const data = await resp.json();
        errEl.textContent = data.detail || 'Registration failed.';
        errEl.style.display = 'block';
    }
});
</script>
{% endblock %}
```

- [ ] **Step 3: Add page routes for login and register**

Add to `app/routes/pages.py`:

```python
@router.get("/login")
async def login_page(request: Request, user=Depends(current_optional_user)):
    if user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": None})


@router.get("/register")
async def register_page(request: Request, user=Depends(current_optional_user)):
    if user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "user": None, "error": None})
```

- [ ] **Step 4: Add login redirect after successful cookie auth**

Add to `app/routes/auth_routes.py` — override the login response to redirect to dashboard for browser-based logins:

```python
from fastapi import Request
from fastapi.responses import RedirectResponse


@router.post("/auth/login/redirect")
async def login_redirect():
    """After FastAPI-Users sets the cookie, redirect to dashboard."""
    return RedirectResponse("/dashboard", status_code=302)
```

Note: The default `/auth/login` endpoint returns JSON. The login form POSTs there, and on success the browser receives the cookie. The register form JS handles the redirect client-side.

- [ ] **Step 5: Commit**

```bash
git add app/templates/login.html app/templates/register.html app/routes/pages.py app/routes/auth_routes.py
git commit -m "Add login and register pages with auth flow"
```

---

### Task 8: Stub dashboard page (auth-protected)

**Files:**
- Create: `app/templates/dashboard.html`
- Modify: `app/routes/pages.py` — add dashboard route

- [ ] **Step 1: Create stub dashboard template**

```html
<!-- app/templates/dashboard.html -->
{% extends "base.html" %}
{% block title %}Dashboard — CyberRank{% endblock %}

{% block content %}
<h1 style="font-size:1.5rem; margin-bottom:0.5rem;">Welcome, {{ user.email }}</h1>
<p class="text-dim">Your CyberRank portal. Full dashboard coming in Phase 2.</p>

<div class="stats-grid mt-2">
    <div class="card stat-card">
        <div class="stat-label">Match Score</div>
        <div class="stat-value text-dim">—</div>
        <div class="stat-sub">Complete your profile to see scores</div>
    </div>
    <div class="card stat-card">
        <div class="stat-label">Jobs Tracked</div>
        <div class="stat-value text-dim">0</div>
        <div class="stat-sub">Jobs load after first scrape</div>
    </div>
</div>

<div class="mt-2">
    <a href="/profile/setup" class="btn btn-primary">Set Up Profile</a>
</div>
{% endblock %}
```

- [ ] **Step 2: Add dashboard route**

Add to `app/routes/pages.py`:

```python
from app.auth import current_active_user

@router.get("/dashboard")
async def dashboard(request: Request, user=Depends(current_active_user)):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
    })
```

- [ ] **Step 3: Verify auth protection**

Run server, then:
`curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/dashboard`
Expected: `401` (not authenticated)

- [ ] **Step 4: Commit**

```bash
git add app/templates/dashboard.html app/routes/pages.py
git commit -m "Add stub dashboard page with auth protection"
```

---

### Task 9: End-to-end smoke test

**Files:** None new — just verification

- [ ] **Step 1: Start the server**

Run: `cd /root/Testing-Stuff/cyber_job_hunter && uvicorn app.main:app --host 0.0.0.0 --port 8000 &`

- [ ] **Step 2: Verify landing page loads**

Run: `curl -s http://localhost:8000/ | grep -o "CyberRank"`
Expected: `CyberRank`

- [ ] **Step 3: Verify register endpoint works**

Run: `curl -s -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"testpass123"}'`
Expected: JSON with `"email":"test@test.com"` and `"id":"..."`

- [ ] **Step 4: Verify login endpoint works**

Run: `curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=test@test.com&password=testpass123" -c cookies.txt`
Expected: JSON response, cookie file written

- [ ] **Step 5: Verify dashboard accessible with auth**

Run: `curl -s -b cookies.txt http://localhost:8000/dashboard | grep -o "Welcome"`
Expected: `Welcome`

- [ ] **Step 6: Cleanup and commit**

```bash
kill %1 2>/dev/null
rm -f cookies.txt cyberrank.db
git add -A
git status
# If any uncommitted changes remain, commit them:
git commit -m "Phase 1 complete: FastAPI app with auth, landing page, and stub dashboard"
```

---

## Phase 1 Complete Checklist

After all tasks, you should have:
- [x] FastAPI app that starts and serves pages
- [x] SQLite database with users, profiles, jobs, match_results tables
- [x] User registration (email + password)
- [x] Cookie-based login/logout
- [x] Landing page with live stats
- [x] Login and register pages
- [x] Auth-protected dashboard stub
- [x] Dark theme CSS with HTMX loaded
- [x] Existing CLI code untouched

**Next:** Phase 2 — Scrapers, matcher service, full dashboard, job browser
