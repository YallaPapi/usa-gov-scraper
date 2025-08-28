#!/usr/bin/env python3
"""
Discover Additional .gov/.us Sites from Seed Pages

Given a list of seed websites (e.g., agency homepages), fetch their
homepages, extract outbound links, and add newly discovered .gov/.us domains
to the database as websites + jurisdictions. This is a conservative, single-hop
discovery (optionally repeatable) to expand coverage without guessing domains.

Usage examples:
  # Discover from a cleaned agencies CSV
  python scripts/discover_gov_sites.py --db government_contacts.db \
      --agencies-csv output_clean/usa_gov_agencies_*.csv --limit 100

  # Discover from existing DB websites at specific level
  python scripts/discover_gov_sites.py --db government_contacts.db \
      --from-level federal --limit 100
"""

import argparse
import glob
import re
import sqlite3
from pathlib import Path
from typing import Iterable, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


GOV_DOMAIN_RE = re.compile(r"\.gov$|\.us$", re.IGNORECASE)
USER_AGENT = 'Mozilla/5.0 (compatible; GovDiscovery/1.0)'

LEVEL_ORDER = {
    'federal': 1,
    'state': 2,
    'county': 3,
    'city': 4,
    'local': 5,
}


def fetch_html(url: str, timeout: float = 20.0) -> str | None:
    try:
        resp = requests.get(url, timeout=timeout, headers={'User-Agent': USER_AGENT})
        if resp.status_code == 200:
            return resp.text
    except Exception:
        return None
    return None


def normalize_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        # Strip leading www.
        return netloc[4:] if netloc.startswith('www.') else netloc
    except Exception:
        return ''


def extract_gov_links(base_url: str, html: str) -> Set[str]:
    soup = BeautifulSoup(html, 'html.parser')
    found: Set[str] = set()
    for a in soup.find_all('a', href=True):
        href = a.get('href') or ''
        full = urljoin(base_url, href)
        domain = normalize_domain(full)
        if domain and GOV_DOMAIN_RE.search(domain):
            # ignore usa.gov aggregator
            if domain in {'usa.gov', 'www.usa.gov'}:
                continue
            found.add(domain)
    return found


def upsert_jurisdiction(conn: sqlite3.Connection, name: str, level: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT jurisdiction_id FROM jurisdictions WHERE name=? AND level=?",
        (name, level),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """
        INSERT INTO jurisdictions (name, level, level_order, state_code, website_url)
        VALUES (?, ?, ?, '', '')
        """,
        (name, level, LEVEL_ORDER.get(level, 5)),
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


def iter_agency_urls_from_csv(patterns: list[str]) -> Iterable[str]:
    files: list[Path] = []
    for p in patterns:
        files.extend([Path(x) for x in glob.glob(p)])
    seen = set()
    for fp in sorted(set(files)):
        try:
            import csv
            with open(fp, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = (row.get('homepage_url') or '').strip()
                    if url and url.lower() != 'see usa.gov' and url not in seen:
                        seen.add(url)
                        yield url
        except Exception:
            continue


def iter_urls_from_db(conn: sqlite3.Connection, level: str, limit: int) -> Iterable[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT w.full_url
        FROM websites w
        JOIN jurisdictions j ON w.jurisdiction_id = j.jurisdiction_id
        WHERE j.level = ?
        LIMIT ?
        """,
        (level, limit),
    )
    for (full_url,) in cur.fetchall():
        yield full_url


def main():
    parser = argparse.ArgumentParser(description='Discover .gov/.us sites from seed pages')
    parser.add_argument('--db', required=True, help='Path to SQLite DB')
    parser.add_argument('--agencies-csv', nargs='*', help='CSV glob(s) for seed agency lists')
    parser.add_argument('--from-level', choices=['federal', 'state', 'county', 'city', 'local'], help='Use existing DB websites at this level as seeds')
    parser.add_argument('--limit', type=int, default=100, help='Max seed pages to fetch')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    parser.add_argument('--default-level', default='local', help='Level to assign to newly discovered sites (default: local)')
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        # Build list of seed URLs
        seeds: list[str] = []
        if args.agencies_csv:
            for url in iter_agency_urls_from_csv(args.agencies_csv):
                seeds.append(url)
                if len(seeds) >= args.limit:
                    break
        elif args.from_level:
            seeds.extend(list(iter_urls_from_db(conn, args.from_level, args.limit)))
        else:
            print('Provide either --agencies-csv or --from-level seeds')
            return

        print(f"Fetching {len(seeds)} seed pages for discovery…")
        discovered_domains: Set[str] = set()
        for i, url in enumerate(seeds, 1):
            html = fetch_html(url)
            if not html:
                continue
            domains = extract_gov_links(url, html)
            discovered_domains.update(domains)
            # polite delay
            if args.delay:
                import time
                time.sleep(args.delay)

        print(f"Discovered {len(discovered_domains)} .gov/.us domains")

        # Upsert into DB as jurisdictions/websites with default level
        inserted_websites = 0
        for domain in sorted(discovered_domains):
            name = domain
            jid = upsert_jurisdiction(conn, name=name, level=args.default_level)
            upsert_website(conn, jurisdiction_id=jid, domain=domain)
            inserted_websites += 1
        conn.commit()
        print(f"✅ Inserted/updated {inserted_websites} websites at level '{args.default_level}'")
    finally:
        conn.close()


if __name__ == '__main__':
    main()

