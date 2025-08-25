"""
TARGETED USA.GOV CRAWLER
Focuses on key pages for maximum results:
- State governments
- Local governments
- Elected officials
- Federal agencies
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time

def crawl_targeted_pages():
    """Crawl specific high-value pages"""
    
    print("="*60)
    print("TARGETED USA.GOV CRAWLER - STATE/LOCAL/OFFICIALS")
    print("="*60)
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    all_links = {}
    
    # Key pages to crawl
    target_pages = [
        ("https://www.usa.gov/states", "State Governments"),
        ("https://www.usa.gov/state-government", "State Government Directory"),
        ("https://www.usa.gov/local-governments", "Local Governments"),
        ("https://www.usa.gov/state-tribal-governments", "State & Tribal Governments"),
        ("https://www.usa.gov/elected-officials", "Elected Officials"),
        ("https://www.usa.gov/contact-elected-officials", "Contact Elected Officials"),
        ("https://www.usa.gov/branches-of-government", "Government Branches"),
        ("https://www.usa.gov/federal-agencies", "Federal Agencies"),
        ("https://www.usa.gov/state-governor", "State Governors"),
        ("https://www.usa.gov/state-attorney-general", "State Attorneys General"),
        ("https://www.usa.gov/congress", "Congress"),
        ("https://www.usa.gov/courts", "Courts"),
        ("https://www.usa.gov/cities", "Cities"),
        ("https://www.usa.gov/counties", "Counties"),
    ]
    
    # Also crawl each state's page
    states = [
        'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut',
        'delaware', 'florida', 'georgia', 'hawaii', 'idaho', 'illinois', 'indiana', 'iowa',
        'kansas', 'kentucky', 'louisiana', 'maine', 'maryland', 'massachusetts', 'michigan',
        'minnesota', 'mississippi', 'missouri', 'montana', 'nebraska', 'nevada', 'new-hampshire',
        'new-jersey', 'new-mexico', 'new-york', 'north-carolina', 'north-dakota', 'ohio',
        'oklahoma', 'oregon', 'pennsylvania', 'rhode-island', 'south-carolina', 'south-dakota',
        'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington', 'west-virginia',
        'wisconsin', 'wyoming', 'district-of-columbia'
    ]
    
    for state in states:
        target_pages.append((f"https://www.usa.gov/states/{state}", f"{state.title()} Government"))
    
    print(f"\nCrawling {len(target_pages)} targeted pages...")
    
    for url, description in target_pages:
        print(f"\n[{description}] {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"  Skip: Status {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all external links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.text.strip()
                
                # Make absolute URL
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                
                # Check if external
                if parsed.netloc and parsed.netloc not in ['www.usa.gov', 'usa.gov', '']:
                    # Categorize
                    category = "Other"
                    
                    if '.gov' in full_url:
                        if state in description.lower():
                            category = f"State: {state.title()}"
                        elif 'local' in description.lower() or 'city' in full_url or 'county' in full_url:
                            category = "Local Government"
                        elif 'congress' in full_url or 'senate' in full_url or 'house' in full_url:
                            category = "Congress/Legislative"
                        elif 'court' in full_url:
                            category = "Judicial/Courts"
                        elif '.state.' in full_url or any(s in full_url for s in states):
                            category = "State Government"
                        else:
                            category = "Federal Agency"
                    elif '.mil' in full_url:
                        category = "Military"
                    elif 'elected' in description.lower():
                        category = "Elected Officials"
                    
                    # Store link
                    if full_url not in all_links:
                        all_links[full_url] = {
                            'url': full_url,
                            'text': text[:200],
                            'category': category,
                            'found_on': url,
                            'page_type': description,
                            'domain': parsed.netloc
                        }
                        print(f"  [{category}] {text[:50]}...")
                        
            time.sleep(0.5)  # Be polite
            
        except Exception as e:
            print(f"  Error: {str(e)}")
    
    return all_links

def save_results(links):
    """Save crawl results"""
    
    if not links:
        print("\nNo links found!")
        return
    
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Convert to list
    links_list = list(links.values())
    links_list.sort(key=lambda x: (x['category'], x['domain']))
    
    # CSV
    csv_file = f"scraped_data/targeted_gov_links_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['category', 'domain', 'url', 'text', 'page_type', 'found_on']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(links_list)
    print(f"\nCSV: {csv_file}")
    
    # JSON
    json_file = f"scraped_data/targeted_gov_links_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(links_list, f, indent=2, ensure_ascii=False)
    print(f"JSON: {json_file}")
    
    # Summary by category
    print("\n" + "="*60)
    print("LINKS BY CATEGORY:")
    categories = {}
    for link in links_list:
        cat = link['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(link)
    
    for category in sorted(categories.keys()):
        print(f"\n{category}: {len(categories[category])} links")
        # Show examples
        for link in categories[category][:3]:
            print(f"  • {link['text'][:40]}... ({link['domain']})")
    
    # State breakdown
    state_links = [l for l in links_list if l['category'].startswith('State:')]
    if state_links:
        print("\n" + "="*60)
        print("STATE GOVERNMENT LINKS:")
        state_counts = {}
        for link in state_links:
            state = link['category'].replace('State: ', '')
            if state not in state_counts:
                state_counts[state] = 0
            state_counts[state] += 1
        
        for state in sorted(state_counts.keys()):
            print(f"  {state}: {state_counts[state]} links")
    
    # Top domains
    print("\n" + "="*60)
    print("TOP GOVERNMENT DOMAINS:")
    domains = {}
    for link in links_list:
        if '.gov' in link['domain'] or '.mil' in link['domain']:
            domain = link['domain']
            if domain not in domains:
                domains[domain] = 0
            domains[domain] += 1
    
    sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:30]
    for domain, count in sorted_domains:
        print(f"  {domain}: {count} links")

def main():
    """Main execution"""
    try:
        # Crawl targeted pages
        links = crawl_targeted_pages()
        
        print("\n" + "="*60)
        print(f"TOTAL EXTERNAL LINKS FOUND: {len(links)}")
        print("="*60)
        
        # Save results
        if links:
            save_results(links)
            print("\n[COMPLETE] Successfully extracted government links!")
        else:
            print("\n[WARNING] No links found!")
            
    except Exception as e:
        print(f"\n[ERROR]: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()