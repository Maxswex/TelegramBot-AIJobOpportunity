import logging
from datetime import datetime
from typing import Optional

import requests

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class RemoteOKScraper(BaseScraper):
    """
    Scraper for RemoteOK - public JSON API, no auth required.
    Excellent for remote tech/AI jobs.
    """

    name = "RemoteOK"
    API_URL = "https://remoteok.com/api"

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from RemoteOK API."""
        jobs = []

        try:
            headers = {
                "User-Agent": "AIJobAlerts/1.0",
                "Accept": "application/json",
            }

            response = requests.get(
                self.API_URL,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # First item is metadata, skip it
            job_listings = data[1:] if len(data) > 1 else []

            keyword_lower = keyword.lower()

            for item in job_listings:
                # Filter by keyword
                title = item.get("position", "").lower()
                tags = " ".join(item.get("tags", [])).lower()
                company = item.get("company", "").lower()
                description = item.get("description", "").lower()

                if keyword_lower in title or keyword_lower in tags or keyword_lower in description:
                    job = self._parse_job(item)
                    if job:
                        jobs.append(job)

        except Exception as e:
            logger.error(f"Error fetching RemoteOK: {e}")

        return jobs

    def _parse_job(self, item: dict) -> Optional[Job]:
        """Parse API response into Job object."""
        try:
            title = item.get("position", "")
            company = item.get("company", "")
            location = item.get("location", "Remote")

            # Build URL
            slug = item.get("slug", "")
            url = f"https://remoteok.com/remote-jobs/{item.get('id', '')}" if item.get("id") else ""

            # Parse date
            posted_date = None
            if item.get("date"):
                try:
                    posted_date = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            # Salary
            salary = None
            if item.get("salary_min") and item.get("salary_max"):
                salary = f"${item['salary_min']:,} - ${item['salary_max']:,}"

            if not title or not url:
                return None

            return Job(
                title=title,
                company=company,
                location=location if location else "Remote",
                url=url,
                source=self.name,
                posted_date=posted_date,
                salary=salary,
            )
        except Exception as e:
            logger.warning(f"Error parsing RemoteOK job: {e}")
            return None

    def search(self, keywords: list[str], locations: list[str]) -> list[Job]:
        """
        Override search - RemoteOK API returns all jobs at once,
        so we filter locally.
        """
        all_jobs = []
        seen_urls = set()

        for keyword in keywords:
            try:
                jobs = self.get_jobs(keyword)
                for job in jobs:
                    if job.url not in seen_urls:
                        seen_urls.add(job.url)
                        all_jobs.append(job)
            except Exception as e:
                logger.error(f"Error searching RemoteOK for '{keyword}': {e}")

        logger.info(f"{self.name}: Found {len(all_jobs)} unique jobs")
        return all_jobs
