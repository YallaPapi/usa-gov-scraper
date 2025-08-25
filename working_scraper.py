"""
Working scraper that handles the actual USA.gov page structure
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime

def scrape_usa_gov():
    """Scrape USA.gov agency index with correct structure"""
    
    print("\n" + "="*60)
    print("USA.gov Agency Scraper - Working Version")
    print("="*60)
    
    start_time = datetime.now()
    all_agencies = []
    
    try:
        # Fetch the page
        print("\n[1] Fetching USA.gov Agency Index...")
        url = "https://www.usa.gov/agency-index"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=30, headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print("   ERROR: Failed to fetch page")
            return []
        
        # Parse HTML
        print("\n[2] Parsing HTML...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # The structure is: h2 (letter) followed by ul with li > a elements
        sections_found = []
        
        print("\n[3] Extracting agencies by letter...")
        
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            # Find the h2 with the letter
            h2 = soup.find('h2', string=letter)
            
            if not h2:
                continue
            
            sections_found.append(letter)
            
            # Find all agencies under this letter
            # They are in ul elements that follow the h2
            agencies_in_section = []
            
            # Get the parent container
            parent = h2.parent
            if parent:
                # Find all ul elements in the parent
                uls = parent.find_all('ul')
                
                for ul in uls:
                    # Get all links in this ul
                    links = ul.find_all('a')
                    
                    for link in links:
                        agency_name = link.text.strip()
                        homepage_url = link.get('href', '')
                        
                        if agency_name and homepage_url:
                            # Make URL absolute if needed
                            if not homepage_url.startswith(('http://', 'https://')):
                                if homepage_url.startswith('/'):
                                    homepage_url = f"https://www.usa.gov{homepage_url}"
                                else:
                                    homepage_url = f"https://{homepage_url}"
                            
                            agencies_in_section.append({
                                'agency_name': agency_name,
                                'homepage_url': homepage_url,
                                'section': letter
                            })
            
            if agencies_in_section:
                all_agencies.extend(agencies_in_section)
                print(f"   {letter}: {len(agencies_in_section)} agencies")
        
        print(f"\n   Total sections found: {len(sections_found)}")
        print(f"   Total agencies found: {len(all_agencies)}")
        
        # Remove duplicates
        print("\n[4] Removing duplicates...")
        unique_agencies = []
        seen_urls = set()
        
        for agency in all_agencies:
            url = agency['homepage_url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_agencies.append(agency)
        
        duplicates = len(all_agencies) - len(unique_agencies)
        print(f"   Removed {duplicates} duplicates")
        print(f"   Unique agencies: {len(unique_agencies)}")
        
        # Export data
        print("\n[5] Exporting data...")
        os.makedirs("scraped_data", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # CSV export
        csv_file = f"scraped_data/agencies_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
            writer.writeheader()
            writer.writerows(unique_agencies)
        print(f"   [OK] CSV: {csv_file}")
        
        # JSON export
        json_file = f"scraped_data/agencies_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(unique_agencies, f, indent=2, ensure_ascii=False)
        print(f"   [OK] JSON: {json_file}")
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        # Show sample agencies
        print("\n[6] Sample agencies:")
        for agency in unique_agencies[:5]:
            print(f"   • {agency['agency_name']}")
            print(f"     {agency['homepage_url']}")
        
        # Summary
        print("\n" + "="*60)
        print("SCRAPING COMPLETE!")
        print(f"Agencies scraped: {len(unique_agencies)}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Files saved: {csv_file}, {json_file}")
        print("="*60)
        
        return unique_agencies
        
    except Exception as e:
        print(f"\n   ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    agencies = scrape_usa_gov()
    print(f"\nFinal result: {len(agencies)} agencies scraped")