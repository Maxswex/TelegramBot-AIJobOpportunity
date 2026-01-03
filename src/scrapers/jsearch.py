import logging
import os
from datetime import datetime
from typing import Optional

import requests

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class JSearchScraper(BaseScraper):
    """
    Scraper for JSearch API (RapidAPI).
    Aggregates: LinkedIn, Indeed, Glassdoor, ZipRecruiter, and more.
    Free tier: 100 requests/month.
    """

    name = "JSearch"
    API_URL = "https://jsearch.p.rapidapi.com/search"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("RAPIDAPI_KEY", "")

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from JSearch API."""
        jobs = []

        if not self.api_key:
            logger.warning("RAPIDAPI_KEY not configured. Skipping JSearch.")
            return jobs

        # Build query
        query = f"{keyword} in {location}" if location else keyword

        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }

        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "date_posted": "week",  # Only recent jobs
        }

        try:
            response = requests.get(
                self.API_URL,
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("data", [])

            for item in results:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("JSearch: Invalid API key")
            elif e.response.status_code == 429:
                logger.warning("JSearch: Rate limit exceeded (100 requests/month)")
            else:
                logger.error(f"JSearch HTTP error: {e}")
        except Exception as e:
            logger.error(f"Error fetching JSearch: {e}")

        return jobs

    def _parse_job(self, item: dict) -> Optional[Job]:
        """Parse API response into Job object."""
        try:
            title = item.get("job_title", "")
            company = item.get("employer_name", "")
            location = item.get("job_city", "")

            # Add country/state if available
            if item.get("job_state"):
                location = f"{location}, {item['job_state']}" if location else item["job_state"]
            if item.get("job_country"):
                location = f"{location}, {item['job_country']}" if location else item["job_country"]

            # Remote indicator
            if item.get("job_is_remote"):
                location = f"{location} (Remote)" if location else "Remote"

            url = item.get("job_apply_link", "") or item.get("job_google_link", "")

            # Source site
            publisher = item.get("job_publisher", "")
            source_name = f"JSearch ({publisher})" if publisher else "JSearch"

            # Parse date
            posted_date = None
            if item.get("job_posted_at_datetime_utc"):
                try:
                    posted_date = datetime.fromisoformat(
                        item["job_posted_at_datetime_utc"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            # Salary
            salary = None
            min_sal = item.get("job_min_salary")
            max_sal = item.get("job_max_salary")
            currency = item.get("job_salary_currency", "EUR")
            if min_sal and max_sal:
                salary = f"{currency} {min_sal:,.0f} - {max_sal:,.0f}"
            elif min_sal:
                salary = f"Da {currency} {min_sal:,.0f}"

            # Description snippet
            description = item.get("job_description", "")[:300]

            if not title or not url:
                return None

            return Job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=source_name,
                description=description,
                posted_date=posted_date,
                salary=salary,
            )
        except Exception as e:
            logger.warning(f"Error parsing JSearch job: {e}")
            return None

    def search(self, keywords: list[str], locations: list[str]) -> list[Job]:
        """
        Search with limited API calls to stay within free tier.
        Combines keywords to minimize requests.
        """
        all_jobs = []
        seen_urls = set()

        # Combine AI-related keywords to reduce API calls
        # Use only the most important keywords
        priority_keywords = ["AI engineer", "machine learning", "data scientist AI", "LLM"]

        # Use only main locations
        priority_locations = ["Italia", "Remote"]

        for keyword in priority_keywords:
            for location in priority_locations:
                try:
                    jobs = self.get_jobs(keyword, location)
                    for job in jobs:
                        if job.url not in seen_urls:
                            seen_urls.add(job.url)
                            all_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error searching JSearch for '{keyword}': {e}")

        logger.info(f"{self.name}: Found {len(all_jobs)} unique jobs")
        return all_jobs
