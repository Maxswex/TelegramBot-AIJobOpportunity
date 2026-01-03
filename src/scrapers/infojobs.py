import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import feedparser

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class InfoJobsScraper(BaseScraper):
    """Scraper for InfoJobs listings using RSS feeds."""

    name = "InfoJobs"
    BASE_URL = "https://www.infojobs.it"

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from InfoJobs RSS feed."""
        jobs = []

        encoded_keyword = quote_plus(keyword)

        # InfoJobs RSS URL format
        rss_url = f"{self.BASE_URL}/offerte-lavoro/{encoded_keyword}.xml"

        try:
            feed = feedparser.parse(rss_url)

            if feed.bozo and not feed.entries:
                # Try alternative URL format
                rss_url = f"{self.BASE_URL}/rss/offerte-lavoro?q={encoded_keyword}"
                feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                job = self._parse_entry(entry, location)
                if job:
                    # Filter by location if specified
                    if location and location.lower() not in job.location.lower():
                        continue
                    jobs.append(job)

        except Exception as e:
            logger.error(f"Error fetching InfoJobs RSS: {e}")

        return jobs

    def _parse_entry(self, entry, default_location: str = "") -> Optional[Job]:
        """Parse RSS entry into Job object."""
        try:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", entry.get("description", ""))

            # Try to extract company from title or summary
            company = ""
            location = default_location

            # InfoJobs often has format: "Title - Company - Location"
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 2:
                    title = parts[0].strip()
                    company = parts[1].strip() if len(parts) > 1 else ""
                    location = parts[2].strip() if len(parts) > 2 else location

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
                description=summary[:500] if summary else "",
                posted_date=posted_date,
            )
        except Exception as e:
            logger.warning(f"Error parsing InfoJobs entry: {e}")
            return None
