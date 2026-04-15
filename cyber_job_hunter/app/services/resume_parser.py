"""Resume parser: extracts structured profile data from PDF/DOCX files using local LLM."""

import io
import json
import re
from pathlib import Path

import requests


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
        return {"skills": [], "certifications": [], "education": {}, "experience_keywords": []}

    # Try LLM first, fall back to regex
    try:
        result = _parse_with_llm(text)
        if result and result.get("skills"):
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
    # Truncate very long resumes to stay within context
    if len(text) > 6000:
        text = text[:6000]

    prompt = f"""Extract the following from this resume and return ONLY valid JSON, no other text:

{{
  "skills": ["list of technical skills, tools, platforms"],
  "certifications": ["list of certifications"],
  "education": {{"degree": "degree type", "major": "field of study", "minor": "minor if any", "school": "school name"}},
  "experience_keywords": ["list of key experience areas like incident response, threat detection, etc"]
}}

Resume text:
---
{text}
---

Return ONLY the JSON object, nothing else."""

    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2:3b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2000},
        },
        timeout=60,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "")

    # Extract JSON from response (LLM might wrap it in markdown)
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        raise ValueError("No JSON found in LLM response")

    data = json.loads(json_match.group())

    # Validate and clean
    result = {
        "skills": _ensure_list(data.get("skills", [])),
        "certifications": _ensure_list(data.get("certifications", [])),
        "education": data.get("education", {}),
        "experience_keywords": _ensure_list(data.get("experience_keywords", [])),
    }

    # Validate education is a dict
    if not isinstance(result["education"], dict):
        result["education"] = {}

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

    # Load skills master list
    skills_path = Path(__file__).resolve().parent.parent.parent / "data" / "skills_master.json"
    all_skills = []
    if skills_path.exists():
        with open(skills_path) as f:
            all_skills = json.load(f)

    matched_skills = [s for s in all_skills if s.lower() in text_lower]

    # Certifications
    cert_patterns = {
        "CompTIA Security+": [r"security\+", r"sec\+", r"comptia security"],
        "CISSP": [r"cissp"],
        "CEH": [r"\bceh\b", r"certified ethical hacker"],
        "OSCP": [r"\boscp\b", r"offensive security certified"],
        "GIAC": [r"\bgiac\b"],
        "CCNA": [r"\bccna\b"],
    }
    matched_certs = []
    for cert, patterns in cert_patterns.items():
        for p in patterns:
            if re.search(p, text_lower):
                matched_certs.append(cert)
                break

    # Education
    education = {}
    degree_patterns = [
        (r"(bachelor|b\.?s\.?|b\.?a\.?)\s*(of\s+)?(science|arts)?\s*(in\s+)?([a-z\s,&]+)", "Bachelor"),
        (r"(master|m\.?s\.?|m\.?a\.?)\s*(of\s+)?(science|arts)?\s*(in\s+)?([a-z\s,&]+)", "Master"),
    ]
    for pattern, degree_type in degree_patterns:
        match = re.search(pattern, text_lower)
        if match:
            major = match.group(5).strip() if match.group(5) else ""
            major = re.sub(r"\s+", " ", major).strip(", ")[:50]
            education = {"degree": degree_type, "major": major.title(), "minor": "", "school": ""}
            break

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
        "experience_keywords": matched_keywords,
    }
