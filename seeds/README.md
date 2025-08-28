Authoritative Seeds Ingestion
============================

This folder is for authoritative domain lists you download externally (e.g., the .gov registry, state agency directories). Because the scraper should avoid guessing domains, these inputs help build a canonical list of government sites to crawl.

Expected CSV format
-------------------
The ingestion script accepts CSVs with the following headers (extra columns are ignored):

- domain: required, e.g., "example.gov"
- level: required, one of: federal, state, county, city, local
- name: optional human-friendly name (e.g., "State of California")
- state_code: optional 2-letter code for state-level jurisdictions (CA, TX, ...)

Example:

domain,level,name,state_code
usa.gov,federal,United States Federal Government,
ca.gov,state,State of California,CA
lacounty.gov,county,Los Angeles County,CA
cityofla.org,city,City of Los Angeles,CA

How to use
----------
1. Download or prepare CSVs that match the above headers.
2. Run the ingestion script:
   python scripts/ingest_authoritative_domains.py --db government_contacts.db --files seeds/*.csv
3. Then run the contact crawler (optional) to extract emails/phones from these sites.

