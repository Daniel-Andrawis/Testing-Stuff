import os
import time
import requests

from app.scrapers.base import BaseScraper

USAJOBS_BASE_URL = "https://data.usajobs.gov/api/Search"

CYBER_KEYWORDS = [
    "cybersecurity", "cyber security", "information security",
    "digital forensics", "incident response", "threat intelligence",
    "penetration testing", "security operations", "SOC analyst",
    "DFIR", "vulnerability", "malware analyst", "security engineer",
    "detection engineer", "red team", "blue team", "forensic examiner",
    "network defense",
]


class USAJobsScraper(BaseScraper):
    name = "USAJobs"
    source_id = "usajobs"

    def is_available(self) -> bool:
        return bool(os.getenv("USAJOBS_API_KEY")) and bool(os.getenv("USAJOBS_EMAIL"))

    def fetch_jobs(self) -> list[dict]:
        api_key = os.getenv("USAJOBS_API_KEY", "")
        email = os.getenv("USAJOBS_EMAIL", "")
        if not api_key or not email:
            print("[!] USAJobs: API credentials not set")
            return []

        headers = {
            "Authorization-Key": api_key,
            "User-Agent": email,
            "Host": "data.usajobs.gov",
        }

        all_jobs = {}
        for keyword in CYBER_KEYWORDS[:8]:
            try:
                resp = requests.get(
                    USAJOBS_BASE_URL,
                    headers=headers,
                    params={"Keyword": keyword, "ResultsPerPage": 25, "Page": 1},
                    timeout=30,
                )
                resp.raise_for_status()
                results = resp.json().get("SearchResult", {}).get("SearchResultItems", [])
                for item in results:
                    job = self._parse(item)
                    all_jobs[job["url"]] = job
            except requests.RequestException as e:
                print(f"[!] USAJobs error for '{keyword}': {e}")
            time.sleep(0.5)

        print(f"[+] USAJobs: {len(all_jobs)} jobs")
        return list(all_jobs.values())

    def _parse(self, item) -> dict:
        m = item.get("MatchedObjectDescriptor", {})
        pos = m.get("PositionLocation", [{}])
        location = pos[0].get("LocationName", "N/A") if pos else "N/A"
        pay = m.get("PositionRemuneration", [{}])
        salary_min = pay[0].get("MinimumRange", "N/A") if pay else "N/A"
        salary_max = pay[0].get("MaximumRange", "N/A") if pay else "N/A"
        grade = m.get("JobGrade", [{}])[0].get("Code", "N/A") if m.get("JobGrade") else "N/A"
        desc = ""
        if m.get("UserArea"):
            duties = m["UserArea"].get("Details", {}).get("MajorDuties", [""])
            desc = duties[0] if duties else ""

        return self.job_dict(
            source="USAJobs",
            title=m.get("PositionTitle", "N/A"),
            organization=m.get("OrganizationName", "N/A"),
            department=m.get("DepartmentName", "N/A"),
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            grade=grade,
            url=m.get("PositionURI", "N/A"),
            description=desc,
            qualifications=m.get("QualificationSummary", ""),
            open_date=m.get("PositionStartDate", "N/A"),
            close_date=m.get("PositionEndDate", "N/A"),
        )
