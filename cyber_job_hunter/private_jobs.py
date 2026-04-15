"""
Private sector job search using web scraping and job board APIs.

Searches multiple sources for cybersecurity positions at private companies.
"""

import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

# Common cybersecurity job titles to search for
CYBER_TITLES = [
    "Cybersecurity Analyst",
    "Security Engineer",
    "SOC Analyst",
    "Incident Response Analyst",
    "Digital Forensics Analyst",
    "Threat Intelligence Analyst",
    "Penetration Tester",
    "Detection Engineer",
    "Security Operations",
    "DFIR Analyst",
    "Vulnerability Analyst",
    "Red Team Operator",
    "Blue Team Analyst",
    "Malware Analyst",
    "Security Consultant",
    "GRC Analyst",
    "Forensic Examiner",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _build_session():
    """Create a requests session with standard headers."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


# ---------------------------------------------------------------------------
# Indeed RSS feed scraper (no API key needed)
# ---------------------------------------------------------------------------

def search_indeed(query="cybersecurity", location="United States", limit=50):
    """
    Search Indeed via their RSS feed for job listings.

    Args:
        query: Job search query
        location: Location filter
        limit: Max results to return

    Returns:
        List of job dicts.
    """
    jobs = []
    encoded_query = urllib.parse.quote_plus(query)
    encoded_location = urllib.parse.quote_plus(location)
    url = (
        f"https://www.indeed.com/rss"
        f"?q={encoded_query}&l={encoded_location}&sort=date&limit={limit}"
    )

    session = _build_session()
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.find_all("item"):
            title = item.find("title")
            link = item.find("link")
            description = item.find("description")
            pub_date = item.find("pubdate")
            source_tag = item.find("source")

            jobs.append({
                "source": "Indeed",
                "title": title.text.strip() if title else "N/A",
                "organization": source_tag.text.strip() if source_tag else "N/A",
                "department": "",
                "location": location,
                "salary_min": "N/A",
                "salary_max": "N/A",
                "grade": "N/A",
                "url": link.text.strip() if link else "N/A",
                "description": _clean_html(description.text) if description else "",
                "qualifications": "",
                "open_date": pub_date.text.strip() if pub_date else "N/A",
                "close_date": "N/A",
            })
    except requests.RequestException as e:
        print(f"[!] Indeed search error: {e}")

    print(f"[+] Found {len(jobs)} jobs from Indeed for '{query}'")
    return jobs


def _clean_html(text):
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", " ", text).strip()


# ---------------------------------------------------------------------------
# RemoteOK API (free, no key needed - good for remote cyber jobs)
# ---------------------------------------------------------------------------

def search_remoteok():
    """
    Search RemoteOK for remote cybersecurity positions.

    Returns:
        List of job dicts.
    """
    jobs = []
    url = "https://remoteok.com/api"

    session = _build_session()
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # First item is metadata, skip it
        for item in data[1:]:
            tags = [t.lower() for t in item.get("tags", [])]
            title_lower = item.get("position", "").lower()
            company_lower = item.get("company", "").lower()

            # Filter for security-related roles
            security_terms = [
                "security", "cyber", "forensic", "soc", "incident",
                "threat", "pentest", "vulnerability", "malware",
                "dfir", "detection", "compliance", "grc",
            ]
            if not any(term in title_lower or term in " ".join(tags) or term in company_lower
                       for term in security_terms):
                continue

            salary_min = item.get("salary_min", "N/A")
            salary_max = item.get("salary_max", "N/A")

            jobs.append({
                "source": "RemoteOK",
                "title": item.get("position", "N/A"),
                "organization": item.get("company", "N/A"),
                "department": "",
                "location": "Remote",
                "salary_min": str(salary_min) if salary_min else "N/A",
                "salary_max": str(salary_max) if salary_max else "N/A",
                "grade": "N/A",
                "url": f"https://remoteok.com/l/{item.get('id', '')}",
                "description": _clean_html(item.get("description", "")),
                "qualifications": ", ".join(item.get("tags", [])),
                "open_date": item.get("date", "N/A"),
                "close_date": "N/A",
            })
    except requests.RequestException as e:
        print(f"[!] RemoteOK search error: {e}")

    print(f"[+] Found {len(jobs)} security jobs from RemoteOK")
    return jobs


# ---------------------------------------------------------------------------
# Jobicy API (free, no key needed - remote tech/security jobs)
# ---------------------------------------------------------------------------

def search_jobicy():
    """
    Search Jobicy for remote cybersecurity positions.

    Returns:
        List of job dicts.
    """
    jobs = []
    url = "https://jobicy.com/api/v2/remote-jobs?count=50&tag=security"

    session = _build_session()
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("jobs", []):
            title_lower = item.get("jobTitle", "").lower()

            # Keep security-related roles
            security_terms = [
                "security", "cyber", "forensic", "soc", "incident",
                "threat", "pentest", "vulnerability", "malware",
                "dfir", "detection", "compliance", "grc",
            ]
            if not any(term in title_lower for term in security_terms):
                continue

            salary_min = item.get("annualSalaryMin", "N/A")
            salary_max = item.get("annualSalaryMax", "N/A")

            jobs.append({
                "source": "Jobicy",
                "title": item.get("jobTitle", "N/A"),
                "organization": item.get("companyName", "N/A"),
                "department": "",
                "location": item.get("jobGeo", "Remote"),
                "salary_min": str(salary_min) if salary_min else "N/A",
                "salary_max": str(salary_max) if salary_max else "N/A",
                "grade": "N/A",
                "url": item.get("url", "N/A"),
                "description": _clean_html(item.get("jobDescription", "")),
                "qualifications": item.get("jobIndustry", ""),
                "open_date": item.get("pubDate", "N/A"),
                "close_date": "N/A",
            })
    except requests.RequestException as e:
        print(f"[!] Jobicy search error: {e}")

    print(f"[+] Found {len(jobs)} security jobs from Jobicy")
    return jobs


# ---------------------------------------------------------------------------
# The Muse API (free, no key needed - large US job database)
# ---------------------------------------------------------------------------

def search_themuse():
    """
    Search The Muse for cybersecurity positions.
    The Muse has 400k+ jobs but no keyword search, so we pull recent
    jobs and filter client-side for security roles.

    Returns:
        List of job dicts.
    """
    jobs = []

    security_terms = [
        "security", "cyber", "forensic", "soc ", "incident",
        "threat", "pentest", "vulnerability", "malware",
        "dfir", "detection", "grc",
    ]

    session = _build_session()
    # Check a few pages to find security roles
    for page in range(5):
        url = f"https://www.themuse.com/api/public/jobs?page={page}&descending=true"
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("results", []):
                name_lower = item.get("name", "").lower()
                if not any(term in name_lower for term in security_terms):
                    continue

                company = item.get("company", {})
                locations = ", ".join(
                    loc.get("name", "") for loc in item.get("locations", [])
                ) or "N/A"

                jobs.append({
                    "source": "TheMuse",
                    "title": item.get("name", "N/A"),
                    "organization": company.get("name", "N/A"),
                    "department": "",
                    "location": locations,
                    "salary_min": "N/A",
                    "salary_max": "N/A",
                    "grade": "N/A",
                    "url": f"https://www.themuse.com/jobs/{item.get('short_name', item.get('id', ''))}",
                    "description": _clean_html(item.get("contents", "")),
                    "qualifications": ", ".join(
                        cat.get("name", "") for cat in item.get("categories", [])
                    ),
                    "open_date": item.get("publication_date", "N/A"),
                    "close_date": "N/A",
                })
        except requests.RequestException as e:
            print(f"[!] TheMuse search error (page {page}): {e}")
            break

        time.sleep(0.5)

    print(f"[+] Found {len(jobs)} security jobs from TheMuse")
    return jobs


# ---------------------------------------------------------------------------
# Generate direct search URLs for boards that block scraping
# ---------------------------------------------------------------------------

def generate_search_urls(companies=None):
    """
    Generate direct job board search URLs for manual browsing.
    Useful for sites that block automated scraping (LinkedIn, Glassdoor, etc).

    Args:
        companies: Optional list of company names to include in searches.

    Returns:
        List of dicts with board name and URL.
    """
    base_query = "cybersecurity OR digital forensics OR security analyst OR incident response"
    encoded = urllib.parse.quote_plus(base_query)

    urls = [
        {
            "board": "LinkedIn",
            "url": f"https://www.linkedin.com/jobs/search/?keywords={encoded}&f_TPR=r604800",
        },
        {
            "board": "Glassdoor",
            "url": f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded}",
        },
        {
            "board": "CyberSecJobs",
            "url": "https://www.cybersecjobs.com/",
        },
        {
            "board": "ClearedJobs.Net (clearance required)",
            "url": "https://www.clearedjobs.net/search?q=cybersecurity",
        },
        {
            "board": "IntelligenceCareers.gov",
            "url": "https://www.intelligencecareers.gov/icjobs",
        },
    ]

    if companies:
        for company in companies[:10]:  # limit to avoid wall of links
            encoded_co = urllib.parse.quote_plus(f"cybersecurity {company}")
            urls.append({
                "board": f"LinkedIn - {company}",
                "url": f"https://www.linkedin.com/jobs/search/?keywords={encoded_co}",
            })

    return urls


def fetch_all_private_jobs(target_companies=None):
    """
    Aggregate private sector cybersecurity jobs from multiple sources.

    Args:
        target_companies: List of company names for targeted searches.

    Returns:
        Tuple of (list of job dicts, list of manual search URL dicts).
    """
    all_jobs = []

    # Indeed: search a few key titles
    for title in CYBER_TITLES[:5]:
        jobs = search_indeed(query=title, limit=25)
        all_jobs.extend(jobs)
        time.sleep(1)  # be respectful

    # RemoteOK
    remote_jobs = search_remoteok()
    all_jobs.extend(remote_jobs)

    # Jobicy
    jobicy_jobs = search_jobicy()
    all_jobs.extend(jobicy_jobs)

    # The Muse
    muse_jobs = search_themuse()
    all_jobs.extend(muse_jobs)

    # Deduplicate by URL
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique_jobs.append(job)

    # Generate manual search URLs for sites that block scraping
    search_urls = generate_search_urls(target_companies)

    print(f"[+] Total unique private sector jobs found: {len(unique_jobs)}")
    return unique_jobs, search_urls
