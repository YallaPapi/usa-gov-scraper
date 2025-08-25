"""
FIXED USA.gov Agency Scraper - Extracts REAL agency names and URLs
NO PLACEHOLDERS, NO FAKE DATA, ACTUAL WORKING IMPLEMENTATION
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from typing import List, Dict

def scrape_real_agencies() -> List[Dict[str, str]]:
    """
    Scrapes REAL agency names and URLs from USA.gov
    Returns actual government agencies, not navigation links
    """
    
    print("\n" + "="*60)
    print("USA.GOV AGENCY SCRAPER - FIXED VERSION")
    print("Extracting REAL agency names, not navigation links")
    print("="*60)
    
    url = "https://www.usa.gov/agency-index"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print("\nFetching page...")
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_agencies = []
    
    # The correct structure: h2 elements for letters, followed by ul > li > a for agencies
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        # Find the h2 element with this letter
        h2 = soup.find('h2', string=letter)
        
        if not h2:
            # Try finding by id attribute
            h2 = soup.find('h2', id=letter)
        
        if not h2:
            print(f"  Warning: Section {letter} not found")
            continue
        
        agencies_in_section = []
        
        # Find the next sibling elements after h2 until we hit another h2
        current = h2.find_next_sibling()
        
        while current and current.name != 'h2':
            if current.name == 'ul':
                # This ul contains the agencies
                links = current.find_all('a')
                
                for link in links:
                    agency_name = link.text.strip()
                    agency_url = link.get('href', '')
                    
                    # Filter out navigation links and empty entries
                    if not agency_name or len(agency_name) == 1:
                        continue
                    
                    # Skip if it's just a letter link
                    if agency_name in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(agency_name) == 1:
                        continue
                    
                    # Make URL absolute if needed
                    if agency_url:
                        if not agency_url.startswith(('http://', 'https://')):
                            if agency_url.startswith('/'):
                                agency_url = f"https://www.usa.gov{agency_url}"
                            else:
                                agency_url = f"https://{agency_url}"
                    
                    # Skip navigation/anchor links
                    if '#' in agency_url and agency_url.endswith(f"#{letter}"):
                        continue
                    
                    agencies_in_section.append({
                        'agency_name': agency_name,
                        'homepage_url': agency_url,
                        'section': letter
                    })
            
            current = current.find_next_sibling()
        
        if agencies_in_section:
            print(f"  Section {letter}: Found {len(agencies_in_section)} real agencies")
            all_agencies.extend(agencies_in_section)
    
    # Additional validation - remove any remaining single-letter entries
    real_agencies = []
    for agency in all_agencies:
        name = agency['agency_name']
        # Must be more than 1 character and not just a single letter
        if len(name) > 1 and name not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            real_agencies.append(agency)
    
    print(f"\nTotal REAL agencies found: {len(real_agencies)}")
    
    # Show sample of real agencies
    if real_agencies:
        print("\nSample of REAL agencies found:")
        for agency in real_agencies[:5]:
            print(f"  • {agency['agency_name']}")
            print(f"    URL: {agency['homepage_url']}")
    
    return real_agencies

def save_agencies(agencies: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Saves the scraped agencies to CSV and JSON files
    Returns paths to saved files
    """
    
    # Create output directory
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save to CSV
    csv_file = f"scraped_data/agencies_fixed_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if agencies:
            writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
            writer.writeheader()
            writer.writerows(agencies)
    
    # Save to JSON
    json_file = f"scraped_data/agencies_fixed_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(agencies, f, indent=2, ensure_ascii=False)
    
    return {
        'csv': csv_file,
        'json': json_file
    }

def validate_agencies(agencies: List[Dict[str, str]]) -> bool:
    """
    Validates that we got real agencies, not navigation links
    Returns True if data looks valid
    """
    
    if not agencies:
        print("ERROR: No agencies found")
        return False
    
    # Check that we don't have single-letter "agencies"
    single_letters = [a for a in agencies if len(a['agency_name']) == 1]
    if single_letters:
        print(f"ERROR: Found {len(single_letters)} single-letter entries (navigation links)")
        return False
    
    # Check for known real agencies that should be present
    known_agencies = [
        'Department of Agriculture',
        'Department of Defense', 
        'Department of Education',
        'Environmental Protection Agency',
        'Federal Bureau of Investigation'
    ]
    
    agency_names = [a['agency_name'].lower() for a in agencies]
    found_known = 0
    
    for known in known_agencies:
        if any(known.lower() in name for name in agency_names):
            found_known += 1
    
    if found_known == 0:
        print("WARNING: None of the expected agencies were found")
        print("This might indicate the scraper is still not working correctly")
        return False
    
    print(f"Validation PASSED: Found {found_known} known agencies")
    return True

def main():
    """
    Main execution function
    """
    
    try:
        # Scrape agencies
        agencies = scrape_real_agencies()
        
        # Validate the data
        if not validate_agencies(agencies):
            print("\n[ERROR] Data validation failed - scraper may still be broken")
            return False
        
        # Save the data
        files = save_agencies(agencies)
        
        print("\n" + "="*60)
        print("SCRAPING COMPLETE - REAL DATA EXTRACTED")
        print(f"Agencies scraped: {len(agencies)}")
        print(f"CSV saved: {files['csv']}")
        print(f"JSON saved: {files['json']}")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Scraping failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)