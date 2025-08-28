#!/usr/bin/env python3
"""
Ingest Authoritative Government Domains into the Database

Reads CSV files with columns: domain, level (federal/state/county/city/local),
name (optional), state_code (optional). Inserts corresponding jurisdictions
and websites records.

Usage:
  python scripts/ingest_authoritative_domains.py --db government_contacts.db --files seeds/*.csv
"""

import argparse
import csv
import glob
import sqlite3
from pathlib import Path


LEVEL_ORDER = {
    'federal': 1,
    'state': 2,
    'county': 3,
    'city': 4,
    'local': 5,
}


def upsert_jurisdiction(conn: sqlite3.Connection, name: str, level: str, state_code: str | None) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT jurisdiction_id FROM jurisdictions WHERE name=? AND level=? AND IFNULL(state_code,'')=IFNULL(?, '')",
        (name, level, state_code or ""),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO jurisdictions (name, level, level_order, state_code, website_url)
        VALUES (?, ?, ?, ?, '')
        """,
        (name, level, LEVEL_ORDER.get(level, 99), state_code or ""),
    )
    return cur.lastrowid


def upsert_website(conn: sqlite3.Connection, jurisdiction_id: int, domain: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT website_id FROM websites WHERE jurisdiction_id=? AND domain=?",
        (jurisdiction_id, domain),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO websites (jurisdiction_id, department_id, domain, full_url, site_type)
        VALUES (?, NULL, ?, ?, 'jurisdiction')
        """,
        (jurisdiction_id, domain, f"https://{domain}"),
    )
    return cur.lastrowid


def ingest_file(conn: sqlite3.Connection, file_path: Path) -> dict:
    inserted = {'jurisdictions': 0, 'websites': 0}
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = (row.get('domain') or '').strip().lower()
            level = (row.get('level') or '').strip().lower()
            name = (row.get('name') or '').strip() or domain
            state_code = (row.get('state_code') or '').strip().upper() or None
            if not domain or not level:
                continue

            jid_before = _count(conn, 'jurisdictions')
            wid_before = _count(conn, 'websites')

            jid = upsert_jurisdiction(conn, name=name, level=level, state_code=state_code)
            upsert_website(conn, jurisdiction_id=jid, domain=domain)

            inserted['jurisdictions'] += _count(conn, 'jurisdictions') - jid_before
            inserted['websites'] += _count(conn, 'websites') - wid_before

    return inserted


def _count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Ingest authoritative domains into DB")
    parser.add_argument('--db', required=True, help='Path to SQLite DB')
    parser.add_argument('--files', required=True, nargs='+', help='CSV glob(s) with domain seeds')
    args = parser.parse_args()

    files: list[Path] = []
    for g in args.files:
        for path in glob.glob(g):
            p = Path(path)
            if p.exists():
                files.append(p)

    if not files:
        print('No input files found.')
        return

    conn = sqlite3.connect(args.db)
    try:
        total = {'jurisdictions': 0, 'websites': 0}
        for fp in files:
            stats = ingest_file(conn, fp)
            conn.commit()
            print(f"Ingested {fp.name}: +{stats['jurisdictions']} jurisdictions, +{stats['websites']} websites")
            total['jurisdictions'] += stats['jurisdictions']
            total['websites'] += stats['websites']
        print(f"✅ Done. Total inserted: {total}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()

