import os

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Search keywords for AI jobs and developers
KEYWORDS = [
    # AI/ML
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "AI engineer",
    "ML engineer",
    "data scientist",
    "NLP engineer",
    "computer vision",
    "LLM",
    "prompt engineer",
    "intelligenza artificiale",
    # Sviluppatori
    "sviluppatore app",
    "app developer",
    "mobile developer",
    "iOS developer",
    "Android developer",
    "sviluppatore siti web",
    "web developer",
    "frontend developer",
    "backend developer",
    "full stack developer",
]

# Location filters (Italy focused)
LOCATIONS = [
    "Italia",
    "Italy",
    "Milano",
    "Roma",
    "Remote",
    "Remoto",
]

# Request settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.5  # seconds between requests
MAX_RETRIES = 3

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Data storage
SEEN_JOBS_FILE = "data/seen_jobs.json"
