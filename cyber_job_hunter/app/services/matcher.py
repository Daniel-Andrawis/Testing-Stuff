"""
Resume-to-job matching engine.

Score = weighted sum of category scores, each 0-100:

  Category             Weight   How it's calculated
  ─────────────────────────────────────────────────────────────
  Skill Match          40%      (matched / total_your_skills) * 100, scaled by relevance
  Experience Keywords  25%      (matched / total_your_keywords) * 100
  Certifications       15%      Exact + alias match against job text
  Education            10%      Degree level match + field relevance
  Target Org           5%       Binary: is this a company you're targeting?
  Language Bonus       5%       Binary: does the job mention your languages?

Each category uses a ratio of YOUR profile items found in the job text.
More matches = higher score. No free floors — if nothing matches, it's 0.
"""

import re


def _normalize(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def score_job(job: dict, profile: dict) -> dict:
    """Score a job against a user profile. Returns score 0-100 with breakdown."""

    # Combine all searchable job text
    fields = []
    for key in ("title", "description", "qualifications", "organization", "department"):
        val = job.get(key, "")
        if isinstance(val, list):
            val = " ".join(str(v) for v in val)
        fields.append(str(val))
    job_text = " ".join(fields)
    job_lower = _normalize(job_text)

    # ── Skills (40%) ──
    # What % of your skills appear in this job?
    skills = profile.get("skills", [])
    matched_skills = [s for s in skills if s.lower() in job_lower]
    if skills:
        skill_ratio = len(matched_skills) / len(skills)
        # Scale: 0 matches = 0, matching 30%+ of your skills = 100
        skill_score = min(skill_ratio / 0.30, 1.0) * 100
    else:
        skill_score = 0

    # ── Experience Keywords (25%) ──
    # What % of your experience keywords appear?
    exp_keywords = profile.get("experience_keywords", [])
    matched_keywords = [k for k in exp_keywords if k.lower() in job_lower]
    if exp_keywords:
        kw_ratio = len(matched_keywords) / len(exp_keywords)
        # Scale: matching 25%+ of keywords = 100
        keyword_score = min(kw_ratio / 0.25, 1.0) * 100
    else:
        keyword_score = 0

    # ── Certifications (15%) ──
    # Check each cert with aliases for fuzzy matching
    certs = profile.get("certifications", [])
    cert_aliases = {
        "CompTIA Security+": ["security+", "sec+", "comptia"],
        "Belkasoft IOS Forensics": ["belkasoft", "ios forensics", "mobile forensics"],
        "Tines Core Certification": ["tines", "soar", "automation"],
        "Tines Advanced Certification": ["tines", "soar", "orchestration"],
        "CISSP": ["cissp", "certified information systems security"],
        "CEH": ["ceh", "certified ethical hacker"],
        "OSCP": ["oscp", "offensive security"],
        "GIAC": ["giac", "sans"],
        "GCIH": ["gcih"],
        "CCNA": ["ccna", "cisco certified"],
    }
    matched_certs = 0
    for cert in certs:
        aliases = cert_aliases.get(cert, [cert.lower()])
        if any(a in job_lower for a in aliases):
            matched_certs += 1
    if certs:
        cert_score = (matched_certs / len(certs)) * 100
    else:
        cert_score = 0

    # ── Education (10%) ──
    # Does the job mention your degree field?
    edu = profile.get("education", {})
    edu_score = 0
    edu_terms = []
    if edu.get("major"):
        edu_terms.append(edu["major"].lower())
    if edu.get("minor"):
        edu_terms.append(edu["minor"].lower())

    # Check if job mentions your field
    field_match = any(t in job_lower for t in edu_terms if t)

    # Check degree level
    degree_terms = ["bachelor", "b.s.", "master", "m.s.", "degree", "bs", "ms"]
    degree_match = any(t in job_lower for t in degree_terms)

    # Related field terms
    related_fields = ["computer science", "information technology", "information security",
                      "cybersecurity", "information systems"]
    related_match = any(t in job_lower for t in related_fields)

    if field_match and degree_match:
        edu_score = 100
    elif field_match or (degree_match and related_match):
        edu_score = 70
    elif degree_match or related_match:
        edu_score = 40
    # else 0

    # ── Target Organization (5%) ──
    org_name = _normalize(job.get("organization", ""))
    dept_name = _normalize(job.get("department", ""))
    targets = [c.lower() for c in profile.get("target_companies", [])]
    org_match = any(t in org_name or t in dept_name for t in targets) if targets else False
    org_score = 100 if org_match else 0

    # ── Language Bonus (5%) ──
    languages = profile.get("languages", [])
    lang_terms = [l.lower() for l in languages if l.lower() != "english"]
    lang_terms += ["bilingual", "foreign language"]
    lang_match = any(t in job_lower for t in lang_terms)
    lang_score = 100 if lang_match else 0

    # ── Weighted Total ──
    total = (
        skill_score * 0.40
        + keyword_score * 0.25
        + cert_score * 0.15
        + edu_score * 0.10
        + org_score * 0.05
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
    from pathlib import Path
    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    try:
        with open(skills_path) as f:
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
