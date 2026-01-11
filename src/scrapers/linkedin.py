import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, Job

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """
    Scraper for LinkedIn Jobs (public page, no login required).

    Note: LinkedIn may block scrapers. Use with caution.
    """

    name = "LinkedIn"
    BASE_URL = "https://www.linkedin.com/jobs/search"

    def __init__(self):
        super().__init__()
        # Extra headers to look more like a browser
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """Fetch jobs from LinkedIn public search page."""
        jobs = []

        # Build search URL
        params = {
            "keywords": keyword,
            "location": location,
            "f_TPR": "r604800",  # Last week
            "position": "1",
            "pageNum": "0",
        }

        url = f"{self.BASE_URL}?keywords={quote_plus(keyword)}&location={quote_plus(location)}&f_TPR=r604800"

        try:
            response = self._make_request(url)
            if not response:
                logger.warning(f"LinkedIn: No response for {keyword} in {location}")
                return jobs

            soup = self._parse_html(response.text)

            # Find job cards - LinkedIn uses various class names
            job_cards = soup.find_all("div", class_="base-card")

            if not job_cards:
                # Try alternative selectors
                job_cards = soup.find_all("li", class_="jobs-search__results-list")

            if not job_cards:
                job_cards = soup.find_all("div", {"data-entity-urn": re.compile(r"jobPosting")})

            logger.debug(f"LinkedIn: Found {len(job_cards)} job cards for '{keyword}'")

            for card in job_cards:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing LinkedIn job card: {e}")
                    continue

            # Add delay to avoid rate limiting
            time.sleep(2)

        except Exception as e:
            logger.error(f"LinkedIn scraping error: {e}")

        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a LinkedIn job card into a Job object."""
        # Try to find title
        title_elem = (
            card.find("h3", class_="base-search-card__title") or
            card.find("h3", class_="job-card-list__title") or
            card.find("a", class_="job-card-list__title")
        )
        title = title_elem.get_text(strip=True) if title_elem else None

        if not title:
            return None

        # Try to find company
        company_elem = (
            card.find("h4", class_="base-search-card__subtitle") or
            card.find("a", class_="job-card-container__company-name")
        )
        company = company_elem.get_text(strip=True) if company_elem else "N/D"

        # Try to find location
        location_elem = (
            card.find("span", class_="job-search-card__location") or
            card.find("span", class_="job-card-container__metadata-item")
        )
        location = location_elem.get_text(strip=True) if location_elem else "N/D"

        # Try to find URL
        link_elem = card.find("a", href=True)
        url = link_elem["href"] if link_elem else None

        if not url:
            return None

        # Clean up URL
        if url.startswith("/"):
            url = f"https://www.linkedin.com{url}"

        # Remove tracking parameters
        if "?" in url:
            url = url.split("?")[0]

        # Try to find posted date
        time_elem = card.find("time")
        posted_date = None
        if time_elem:
            datetime_str = time_elem.get("datetime")
            if datetime_str:
                try:
                    posted_date = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

        # If no datetime attribute, try to parse text like "2 days ago"
        if not posted_date:
            time_text_elem = (
                card.find("time", class_="job-search-card__listdate") or
                card.find("time", class_="job-search-card__listdate--new")
            )
            if time_text_elem:
                posted_date = self._parse_relative_date(time_text_elem.get_text(strip=True))

        return Job(
            title=title,
            company=company,
            location=location,
            url=url,
            source="LinkedIn",
            posted_date=posted_date,
        )

    def _parse_relative_date(self, date_text: str) -> Optional[datetime]:
        """Parse relative date strings like '2 days ago', '1 week ago'."""
        if not date_text:
            return None

        date_text = date_text.lower()
        now = datetime.now()

        try:
            if "just now" in date_text or "now" in date_text:
                return now
            elif "hour" in date_text:
                hours = int(re.search(r"(\d+)", date_text).group(1))
                return now - timedelta(hours=hours)
            elif "day" in date_text:
                days = int(re.search(r"(\d+)", date_text).group(1))
                return now - timedelta(days=days)
            elif "week" in date_text:
                weeks = int(re.search(r"(\d+)", date_text).group(1))
                return now - timedelta(weeks=weeks)
            elif "month" in date_text:
                months = int(re.search(r"(\d+)", date_text).group(1))
                return now - timedelta(days=months * 30)
        except (AttributeError, ValueError):
            pass

        return None

    def search(self, keywords: list[str], locations: list[str]) -> list[Job]:
        """Search LinkedIn with AI-focused keywords."""
        all_jobs = []
        seen_urls = set()

        # Use a subset of keywords to avoid rate limiting
        priority_keywords = [
            "artificial intelligence",
            "machine learning",
            "AI engineer",
            "data scientist",
        ]

        # Focus on Italy
        priority_locations = ["Italy", "Italia", "Milano", "Roma"]

        for keyword in priority_keywords:
            for location in priority_locations:
                try:
                    logger.info(f"LinkedIn: Searching '{keyword}' in '{location}'...")
                    jobs = self.get_jobs(keyword, location)

                    for job in jobs:
                        if job.url not in seen_urls:
                            seen_urls.add(job.url)
                            all_jobs.append(job)

                    # Longer delay between searches to avoid blocking
                    time.sleep(3)

                except Exception as e:
                    logger.error(f"LinkedIn error for '{keyword}': {e}")
                    continue

        logger.info(f"{self.name}: Found {len(all_jobs)} unique jobs")
        return all_jobs
