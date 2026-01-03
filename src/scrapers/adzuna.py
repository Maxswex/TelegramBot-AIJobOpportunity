import logging
import os
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import requests

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class AdzunaScraper(BaseScraper):
    """
    Scraper for Adzuna API.
    Free tier: 200 requests/day.
    Register at: https://developer.adzuna.com/
    """

    name = "Adzuna"
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self):
        super().__init__()
        self.app_id = os.getenv("ADZUNA_APP_ID", "")
        self.app_key = os.getenv("ADZUNA_APP_KEY", "")

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from Adzuna API."""
        jobs = []

        if not self.app_id or not self.app_key:
            logger.warning("Adzuna API credentials not configured. Skipping.")
            return jobs

        # Use Italy country code
        country = "it"
        encoded_keyword = quote_plus(keyword)

        url = f"{self.BASE_URL}/{country}/search/1"

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": keyword,
            "results_per_page": 50,
            "content-type": "application/json",
        }

        if location:
            params["where"] = location

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            for item in results:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Adzuna: Invalid API credentials")
            else:
                logger.error(f"Adzuna HTTP error: {e}")
        except Exception as e:
            logger.error(f"Error fetching Adzuna: {e}")

        return jobs

    def _parse_job(self, item: dict) -> Optional[Job]:
        """Parse API response into Job object."""
        try:
            title = item.get("title", "")
            company = item.get("company", {}).get("display_name", "")
            location = item.get("location", {}).get("display_name", "")
            url = item.get("redirect_url", "")

            # Parse date
            posted_date = None
            if item.get("created"):
                try:
                    posted_date = datetime.fromisoformat(
                        item["created"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            # Salary
            salary = None
            if item.get("salary_min") and item.get("salary_max"):
                salary = f"€{item['salary_min']:,.0f} - €{item['salary_max']:,.0f}"
            elif item.get("salary_min"):
                salary = f"Da €{item['salary_min']:,.0f}"

            # Description snippet
            description = item.get("description", "")[:300]

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
                salary=salary,
            )
        except Exception as e:
            logger.warning(f"Error parsing Adzuna job: {e}")
            return None
