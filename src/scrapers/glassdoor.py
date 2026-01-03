import logging
import re
from typing import Optional
from urllib.parse import quote_plus

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class GlassdoorScraper(BaseScraper):
    """Scraper for Glassdoor job listings."""

    name = "Glassdoor"
    BASE_URL = "https://www.glassdoor.it"

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from Glassdoor search page."""
        jobs = []

        encoded_keyword = quote_plus(keyword)
        search_url = f"{self.BASE_URL}/Lavoro/{encoded_keyword}-lavori-SRCH_KO0,{len(keyword)}.htm"

        if location:
            encoded_location = quote_plus(location)
            search_url = f"{self.BASE_URL}/Lavoro/{encoded_location}-{encoded_keyword}-lavori-SRCH_IL.0,{len(location)}_KO{len(location)+1},{len(location)+1+len(keyword)}.htm"

        response = self._make_request(search_url)
        if not response:
            return jobs

        soup = self._parse_html(response.text)

        # Find job cards
        job_cards = soup.select('[data-test="jobListing"]')

        # Fallback selectors if primary doesn't work
        if not job_cards:
            job_cards = soup.select(".jobCard, .job-listing, .react-job-listing")

        for card in job_cards[:20]:  # Limit to 20 per search
            job = self._parse_job_card(card)
            if job:
                jobs.append(job)

        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse job card HTML into Job object."""
        try:
            # Title
            title_elem = card.select_one('[data-test="job-title"], .jobTitle, .job-title a')
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Company
            company_elem = card.select_one('[data-test="employer-name"], .jobEmployer, .employer-name')
            company = company_elem.get_text(strip=True) if company_elem else ""

            # Location
            location_elem = card.select_one('[data-test="employer-location"], .jobLocation, .location')
            location = location_elem.get_text(strip=True) if location_elem else ""

            # URL
            link_elem = card.select_one('a[href*="job-listing"], a[href*="/job/"]')
            if not link_elem:
                link_elem = title_elem if title_elem and title_elem.name == 'a' else card.select_one('a')

            url = ""
            if link_elem and link_elem.get("href"):
                href = link_elem.get("href")
                url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            # Salary (if available)
            salary_elem = card.select_one('[data-test="detailSalary"], .salary-estimate')
            salary = salary_elem.get_text(strip=True) if salary_elem else None

            if not title or not url:
                return None

            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=self.name,
                salary=salary,
            )
        except Exception as e:
            logger.warning(f"Error parsing Glassdoor card: {e}")
            return None
