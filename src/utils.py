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

# European countries (EU-27 + UK + Switzerland) with common variations
EUROPEAN_COUNTRIES = {
    # Austria
    "austria", "osterreich", "vienna", "wien", "salzburg", "graz", "linz",
    # Belgium
    "belgium", "belgique", "belgie", "brussels", "bruxelles", "antwerp", "ghent",
    # Bulgaria
    "bulgaria", "sofia", "plovdiv", "varna",
    # Croatia
    "croatia", "hrvatska", "zagreb", "split", "rijeka",
    # Cyprus
    "cyprus", "nicosia", "limassol",
    # Czech Republic
    "czech republic", "czechia", "cesko", "prague", "praha", "brno",
    # Denmark
    "denmark", "danmark", "copenhagen", "kobenhavn", "aarhus",
    # Estonia
    "estonia", "eesti", "tallinn", "tartu",
    # Finland
    "finland", "suomi", "helsinki", "espoo", "tampere",
    # France
    "france", "paris", "lyon", "marseille", "toulouse", "nice", "nantes", "strasbourg", "bordeaux", "lille",
    # Germany
    "germany", "deutschland", "berlin", "munich", "munchen", "frankfurt", "hamburg", "cologne", "koln", "dusseldorf", "stuttgart", "leipzig", "dresden",
    # Greece
    "greece", "hellas", "ellada", "athens", "athina", "thessaloniki",
    # Hungary
    "hungary", "magyarorszag", "budapest", "debrecen",
    # Ireland
    "ireland", "dublin", "cork", "galway", "limerick",
    # Italy
    "italy", "italia", "italian", "milan", "milano", "rome", "roma", "turin", "torino", "florence", "firenze",
    "naples", "napoli", "bologna", "genoa", "genova", "venice", "venezia", "verona", "padova", "padua",
    "bari", "palermo", "catania", "trieste", "brescia", "parma", "modena", "reggio emilia", "bergamo", "monza",
    "rimini", "perugia", "cagliari", "trento", "bolzano", "lombardia", "lombardy", "lazio", "piemonte", "piedmont",
    "toscana", "tuscany", "emilia-romagna", "emilia romagna", "veneto", "campania", "sicilia", "sicily",
    "puglia", "apulia", "calabria", "sardegna", "sardinia", "liguria", "friuli", "trentino", "marche", "abruzzo", "umbria",
    # Latvia
    "latvia", "latvija", "riga",
    # Lithuania
    "lithuania", "lietuva", "vilnius", "kaunas",
    # Luxembourg
    "luxembourg", "luxemburg",
    # Malta
    "malta", "valletta",
    # Netherlands
    "netherlands", "nederland", "holland", "amsterdam", "rotterdam", "the hague", "den haag", "utrecht", "eindhoven",
    # Poland
    "poland", "polska", "warsaw", "warszawa", "krakow", "wroclaw", "gdansk", "poznan", "lodz", "katowice",
    # Portugal
    "portugal", "lisboa", "lisbon", "porto", "oporto", "braga", "coimbra",
    # Romania
    "romania", "bucuresti", "bucharest", "cluj", "timisoara", "iasi",
    # Slovakia
    "slovakia", "slovensko", "bratislava", "kosice",
    # Slovenia
    "slovenia", "slovenija", "ljubljana", "maribor",
    # Spain
    "spain", "espana", "madrid", "barcelona", "valencia", "seville", "sevilla", "bilbao", "malaga", "zaragoza",
    # Sweden
    "sweden", "sverige", "stockholm", "gothenburg", "goteborg", "malmo", "uppsala",
    # UK
    "united kingdom", "uk", "britain", "great britain", "england", "scotland", "wales", "northern ireland",
    "london", "manchester", "birmingham", "leeds", "glasgow", "edinburgh", "liverpool", "bristol", "sheffield", "newcastle", "nottingham", "cambridge", "oxford",
    # Switzerland
    "switzerland", "schweiz", "suisse", "svizzera", "zurich", "zuerich", "geneva", "geneve", "basel", "bern", "lausanne", "lugano",
    # European identifiers
    "eu", "europe", "european", "emea",
}

# Italian locations for priority sorting
ITALIAN_LOCATIONS = {
    # Country
    "italy", "italia", "italian",
    # Major cities
    "milan", "milano", "rome", "roma", "turin", "torino", "florence", "firenze",
    "naples", "napoli", "bologna", "genoa", "genova", "venice", "venezia",
    "verona", "padova", "padua", "bari", "palermo", "catania", "trieste",
    "brescia", "parma", "modena", "reggio emilia", "bergamo", "monza",
    "rimini", "perugia", "cagliari", "trento", "bolzano",
    # Regions
    "lombardia", "lombardy", "lazio", "piemonte", "piedmont", "toscana", "tuscany",
    "emilia-romagna", "emilia romagna", "veneto", "campania", "sicilia", "sicily",
    "puglia", "apulia", "calabria", "sardegna", "sardinia", "liguria",
    "friuli-venezia giulia", "friuli", "trentino-alto adige", "trentino",
    "marche", "abruzzo", "umbria", "basilicata", "molise", "valle d'aosta",
}

