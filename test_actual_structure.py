"""
Test script to understand the actual USA.gov page structure
"""

import requests
from bs4 import BeautifulSoup
import json

def test_structure():
    """Analyze the actual page structure"""
    
    print("Fetching USA.gov agency index page...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get('https://www.usa.gov/agency-index', headers=headers, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print("Failed to fetch page")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # First, let's see what the page actually contains
    print("\n1. Looking for h2 elements (letters):")
    h2_elements = soup.find_all('h2')
    print(f"Found {len(h2_elements)} h2 elements")
    for h2 in h2_elements[:5]:
        print(f"  - {h2.text.strip()}")
    
    # Now let's look for the actual structure
    print("\n2. Checking structure for letter 'A':")
    
    # Try different methods to find the 'A' section
    
    # Method 1: Find h2 with id="A"
    a_section = soup.find('h2', id='A')
    if a_section:
        print("  Found h2 with id='A'")
        print(f"  Text: {a_section.text.strip()}")
    
    # Method 2: Find h2 containing 'A'
    a_section2 = soup.find('h2', string='A')
    if a_section2:
        print("  Found h2 with string='A'")
    
    # Let's find what comes after the h2
    if a_section:
        print("\n3. Looking for agencies after 'A' heading:")
        
        # Get the parent element
        parent = a_section.parent
        print(f"  Parent tag: {parent.name if parent else 'None'}")
        
        # Look for ul elements
        if parent:
            uls = parent.find_all('ul')
            print(f"  Found {len(uls)} ul elements in parent")
            
            if uls:
                first_ul = uls[0]
                links = first_ul.find_all('a')
                print(f"  First ul has {len(links)} links")
                
                # Show first 5 agencies
                print("\n  First 5 agencies found:")
                for i, link in enumerate(links[:5], 1):
                    text = link.text.strip()
                    href = link.get('href', '')
                    print(f"    {i}. {text}")
                    print(f"       URL: {href}")
        
        # Alternative: look for next sibling
        print("\n4. Checking siblings after h2:")
        next_elem = a_section.find_next_sibling()
        while next_elem and next_elem.name != 'h2':
            if next_elem.name == 'ul':
                print(f"  Found ul as sibling")
                links = next_elem.find_all('a')
                print(f"  Has {len(links)} links")
                
                # Show first 3
                for link in links[:3]:
                    print(f"    - {link.text.strip()}")
                break
            next_elem = next_elem.find_next_sibling()
    
    # Let's also check the overall page structure
    print("\n5. Checking overall page structure:")
    
    # Find main content area
    main = soup.find('main')
    if main:
        print("  Found <main> element")
        
        # Look for agency lists in main
        all_links = main.find_all('a')
        print(f"  Total links in main: {len(all_links)}")
        
        # Filter to likely agency links
        agency_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.text.strip()
            
            # Skip navigation links and empty text
            if text and len(text) > 2 and not href.startswith('#'):
                # Skip if it's just a letter
                if len(text) == 1 and text.isalpha():
                    continue
                    
                agency_links.append({
                    'name': text,
                    'url': href
                })
        
        print(f"  Potential agency links: {len(agency_links)}")
        print("\n  Sample agencies:")
        for agency in agency_links[:10]:
            print(f"    • {agency['name']}")

if __name__ == "__main__":
    test_structure()