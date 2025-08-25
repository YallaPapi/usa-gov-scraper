"""
ULTIMATE FIX - USA.gov Agency Scraper
Extracts agencies directly from h2 elements based on diagnostic analysis
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from typing import List, Dict

def scrape_agencies_ultimate() -> List[Dict[str, str]]:
    """
    Ultimate fix - extracts agencies from h2 elements that are NOT letter headings
    Based on diagnostic showing agencies like:
    - 'AbilityOne Commission'
    - 'Access Board'
    - 'Administration for Children and Families (ACF)'
    - etc.
    """
    
    print("\n" + "="*60)
    print("USA.GOV AGENCY SCRAPER - ULTIMATE FIX")
    print("="*60)
    
    url = "https://www.usa.gov/agency-index"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print("\nFetching page...")
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_agencies = []
    
    # Get ALL h2 elements
    all_h2 = soup.find_all('h2')
    
    print(f"Found {len(all_h2)} h2 elements total")
    
    # Track current section letter
    current_section = 'A'
    
    for h2 in all_h2:
        h2_text = h2.text.strip()
        h2_id = h2.get('id', '')
        
        # Clean up text (remove extra spaces and newlines)
        h2_text = ' '.join(h2_text.split())
        
        # Check if this is a letter heading
        if h2_id in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(h2_id) == 1:
            current_section = h2_id
            continue
        
        # Skip if it's just a single letter
        if h2_text in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(h2_text) == 1:
            current_section = h2_text
            continue
        
        # Skip meta content
        skip_phrases = ['Have a question?', 'About', 'Help', 'Contact', 'Search']
        if any(phrase in h2_text for phrase in skip_phrases):
            continue
        
        # This is likely an agency name
        if len(h2_text) > 2:  # Must be more than 2 chars
            # Extract URL from associated links
            agency_url = ''
            
            # Check if there's a parent element with links
            parent = h2.parent
            if parent:
                # Look for links in the parent or siblings
                links = parent.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    link_text = link.text.strip().lower()
                    
                    # Skip internal navigation links
                    if href and not href.startswith('#'):
                        # Prefer official website links
                        if 'website' in link_text or 'official' in link_text:
                            agency_url = href
                            break
                        # Use first external link as fallback
                        elif not agency_url and not href.startswith('/'):
                            agency_url = href
            
            # Clean up the agency name (remove abbreviations in parens if at the end)
            # but keep them for reference
            agency_name = h2_text
            
            all_agencies.append({
                'agency_name': agency_name,
                'homepage_url': agency_url if agency_url else 'See USA.gov',
                'section': current_section
            })
    
    # Remove any duplicates
    seen = set()
    unique_agencies = []
    for agency in all_agencies:
        if agency['agency_name'] not in seen:
            seen.add(agency['agency_name'])
            unique_agencies.append(agency)
    
    return unique_agencies

def validate_and_save(agencies: List[Dict[str, str]]):
    """
    Validates and saves the scraped agencies
    """
    
    print(f"\n[RESULTS]")
    print(f"Total agencies extracted: {len(agencies)}")
    
    if not agencies:
        print("[ERROR] No agencies found!")
        return False
    
    # Show first 20 agencies as proof
    print("\nFirst 20 agencies found:")
    for i, agency in enumerate(agencies[:20], 1):
        print(f"  {i:2}. {agency['agency_name']}")
    
    # Validate we have real agencies
    expected_patterns = [
        'Department', 'Agency', 'Administration', 'Bureau', 
        'Commission', 'Office', 'Service', 'Institute',
        'Foundation', 'Corporation', 'Board', 'Command'
    ]
    
    valid_count = 0
    for agency in agencies:
        if any(pattern in agency['agency_name'] for pattern in expected_patterns):
            valid_count += 1
    
    print(f"\n[VALIDATION]")
    print(f"Agencies with valid patterns: {valid_count}/{len(agencies)}")
    
    if valid_count < len(agencies) * 0.5:  # At least 50% should match patterns
        print("[WARNING] Less than 50% of entries match agency patterns")
    
    # Save to files
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # CSV
    csv_file = f"scraped_data/agencies_ultimate_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
        writer.writeheader()
        writer.writerows(agencies)
    
    # JSON
    json_file = f"scraped_data/agencies_ultimate_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(agencies, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVED]")
    print(f"CSV: {csv_file}")
    print(f"JSON: {json_file}")
    
    return True

def main():
    """
    Main execution
    """
    
    try:
        agencies = scrape_agencies_ultimate()
        
        if validate_and_save(agencies):
            print("\n" + "="*60)
            print("SUCCESS - REAL AGENCIES EXTRACTED")
            print(f"Total: {len(agencies)} agencies")
            print("="*60)
            return True
        else:
            print("\n[FAILED] Validation failed")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)