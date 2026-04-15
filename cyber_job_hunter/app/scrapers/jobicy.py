import requests

from app.scrapers.base import BaseScraper

SECURITY_TERMS = [
    "security", "cyber", "forensic", "soc", "incident",
    "threat", "pentest", "vulnerability", "malware",
    "dfir", "detection", "compliance", "grc",
]


class JobicyScraper(BaseScraper):
    name = "Jobicy"
    source_id = "jobicy"

    def fetch_jobs(self) -> list[dict]:
        jobs = []
        try:
            resp = requests.get(
                "https://jobicy.com/api/v2/remote-jobs?count=50&tag=security",
                headers={"User-Agent": "CyberRank/1.0"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("jobs", []):
                title_lower = item.get("jobTitle", "").lower()
                if not any(t in title_lower for t in SECURITY_TERMS):
                    continue

                jobs.append(self.job_dict(
                    source="Jobicy",
                    title=item.get("jobTitle", "N/A"),
                    organization=item.get("companyName", "N/A"),
                    url=item.get("url", "N/A"),
                    description=item.get("jobDescription", ""),
                    qualifications=", ".join(item["jobIndustry"]) if isinstance(item.get("jobIndustry"), list) else str(item.get("jobIndustry", "")),
                    salary_min=item.get("annualSalaryMin", "N/A"),
                    salary_max=item.get("annualSalaryMax", "N/A"),
                    open_date=item.get("pubDate", "N/A"),
                    location=item.get("jobGeo", "Remote"),
                ))
        except requests.RequestException as e:
            print(f"[!] Jobicy error: {e}")

        print(f"[+] Jobicy: {len(jobs)} jobs")
        return jobs
