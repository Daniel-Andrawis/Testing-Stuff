import json
from pathlib import Path

from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_optional_user, current_active_user
from app.database import get_session
from app.models import User, Job, MatchResult, Profile
from app.services.matcher import compute_skill_gaps

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter()


@router.get("/")
async def landing(
    request: Request,
    user=Depends(current_optional_user),
    session: AsyncSession = Depends(get_session),
):
    job_count = (await session.execute(
        select(func.count(Job.id)).where(Job.is_active == True)
    )).scalar() or 0
    user_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
    source_count = (await session.execute(
        select(func.count(distinct(Job.source)))
    )).scalar() or 0

    return templates.TemplateResponse(request, "landing.html", {
        "user": user,
        "job_count": job_count,
        "source_count": source_count,
        "user_count": user_count,
    })


@router.get("/login")
async def login_page(request: Request, user=Depends(current_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"user": None, "error": None})


@router.get("/register")
async def register_page(request: Request, user=Depends(current_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html", {"user": None, "error": None})


@router.get("/dashboard")
async def dashboard(
    request: Request,
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(user.id)

    # Check profile
    profile = (await session.execute(
        select(Profile).where(Profile.user_id == uid)
    )).scalar_one_or_none()
    has_profile = profile is not None

    # Stats
    total_jobs = (await session.execute(
        select(func.count(Job.id)).where(Job.is_active == True)
    )).scalar() or 0

    source_count = (await session.execute(
        select(func.count(distinct(Job.source))).select_from(Job).where(Job.is_active == True)
    )).scalar() or 0

    avg_result = await session.execute(
        select(func.avg(MatchResult.total_score)).where(MatchResult.user_id == uid)
    )
    avg_score = avg_result.scalar() or 0

    strong_result = await session.execute(
        select(func.count(MatchResult.id)).where(
            MatchResult.user_id == uid, MatchResult.total_score >= 70
        )
    )
    strong_count = strong_result.scalar() or 0

    # Top matches
    top_result = await session.execute(
        select(MatchResult, Job)
        .join(Job, MatchResult.job_id == Job.id)
        .where(MatchResult.user_id == uid)
        .order_by(MatchResult.total_score.desc())
        .limit(5)
    )
    top_matches = top_result.all()

    # Source breakdown
    src_result = await session.execute(
        select(Job.source, func.count(Job.id))
        .where(Job.is_active == True)
        .group_by(Job.source)
        .order_by(func.count(Job.id).desc())
    )
    source_breakdown = src_result.all()

    # Skill gaps
    skill_gaps = []
    if has_profile and total_jobs > 0:
        jobs_result = await session.execute(select(Job).where(Job.is_active == True).limit(200))
        job_dicts = [{"title": j.title, "description": j.description, "qualifications": j.qualifications}
                     for j in jobs_result.scalars()]
        skill_gaps = compute_skill_gaps(job_dicts, profile.skills or [])

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "has_profile": has_profile,
        "total_jobs": total_jobs,
        "source_count": source_count,
        "avg_score": avg_score,
        "strong_count": strong_count,
        "top_matches": top_matches,
        "source_breakdown": source_breakdown,
        "skill_gaps": skill_gaps,
        "skill_count": len(profile.skills) if has_profile else 0,
    })


@router.get("/jobs")
async def job_browser(
    request: Request,
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    source: str = "",
    min_score: float = 0,
    sort: str = "score",
    page: int = 1,
):
    uid = str(user.id)
    page_size = 25

    profile = (await session.execute(
        select(Profile).where(Profile.user_id == uid)
    )).scalar_one_or_none()

    query = (
        select(MatchResult, Job)
        .join(Job, MatchResult.job_id == Job.id)
        .where(MatchResult.user_id == uid, Job.is_active == True)
    )

    if source:
        query = query.where(Job.source == source)
    if min_score > 0:
        query = query.where(MatchResult.total_score >= min_score)

    if sort == "date":
        query = query.order_by(Job.open_date.desc())
    elif sort == "salary":
        query = query.order_by(Job.salary_max.desc())
    else:
        query = query.order_by(MatchResult.total_score.desc())

    # Count total
    count_query = (
        select(func.count())
        .select_from(MatchResult)
        .join(Job, MatchResult.job_id == Job.id)
        .where(MatchResult.user_id == uid, Job.is_active == True)
    )
    if source:
        count_query = count_query.where(Job.source == source)
    if min_score > 0:
        count_query = count_query.where(MatchResult.total_score >= min_score)

    total = (await session.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    jobs = result.all()

    # Get unique sources for filter
    src_result = await session.execute(
        select(distinct(Job.source)).where(Job.is_active == True)
    )
    sources = [r[0] for r in src_result.all()]

    return templates.TemplateResponse(request, "jobs.html", {
        "user": user,
        "has_profile": profile is not None,
        "jobs": jobs,
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
        "sources": sources,
        "current_source": source,
        "current_min_score": min_score,
        "current_sort": sort,
    })


@router.get("/profile/setup")
async def profile_setup_page(request: Request, user=Depends(current_active_user)):
    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    all_skills = []
    if skills_path.exists():
        with open(skills_path) as f:
            all_skills = json.load(f)
    return templates.TemplateResponse(request, "profile_setup.html", {
        "user": user,
        "all_skills": all_skills,
        "profile": None,
    })


@router.post("/profile/setup")
async def profile_setup_submit(
    request: Request,
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    name: str = Form(""),
    skills: str = Form(""),
    certifications: str = Form(""),
    experience_keywords: str = Form(""),
    edu_degree: str = Form(""),
    edu_major: str = Form(""),
    edu_minor: str = Form(""),
    edu_school: str = Form(""),
    years_experience: int = Form(0),
    languages: str = Form(""),
    clearance_eligible: bool = Form(False),
    target_companies: str = Form(""),
):
    import uuid
    uid = str(user.id)

    existing = (await session.execute(
        select(Profile).where(Profile.user_id == uid)
    )).scalar_one_or_none()

    skills_list = [s.strip() for s in skills.split(",") if s.strip()]
    certs_list = [c.strip() for c in certifications.split(",") if c.strip()]
    keywords_list = [k.strip() for k in experience_keywords.split(",") if k.strip()]
    langs_list = [l.strip() for l in languages.split(",") if l.strip()]
    companies_list = [c.strip() for c in target_companies.split(",") if c.strip()]
    education = {"degree": edu_degree, "major": edu_major, "minor": edu_minor, "school": edu_school}

    if existing:
        existing.name = name
        existing.skills = skills_list
        existing.certifications = certs_list
        existing.experience_keywords = keywords_list
        existing.education = education
        existing.years_experience = years_experience
        existing.languages = langs_list
        existing.clearance_eligible = clearance_eligible
        existing.target_companies = companies_list
    else:
        profile = Profile(
            id=str(uuid.uuid4()),
            user_id=uid,
            name=name,
            skills=skills_list,
            certifications=certs_list,
            experience_keywords=keywords_list,
            education=education,
            years_experience=years_experience,
            languages=langs_list,
            clearance_eligible=clearance_eligible,
            target_companies=companies_list,
        )
        session.add(profile)

    await session.commit()

    # Recompute matches
    from app.services.scheduler import recompute_user_matches
    await recompute_user_matches(uid)

    return RedirectResponse("/dashboard", status_code=302)


@router.get("/profile")
async def profile_edit_page(
    request: Request,
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    uid = str(user.id)
    profile = (await session.execute(
        select(Profile).where(Profile.user_id == uid)
    )).scalar_one_or_none()

    if not profile:
        return RedirectResponse("/profile/setup", status_code=302)

    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    all_skills = []
    if skills_path.exists():
        with open(skills_path) as f:
            all_skills = json.load(f)

    return templates.TemplateResponse(request, "profile_setup.html", {
        "user": user,
        "all_skills": all_skills,
        "profile": profile,
    })


@router.get("/try")
async def try_it_page(
    request: Request,
    user=Depends(current_optional_user),
    session: AsyncSession = Depends(get_session),
):
    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    all_skills = []
    if skills_path.exists():
        with open(skills_path) as f:
            all_skills = json.load(f)

    return templates.TemplateResponse(request, "try_it.html", {
        "user": user,
        "all_skills": all_skills,
        "results": None,
    })


@router.post("/try")
async def try_it_submit(
    request: Request,
    user=Depends(current_optional_user),
    session: AsyncSession = Depends(get_session),
    skills: str = Form(""),
    certifications: str = Form(""),
    edu_major: str = Form(""),
):
    from app.services.matcher import score_job

    skills_list = [s.strip() for s in skills.split(",") if s.strip()]
    certs_list = [c.strip() for c in certifications.split(",") if c.strip()]
    profile_dict = {
        "skills": skills_list,
        "certifications": certs_list,
        "experience_keywords": [],
        "education": {"major": edu_major, "minor": ""},
        "target_companies": [],
        "languages": [],
    }

    jobs_result = await session.execute(
        select(Job).where(Job.is_active == True).limit(200)
    )
    active_jobs = jobs_result.scalars().all()

    scored = []
    for job in active_jobs:
        job_dict = {
            "title": job.title, "description": job.description,
            "qualifications": job.qualifications,
            "organization": job.organization, "department": job.department,
        }
        info = score_job(job_dict, profile_dict)
        scored.append((job, info))

    scored.sort(key=lambda x: x[1]["total_score"], reverse=True)
    top_10 = scored[:10]

    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    all_skills = []
    if skills_path.exists():
        with open(skills_path) as f:
            all_skills = json.load(f)

    return templates.TemplateResponse(request, "try_it.html", {
        "user": user,
        "all_skills": all_skills,
        "results": top_10,
        "input_skills": skills,
        "input_certs": certifications,
        "input_major": edu_major,
    })
