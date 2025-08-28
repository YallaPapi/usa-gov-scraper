#!/usr/bin/env python3
"""
Database Bootstrap for Government Contacts API
Creates SQLite schema and FTS indexes compatible with export utilities and API.

Usage:
  python scripts/db_init.py --db government_contacts.db
"""

import argparse
import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- Jurisdictions (federal/state/county/city)
CREATE TABLE IF NOT EXISTS jurisdictions (
    jurisdiction_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    level TEXT NOT NULL,                -- federal/state/county/city/local
    level_order INTEGER NOT NULL,       -- used for ordering
    state_code TEXT,                    -- optional state code
    county_name TEXT,                   -- optional county name
    city_name TEXT,                     -- optional city name
    website_url TEXT
);

-- Departments (agencies/offices under jurisdictions)
CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY,
    jurisdiction_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,             -- e.g., federal_agency, law_enforcement
    description TEXT,
    website_url TEXT,
    main_email TEXT,
    main_phone TEXT,
    address_street TEXT,
    address_city TEXT,
    address_state TEXT,
    address_zip TEXT,
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id)
);

-- Contacts (people/points of contact under departments)
CREATE TABLE IF NOT EXISTS contacts (
    contact_id INTEGER PRIMARY KEY,
    department_id INTEGER NOT NULL,
    contact_type TEXT NOT NULL,         -- official/staff/general/emergency
    name TEXT,
    title TEXT,
    email TEXT,
    phone TEXT,
    mobile TEXT,
    fax TEXT,
    office_location TEXT,
    contact_hours TEXT,
    specializations TEXT,               -- JSON array (text)
    languages_spoken TEXT,              -- JSON array (text)
    validation_status TEXT DEFAULT 'pending',
    last_validated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- Websites (domains/URLs associated with departments or jurisdictions)
CREATE TABLE IF NOT EXISTS websites (
    website_id INTEGER PRIMARY KEY,
    jurisdiction_id INTEGER,
    department_id INTEGER,
    domain TEXT,
    full_url TEXT,
    site_type TEXT,
    last_scraped TIMESTAMP,
    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(jurisdiction_id),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- FTS5 virtual tables for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts USING fts5(
    contact_name, title, email, phone,
    content='contacts', content_rowid='contact_id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS departments_fts USING fts5(
    name, description, category,
    content='departments', content_rowid='department_id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS jurisdictions_fts USING fts5(
    name, level, state_code, county_name, city_name,
    content='jurisdictions', content_rowid='jurisdiction_id'
);

-- Triggers to keep FTS indexes in sync
-- Contacts
CREATE TRIGGER IF NOT EXISTS contacts_ai AFTER INSERT ON contacts BEGIN
  INSERT INTO contacts_fts(rowid, contact_name, title, email, phone)
  VALUES (new.contact_id, new.name, new.title, new.email, new.phone);
END;

CREATE TRIGGER IF NOT EXISTS contacts_ad AFTER DELETE ON contacts BEGIN
  INSERT INTO contacts_fts(contacts_fts, rowid, contact_name, title, email, phone)
  VALUES('delete', old.contact_id, old.name, old.title, old.email, old.phone);
END;

CREATE TRIGGER IF NOT EXISTS contacts_au AFTER UPDATE ON contacts BEGIN
  INSERT INTO contacts_fts(contacts_fts, rowid, contact_name, title, email, phone)
  VALUES('delete', old.contact_id, old.name, old.title, old.email, old.phone);
  INSERT INTO contacts_fts(rowid, contact_name, title, email, phone)
  VALUES (new.contact_id, new.name, new.title, new.email, new.phone);
END;

-- Departments
CREATE TRIGGER IF NOT EXISTS departments_ai AFTER INSERT ON departments BEGIN
  INSERT INTO departments_fts(rowid, name, description, category)
  VALUES (new.department_id, new.name, new.description, new.category);
END;

CREATE TRIGGER IF NOT EXISTS departments_ad AFTER DELETE ON departments BEGIN
  INSERT INTO departments_fts(departments_fts, rowid, name, description, category)
  VALUES('delete', old.department_id, old.name, old.description, old.category);
END;

CREATE TRIGGER IF NOT EXISTS departments_au AFTER UPDATE ON departments BEGIN
  INSERT INTO departments_fts(departments_fts, rowid, name, description, category)
  VALUES('delete', old.department_id, old.name, old.description, old.category);
  INSERT INTO departments_fts(rowid, name, description, category)
  VALUES (new.department_id, new.name, new.description, new.category);
END;

-- Jurisdictions
CREATE TRIGGER IF NOT EXISTS jurisdictions_ai AFTER INSERT ON jurisdictions BEGIN
  INSERT INTO jurisdictions_fts(rowid, name, level, state_code, county_name, city_name)
  VALUES (new.jurisdiction_id, new.name, new.level, new.state_code, new.county_name, new.city_name);
END;

CREATE TRIGGER IF NOT EXISTS jurisdictions_ad AFTER DELETE ON jurisdictions BEGIN
  INSERT INTO jurisdictions_fts(jurisdictions_fts, rowid, name, level, state_code, county_name, city_name)
  VALUES('delete', old.jurisdiction_id, old.name, old.level, old.state_code, old.county_name, old.city_name);
END;

CREATE TRIGGER IF NOT EXISTS jurisdictions_au AFTER UPDATE ON jurisdictions BEGIN
  INSERT INTO jurisdictions_fts(jurisdictions_fts, rowid, name, level, state_code, county_name, city_name)
  VALUES('delete', old.jurisdiction_id, old.name, old.level, old.state_code, old.county_name, old.city_name);
  INSERT INTO jurisdictions_fts(rowid, name, level, state_code, county_name, city_name)
  VALUES (new.jurisdiction_id, new.name, new.level, new.state_code, new.county_name, new.city_name);
END;
"""


def ensure_parent_dirs(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Initialize SQLite database schema for Government Contacts API")
    parser.add_argument("--db", required=True, help="Path to SQLite database file")
    args = parser.parse_args()

    db_path = Path(args.db)
    ensure_parent_dirs(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print(f"✅ Database initialized at: {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

