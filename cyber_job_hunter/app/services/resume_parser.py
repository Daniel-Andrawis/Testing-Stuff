"""Resume parser: extracts structured profile data from PDF/DOCX files."""

import io
import json
import re
from pathlib import Path


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """
    Parse a resume file and extract structured profile data.

    Returns dict with: skills, certifications, education, experience_keywords
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        text = _extract_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        text = _extract_docx(file_bytes)
    else:
        text = file_bytes.decode("utf-8", errors="ignore")

    return _extract_profile(text)


def _extract_pdf(file_bytes: bytes) -> str:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def _extract_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_profile(text: str) -> dict:
    text_lower = text.lower()

    # Load skills master list
    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    all_skills = []
    if skills_path.exists():
        with open(skills_path) as f:
            all_skills = json.load(f)

    # Match skills
    matched_skills = [s for s in all_skills if s.lower() in text_lower]

    # Match certifications
    cert_patterns = {
        "CompTIA Security+": [r"security\+", r"sec\+", r"comptia security"],
        "CISSP": [r"cissp"],
        "CEH": [r"\bceh\b", r"certified ethical hacker"],
        "OSCP": [r"\boscp\b", r"offensive security certified"],
        "GIAC": [r"\bgiac\b"],
        "GCIH": [r"\bgcih\b"],
        "GPEN": [r"\bgpen\b"],
        "CompTIA Network+": [r"network\+", r"comptia network"],
        "CompTIA A+": [r"comptia a\+", r"\ba\+\b"],
        "CCNA": [r"\bccna\b"],
        "AWS Security Specialty": [r"aws.*security.*specialty"],
        "Azure Security Engineer": [r"azure.*security.*engineer"],
    }
    matched_certs = []
    for cert, patterns in cert_patterns.items():
        for p in patterns:
            if re.search(p, text_lower):
                matched_certs.append(cert)
                break

    # Also find certs mentioned literally
    for line in text.split("\n"):
        line_stripped = line.strip()
        if any(kw in line_stripped.lower() for kw in ["certification", "certified", "belkasoft", "tines"]):
            if len(line_stripped) < 100 and line_stripped not in matched_certs:
                matched_certs.append(line_stripped)

    # Extract education
    education = {}
    degree_patterns = [
        (r"(bachelor|b\.?s\.?|b\.?a\.?)\s*(of\s+)?(science|arts)?\s*(in\s+)?([a-z\s,&]+)", "Bachelor"),
        (r"(master|m\.?s\.?|m\.?a\.?)\s*(of\s+)?(science|arts)?\s*(in\s+)?([a-z\s,&]+)", "Master"),
        (r"(associate|a\.?s\.?|a\.?a\.?)\s*(of\s+)?(science|arts)?\s*(in\s+)?([a-z\s,&]+)", "Associate"),
    ]
    for pattern, degree_type in degree_patterns:
        match = re.search(pattern, text_lower)
        if match:
            major = match.group(5).strip() if match.group(5) else ""
            major = re.sub(r"\s+", " ", major).strip(", ")
            if len(major) > 50:
                major = major[:50]
            education = {"degree": degree_type, "major": major.title(), "minor": "", "school": ""}
            break

    # Experience keywords
    exp_keywords_master = [
        "threat detection", "security operations", "incident response",
        "SIEM", "EDR", "endpoint detection", "playbook", "automation",
        "triage", "alert", "compliance", "vulnerability", "forensics",
        "malware analysis", "threat intelligence", "penetration testing",
        "red team", "blue team", "OSINT", "detection engineering",
        "log analysis", "network security", "intrusion detection",
        "risk assessment", "security audit", "GRC", "governance",
        "cloud security", "application security", "identity management",
    ]
    matched_keywords = [k for k in exp_keywords_master if k.lower() in text_lower]

    return {
        "skills": matched_skills,
        "certifications": matched_certs,
        "education": education,
        "experience_keywords": matched_keywords,
    }
