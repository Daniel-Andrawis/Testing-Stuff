"""CrowdStrike careers scraper via Workday API."""

import requests

from app.scrapers.base import BaseScraper

WORKDAY_URL = "https://crowdstrike.wd5.myworkdayjobs.com/wday/cxs/crowdstrike/crowdstrikecareers/jobs"


class CrowdStrikeScraper(BaseScraper):
    name = "CrowdStrike"
    source_id = "crowdstrike"

    def fetch_jobs(self) -> list[dict]:
        jobs = []
        offset = 0
        limit = 20

        while offset < 200:  # Cap at 200 to be respectful
            try:
                resp = requests.post(
                    WORKDAY_URL,
                    json={"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": "security"},
                    headers={"Content-Type": "application/json", "User-Agent": "CyberRank/1.0"},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                postings = data.get("jobPostings", [])
                if not postings:
                    break

                for item in postings:
                    title = item.get("title", "")
                    jobs.append(self.job_dict(
                        source="CrowdStrike",
                        title=title,
                        organization="CrowdStrike",
                        url=f"https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers{item.get('externalPath', '')}",
                        location=item.get("locationsText", "N/A"),
                        open_date=item.get("postedOn", "N/A"),
                        external_id=item.get("bulletFields", [""])[0] if item.get("bulletFields") else "",
                    ))

                offset += limit
            except requests.RequestException as e:
                print(f"[!] CrowdStrike error: {e}")
                break

        print(f"[+] CrowdStrike: {len(jobs)} jobs")
        return jobs
