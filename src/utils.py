import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Set

import sys
sys.path.insert(0, "/Users/maxswex/ai-job-alerts")
from config import SEEN_JOBS_FILE

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def load_seen_jobs() -> Set[str]:
    """Load set of previously seen job IDs."""
    filepath = get_project_root() / SEEN_JOBS_FILE

    if not filepath.exists():
        return set()

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error loading seen jobs: {e}")
        return set()


def save_seen_jobs(seen_ids: Set[str]):
    """Save set of seen job IDs."""
    filepath = get_project_root() / SEEN_JOBS_FILE
    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "seen_ids": list(seen_ids),
        "last_updated": datetime.now().isoformat(),
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved {len(seen_ids)} seen job IDs")


def filter_new_jobs(jobs: list, seen_ids: Set[str]) -> list:
    """Filter out jobs that have already been seen."""
    new_jobs = [job for job in jobs if job.id not in seen_ids]
    logger.info(f"Filtered {len(jobs)} jobs to {len(new_jobs)} new jobs")
    return new_jobs


def deduplicate_jobs(jobs: list) -> list:
    """Remove duplicate jobs based on URL."""
    seen_urls = set()
    unique_jobs = []

    for job in jobs:
        if job.url not in seen_urls:
            seen_urls.add(job.url)
            unique_jobs.append(job)

    logger.info(f"Deduplicated {len(jobs)} jobs to {len(unique_jobs)} unique jobs")
    return unique_jobs
