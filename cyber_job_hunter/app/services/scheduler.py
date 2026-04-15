"""Background job scheduler — scrapes jobs and recomputes match scores."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Job, Profile, MatchResult, User
from app.scrapers.registry import get_all_scrapers, get_scraper
from app.services.matcher import score_job
from app.mail import send_job_alert


async def run_all_scrapers():
    """Run all registered scrapers and upsert jobs into DB."""
    print("[scheduler] Running all scrapers...")
    total = 0
    for scraper in get_all_scrapers():
        if not scraper.is_available():
            print(f"[scheduler] Skipping {scraper.name} (not available)")
            continue
        try:
            jobs = scraper.fetch_jobs()
            count = await upsert_jobs(jobs)
            total += count
            print(f"[scheduler] {scraper.name}: {count} jobs upserted")
        except Exception as e:
            print(f"[scheduler] {scraper.name} failed: {e}")

    await mark_stale_jobs()
    await recompute_all_matches()
    print(f"[scheduler] Done. {total} total jobs upserted.")
    return total


async def run_single_scraper(source_id: str) -> int:
    """Run a single scraper by source_id and upsert results."""
    scraper = get_scraper(source_id)
    if not scraper:
        print(f"[scheduler] Unknown scraper: {source_id}")
        return 0
    if not scraper.is_available():
        print(f"[scheduler] {scraper.name} not available")
        return 0

    jobs = scraper.fetch_jobs()
    count = await upsert_jobs(jobs)
    await recompute_all_matches()
    return count


async def upsert_jobs(job_dicts: list[dict]) -> int:
    """Insert new jobs or update existing ones. Returns count of new jobs."""
    count = 0
    async with async_session() as session:
        for jd in job_dicts:
            existing = await session.execute(
                select(Job).where(Job.url == jd["url"])
            )
            existing_job = existing.scalar_one_or_none()

            if existing_job:
                existing_job.fetched_at = datetime.utcnow()
                existing_job.is_active = True
            else:
                job = Job(
                    id=str(uuid.uuid4()),
                    source=jd["source"],
                    external_id=jd.get("external_id", jd["url"]),
                    title=jd["title"],
                    organization=jd.get("organization", ""),
                    department=jd.get("department", ""),
                    location=jd.get("location", ""),
                    salary_min=jd.get("salary_min", "N/A"),
                    salary_max=jd.get("salary_max", "N/A"),
                    grade=jd.get("grade", "N/A"),
                    description=jd.get("description", ""),
                    qualifications=jd.get("qualifications", ""),
                    url=jd["url"],
                    open_date=jd.get("open_date", "N/A"),
                    close_date=jd.get("close_date", "N/A"),
                    fetched_at=datetime.utcnow(),
                    is_active=True,
                )
                session.add(job)
                count += 1

        await session.commit()
    return count


async def mark_stale_jobs(days: int = 7):
    """Mark jobs not seen in `days` as inactive."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.fetched_at < cutoff, Job.is_active == True))
        for job in result.scalars():
            job.is_active = False
        await session.commit()


async def recompute_all_matches(send_alerts: bool = True):
    """Recompute match scores for all users with profiles against all active jobs.
    Optionally sends email alerts for new high-scoring matches."""
    alert_threshold = 40  # notify on matches >= this score

    async with async_session() as session:
        profiles = (await session.execute(select(Profile))).scalars().all()
        if not profiles:
            return

        jobs_result = await session.execute(select(Job).where(Job.is_active == True))
        active_jobs = jobs_result.scalars().all()
        if not active_jobs:
            return

        for profile in profiles:
            profile_dict = {
                "skills": profile.skills or [],
                "experience_keywords": profile.experience_keywords or [],
                "certifications": profile.certifications or [],
                "education": profile.education or {},
                "target_companies": profile.target_companies or [],
                "languages": profile.languages or [],
                "years_experience": profile.years_experience or 0,
            }

            # Get existing matched job IDs before deleting
            old_job_ids = set()
            if send_alerts:
                old_result = await session.execute(
                    select(MatchResult.job_id).where(MatchResult.user_id == str(profile.user_id))
                )
                old_job_ids = {r[0] for r in old_result.all()}

            await session.execute(
                delete(MatchResult).where(MatchResult.user_id == str(profile.user_id))
            )

            new_high_matches = []
            for job in active_jobs:
                job_dict = {
                    "title": job.title,
                    "description": job.description,
                    "qualifications": job.qualifications,
                    "organization": job.organization,
                    "department": job.department,
                }
                score_info = score_job(job_dict, profile_dict)

                match = MatchResult(
                    id=str(uuid.uuid4()),
                    user_id=str(profile.user_id),
                    job_id=job.id,
                    total_score=score_info["total_score"],
                    breakdown=score_info["breakdown"],
                    matched_skills=score_info["matched_skills"],
                    matched_keywords=score_info["matched_keywords"],
                    computed_at=datetime.utcnow(),
                )
                session.add(match)

                # Track new high-scoring matches
                if send_alerts and job.id not in old_job_ids and score_info["total_score"] >= alert_threshold:
                    new_high_matches.append({
                        "title": job.title,
                        "organization": job.organization,
                        "location": job.location,
                        "url": job.url,
                        "score": score_info["total_score"],
                    })

            await session.commit()

            # Send email alert if there are new high matches
            if send_alerts and new_high_matches:
                user_result = await session.execute(
                    select(User).where(User.id == profile.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    new_high_matches.sort(key=lambda x: x["score"], reverse=True)
                    try:
                        send_job_alert(user.email, new_high_matches)
                        print(f"[scheduler] Sent alert to {user.email}: {len(new_high_matches)} new matches")
                    except Exception as e:
                        print(f"[scheduler] Failed to send alert to {user.email}: {e}")

    print(f"[scheduler] Recomputed matches for {len(profiles)} profiles against {len(active_jobs)} jobs")


async def recompute_user_matches(user_id: str):
    """Recompute matches for a single user."""
    async with async_session() as session:
        profile_result = await session.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return

        profile_dict = {
            "skills": profile.skills or [],
            "experience_keywords": profile.experience_keywords or [],
            "certifications": profile.certifications or [],
            "education": profile.education or {},
            "target_companies": profile.target_companies or [],
            "languages": profile.languages or [],
            "years_experience": profile.years_experience or 0,
        }

        jobs_result = await session.execute(select(Job).where(Job.is_active == True))
        active_jobs = jobs_result.scalars().all()

        await session.execute(
            delete(MatchResult).where(MatchResult.user_id == user_id)
        )

        for job in active_jobs:
            job_dict = {
                "title": job.title,
                "description": job.description,
                "qualifications": job.qualifications,
                "organization": job.organization,
                "department": job.department,
            }
            score_info = score_job(job_dict, profile_dict)
            match = MatchResult(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_id=job.id,
                total_score=score_info["total_score"],
                breakdown=score_info["breakdown"],
                matched_skills=score_info["matched_skills"],
                matched_keywords=score_info["matched_keywords"],
                computed_at=datetime.utcnow(),
            )
            session.add(match)

        await session.commit()
