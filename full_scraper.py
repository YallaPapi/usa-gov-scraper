"""
FULL USA.gov Scraper - Gets ALL agencies A-Z with their websites
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime

def scrape_all_sections():
    """Scrape ALL letter sections A-Z"""
    
    print("="*60)
    print("FULL USA.GOV SCRAPER - ALL SECTIONS A-Z")
    print("="*60)
    
    all_agencies = []
    base_url = "https://www.usa.gov/agency-index"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # First get the main page
    print("\nFetching main index page...")
    response = requests.get(base_url, headers=headers, timeout=30)
    main_soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try to get agencies from each letter page
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        print(f"\nChecking section {letter}...")
        
        # Try different URL patterns
        urls_to_try = [
            f"https://www.usa.gov/agency-index/{letter.lower()}",  # /a, /b, etc
            f"https://www.usa.gov/agency-index#{letter}",  # #A, #B, etc
            f"https://www.usa.gov/federal-agencies/{letter.lower()}",  # alternative path
        ]
        
        # Also check the main page for this letter's section
        letter_section = main_soup.find('h2', id=letter)
        if not letter_section:
            letter_section = main_soup.find('h2', string=letter)
        
        if letter_section:
            # Get all agencies after this letter heading until next letter
            current = letter_section
            while True:
                current = current.find_next_sibling()
                if not current:
                    break
                    
                # Stop at next letter heading
                if current.name == 'h2' and current.get('id', '') in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    break
                    
                # Look for agency accordions
                if 'usa-accordion' in str(current.get('class', [])):
                    heading = current.find('h2', class_='usa-accordion__heading')
                    if heading:
                        button = heading.find('button')
                        if button:
                            agency_name = button.text.strip()
                            agency_name = ' '.join(agency_name.split())
                            
                            # Get URL from accordion content
                            agency_url = ''
                            content_id = button.get('aria-controls', '')
                            if content_id:
                                content = main_soup.find('div', id=content_id)
                                if content:
                                    links = content.find_all('a', href=True)
                                    for link in links:
                                        href = link.get('href', '')
                                        if href and '.gov' in href and href.startswith('http'):
                                            agency_url = href
                                            break
                            
                            if len(agency_name) > 2:
                                all_agencies.append({
                                    'agency_name': agency_name,
                                    'homepage_url': agency_url if agency_url else 'Not found',
                                    'section': letter
                                })
                                print(f"  Found: {agency_name[:50]}...")
                
                # Also check for h2 agency headings
                if current.name == 'h2' and 'usa-accordion__heading' not in str(current.get('class', [])):
                    text = current.text.strip()
                    text = ' '.join(text.split())
                    
                    if len(text) > 2 and text not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                        # Get URL
                        url = ''
                        parent = current.parent
                        if parent:
                            links = parent.find_all('a', href=True)
                            for link in links:
                                href = link.get('href', '')
                                if href and '.gov' in href and href.startswith('http'):
                                    url = href
                                    break
                        
                        all_agencies.append({
                            'agency_name': text,
                            'homepage_url': url if url else 'Not found',
                            'section': letter
                        })
                        print(f"  Found: {text[:50]}...")
        
        # Try fetching separate pages
        for url in urls_to_try:
            if '#' not in url:  # Skip anchor URLs
                try:
                    print(f"  Trying {url}...")
                    resp = requests.get(url, headers=headers, timeout=5)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        
                        # Look for agencies on this page
                        headings = soup.find_all('h2')
                        for h2 in headings:
                            text = h2.text.strip()
                            text = ' '.join(text.split())
                            
                            # Skip letters and meta
                            if len(text) <= 2 or text in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                                continue
                            if any(skip in text for skip in ['Have a question', 'About', 'Help']):
                                continue
                                
                            # Check if already added
                            if not any(a['agency_name'] == text for a in all_agencies):
                                all_agencies.append({
                                    'agency_name': text,
                                    'homepage_url': 'See USA.gov',
                                    'section': letter
                                })
                                print(f"  Found: {text[:50]}...")
                        break
                except:
                    continue
    
    # Remove duplicates
    seen = set()
    unique = []
    for agency in all_agencies:
        key = agency['agency_name']
        if key not in seen:
            seen.add(key)
            unique.append(agency)
    
    return unique

def save_all_data(agencies):
    """Save complete data"""
    
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Sort by section then name
    agencies.sort(key=lambda x: (x['section'], x['agency_name']))
    
    # CSV
    csv_file = f"scraped_data/all_agencies_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['section', 'agency_name', 'homepage_url'])
        writer.writeheader()
        writer.writerows(agencies)
    
    # JSON
    json_file = f"scraped_data/all_agencies_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(agencies, f, indent=2, ensure_ascii=False)
    
    print(f"\nCSV: {csv_file}")
    print(f"JSON: {json_file}")
    
    # Summary
    sections = {}
    for agency in agencies:
        s = agency['section']
        if s not in sections:
            sections[s] = 0
        sections[s] += 1
    
    print("\nAGENCIES BY SECTION:")
    for letter in sorted(sections.keys()):
        print(f"  {letter}: {sections[letter]} agencies")
    
    with_url = sum(1 for a in agencies if a['homepage_url'] and a['homepage_url'] != 'Not found' and a['homepage_url'] != 'See USA.gov')
    print(f"\nAgencies with direct website URLs: {with_url}")
    print(f"Agencies without direct URLs: {len(agencies) - with_url}")

def main():
    try:
        agencies = scrape_all_sections()
        
        print("\n" + "="*60)
        print(f"TOTAL AGENCIES FOUND: {len(agencies)}")
        print("="*60)
        
        if agencies:
            save_all_data(agencies)
            print("\n[DONE] SCRAPING COMPLETE!")
        else:
            print("\n[ERROR] No agencies found!")
            
    except Exception as e:
        print(f"\n[ERROR]: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()