#!/usr/bin/env python3
"""
Quick test to scrape multiple real agencies and show actual results
"""

import csv
from scrapers.email_scraper import GovernmentEmailScraper
import logging

def main():
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    print("🏛️ REAL Government Email Scraping Test")
    print("=" * 50)
    
    # Load agencies with real URLs
    agencies_file = "scraped_data/usa_gov_agencies_20250825_225741.csv"
    
    # Create a test file with first 5 agencies that have real URLs
    test_agencies = []
    with open(agencies_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('homepage_url', '').strip()
            if url and url.startswith('http') and len(test_agencies) < 5:
                test_agencies.append(row)
    
    print(f"📊 Testing with {len(test_agencies)} real federal agencies:")
    for agency in test_agencies:
        print(f"  • {agency['agency_name']}: {agency['homepage_url']}")
    
    # Create test CSV
    test_csv = "test_5_agencies.csv"
    with open(test_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section', 'parent_department'])
        writer.writeheader()
        writer.writerows(test_agencies)
    
    print(f"\n🚀 Starting real scraping...")
    
    # Run the scraper
    scraper = GovernmentEmailScraper("test_results")
    result = scraper.scrape_federal_agencies(test_csv)
    
    if result['success']:
        print(f"\n✅ REAL SCRAPING RESULTS:")
        print(f"   • Agencies scraped: {result['agencies_scraped']}")
        print(f"   • Unique emails found: {result['unique_emails_found']}")
        print(f"   • Gov sites discovered: {result['gov_sites_discovered']}")
        
        # Show sample emails
        stats = scraper.get_statistics()
        if stats['scraped_emails']:
            print(f"\n📧 Sample emails found:")
            for email in stats['scraped_emails'][:10]:
                print(f"     {email}")
    else:
        print(f"❌ Scraping failed: {result.get('error')}")
    
    # Cleanup
    import os
    os.remove(test_csv)

if __name__ == "__main__":
    main()