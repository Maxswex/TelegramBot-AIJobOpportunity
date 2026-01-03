import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import feedparser

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    """Scraper for Indeed job listings using RSS feeds."""

    name = "Indeed"
    BASE_URL = "https://it.indeed.com"

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from Indeed RSS feed."""
        jobs = []

        # Build RSS URL
        # Indeed Italy RSS format
        encoded_keyword = quote_plus(keyword)
        encoded_location = quote_plus(location) if location else ""

        rss_url = f"{self.BASE_URL}/rss?q={encoded_keyword}&l={encoded_location}"

        try:
            feed = feedparser.parse(rss_url)

            if feed.bozo and not feed.entries:
                logger.warning(f"Indeed RSS feed error: {feed.bozo_exception}")
                return jobs

            for entry in feed.entries:
                job = self._parse_entry(entry)
                if job:
                    jobs.append(job)

        except Exception as e:
            logger.error(f"Error fetching Indeed RSS: {e}")

        return jobs

    def _parse_entry(self, entry) -> Optional[Job]:
        """Parse RSS entry into Job object."""
        try:
            title = entry.get("title", "")
            link = entry.get("link", "")

            # Extract company and location from summary
            summary = entry.get("summary", "")
            company = ""
            location = ""

            # Indeed format: "Company - Location"
            if " - " in summary:
                parts = summary.split(" - ", 1)
                company = parts[0].strip()
                if len(parts) > 1:
                    location = parts[1].split("<")[0].strip()

            # Parse date
            posted_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                posted_date = datetime(*entry.published_parsed[:6])

            return Job(
                title=title,
                company=company,
                location=location,
                url=link,
                source=self.name,
                description=summary,
                posted_date=posted_date,
            )
        except Exception as e:
            logger.warning(f"Error parsing Indeed entry: {e}")
            return None
