"""
Diagnose the actual HTML structure of USA.gov agency index
"""

import requests
from bs4 import BeautifulSoup

def diagnose():
    """Thoroughly analyze the page structure"""
    
    print("Fetching USA.gov agency index...")
    url = "https://www.usa.gov/agency-index"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n1. ALL H2 ELEMENTS ON PAGE:")
    h2_elements = soup.find_all('h2')
    for i, h2 in enumerate(h2_elements):
        text = h2.text.strip()
        h2_id = h2.get('id', 'no-id')
        print(f"  [{i}] Text: '{text}' | ID: '{h2_id}'")
    
    print("\n2. SEARCHING FOR LETTER 'A':")
    
    # Method 1: By text content
    a_by_text = soup.find('h2', string='A')
    if a_by_text:
        print("  Found by text='A'")
    
    # Method 2: By ID
    a_by_id = soup.find('h2', id='A')
    if a_by_id:
        print("  Found by id='A'")
    
    # Method 3: Contains text
    a_contains = soup.find('h2', string=lambda text: text and 'A' in text)
    if a_contains:
        print(f"  Found containing 'A': {a_contains.text.strip()}")
    
    # Method 4: Search all h2s
    for h2 in h2_elements:
        if h2.text.strip() == 'A':
            print(f"  Found exact match 'A': {h2}")
            a_by_text = h2
            break
    
    print("\n3. STRUCTURE AROUND 'A':")
    if a_by_text or a_by_id:
        target_h2 = a_by_text or a_by_id
        print(f"  H2 element: {target_h2}")
        
        # Check parent
        parent = target_h2.parent
        print(f"  Parent tag: {parent.name if parent else 'None'}")
        
        # Check next siblings
        print("  Next 5 siblings:")
        sibling = target_h2.find_next_sibling()
        for i in range(5):
            if sibling:
                print(f"    [{i}] {sibling.name}: {str(sibling)[:100]}...")
                sibling = sibling.find_next_sibling()
    
    print("\n4. LOOKING FOR AGENCIES:")
    
    # Find all links that look like agencies
    all_links = soup.find_all('a')
    agency_candidates = []
    
    for link in all_links:
        text = link.text.strip()
        href = link.get('href', '')
        
        # Skip single letters and empty
        if not text or len(text) == 1:
            continue
        
        # Skip navigation
        if text in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            continue
            
        # Look for government-sounding names
        gov_keywords = ['Department', 'Agency', 'Administration', 'Bureau', 'Commission', 
                       'Office', 'Service', 'Institute', 'Foundation', 'Corporation']
        
        if any(keyword in text for keyword in gov_keywords):
            agency_candidates.append({
                'name': text,
                'url': href
            })
    
    print(f"  Found {len(agency_candidates)} potential agencies")
    if agency_candidates:
        print("  First 10 agencies:")
        for agency in agency_candidates[:10]:
            print(f"    • {agency['name']}")
    
    # Alternative: Look for ul elements with multiple links
    print("\n5. UL ELEMENTS WITH LINKS:")
    all_uls = soup.find_all('ul')
    for i, ul in enumerate(all_uls[:5]):
        links_in_ul = ul.find_all('a')
        if len(links_in_ul) > 5:  # Likely contains agencies
            print(f"  UL {i}: Contains {len(links_in_ul)} links")
            print("    First 3 links:")
            for link in links_in_ul[:3]:
                print(f"      • {link.text.strip()}")

if __name__ == "__main__":
    diagnose()