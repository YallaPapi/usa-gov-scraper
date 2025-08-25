"""
FINAL FIXED USA.gov Agency Scraper
Handles the actual accordion structure of the page
NO FAKE DATA - REAL AGENCIES ONLY
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from typing import List, Dict

def scrape_usa_gov_agencies() -> List[Dict[str, str]]:
    """
    Scrapes REAL agencies from USA.gov using the correct page structure
    The page uses accordions for each agency, not simple lists
    """
    
    print("\n" + "="*60)
    print("USA.GOV AGENCY SCRAPER - FINAL FIXED VERSION")
    print("="*60)
    
    url = "https://www.usa.gov/agency-index"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print("\n[1] Fetching page...")
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: {response.status_code}")
    
    print("[2] Parsing HTML...")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_agencies = []
    
    # The page structure:
    # - h2 with class "usagov-directory-letter-heading" for each letter (A-Z)
    # - After each letter h2, there are div.usa-accordion elements
    # - Each accordion contains an agency with h2.usa-accordion__heading
    
    print("[3] Extracting agencies...")
    
    # Find all accordion divs (these contain the agencies)
    accordions = soup.find_all('div', class_='usa-accordion')
    
    for accordion in accordions:
        # Find the agency name in the h2 within the accordion
        agency_h2 = accordion.find('h2', class_='usa-accordion__heading')
        
        if not agency_h2:
            continue
        
        # Get the button text which contains the agency name
        button = agency_h2.find('button')
        if button:
            agency_name = button.text.strip()
        else:
            # Fallback to h2 text
            agency_name = agency_h2.text.strip()
        
        # Clean up the agency name
        agency_name = agency_name.replace('\n', ' ').replace('  ', ' ').strip()
        
        # Skip if it's empty or just a letter
        if not agency_name or len(agency_name) <= 1:
            continue
        
        # Skip navigation entries
        if agency_name in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            continue
        
        # Find the agency website in the accordion content
        agency_url = ''
        accordion_content = accordion.find('div', class_='usa-accordion__content')
        
        if accordion_content:
            # Look for the official website link
            links = accordion_content.find_all('a')
            for link in links:
                href = link.get('href', '')
                link_text = link.text.strip().lower()
                
                # Priority: Official website links
                if 'official website' in link_text or 'website' in link_text:
                    agency_url = href
                    break
                # Fallback: First external link
                elif href and not href.startswith('#') and not href.startswith('/'):
                    if not agency_url:  # Only set if we haven't found one yet
                        agency_url = href
        
        # Determine which letter section this belongs to
        # Find the nearest preceding letter heading
        section = 'Unknown'
        prev_element = accordion.find_previous('h2', class_='usagov-directory-letter-heading')
        if prev_element:
            section = prev_element.text.strip()
        
        # Add to our list if we have a valid agency name
        if agency_name and len(agency_name) > 1:
            all_agencies.append({
                'agency_name': agency_name,
                'homepage_url': agency_url if agency_url else 'Not provided',
                'section': section
            })
    
    # Alternative method: Look for h2 elements that are NOT letter headings
    if len(all_agencies) == 0:
        print("  Trying alternative extraction method...")
        all_h2 = soup.find_all('h2')
        
        for h2 in all_h2:
            # Skip letter headings
            if h2.get('class') and 'usagov-directory-letter-heading' in h2.get('class'):
                continue
            
            text = h2.text.strip()
            
            # Clean up text
            text = text.replace('\n', ' ').replace('  ', ' ').strip()
            
            # Must contain agency-like keywords
            agency_keywords = ['Department', 'Agency', 'Administration', 'Bureau', 
                             'Commission', 'Office', 'Service', 'Institute', 
                             'Foundation', 'Corporation', 'Authority', 'Board']
            
            if any(keyword in text for keyword in agency_keywords) or len(text) > 10:
                # Skip navigation and meta content
                if text not in ['Have a question?', 'About', 'Help', 'Contact']:
                    all_agencies.append({
                        'agency_name': text,
                        'homepage_url': 'See USA.gov for details',
                        'section': 'Various'
                    })
    
    # Remove duplicates based on agency name
    seen_names = set()
    unique_agencies = []
    
    for agency in all_agencies:
        name = agency['agency_name']
        if name not in seen_names:
            seen_names.add(name)
            unique_agencies.append(agency)
    
    print(f"\n[4] Results:")
    print(f"  Total agencies found: {len(unique_agencies)}")
    
    # Show sample
    if unique_agencies:
        print("\n  Sample agencies:")
        for agency in unique_agencies[:10]:
            print(f"    • {agency['agency_name']}")
            if agency['homepage_url'] != 'Not provided':
                print(f"      URL: {agency['homepage_url']}")
    
    return unique_agencies

def validate_results(agencies: List[Dict[str, str]]) -> bool:
    """
    Validates that we extracted real agencies
    """
    
    if not agencies:
        print("\n[ERROR] No agencies found")
        return False
    
    # Check for known agencies
    known_agencies = [
        'Agriculture Department',
        'Air Force',
        'Army', 
        'AmeriCorps',
        'Archives'
    ]
    
    agency_names = [a['agency_name'].lower() for a in agencies]
    found_count = 0
    
    for known in known_agencies:
        if any(known.lower() in name for name in agency_names):
            found_count += 1
    
    if found_count < 2:
        print(f"\n[WARNING] Only found {found_count} known agencies")
        return False
    
    # Check we don't have single letters
    single_letters = [a for a in agencies if len(a['agency_name']) == 1]
    if single_letters:
        print(f"\n[ERROR] Found {len(single_letters)} single-letter entries")
        return False
    
    print(f"\n[VALIDATION] Passed - Found {found_count} known agencies")
    return True

def save_results(agencies: List[Dict[str, str]]):
    """
    Saves agencies to CSV and JSON
    """
    
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save CSV
    csv_file = f"scraped_data/agencies_real_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if agencies:
            writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
            writer.writeheader()
            writer.writerows(agencies)
    print(f"\n[SAVED] CSV: {csv_file}")
    
    # Save JSON
    json_file = f"scraped_data/agencies_real_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(agencies, f, indent=2, ensure_ascii=False)
    print(f"[SAVED] JSON: {json_file}")
    
    return csv_file, json_file

def main():
    """
    Main execution
    """
    
    try:
        # Scrape
        agencies = scrape_usa_gov_agencies()
        
        # Validate
        if not validate_results(agencies):
            print("\n[FAILED] Validation failed - check scraper logic")
            return False
        
        # Save
        csv_file, json_file = save_results(agencies)
        
        print("\n" + "="*60)
        print("SUCCESS - REAL AGENCIES EXTRACTED")
        print(f"Total agencies: {len(agencies)}")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)