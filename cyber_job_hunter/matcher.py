"""
Resume-to-job matching engine.

Scores each job listing against the resume profile based on:
  - Skill keyword matches
  - Experience keyword matches
  - Certification mentions
  - Education/degree relevance
  - Agency/company preference match
"""

import re


def _normalize(text):
    """Lowercase and strip extra whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _count_matches(needles, haystack):
    """Count how many needle strings appear in the haystack text."""
    haystack_lower = haystack.lower()
    return sum(1 for needle in needles if needle.lower() in haystack_lower)


def score_job(job, resume):
    """
    Score a job listing against a resume profile.

    Returns a dict with:
      - total_score: weighted composite score (0-100)
      - breakdown: per-category scores
      - matched_skills: list of skills that matched
      - matched_keywords: list of experience keywords that matched
    """
    # Combine all searchable text from the job
    fields = []
    for key in ("title", "description", "qualifications", "organization", "department"):
        val = job.get(key, "")
        if isinstance(val, list):
            val = " ".join(str(v) for v in val)
        fields.append(str(val))
    job_text = " ".join(fields)
    job_text_lower = _normalize(job_text)

    # --- Skill matches (weight: 35%) ---
    skills = resume.get("skills", [])
    matched_skills = [s for s in skills if s.lower() in job_text_lower]
    skill_score = min(len(matched_skills) / max(len(skills) * 0.15, 1), 1.0) * 100

    # --- Experience keyword matches (weight: 25%) ---
    exp_keywords = resume.get("experience_keywords", [])
    matched_keywords = [k for k in exp_keywords if k.lower() in job_text_lower]
    keyword_score = min(len(matched_keywords) / max(len(exp_keywords) * 0.12, 1), 1.0) * 100

    # --- Certification matches (weight: 15%) ---
    certs = resume.get("certifications", [])
    cert_aliases = {
        "CompTIA Security+": ["security+", "sec+", "comptia", "certification"],
        "Belkasoft IOS Forensics": ["belkasoft", "ios forensics", "mobile forensics", "forensic cert"],
        "Tines Core Certification": ["tines", "soar", "automation"],
        "Tines Advanced Certification": ["tines", "soar", "orchestration", "automation"],
    }
    matched_certs = 0
    for cert in certs:
        aliases = cert_aliases.get(cert, [cert.lower()])
        if any(alias.lower() in job_text_lower for alias in aliases):
            matched_certs += 1
    # Any cert match is a strong signal; 1 match = 70%, 2+ = 100%
    cert_score = min(matched_certs / max(len(certs), 1), 1.0) * 100
    if matched_certs == 0:
        # Give base score if job mentions certs generically
        generic_cert_terms = ["certification", "certified", "clearance"]
        if any(t in job_text_lower for t in generic_cert_terms):
            cert_score = 30

    # --- Education relevance (weight: 10%) ---
    edu_terms = [
        resume["education"]["major"].lower(),
        resume["education"]["minor"].lower(),
        "bachelor",
        "b.s.",
        "bs",
        "degree",
        "computer science",
        "information technology",
        "information security",
    ]
    edu_matches = _count_matches(edu_terms, job_text)
    edu_score = min(edu_matches / 2, 1.0) * 100

    # --- Target org preference (weight: 10%) ---
    org_name = _normalize(job.get("organization", ""))
    dept_name = _normalize(job.get("department", ""))
    target_fed = [a.lower() for a in resume.get("target_federal_agencies", [])]
    target_priv = [c.lower() for c in resume.get("target_private_companies", [])]
    org_match = any(t in org_name or t in dept_name for t in target_fed + target_priv)
    org_score = 100 if org_match else 50  # non-target orgs still get decent base

    # --- Bilingual bonus (weight: 5%) ---
    lang_terms = ["russian", "bilingual", "foreign language", "language"]
    lang_matches = _count_matches(lang_terms, job_text)
    lang_score = min(lang_matches, 1) * 100

    # --- Weighted total ---
    total = (
        skill_score * 0.35
        + keyword_score * 0.25
        + cert_score * 0.15
        + edu_score * 0.10
        + org_score * 0.10
        + lang_score * 0.05
    )

    return {
        "total_score": round(total, 1),
        "breakdown": {
            "skills": round(skill_score, 1),
            "experience_keywords": round(keyword_score, 1),
            "certifications": round(cert_score, 1),
            "education": round(edu_score, 1),
            "target_org": round(org_score, 1),
            "language_bonus": round(lang_score, 1),
        },
        "matched_skills": matched_skills,
        "matched_keywords": matched_keywords,
    }


def rank_jobs(jobs, resume):
    """
    Score and rank a list of jobs against a resume.

    Returns list of (job, score_info) tuples sorted by total_score descending.
    """
    scored = []
    for job in jobs:
        score_info = score_job(job, resume)
        scored.append((job, score_info))

    scored.sort(key=lambda x: x[1]["total_score"], reverse=True)
    return scored
