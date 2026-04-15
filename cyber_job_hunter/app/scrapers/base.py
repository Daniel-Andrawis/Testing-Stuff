from abc import ABC, abstractmethod


class BaseScraper(ABC):
    name: str = ""
    source_id: str = ""

    @abstractmethod
    def fetch_jobs(self) -> list[dict]:
        """Fetch jobs and return list of standardized job dicts."""
        ...

    def is_available(self) -> bool:
        """Check if this scraper can run (e.g. API key present)."""
        return True

    @staticmethod
    def job_dict(
        source, title, organization, url,
        department="", location="", salary_min="N/A", salary_max="N/A",
        grade="N/A", description="", qualifications="",
        open_date="N/A", close_date="N/A", external_id="",
    ) -> dict:
        return {
            "source": source,
            "external_id": external_id or url,
            "title": title,
            "organization": organization,
            "department": department,
            "location": location,
            "salary_min": str(salary_min) if salary_min else "N/A",
            "salary_max": str(salary_max) if salary_max else "N/A",
            "grade": str(grade) if grade else "N/A",
            "description": description,
            "qualifications": qualifications,
            "url": url,
            "open_date": str(open_date) if open_date else "N/A",
            "close_date": str(close_date) if close_date else "N/A",
        }
