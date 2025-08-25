"""
Configuration settings for the USA.gov scraper
"""

import os
from pathlib import Path

# Base configuration
BASE_URL = "https://www.usa.gov/agency-index"
OUTPUT_DIR = Path(__file__).parent / "data"
LOGS_DIR = Path(__file__).parent / "logs"

# Scraping configuration
REQUEST_DELAY = 1.0  # Delay between requests in seconds
MAX_RETRIES = 3
RETRY_DELAY = 2.0
TIMEOUT = 30

# Cache configuration
CACHE_ENABLED = True
CACHE_EXPIRY_HOURS = 24

# Output configuration
CSV_FILENAME = "usa_gov_agencies.csv"
JSON_FILENAME = "usa_gov_agencies.json"

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Headers for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)