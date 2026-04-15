"""SpaceX careers page scraper — pulls cybersecurity-related positions."""

import requests
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper

SECURITY_TERMS = [
    "security", "cyber", "forensic", "soc", "incident",
    "threat", "vulnerability", "compliance", "grc",
    "information assurance", "infosec", "network defense",
    "penetration", "red team", "blue team",
]


class SpaceXScraper(BaseScraper):
    name = "SpaceX"
    source_id = "spacex"

    def fetch_jobs(self) -> list[dict]:
        jobs = []
        # SpaceX uses Greenhouse for their careers
        url = "https://boards-api.greenhouse.io/v1/boards/spacex/jobs"
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "CyberRank/1.0"})
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("jobs", []):
                title = item.get("title", "")
                title_lower = title.lower()

                # Filter for security-related roles
                if not any(t in title_lower for t in SECURITY_TERMS):
                    # Also check department
                    depts = [d.get("name", "").lower() for d in item.get("departments", [])]
                    if not any(t in " ".join(depts) for t in SECURITY_TERMS):
                        continue

                location = item.get("location", {}).get("name", "N/A")
                departments = ", ".join(d.get("name", "") for d in item.get("departments", []))

                jobs.append(self.job_dict(
                    source="SpaceX",
                    title=title,
                    organization="SpaceX",
                    department=departments,
                    url=item.get("absolute_url", ""),
                    location=location,
                    open_date=item.get("updated_at", "N/A"),
                    external_id=str(item.get("id", "")),
                ))

        except requests.RequestException as e:
            print(f"[!] SpaceX error: {e}")

        print(f"[+] SpaceX: {len(jobs)} security jobs")
        return jobs
