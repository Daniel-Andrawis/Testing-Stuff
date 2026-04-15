"""Resume-to-job matching engine adapted for web app use."""

import re


def _normalize(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def _count_matches(needles, haystack):
    haystack_lower = haystack.lower()
    return sum(1 for n in needles if n.lower() in haystack_lower)


def score_job(job: dict, profile: dict) -> dict:
    """
    Score a job dict against a user profile dict.

    Profile expected keys: skills, experience_keywords, certifications,
    education, target_companies, languages, years_experience
    """
    fields = []
    for key in ("title", "description", "qualifications", "organization", "department"):
        val = job.get(key, "")
        if isinstance(val, list):
            val = " ".join(str(v) for v in val)
        fields.append(str(val))
    job_text = " ".join(fields)
    job_text_lower = _normalize(job_text)

    # --- Skill matches (35%) ---
    skills = profile.get("skills", [])
    matched_skills = [s for s in skills if s.lower() in job_text_lower]
    skill_score = min(len(matched_skills) / max(len(skills) * 0.15, 1), 1.0) * 100

    # --- Experience keyword matches (25%) ---
    exp_keywords = profile.get("experience_keywords", [])
    matched_keywords = [k for k in exp_keywords if k.lower() in job_text_lower]
    keyword_score = min(len(matched_keywords) / max(len(exp_keywords) * 0.12, 1), 1.0) * 100

    # --- Certification matches (15%) ---
    certs = profile.get("certifications", [])
    cert_aliases = {
        "CompTIA Security+": ["security+", "sec+", "comptia", "certification"],
        "CISSP": ["cissp", "certified information systems"],
        "CEH": ["ceh", "certified ethical hacker"],
        "OSCP": ["oscp", "offensive security"],
        "GIAC": ["giac", "sans"],
    }
    matched_certs = 0
    for cert in certs:
        aliases = cert_aliases.get(cert, [cert.lower()])
        if any(a.lower() in job_text_lower for a in aliases):
            matched_certs += 1
    cert_score = min(matched_certs / max(len(certs), 1), 1.0) * 100
    if matched_certs == 0:
        generic = ["certification", "certified", "clearance"]
        if any(t in job_text_lower for t in generic):
            cert_score = 30

    # --- Education (10%) ---
    edu = profile.get("education", {})
    edu_terms = [
        edu.get("major", "").lower(),
        edu.get("minor", "").lower(),
        "bachelor", "b.s.", "bs", "degree",
        "computer science", "information technology", "information security",
    ]
    edu_terms = [t for t in edu_terms if t]
    edu_matches = _count_matches(edu_terms, job_text)
    edu_score = min(edu_matches / 2, 1.0) * 100

    # --- Target org (10%) ---
    org_name = _normalize(job.get("organization", ""))
    dept_name = _normalize(job.get("department", ""))
    targets = [c.lower() for c in profile.get("target_companies", [])]
    org_match = any(t in org_name or t in dept_name for t in targets)
    org_score = 100 if org_match else 50

    # --- Language bonus (5%) ---
    languages = profile.get("languages", [])
    lang_terms = [l.lower() for l in languages] + ["bilingual", "foreign language"]
    lang_matches = _count_matches(lang_terms, job_text)
    lang_score = min(lang_matches, 1) * 100

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


def compute_skill_gaps(jobs: list[dict], profile_skills: list[str], top_n: int = 10) -> list[str]:
    """Find skills frequently in jobs but missing from the user's profile."""
    import json
    skill_master_path = "data/skills_master.json"
    try:
        with open(skill_master_path) as f:
            all_skills = json.load(f)
    except FileNotFoundError:
        return []

    profile_lower = {s.lower() for s in profile_skills}
    counts = {}

    for job in jobs:
        text = " ".join([
            job.get("title", ""), job.get("description", ""),
            job.get("qualifications", ""),
        ]).lower()
        for skill in all_skills:
            if skill.lower() in text and skill.lower() not in profile_lower:
                counts[skill] = counts.get(skill, 0) + 1

    sorted_gaps = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [s for s, _ in sorted_gaps[:top_n]]
