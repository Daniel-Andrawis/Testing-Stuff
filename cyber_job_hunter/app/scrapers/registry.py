from app.scrapers.usajobs import USAJobsScraper
from app.scrapers.indeed import IndeedScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.jobicy import JobicyScraper
from app.scrapers.themuse import TheMuseScraper
from app.scrapers.spacex import SpaceXScraper
from app.scrapers.crowdstrike import CrowdStrikeScraper

_SCRAPERS = {
    "usajobs": USAJobsScraper(),
    "indeed": IndeedScraper(),
    "remoteok": RemoteOKScraper(),
    "jobicy": JobicyScraper(),
    "themuse": TheMuseScraper(),
    "spacex": SpaceXScraper(),
    "crowdstrike": CrowdStrikeScraper(),
}


def get_all_scrapers():
    return list(_SCRAPERS.values())


def get_scraper(source_id: str):
    return _SCRAPERS.get(source_id)


def register_scraper(scraper):
    _SCRAPERS[scraper.source_id] = scraper
