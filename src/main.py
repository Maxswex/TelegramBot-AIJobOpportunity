#!/usr/bin/env python3
"""
AI Job Alerts - Main entry point

Fetches AI/ML job listings from multiple sources and sends
a daily summary via Telegram.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import KEYWORDS, LOCATIONS
from src.scrapers import (
    RemoteOKScraper,
    AdzunaScraper,
    ArbeitnowScraper,
    JSearchScraper,
)
from src.telegram_bot import TelegramBot
from src.utils import (
    deduplicate_jobs,
    filter_european_jobs,
    is_italian_location,
    is_remote_location,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


def collect_jobs() -> list:
    """Collect jobs from all scrapers."""
    all_jobs = []

    scrapers = [
        JSearchScraper(),    # LinkedIn, Indeed, Glassdoor aggregator (100 req/month free)
        RemoteOKScraper(),   # Public API, no auth - remote tech jobs
        ArbeitnowScraper(),  # Public API, no auth - EU tech jobs
        AdzunaScraper(),     # Free API with key - comprehensive IT jobs
    ]

    for scraper in scrapers:
        try:
            logger.info(f"Scraping {scraper.name}...")
            jobs = scraper.search(KEYWORDS, LOCATIONS)
            all_jobs.extend(jobs)
            logger.info(f"{scraper.name}: found {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"Error with {scraper.name}: {e}")
            continue

    return all_jobs


def main():
    """Main execution flow."""
    logger.info("Starting AI Job Alerts...")

    # 1. Collect jobs from all sources
    all_jobs = collect_jobs()
    logger.info(f"Total jobs collected: {len(all_jobs)}")

    # 2. Deduplicate
    unique_jobs = deduplicate_jobs(all_jobs)

    # 3. Filter to European jobs only
    european_jobs = filter_european_jobs(unique_jobs)
    logger.info(f"European jobs to send: {len(european_jobs)}")

    # 4. Sort by date (newest first), then by location (Italy first)
    def get_sort_key(job):
        """Get sort key: (date_priority, location_priority)."""
        # Date priority (negative timestamp so newer = smaller = first)
        if job.posted_date:
            if job.posted_date.tzinfo is not None:
                date_val = job.posted_date.replace(tzinfo=None)
            else:
                date_val = job.posted_date
            date_priority = -date_val.timestamp()
        else:
            date_priority = 0  # Jobs without date go after dated ones

        # Location priority: 0=Italy, 1=EU, 2=Remote
        location = job.location or ""
        if is_italian_location(location):
            location_priority = 0
        elif is_remote_location(location):
            location_priority = 2
        else:
            location_priority = 1

        return (date_priority, location_priority)

    sorted_jobs = sorted(european_jobs, key=get_sort_key)
    logger.info(f"Jobs sorted by date (newest first), then location (Italy first)")

    # 5. Send via Telegram
    try:
        bot = TelegramBot()
        success = bot.send_job_alert(sorted_jobs)

        if success:
            logger.info("Telegram message sent successfully")
        else:
            logger.error("Failed to send Telegram message")
            sys.exit(1)

    except ValueError as e:
        logger.error(f"Telegram configuration error: {e}")
        logger.info("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        sys.exit(1)

    logger.info("AI Job Alerts completed successfully")


if __name__ == "__main__":
    main()
