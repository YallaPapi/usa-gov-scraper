#!/usr/bin/env python3
"""
Simple Contact Crawler from Websites in DB (Requests-based)

Fetches website homepages from the database, detects likely contact pages,
extracts emails and phone numbers, and stores results in the `contacts` table
linked to a synthetic department per website.

Usage:
  python scripts/crawl_contacts_from_db.py --db government_contacts.db --limit 50 --level state

Note: This is a conservative, requests+bs4-based crawler meant for initial
coverage. It respects politeness via small delays and only follows obvious
"contact"-like links. For larger-scale crawling, add rate limiting per domain
and consider caching.
"""

import argparse
import re
import time
import sqlite3
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE)
PHONE_RES = [
    re.compile(r"\b\d{3}-\d{3}-\d{4}\b"),
    re.compile(r"\b\(\d{3}\)\s*\d{3}-\d{4}\b"),
    re.compile(r"\b\d{3}\.\d{3}\.\d{4}\b"),
    re.compile(r"\b1-\d{3}-\d{3}-\d{4}\b"),
]


def fetch(url: str, timeout: float = 20.0) -> str | None:
    try:
        resp = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; GovCrawler/1.0)'
        })
        if resp.status_code == 200:
            return resp.text
    except Exception:
        return None
    return None


def detect_contact_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    links = []
    for a in soup.find_all('a', href=True):
        href = a.get('href')
        text = (a.get_text() or '').strip().lower()
        if any(k in (href.lower() or '') or k in text for k in ['contact', 'staff', 'directory', 'about']):
            full = urljoin(base_url, href)
            links.append(full)
    return list(dict.fromkeys(links))[:10]


def extract_contacts(text: str) -> tuple[list[str], list[str]]:
    emails = set(EMAIL_RE.findall(text or ''))
    phones = set()
    for rx in PHONE_RES:
        for m in rx.findall(text or ''):
            phones.add(m)
    return sorted(emails), sorted(phones)


def upsert_department_for_site(conn: sqlite3.Connection, jurisdiction_id: int, site_domain: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT department_id FROM departments WHERE jurisdiction_id=? AND name=?",
        (jurisdiction_id, site_domain),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """
        INSERT INTO departments (jurisdiction_id, name, category, description, website_url)
        VALUES (?, ?, 'government_site', '', ?)
        """,
        (jurisdiction_id, site_domain, f"https://{site_domain}"),
    )
    return cur.lastrowid


def insert_contacts(conn: sqlite3.Connection, department_id: int, emails: list[str], phones: list[str]) -> int:
    cur = conn.cursor()
    inserted = 0
    # Email contacts
    for email in emails:
        cur.execute(
            """
            INSERT INTO contacts (department_id, contact_type, name, title, email, phone, validation_status)
            VALUES (?, 'general', '', '', ?, '', 'pending')
            """,
            (department_id, email),
        )
        inserted += 1
    # Phone contacts
    for phone in phones:
        cur.execute(
            """
            INSERT INTO contacts (department_id, contact_type, name, title, email, phone, validation_status)
            VALUES (?, 'general', '', '', '', ?, 'pending')
            """,
            (department_id, phone),
        )
        inserted += 1
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Crawl websites from DB and extract basic contacts")
    parser.add_argument('--db', required=True, help='Path to SQLite DB')
    parser.add_argument('--level', default='state', help='Jurisdiction level to crawl (federal/state/county/city/local)')
    parser.add_argument('--limit', type=int, default=50, help='Max sites to crawl')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT w.website_id, w.domain, w.full_url, j.jurisdiction_id
            FROM websites w
            JOIN jurisdictions j ON w.jurisdiction_id = j.jurisdiction_id
            WHERE j.level = ?
            ORDER BY j.name
            LIMIT ?
            """,
            (args.level, args.limit),
        )
        sites = cur.fetchall()

        total_contacts = 0
        for row in sites:
            domain = row['domain']
            base_url = row['full_url'] or f"https://{domain}"
            html = fetch(base_url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'html.parser')
            emails, phones = extract_contacts(soup.get_text())

            # Follow a few likely contact links
            for link in detect_contact_links(base_url, soup)[:3]:
                time.sleep(args.delay)
                page = fetch(link)
                if not page:
                    continue
                ee, pp = extract_contacts(page)
                emails.extend(ee)
                phones.extend(pp)

            # Insert into DB under a synthetic department per site
            dept_id = upsert_department_for_site(conn, row['jurisdiction_id'], domain)
            inserted = insert_contacts(conn, dept_id, sorted(set(emails)), sorted(set(phones)))
            conn.commit()
            total_contacts += inserted

            time.sleep(args.delay)

        print(f"✅ Crawled {len(sites)} sites, inserted {total_contacts} contacts.")
    finally:
        conn.close()


if __name__ == '__main__':
    main()

