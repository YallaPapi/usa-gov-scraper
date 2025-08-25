"""
Test scraper to verify functionality
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime

def test_scrape():
    """Test basic scraping functionality"""
    print("\n" + "="*60)
    print("USA.gov Agency Scraper - Test Run")
    print("="*60)
    
    try:
        print("\n[1] Fetching USA.gov Agency Index...")
        url = "https://www.usa.gov/agency-index"
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ERROR: Failed to fetch page")
            return
        
        print("\n[2] Parsing HTML...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find sections
        sections_found = []
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            section = soup.find('section', {'id': letter})
            if section:
                sections_found.append(letter)
        
        print(f"   Found {len(sections_found)} sections: {', '.join(sections_found[:10])}...")
        
        # Test scraping section A
        print("\n[3] Testing Section A extraction...")
        section_a = soup.find('section', {'id': 'A'})
        
        if not section_a:
            print("   ERROR: Section A not found")
            return
        
        agencies = []
        links = section_a.find_all('a', href=True)
        
        for link in links:
            if link.get('href', '').startswith('#'):
                continue
            
            agency_name = link.text.strip()
            homepage_url = link.get('href', '')
            
            if agency_name and homepage_url:
                if not homepage_url.startswith(('http://', 'https://')):
                    homepage_url = f"https://www.usa.gov{homepage_url}" if homepage_url.startswith('/') else f"https://{homepage_url}"
                
                agencies.append({
                    'agency_name': agency_name,
                    'homepage_url': homepage_url,
                    'section': 'A'
                })
        
        print(f"   Found {len(agencies)} agencies in section A")
        
        # Show sample agencies
        print("\n[4] Sample agencies from section A:")
        for agency in agencies[:5]:
            print(f"   • {agency['agency_name']}")
            print(f"     URL: {agency['homepage_url']}")
        
        # Test export
        print("\n[5] Testing export functionality...")
        os.makedirs("test_output", exist_ok=True)
        
        # CSV export
        csv_file = "test_output/test_agencies.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
            writer.writeheader()
            writer.writerows(agencies)
        print(f"   ✓ CSV exported: {csv_file}")
        
        # JSON export
        json_file = "test_output/test_agencies.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(agencies, f, indent=2, ensure_ascii=False)
        print(f"   ✓ JSON exported: {json_file}")
        
        print("\n[6] Test Summary:")
        print(f"   ✓ Page fetched successfully")
        print(f"   ✓ Found {len(sections_found)} sections")
        print(f"   ✓ Extracted {len(agencies)} agencies from section A")
        print(f"   ✓ Export functionality working")
        
        print("\n" + "="*60)
        print("TEST SUCCESSFUL - Scraper is working!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n   ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    test_scrape()