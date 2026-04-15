"""Resume parser: extracts structured profile data from PDF/DOCX files using local LLM."""

import io
import json
import re
from pathlib import Path

import requests

OLLAMA_MODEL = "qwen2.5:0.5b"
OLLAMA_URL = "http://localhost:11434/api/generate"


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """Parse a resume file and extract structured profile data."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        text = _extract_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        text = _extract_docx(file_bytes)
    else:
        text = file_bytes.decode("utf-8", errors="ignore")

    if not text.strip():
        return {"skills": [], "certifications": [], "education": {}, "experience_keywords": [], "work_history": []}

    try:
        result = _parse_with_llm(text)
        if result and (result.get("skills") or result.get("work_history")):
            return result
    except Exception as e:
        print(f"[resume_parser] LLM parse failed, falling back to regex: {e}")

    return _parse_with_regex(text)


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


def _parse_with_llm(text: str) -> dict:
    """Use local Ollama LLM to extract structured resume data."""
    if len(text) > 8000:
        text = text[:8000]

    prompt = f"""Parse this resume into JSON. Return ONLY valid JSON.

RULES:
- education.degree = ONLY "Bachelor of Science" or "Master of Arts" etc
- education.major = ONLY the field like "Digital Forensics"
- education.minor = ONLY the minor like "Cyber Security"
- education.school = ONLY the school like "University at Albany"
- DO NOT put city, state, honors, or dates in education fields
- work_history = list of EVERY job. Include title, company, duration, description
- skills = all technical skills and tools
- certifications = formal cert names

JSON format:
{{"skills":[],"certifications":[],"education":{{"degree":"","major":"","minor":"","school":""}},"work_history":[{{"title":"","company":"","duration":"","description":""}}],"experience_keywords":[]}}

Resume:
{text}

