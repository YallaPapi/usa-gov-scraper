#!/usr/bin/env python3
"""
End-to-End Pipeline Runner (Simple Path)

Scrape -> Clean -> Initialize DB -> Load -> (Optional) Print summary

Usage:
  python scripts/run_pipeline.py --db government_contacts.db
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

from scraper.core import GovernmentAgencyScraper
from data_cleanup import DataCleanup
import subprocess


def run_scrape(output_dir: Path) -> Path:
    scraper = GovernmentAgencyScraper(rate_limit=0.5, max_retries=3)
    result = scraper.scrape_all_sections()
    agencies = result.get('agencies', [])
    paths = scraper.export_data(agencies, output_dir=str(output_dir))
    return Path(paths['csv'])


def run_cleanup(input_dir: Path, output_dir: Path):
    cleanup = DataCleanup(str(input_dir), str(output_dir))
    cleanup.process_directory()


def run_db_init(db_path: Path):
    subprocess.check_call(["python", "scripts/db_init.py", "--db", str(db_path)])


def run_load(db_path: Path, cleaned_dir: Path):
    pattern = str(cleaned_dir / "usa_gov_agencies_*.csv")
    subprocess.check_call(["python", "scripts/load_from_csv.py", "--db", str(db_path), "--agencies", pattern])


def main():
    parser = argparse.ArgumentParser(description="Run the simple end-to-end pipeline")
    parser.add_argument("--db", default="government_contacts.db", help="Path to SQLite DB")
    parser.add_argument("--discover", action="store_true", help="Run a single-hop .gov/.us discovery from agencies")
    parser.add_argument("--discover-limit", type=int, default=100, help="Max seed pages to fetch for discovery")
    args = parser.parse_args()

    root = Path.cwd()
    raw_dir = root / "scraped_data"
    clean_dir = root / "output_clean"
    db_path = Path(args.db)

    raw_dir.mkdir(exist_ok=True)
    clean_dir.mkdir(exist_ok=True)

    print("[1/4] Scraping agencies (simple mode)...")
    csv_path = run_scrape(raw_dir)
    print(f"  Wrote: {csv_path}")

    print("[2/4] Cleaning data...")
    run_cleanup(raw_dir, clean_dir)

    print("[3/4] Initializing database schema...")
    run_db_init(db_path)

    print("[4/4] Loading agencies into database...")
    run_load(db_path, clean_dir)

    if args.discover:
        print("[Optional] Discovering additional .gov/.us sites from agencies…")
        subprocess.check_call([
            "python", "scripts/discover_gov_sites.py",
            "--db", str(db_path),
            "--agencies-csv", str(clean_dir / "usa_gov_agencies_*.csv"),
            "--limit", str(args.discover_limit)
        ])

    print("✅ Pipeline completed.")
    print(f"   DB: {db_path}")
    print("   Set GOV_CONTACTS_DB_PATH to this path and start the API:")
    print("   python src/api/government_contacts_api.py")


if __name__ == "__main__":
    main()
