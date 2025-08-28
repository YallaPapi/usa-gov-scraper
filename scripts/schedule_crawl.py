#!/usr/bin/env python3
"""
Scheduled Crawler: pick next websites by least recently scraped and extract contacts.

This script processes a batch of sites per run, updates websites.last_scraped,
and uses the same conservative extraction as the basic crawler. Run it via cron/
Task Scheduler to incrementally refresh contacts without re-crawling everything.

Usage:
  python scripts/schedule_crawl.py --db government_contacts.db --level state --batch 50 --delay 1.0
"""

import argparse
import sqlite3
import time
from datetime import datetime

from scripts.crawl_contacts_from_db import fetch, detect_contact_links, extract_contacts_from_page, upsert_department_for_site, insert_contacts
from bs4 import BeautifulSoup


def main():
    parser = argparse.ArgumentParser(description='Scheduled batch crawler')
    parser.add_argument('--db', required=True, help='Path to SQLite DB')
    parser.add_argument('--level', default='state', help='Jurisdiction level to crawl')
    parser.add_argument('--batch', type=int, default=50, help='Batch size per run')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests')
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Pick least recently scraped first (NULLs first)
        cur.execute(
            """
            SELECT w.website_id, w.domain, w.full_url, j.jurisdiction_id
            FROM websites w
            JOIN jurisdictions j ON w.jurisdiction_id = j.jurisdiction_id
            WHERE j.level = ?
            ORDER BY CASE WHEN w.last_scraped IS NULL THEN 0 ELSE 1 END, w.last_scraped ASC
            LIMIT ?
            """,
            (args.level, args.batch),
        )
        rows = cur.fetchall()
        processed = 0
        contacts_total = 0
        for row in rows:
            base_url = row['full_url'] or f"https://{row['domain']}"
            html = fetch(base_url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'html.parser')
            emails, phones = extract_contacts_from_page(html)
            for link in detect_contact_links(base_url, soup)[:3]:
                time.sleep(args.delay)
                page = fetch(link)
                if page:
                    ee, pp = extract_contacts_from_page(page)
                    emails.extend(ee)
                    phones.extend(pp)
            dept_id = upsert_department_for_site(conn, row['jurisdiction_id'], row['domain'])
            inserted = insert_contacts(conn, dept_id, sorted(set(emails)), sorted(set(phones)))
            cur.execute("UPDATE websites SET last_scraped = ? WHERE website_id = ?", (datetime.utcnow().isoformat(), row['website_id']))
            conn.commit()
            processed += 1
            contacts_total += inserted
            time.sleep(args.delay)
        print(f"✅ Processed {processed} sites, inserted {contacts_total} contacts.")
    finally:
        conn.close()


if __name__ == '__main__':
    main()