# Remote work keywords
REMOTE_KEYWORDS = {
    "remote", "remoto", "anywhere", "worldwide", "global", "work from home", "wfh", "telelavoro", "full remote", "fully remote",
}


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


def is_european_location(location: str) -> bool:
    """Check if a location string indicates a European location."""
    if not location:
        return False

    location_lower = location.lower().strip()

    # Check for European location first
    for eu_location in EUROPEAN_COUNTRIES:
        if eu_location in location_lower:
            return True

    # Check for remote WITH European context (e.g., "Remote - Europe", "EU Remote")
    is_remote = any(remote_kw in location_lower for remote_kw in REMOTE_KEYWORDS)
    if is_remote:
        # Only include remote if it mentions Europe/EU or has no specific country
        # Exclude if it mentions non-EU countries
        non_eu_indicators = ["usa", "us ", "united states", "america", "canada", "asia",
                            "india", "china", "japan", "australia", "brazil", "mexico",
                            "singapore", "hong kong", "israel", "uae", "dubai"]
        for indicator in non_eu_indicators:
            if indicator in location_lower:
                return False
        # Include remote jobs that don't specify a non-EU location
        return True

    return False


# Non-EU indicators to check in job title and description
NON_EU_INDICATORS = [
    # Countries
    "usa", "u.s.a", "united states", "america", "canada", "india", "china", "japan",
    "australia", "brazil", "mexico", "singapore", "hong kong", "israel", "uae", "dubai",
    # US States and cities
    "california", "new york", "texas", "florida", "washington", "massachusetts",
    "san francisco", "los angeles", "seattle", "boston", "chicago", "austin", "denver",
    "pittsburgh", "atlanta", "miami", "phoenix", "portland", "san diego", "san jose",
    "raleigh", "charlotte", "nashville", "detroit", "minneapolis", "philadelphia",
    # State abbreviations (with comma to avoid false positives)
    ", ca", ", ny", ", tx", ", fl", ", wa", ", ma", ", il", ", co", ", nc", ", ga",
    ", az", ", or", ", pa", ", oh", ", mi", ", mn", ", va", ", nj", ", md",
]


def is_non_eu_job(job) -> bool:
    """Check if a job appears to be from a non-EU country based on title, location, and salary."""
    # Combine all text fields to check
    text_to_check = " ".join([
        (job.title or "").lower(),
        (job.location or "").lower(),
        (job.company or "").lower(),
        (job.description or "").lower(),
    ])

    # Check for non-EU indicators
    for indicator in NON_EU_INDICATORS:
        if indicator in text_to_check:
            return True

    # Check for USD salary (strong indicator of US job)
    if job.salary:
        salary_lower = job.salary.lower()
        if "$" in job.salary or "usd" in salary_lower:
            return True

    return False


def filter_european_jobs(jobs: list) -> list:
    """Filter jobs to include only those in Europe (EU-27 + UK + Switzerland)."""
    european_jobs = []

    for job in jobs:
        # First check: location must be European or generic remote
        if not is_european_location(job.location):
            continue

        # Second check: exclude if job has non-EU indicators in title/description
        if is_non_eu_job(job):
            continue

        european_jobs.append(job)

    excluded_count = len(jobs) - len(european_jobs)
    logger.info(f"European filter: kept {len(european_jobs)} jobs, excluded {excluded_count} non-European")

    return european_jobs


def is_italian_location(location: str) -> bool:
    """Check if a location string indicates an Italian location."""
    if not location:
        return False

    location_lower = location.lower().strip()

    for italian_loc in ITALIAN_LOCATIONS:
        if italian_loc in location_lower:
            return True

    return False


def is_remote_location(location: str) -> bool:
    """Check if a location string indicates a remote position."""
    if not location:
        return False

    location_lower = location.lower().strip()

    for remote_kw in REMOTE_KEYWORDS:
        if remote_kw in location_lower:
            return True

    return False


def get_location_priority(job) -> int:
    """
    Get sorting priority for a job based on location.

    Priority:
        0 - Italian jobs (highest priority, shown first) - includes Italian remote
        1 - Other European jobs
        2 - Remote jobs (non-Italian, shown last)
    """
    location = job.location or ""

    # Check Italian first (even if also marked as remote)
    if is_italian_location(location):
        return 0

    # Remote jobs last (only if not Italian)
    if is_remote_location(location):
        return 2

    # Other European jobs in the middle
    return 1


def sort_jobs_by_location_priority(jobs: list) -> list:
    """
    Sort jobs by location priority:
    1. Italian jobs first (including Italian remote)
    2. Other European jobs second
    3. Remote jobs last (non-Italian)
    """
    sorted_jobs = sorted(jobs, key=get_location_priority)

    # Log distribution for debugging
    italian_count = sum(1 for j in jobs if get_location_priority(j) == 0)
    european_count = sum(1 for j in jobs if get_location_priority(j) == 1)
    remote_count = sum(1 for j in jobs if get_location_priority(j) == 2)

    logger.info(f"Location sort: {italian_count} Italian, {european_count} EU, {remote_count} Remote")

    return sorted_jobs
