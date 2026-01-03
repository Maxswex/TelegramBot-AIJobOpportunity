import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import requests

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class ArbeitnowScraper(BaseScraper):
    """
    Scraper for Arbeitnow - public JSON API, no auth required.
    Good for European tech jobs.
    """

    name = "Arbeitnow"
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from Arbeitnow API."""
        jobs = []

        try:
            response = requests.get(self.API_URL, timeout=30)
            response.raise_for_status()

            data = response.json()
            job_listings = data.get("data", [])

            keyword_lower = keyword.lower()
            location_lower = location.lower() if location else ""

            for item in job_listings:
                # Filter by keyword
                title = item.get("title", "").lower()
                description = item.get("description", "").lower()
                tags = " ".join(item.get("tags", [])).lower()

                if keyword_lower not in title and keyword_lower not in description and keyword_lower not in tags:
                    continue

                # Filter by location if specified
                job_location = item.get("location", "").lower()
                if location_lower and location_lower not in job_location and "remote" not in job_location:
                    continue

                job = self._parse_job(item)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.error(f"Error fetching Arbeitnow: {e}")

        return jobs

    def _parse_job(self, item: dict) -> Optional[Job]:
        """Parse API response into Job object."""
        try:
            title = item.get("title", "")
            company = item.get("company_name", "")
            location = item.get("location", "")
            url = item.get("url", "")

            # Parse date
            posted_date = None
            if item.get("created_at"):
                try:
                    # Unix timestamp
                    posted_date = datetime.fromtimestamp(item["created_at"])
                except (ValueError, TypeError):
                    pass

            # Remote indicator
            if item.get("remote", False):
                location = f"{location} (Remote)" if location else "Remote"

            # Tags as description
            tags = item.get("tags", [])
            description = ", ".join(tags) if tags else ""

            if not title or not url:
                return None

            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=self.name,
                description=description,
                posted_date=posted_date,
            )
        except Exception as e:
            logger.warning(f"Error parsing Arbeitnow job: {e}")
            return None

    def search(self, keywords: list[str], locations: list[str]) -> list[Job]:
        """
        Override search - API returns all jobs at once,
        so we fetch once and filter locally for all keywords.
        """
        all_jobs = []
        seen_urls = set()

        # Fetch API only once
        try:
            response = requests.get(self.API_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            job_listings = data.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching Arbeitnow: {e}")
            return all_jobs

        # Filter locally for each keyword/location combo
        for item in job_listings:
            title = item.get("title", "").lower()
            description = item.get("description", "").lower()
            tags = " ".join(item.get("tags", [])).lower()
            job_location = item.get("location", "").lower()

            # Check if any keyword matches
            keyword_match = any(
                kw.lower() in title or kw.lower() in description or kw.lower() in tags
                for kw in keywords
            )

            if not keyword_match:
                continue

            job = self._parse_job(item)
            if job and job.url not in seen_urls:
                seen_urls.add(job.url)
                all_jobs.append(job)

        logger.info(f"{self.name}: Found {len(all_jobs)} unique jobs")
        return all_jobs
