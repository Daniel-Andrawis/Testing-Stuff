import requests

from app.scrapers.base import BaseScraper

SECURITY_TERMS = [
    "security", "cyber", "forensic", "soc", "incident",
    "threat", "pentest", "vulnerability", "malware",
    "dfir", "detection", "compliance", "grc",
]


class RemoteOKScraper(BaseScraper):
    name = "RemoteOK"
    source_id = "remoteok"

    def fetch_jobs(self) -> list[dict]:
        jobs = []
        try:
            resp = requests.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "CyberRank/1.0"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data[1:]:
                tags = [t.lower() for t in item.get("tags", [])]
                title_lower = item.get("position", "").lower()
                company_lower = item.get("company", "").lower()

                if not any(t in title_lower or t in " ".join(tags) or t in company_lower
                           for t in SECURITY_TERMS):
                    continue

                jobs.append(self.job_dict(
                    source="RemoteOK",
                    title=item.get("position", "N/A"),
                    organization=item.get("company", "N/A"),
                    url=f"https://remoteok.com/l/{item.get('id', '')}",
                    description=item.get("description", ""),
                    qualifications=", ".join(item.get("tags", [])),
                    salary_min=item.get("salary_min", "N/A"),
                    salary_max=item.get("salary_max", "N/A"),
                    open_date=item.get("date", "N/A"),
                    location="Remote",
                ))
        except requests.RequestException as e:
            print(f"[!] RemoteOK error: {e}")

        print(f"[+] RemoteOK: {len(jobs)} jobs")
        return jobs
