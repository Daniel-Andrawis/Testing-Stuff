import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.database import get_session
from app.models import User, Job, MatchResult, Profile
from app.services.scheduler import run_single_scraper, recompute_user_matches
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/parse-resume")
async def api_parse_resume(file: UploadFile = File(...)):
    """Parse an uploaded resume and return structured profile data."""
    contents = await file.read()
    try:
        result = parse_resume(contents, file.filename or "resume.pdf")
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {e}")


@router.post("/scrape/{source_id}")
async def trigger_scrape(source_id: str, user=Depends(current_active_user)):
    """On-demand scrape for a specific source."""
    count = await run_single_scraper(source_id)
    return {"source": source_id, "jobs_added": count}


@router.post("/recompute")
async def trigger_recompute(user=Depends(current_active_user)):
    """Recompute match scores for the current user."""
    await recompute_user_matches(str(user.id))
    return {"status": "ok"}


@router.get("/export/csv")
async def export_csv(
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Export user's match results as CSV."""
    results = await session.execute(
        select(MatchResult, Job)
        .join(Job, MatchResult.job_id == Job.id)
        .where(MatchResult.user_id == str(user.id))
        .order_by(MatchResult.total_score.desc())
    )
    rows = results.all()

    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Rank", "Score", "Title", "Organization", "Location",
        "Salary Min", "Salary Max", "Source", "URL",
        "Matched Skills", "Matched Keywords",
    ])
    for i, (match, job) in enumerate(rows, 1):
        writer.writerow([
            i, match.total_score, job.title, job.organization, job.location,
            job.salary_min, job.salary_max, job.source, job.url,
            "; ".join(match.matched_skills or []),
            "; ".join(match.matched_keywords or []),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cyberrank-results.csv"},
    )
