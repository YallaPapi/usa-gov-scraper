#!/usr/bin/env python3
"""
Load Agencies CSV into SQLite DB
Minimal loader to populate jurisdictions, departments, and websites from
scraped USA.gov agencies CSVs (section, agency_name, homepage_url, parent_department).

Usage:
  python scripts/load_from_csv.py --db government_contacts.db --agencies scraped_data/usa_gov_agencies_*.csv
"""

import argparse
import csv
import glob
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


def upsert_federal_jurisdiction(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT jurisdiction_id FROM jurisdictions WHERE name = ? AND level = ?
        """,
        ("United States Federal Government", "federal"),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO jurisdictions (name, level, level_order, state_code, website_url)
        VALUES (?, 'federal', 1, '', 'https://usa.gov')
        """,
        ("United States Federal Government",),
    )
    return cur.lastrowid


def domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def load_agencies_csv(conn: sqlite3.Connection, csv_path: Path, federal_jid: int) -> int:
    cur = conn.cursor()
    seen_departments = set()
    inserted = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("agency_name") or "").strip()
            url = (row.get("homepage_url") or "").strip()
            if not name or not url or url.lower() == "see usa.gov":
                continue

            key = (name.lower(), url.lower())
            if key in seen_departments:
                continue
            seen_departments.add(key)

            # Insert department (treat agency as department)
            cur.execute(
                """
                INSERT INTO departments (
                    jurisdiction_id, name, category, description, website_url,
                    main_email, main_phone, address_street, address_city, address_state, address_zip
                ) VALUES (?, ?, 'federal_agency', '', ?, '', '', '', '', '', '')
                """,
                (federal_jid, name, url),
            )
            dept_id = cur.lastrowid

            # Insert website record
            cur.execute(
                """
                INSERT INTO websites (jurisdiction_id, department_id, domain, full_url, site_type)
                VALUES (?, ?, ?, ?, 'department')
                """,
                (federal_jid, dept_id, domain_from_url(url), url),
            )
            inserted += 1

    return inserted


def main():
    parser = argparse.ArgumentParser(description="Load agencies CSV(s) into SQLite DB")
    parser.add_argument("--db", required=True, help="Path to SQLite database file")
    parser.add_argument("--agencies", required=True, nargs="+", help="Glob(s) for agencies CSV files")
    args = parser.parse_args()

    # Resolve files from globs
    files = []
    for g in args.agencies:
        files.extend(glob.glob(g))
    files = [Path(p) for p in sorted(set(files)) if Path(p).exists()]
    if not files:
        print("No agencies CSV files matched.")
        return

    conn = sqlite3.connect(args.db)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        federal_jid = upsert_federal_jurisdiction(conn)
        total_inserted = 0
        for fp in files:
            inserted = load_agencies_csv(conn, fp, federal_jid)
            total_inserted += inserted
            conn.commit()
            print(f"Loaded {inserted} departments from {fp.name}")
        print(f"✅ Finished loading. Total departments inserted: {total_inserted}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

