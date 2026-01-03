import logging
import json
import re
from typing import Optional
from urllib.parse import quote_plus

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class GoogleJobsScraper(BaseScraper):
    """
    Scraper for Google Jobs search results.
    Uses Google Search with job-specific parameters.
    """

    name = "Google Jobs"
    BASE_URL = "https://www.google.com/search"

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from Google Jobs search."""
        jobs = []

        # Build search query for Google Jobs
        query = f"{keyword} jobs"
        if location:
            query += f" {location}"

        encoded_query = quote_plus(query)

        # Google Jobs URL - ibp=htl;jobs enables the jobs widget
        search_url = f"{self.BASE_URL}?q={encoded_query}&ibp=htl;jobs"

        response = self._make_request(search_url)
        if not response:
            return jobs

        # Try to extract job data from the page
        jobs.extend(self._parse_jobs_page(response.text))

        return jobs

    def _parse_jobs_page(self, html: str) -> list[Job]:
        """Parse Google Jobs page."""
        jobs = []
        soup = self._parse_html(html)

        # Google Jobs uses dynamic rendering, but some data is in script tags
        # or data attributes

        # Try to find job listings in various formats
        job_elements = soup.select('[data-ved] [jsname]')

        # Look for structured data in script tags
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        job = self._parse_json_ld(item)
                        if job:
                            jobs.append(job)
                elif isinstance(data, dict):
                    job = self._parse_json_ld(data)
                    if job:
                        jobs.append(job)
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback: try to parse visible job cards
        job_cards = soup.select('[class*="job"], [class*="Job"], [role="listitem"]')

        for card in job_cards[:15]:
            job = self._parse_job_card(card)
            if job:
                jobs.append(job)

        return jobs

    def _parse_json_ld(self, data: dict) -> Optional[Job]:
        """Parse JSON-LD structured data for job postings."""
        try:
            if data.get("@type") != "JobPosting":
                return None

            title = data.get("title", "")
            company = ""
            location = ""

            # Company info
            hiring_org = data.get("hiringOrganization", {})
            if isinstance(hiring_org, dict):
                company = hiring_org.get("name", "")

            # Location
            job_location = data.get("jobLocation", {})
            if isinstance(job_location, dict):
                address = job_location.get("address", {})
                if isinstance(address, dict):
                    parts = [
                        address.get("addressLocality", ""),
                        address.get("addressRegion", ""),
                    ]
                    location = ", ".join(p for p in parts if p)

            # URL
            url = data.get("url", "")

            # Salary
            salary = None
            base_salary = data.get("baseSalary", {})
            if isinstance(base_salary, dict):
                value = base_salary.get("value", {})
                if isinstance(value, dict):
                    min_val = value.get("minValue", "")
                    max_val = value.get("maxValue", "")
                    currency = base_salary.get("currency", "EUR")
                    if min_val and max_val:
                        salary = f"{currency} {min_val}-{max_val}"

            if not title:
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
            logger.warning(f"Error parsing JSON-LD: {e}")
            return None

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse visible job card element."""
        try:
            # Extract text content
            text = card.get_text(separator=" | ", strip=True)

            # Try to find links
            link = card.find("a")
            url = ""
            if link and link.get("href"):
                href = link.get("href")
                if href.startswith("/url?"):
                    # Extract actual URL from Google redirect
                    import re
                    match = re.search(r'url=([^&]+)', href)
                    if match:
                        from urllib.parse import unquote
                        url = unquote(match.group(1))
                elif href.startswith("http"):
                    url = href

            # Basic parsing of visible text
            parts = text.split("|")
            title = parts[0].strip() if parts else ""

            if not title or len(title) < 5:
                return None

            return Job(
                title=title[:100],
                company="",
                location="",
                url=url,
                source=self.name,
            )
        except Exception as e:
            logger.warning(f"Error parsing Google job card: {e}")
            return None
