"""
USAJobs.gov API client for searching federal cybersecurity positions.

To use this module you need a free API key from:
  https://developer.usajobs.gov/APIRequest/Index

Set your credentials in a .env file:
  USAJOBS_API_KEY=your_api_key_here
  USAJOBS_EMAIL=your_email@example.com
"""

import os
import time
import requests

USAJOBS_BASE_URL = "https://data.usajobs.gov/api/Search"

# OPM job series codes relevant to cybersecurity
CYBER_SERIES = [
    "2210",  # Information Technology Management
    "0132",  # Intelligence
    "1550",  # Computer Science
    "0855",  # Electronics Engineering
    "1071",  # Audiovisual Production (forensics overlap)
    "0080",  # Security Administration
    "1801",  # General Inspection, Investigation, Enforcement
    "1811",  # Criminal Investigation
    "0301",  # Miscellaneous Administration (often used for cyber roles)
]

CYBER_KEYWORDS = [
    "cybersecurity",
    "cyber security",
    "information security",
    "digital forensics",
    "incident response",
    "threat intelligence",
    "penetration testing",
    "security operations",
    "SOC analyst",
    "DFIR",
    "vulnerability",
    "malware analyst",
    "security engineer",
    "detection engineer",
    "CISO",
    "red team",
    "blue team",
    "forensic examiner",
    "network defense",
]


def _get_headers():
    """Build auth headers for USAJobs API."""
    api_key = os.getenv("USAJOBS_API_KEY", "")
    email = os.getenv("USAJOBS_EMAIL", "")
    if not api_key or not email:
        return None
    return {
        "Authorization-Key": api_key,
        "User-Agent": email,
        "Host": "data.usajobs.gov",
    }


def search_usajobs(keyword, agency_name=None, results_per_page=25, page=1):
    """
    Search USAJobs API for positions matching a keyword.

    Args:
        keyword: Search term (e.g. 'cybersecurity')
        agency_name: Optional agency filter (e.g. 'National Aeronautics and Space Administration')
        results_per_page: Number of results per page (max 500)
        page: Page number

    Returns:
        List of job dicts or empty list on error.
    """
    headers = _get_headers()
    if not headers:
        print("[!] USAJobs API credentials not set. Add USAJOBS_API_KEY and USAJOBS_EMAIL to .env")
        return []

    params = {
        "Keyword": keyword,
        "ResultsPerPage": results_per_page,
        "Page": page,
    }
    if agency_name:
        params["AgencyName"] = agency_name

    try:
        resp = requests.get(USAJOBS_BASE_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("SearchResult", {}).get("SearchResultItems", [])
        return [_parse_job(item) for item in results]
    except requests.RequestException as e:
        print(f"[!] USAJobs API error: {e}")
        return []


def _parse_job(item):
    """Extract relevant fields from a USAJobs search result item."""
    match = item.get("MatchedObjectDescriptor", {})
    position = match.get("PositionLocation", [{}])
    location = position[0].get("LocationName", "N/A") if position else "N/A"

    pay = match.get("PositionRemuneration", [{}])
    salary_min = pay[0].get("MinimumRange", "N/A") if pay else "N/A"
    salary_max = pay[0].get("MaximumRange", "N/A") if pay else "N/A"

    return {
        "source": "USAJobs",
        "title": match.get("PositionTitle", "N/A"),
        "organization": match.get("OrganizationName", "N/A"),
        "department": match.get("DepartmentName", "N/A"),
        "location": location,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "grade": match.get("JobGrade", [{}])[0].get("Code", "N/A") if match.get("JobGrade") else "N/A",
        "url": match.get("PositionURI", "N/A"),
        "description": match.get("UserArea", {}).get("Details", {}).get("MajorDuties", [""])[0] if match.get("UserArea") else "",
        "qualifications": match.get("QualificationSummary", ""),
        "open_date": match.get("PositionStartDate", "N/A"),
        "close_date": match.get("PositionEndDate", "N/A"),
    }


def fetch_all_cyber_jobs(target_agencies=None):
    """
    Search USAJobs for cybersecurity positions across target agencies.

    Args:
        target_agencies: List of agency names to search. If None, searches all agencies.

    Returns:
        List of unique job dicts.
    """
    all_jobs = {}
    headers = _get_headers()
    if not headers:
        print("[!] USAJobs API credentials not set. Skipping federal job search.")
        print("    Get a free API key at: https://developer.usajobs.gov/APIRequest/Index")
        print("    Then add to your .env file:")
        print("      USAJOBS_API_KEY=your_key")
        print("      USAJOBS_EMAIL=your_email")
        return []

    keywords_to_search = CYBER_KEYWORDS[:8]  # top keywords to avoid rate limiting

    for keyword in keywords_to_search:
        if target_agencies:
            for agency in target_agencies:
                jobs = search_usajobs(keyword, agency_name=agency)
                for job in jobs:
                    key = job["url"]
                    if key not in all_jobs:
                        all_jobs[key] = job
                time.sleep(0.5)  # respect rate limits
        else:
            jobs = search_usajobs(keyword)
            for job in jobs:
                key = job["url"]
                if key not in all_jobs:
                    all_jobs[key] = job
            time.sleep(0.5)

    print(f"[+] Found {len(all_jobs)} unique federal jobs from USAJobs")
    return list(all_jobs.values())
