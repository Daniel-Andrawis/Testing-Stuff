import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper

CYBER_TITLES = [
    "Cybersecurity Analyst", "Security Engineer", "SOC Analyst",
    "Incident Response Analyst", "Digital Forensics Analyst",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class IndeedScraper(BaseScraper):
    name = "Indeed"
    source_id = "indeed"

    def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        for title in CYBER_TITLES:
            encoded = urllib.parse.quote_plus(title)
            url = f"https://www.indeed.com/rss?q={encoded}&l=United+States&sort=date&limit=25"
            try:
                resp = session.get(url, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for item in soup.find_all("item"):
                    t = item.find("title")
                    link = item.find("link")
                    desc = item.find("description")
                    pub = item.find("pubdate")
                    src = item.find("source")
                    all_jobs.append(self.job_dict(
                        source="Indeed",
                        title=t.text.strip() if t else "N/A",
                        organization=src.text.strip() if src else "N/A",
                        url=link.text.strip() if link else "N/A",
                        description=re.sub(r"<[^>]+>", " ", desc.text).strip() if desc else "",
                        open_date=pub.text.strip() if pub else "N/A",
                        location="United States",
                    ))
            except requests.RequestException as e:
                print(f"[!] Indeed error for '{title}': {e}")
            time.sleep(1)

        seen = set()
        unique = []
        for j in all_jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique.append(j)

        print(f"[+] Indeed: {len(unique)} jobs")
        return unique
