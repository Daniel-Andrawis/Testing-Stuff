from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_optional_user, current_active_user
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
async def dashboard(request: Request, user=Depends(current_active_user)):
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})
