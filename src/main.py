#!/usr/bin/env python3
"""
AI Job Alerts - Main entry point

Fetches AI/ML job listings from multiple sources and sends
a daily summary via Telegram.
"""

import logging
import sys
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
    load_seen_jobs,
    save_seen_jobs,
    filter_new_jobs,
    deduplicate_jobs,
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

    # 1. Load previously seen jobs
    seen_ids = load_seen_jobs()
    logger.info(f"Loaded {len(seen_ids)} previously seen job IDs")

    # 2. Collect jobs from all sources
    all_jobs = collect_jobs()
    logger.info(f"Total jobs collected: {len(all_jobs)}")

    # 3. Deduplicate
    unique_jobs = deduplicate_jobs(all_jobs)

    # 4. Filter out already seen jobs
    new_jobs = filter_new_jobs(unique_jobs, seen_ids)
    logger.info(f"New jobs to send: {len(new_jobs)}")

    # 5. Send via Telegram
    try:
        bot = TelegramBot()
        success = bot.send_job_alert(new_jobs)

        if success:
            logger.info("Telegram message sent successfully")

            # 6. Update seen jobs
            new_ids = {job.id for job in new_jobs}
            all_seen_ids = seen_ids | new_ids
            save_seen_jobs(all_seen_ids)
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
