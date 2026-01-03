from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib
import logging
import random
import time

import requests
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, "/Users/maxswex/ai-job-alerts")
from config import USER_AGENTS, REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a job posting."""
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    posted_date: Optional[datetime] = None
    salary: Optional[str] = None

    @property
    def id(self) -> str:
        """Generate unique ID based on URL."""
        return hashlib.md5(self.url.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source": self.source,
            "description": self.description,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "salary": self.salary,
        }


class BaseScraper(ABC):
    """Base class for all job scrapers."""

    name: str = "base"

    def __init__(self):
        self.session = requests.Session()
        self._update_headers()

    def _update_headers(self):
        """Set random user agent."""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                self._update_headers()
                response = self.session.get(
                    url,
                    timeout=REQUEST_TIMEOUT,
                    **kwargs
                )
                response.raise_for_status()
                time.sleep(REQUEST_DELAY)
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(REQUEST_DELAY * (attempt + 1))
        return None

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content."""
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    def get_jobs(self, keyword: str, location: str = "") -> list[Job]:
        """
        Fetch jobs for given keyword and location.
        Must be implemented by subclasses.
        """
        pass

    def search(self, keywords: list[str], locations: list[str]) -> list[Job]:
        """Search for jobs with multiple keywords and locations."""
        all_jobs = []
        seen_urls = set()

        for keyword in keywords:
            for location in locations:
                try:
                    jobs = self.get_jobs(keyword, location)
                    for job in jobs:
                        if job.url not in seen_urls:
                            seen_urls.add(job.url)
                            all_jobs.append(job)
                except Exception as e:
                    logger.error(f"Error scraping {self.name} for '{keyword}' in '{location}': {e}")

        logger.info(f"{self.name}: Found {len(all_jobs)} unique jobs")
        return all_jobs
