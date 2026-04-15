import time
import requests

from app.scrapers.base import BaseScraper

SECURITY_TERMS = [
    "security", "cyber", "forensic", "soc ", "incident",
    "threat", "pentest", "vulnerability", "malware",
    "dfir", "detection", "grc",
]


class TheMuseScraper(BaseScraper):
    name = "TheMuse"
    source_id = "themuse"

    def fetch_jobs(self) -> list[dict]:
        jobs = []
        session = requests.Session()
        session.headers.update({"User-Agent": "CyberRank/1.0"})

        for page in range(5):
            try:
                resp = session.get(
                    f"https://www.themuse.com/api/public/jobs?page={page}&descending=true",
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("results", []):
                    name_lower = item.get("name", "").lower()
                    if not any(t in name_lower for t in SECURITY_TERMS):
                        continue

                    company = item.get("company", {})
                    locations = ", ".join(
                        loc.get("name", "") for loc in item.get("locations", [])
                    ) or "N/A"

                    jobs.append(self.job_dict(
                        source="TheMuse",
                        title=item.get("name", "N/A"),
                        organization=company.get("name", "N/A"),
                        url=f"https://www.themuse.com/jobs/{item.get('short_name', item.get('id', ''))}",
                        description=item.get("contents", ""),
                        qualifications=", ".join(c.get("name", "") for c in item.get("categories", [])),
                        open_date=item.get("publication_date", "N/A"),
                        location=locations,
                    ))
            except requests.RequestException as e:
                print(f"[!] TheMuse error (page {page}): {e}")
                break
            time.sleep(0.5)

        print(f"[+] TheMuse: {len(jobs)} jobs")
        return jobs