JSON:"""

    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 3000},
        },
        timeout=120,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "")
    print(f"[resume_parser] LLM raw response ({len(raw)} chars): {raw[:500]}")

    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        raise ValueError("No JSON found in LLM response")

    data = json.loads(json_match.group())

    result = {
        "skills": _ensure_list(data.get("skills", [])),
        "certifications": _ensure_list(data.get("certifications", [])),
        "education": data.get("education", {}),
        "work_history": data.get("work_history", []),
        "experience_keywords": _ensure_list(data.get("experience_keywords", [])),
    }

    if not isinstance(result["education"], dict):
        result["education"] = {}
    if not isinstance(result["work_history"], list):
        result["work_history"] = []

    return result


def _ensure_list(val) -> list:
    if isinstance(val, list):
        return [str(v).strip() for v in val if v]
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    return []


def _parse_with_regex(text: str) -> dict:
    """Fallback: regex-based extraction."""
    text_lower = text.lower()
    lines = text.split("\n")

    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    all_skills = []
    if skills_path.exists():
        with open(skills_path) as f:
            all_skills = json.load(f)

    matched_skills = [s for s in all_skills if s.lower() in text_lower]

    # Certifications
    cert_patterns = {
        "CompTIA Security+": [r"security\+", r"sec\+", r"comptia security"],
        "Belkasoft IOS Forensics": [r"belkasoft"],
        "Tines Core Certification": [r"tines core"],
        "Tines Advanced Certification": [r"tines advanced"],
        "CISSP": [r"\bcissp\b"],
        "CEH": [r"\bceh\b", r"certified ethical hacker"],
        "OSCP": [r"\boscp\b"],
        "GIAC": [r"\bgiac\b"],
        "CCNA": [r"\bccna\b"],
    }
    matched_certs = []
    for cert, patterns in cert_patterns.items():
        for p in patterns:
            if re.search(p, text_lower):
                matched_certs.append(cert)
                break

    # Education — look for specific patterns
    education = {}
    # Try to find "Bachelor of Science in X" pattern first
    edu_match = re.search(
        r'(bachelor|master|associate)\s+of\s+(science|arts)\s+(?:in\s+)?([a-zA-Z\s&]+?)(?:\s*[,\|]\s*|\s*$|\s+minor|\s+university|\s+college|\n)',
        text, re.IGNORECASE
    )
    if edu_match:
        degree = f"{edu_match.group(1).title()} of {edu_match.group(2).title()}"
        major = edu_match.group(3).strip().rstrip(",. ")
        education["degree"] = degree
        education["major"] = major

    # Minor
    minor_match = re.search(r'minor\s*(?:in|:)\s*([a-zA-Z\s&]+?)(?:\s*[,\|]\s*|\s*$|\n)', text, re.IGNORECASE)
    if minor_match:
        education["minor"] = minor_match.group(1).strip().rstrip(",. ")

    # School
    school_patterns = [
        r'(university\s+(?:of|at)\s+[a-zA-Z\s,]+?)(?:\s*[|\n]|\s+bachelor|\s+master|\s+magna|\s+cum|\s+summa|\s+\d{4})',
        r'([A-Z][a-zA-Z\s]+ (?:University|College|Institute|School)[a-zA-Z\s,]*?)(?:\s*[|\n]|\s+\d{4})',
    ]
    for sp in school_patterns:
        school_match = re.search(sp, text, re.IGNORECASE)
        if school_match:
            education["school"] = school_match.group(1).strip().rstrip(",. ")
            break

    # Work history — look for job-like patterns
    work_history = []
    # Common patterns: "Title | Company" or "Title, Company" or "Title at Company"
    # Also look for date ranges like "Jun 2024 - Present" or "2023 - 2024"
    job_pattern = re.compile(
        r'^(.+?)\s*[|,–—]\s*(.+?)$',
        re.MULTILINE
    )
    date_pattern = re.compile(
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|'
        r'\d{1,2}/\d{4}|\d{4})\s*[-–—]\s*'
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|'
        r'\d{1,2}/\d{4}|\d{4}|[Pp]resent|[Cc]urrent)',
        re.IGNORECASE
    )

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        date_match = date_pattern.search(line)

        # Check if this line or the next has a date range (indicates a job entry)
        if date_match or (i + 1 < len(lines) and date_pattern.search(lines[i + 1].strip())):
            duration = ""
            title = ""
            company = ""

            if date_match:
                duration = date_match.group(0)
                # Title is the part before the date or on the line above
                before_date = line[:date_match.start()].strip().rstrip("|,–— ")
                if before_date:
                    parts = re.split(r'\s*[|–—]\s*', before_date, maxsplit=1)
                    title = parts[0].strip()
                    company = parts[1].strip() if len(parts) > 1 else ""
                elif i > 0:
                    prev = lines[i - 1].strip()
                    if prev and len(prev) < 100:
                        parts = re.split(r'\s*[|–—]\s*', prev, maxsplit=1)
                        title = parts[0].strip()
                        company = parts[1].strip() if len(parts) > 1 else ""
            elif i + 1 < len(lines):
                next_date = date_pattern.search(lines[i + 1].strip())
                if next_date:
                    duration = next_date.group(0)
                    parts = re.split(r'\s*[|–—]\s*', line, maxsplit=1)
                    title = parts[0].strip()
                    company = parts[1].strip() if len(parts) > 1 else ""
                    i += 1

            # Collect description from following lines
            desc_lines = []
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if not l or date_pattern.search(l) or (len(l) < 80 and re.match(r'^[A-Z]', l) and '|' in l):
                    break
                if l.startswith(('-', '•', '·', '○', '▪')):
                    desc_lines.append(l.lstrip('-•·○▪ '))
                elif len(l) > 20:
                    desc_lines.append(l)
                i += 1

            if title and len(title) < 80:
                work_history.append({
                    "title": title,
                    "company": company,
                    "duration": duration,
                    "description": "; ".join(desc_lines[:3]),
                })
            continue
        i += 1

    # Experience keywords
    exp_master = [
        "threat detection", "security operations", "incident response",
        "SIEM", "EDR", "playbook", "automation", "compliance",
        "vulnerability", "forensics", "malware analysis",
        "threat intelligence", "penetration testing", "red team",
        "blue team", "OSINT", "detection engineering", "log analysis",
        "network security", "risk assessment", "GRC",
    ]
    matched_keywords = [k for k in exp_master if k.lower() in text_lower]

    return {
        "skills": matched_skills,
        "certifications": matched_certs,
        "education": education,
        "work_history": work_history,
        "experience_keywords": matched_keywords,
    }
