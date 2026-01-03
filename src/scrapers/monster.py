import logging
from typing import Optional
from urllib.parse import quote_plus

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class MonsterScraper(BaseScraper):
    """Scraper for Monster Italia job listings."""

    name = "Monster"
    BASE_URL = "https://www.monster.it"

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from Monster search page."""
        jobs = []

        encoded_keyword = quote_plus(keyword)
        search_url = f"{self.BASE_URL}/lavoro/cerca?q={encoded_keyword}"

        if location:
            encoded_location = quote_plus(location)
            search_url += f"&where={encoded_location}"

        response = self._make_request(search_url)
        if not response:
            return jobs

        soup = self._parse_html(response.text)

        # Find job cards - Monster uses various class patterns
        job_cards = soup.select('[data-testid="job-card"], .job-cardstyle, .card-content')

        # Fallback selectors
        if not job_cards:
            job_cards = soup.select('article.job-card, .job-search-resultcard, [class*="JobCard"]')

        for card in job_cards[:20]:
            job = self._parse_job_card(card)
            if job:
                jobs.append(job)

        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse job card HTML into Job object."""
        try:
            # Title
            title_elem = card.select_one('[data-testid="job-title"], .title a, h3 a, .job-title')
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Company
            company_elem = card.select_one('[data-testid="company"], .company, .company-name')
            company = company_elem.get_text(strip=True) if company_elem else ""

            # Location
            location_elem = card.select_one('[data-testid="location"], .location, .job-location')
            location = location_elem.get_text(strip=True) if location_elem else ""

            # URL
            link_elem = card.select_one('a[href*="/lavoro/"], a[href*="/job/"]')
            if not link_elem:
                link_elem = title_elem if title_elem and title_elem.name == 'a' else card.select_one('a')

            url = ""
            if link_elem and link_elem.get("href"):
                href = link_elem.get("href")
                url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            if not title or not url:
                return None

            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=self.name,
            )
        except Exception as e:
            logger.warning(f"Error parsing Monster card: {e}")
            return None
