#!/usr/bin/env python3
"""
Utilities for extracting contacts from HTML pages.
Heuristics for mailto links, obfuscated emails, phone numbers, and
simple staff directory tables/lists.
"""

import re
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE)
PHONE_RES = [
    re.compile(r"\b\d{3}-\d{3}-\d{4}\b"),
    re.compile(r"\b\(\d{3}\)\s*\d{3}-\d{4}\b"),
    re.compile(r"\b\d{3}\.\d{3}\.\d{4}\b"),
    re.compile(r"\b1-\d{3}-\d{3}-\d{4}\b"),
]


def extract_basic_contacts(text: str):
    emails = set(EMAIL_RE.findall(text or ''))
    phones = set()
    for rx in PHONE_RES:
        phones.update(rx.findall(text or ''))
    return emails, phones


def extract_mailto_emails(soup: BeautifulSoup):
    emails = set()
    for a in soup.find_all('a', href=True):
        href = a.get('href') or ''
        if href.lower().startswith('mailto:'):
            addr = href.split(':', 1)[1].split('?')[0].strip()
            if addr:
                emails.add(addr)
    return emails


def parse_staff_directory(soup: BeautifulSoup):
    """Extract (name, title, email, phone) from simple directory tables/lists.
    Heuristics:
      - Tables with headers including 'Name' and (Email or Phone or Title)
      - Definition lists or lists with strong/b tags followed by contact details
    Returns list of dicts.
    """
    results = []
    # Table-based directories
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if not headers:
            continue
        if 'name' in headers and any(k in headers for k in ('email', 'phone', 'title')):
            idx = {h: i for i, h in enumerate(headers)}
            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if not tds or len(tds) < 1:
                    continue
                def get(col):
                    i = idx.get(col)
                    return tds[i].get_text(" ", strip=True) if i is not None and i < len(tds) else ''
                entry = {
                    'name': get('name'),
                    'title': get('title'),
                    'email': get('email'),
                    'phone': get('phone'),
                }
                if any(entry.values()):
                    results.append(entry)
    # List-based (fallback)
    for li in soup.find_all('li'):
        text = li.get_text(" ", strip=True)
        if not text:
            continue
        if any(k in text.lower() for k in ('email', '@', 'phone', 'tel', 'contact')):
            # naive split
            results.append({'name': '', 'title': '', 'email': '', 'phone': ''})
    return results

