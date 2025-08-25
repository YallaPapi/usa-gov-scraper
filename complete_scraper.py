"""
COMPLETE USA.gov Agency Scraper
Gets ALL agencies from ALL sections and their ACTUAL websites
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
import re

def get_all_agencies():
    """Get ALL agencies from USA.gov, not just section A"""
    
    print("="*60)
    print("COMPLETE USA.GOV SCRAPER - ALL AGENCIES")
    print("="*60)
    
    url = "https://www.usa.gov/agency-index"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print("\nFetching main page...")
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_agencies = []
    
    # Method 1: Get from accordion structure
    print("\nExtracting agencies from accordions...")
    accordions = soup.find_all('div', class_='usa-accordion')
    
    for accordion in accordions:
        # Find agency name in accordion heading
        heading = accordion.find('h2', class_='usa-accordion__heading')
        if not heading:
            continue
            
        button = heading.find('button')
        if not button:
            continue
            
        agency_name = button.text.strip()
        agency_name = ' '.join(agency_name.split())
        
        # Skip if empty or single letter
        if not agency_name or len(agency_name) <= 1:
            continue
        if agency_name in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            continue
            
        # Find agency URL in accordion content
        agency_url = ''
        content_id = button.get('aria-controls', '')
        if content_id:
            content = soup.find('div', id=content_id)
            if content:
                # Look for official website link
                links = content.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    text = link.text.strip().lower()
                    
                    # Get the actual agency website
                    if href and not href.startswith('#'):
                        if 'website' in text or 'official' in text or href.startswith('http'):
                            if not href.startswith('/'):  # Not internal link
                                agency_url = href
                                break
        
        # Determine section
        section = agency_name[0].upper() if agency_name else 'Unknown'
        
        all_agencies.append({
            'agency_name': agency_name,
            'homepage_url': agency_url if agency_url else 'Not found',
            'section': section
        })
        
        print(f"  [{section}] {agency_name[:50]}... - {agency_url[:30] if agency_url else 'No URL'}")
    
    # Method 2: Also check all h2 elements for any we missed
    print("\nChecking for additional agencies in h2 elements...")
    all_h2 = soup.find_all('h2')
    existing_names = {a['agency_name'] for a in all_agencies}
    
    for h2 in all_h2:
        text = h2.text.strip()
        text = ' '.join(text.split())
        
        # Skip if already found, single letter, or meta
        if text in existing_names:
            continue
        if len(text) <= 2:
            continue
        if text in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            continue
        if any(skip in text for skip in ['Have a question?', 'About', 'Help']):
            continue
            
        # This might be an agency we missed
        section = text[0].upper() if text else 'Unknown'
        
        # Try to find URL
        url = ''
        parent = h2.parent
        if parent:
            links = parent.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if href and not href.startswith('#') and not href.startswith('/'):
                    url = href
                    break
        
        all_agencies.append({
            'agency_name': text,
            'homepage_url': url if url else 'Not found',
            'section': section
        })
        print(f"  [{section}] {text[:50]}...")
    
    # Method 3: Find ALL links that look like agency websites
    print("\nScanning all links for agency websites...")
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '')
        text = link.text.strip()
        
        # Look for .gov sites
        if '.gov' in href and href.startswith('http'):
            # Check if this URL is already captured
            urls = {a['homepage_url'] for a in all_agencies}
            if href not in urls:
                # Try to find which agency this belongs to
                parent_h2 = link.find_previous('h2')
                if parent_h2:
                    agency_name = parent_h2.text.strip()
                    agency_name = ' '.join(agency_name.split())
                    
                    if len(agency_name) > 2 and agency_name not in existing_names:
                        section = agency_name[0].upper()
                        all_agencies.append({
                            'agency_name': agency_name,
                            'homepage_url': href,
                            'section': section
                        })
                        existing_names.add(agency_name)
                        print(f"  [{section}] Found website for: {agency_name[:30]}...")
    
    # Remove duplicates
    seen = set()
    unique_agencies = []
    for agency in all_agencies:
        key = agency['agency_name']
        if key not in seen:
            seen.add(key)
            unique_agencies.append(agency)
    
    return unique_agencies

def save_results(agencies):
    """Save results to CSV and JSON"""
    
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Sort by section then name
    agencies.sort(key=lambda x: (x['section'], x['agency_name']))
    
    # CSV
    csv_file = f"scraped_data/complete_agencies_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['section', 'agency_name', 'homepage_url'])
        writer.writeheader()
        writer.writerows(agencies)
    print(f"\nCSV saved: {csv_file}")
    
    # JSON
    json_file = f"scraped_data/complete_agencies_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(agencies, f, indent=2, ensure_ascii=False)
    print(f"JSON saved: {json_file}")
    
    # Summary by section
    print("\n" + "="*60)
    print("SUMMARY BY SECTION:")
    sections = {}
    for agency in agencies:
        section = agency['section']
        if section not in sections:
            sections[section] = []
        sections[section].append(agency)
    
    for letter in sorted(sections.keys()):
        print(f"  {letter}: {len(sections[letter])} agencies")
    
    # Agencies with websites vs without
    with_url = sum(1 for a in agencies if a['homepage_url'] and a['homepage_url'] != 'Not found')
    without_url = len(agencies) - with_url
    
    print(f"\nAgencies with websites: {with_url}")
    print(f"Agencies without websites: {without_url}")
    
    return csv_file, json_file

def main():
    """Main execution"""
    
    try:
        # Get all agencies
        agencies = get_all_agencies()
        
        print("\n" + "="*60)
        print(f"TOTAL AGENCIES FOUND: {len(agencies)}")
        print("="*60)
        
        if agencies:
            # Save results
            csv_file, json_file = save_results(agencies)
            
            print("\n✅ SCRAPING COMPLETE!")
            print(f"Total agencies: {len(agencies)}")
            print(f"Files saved in scraped_data/")
            
            # Show sample
            print("\nSample agencies with websites:")
            samples = [a for a in agencies if a['homepage_url'] and '.gov' in a['homepage_url']][:10]
            for agency in samples:
                print(f"  • {agency['agency_name']}")
                print(f"    {agency['homepage_url']}")
        else:
            print("\n❌ No agencies found!")
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()