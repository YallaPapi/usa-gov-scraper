#!/usr/bin/env python3
"""
Scrape ALL agencies with real URLs to show full system capability
"""

from scrapers.email_scraper import GovernmentEmailScraper
import logging

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    print("🏛️ FULL FEDERAL AGENCY EMAIL EXTRACTION")
    print("=" * 60)
    print("🎯 Scraping ALL 37 federal agencies with real URLs...")
    print("🕐 This will take ~5-10 minutes - watch for real results!")
    print()
    
    # Use the CSV with real URLs
    agencies_file = "scraped_data/usa_gov_agencies_20250825_225741.csv"
    
    # Run full scraping
    scraper = GovernmentEmailScraper("full_results")
    result = scraper.scrape_federal_agencies(agencies_file)
    
    if result['success']:
        print(f"\n🎉 FULL SCRAPING COMPLETE!")
        print(f"   • Total agencies: {result['agencies_scraped']}")
        print(f"   • Unique emails found: {result['unique_emails_found']}")  
        print(f"   • Government sites discovered: {result['gov_sites_discovered']}")
        
        # Show all emails found
        stats = scraper.get_statistics()
        if stats['scraped_emails']:
            print(f"\n📧 ALL EMAILS FOUND ({len(stats['scraped_emails'])}):")
            for i, email in enumerate(stats['scraped_emails'], 1):
                print(f"   {i:2d}. {email}")
        
        print(f"\n📁 Results saved to: full_results/")
        print(f"🔗 Plus {len(stats['discovered_sites_sample'])} government sites discovered for further scraping!")
        
    else:
        print(f"❌ Error: {result.get('error')}")

if __name__ == "__main__":
    main()