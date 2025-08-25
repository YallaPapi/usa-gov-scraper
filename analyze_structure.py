"""
Analyze the actual structure of USA.gov agency index
"""

import requests
from bs4 import BeautifulSoup

def analyze():
    r = requests.get('https://www.usa.gov/agency-index')
    soup = BeautifulSoup(r.text, 'html.parser')
    
    print('Looking for A-Z structure:')
    
    agencies_found = []
    
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        h2 = soup.find('h2', string=letter)
        if h2:
            print(f'\n{letter}: Found')
            
            # Find the next ul element after the h2
            current = h2.find_next_sibling()
            while current and current.name != 'h2':
                if current.name == 'ul':
                    links = current.find_all('a')
                    print(f'  Found {len(links)} agencies')
                    
                    for link in links[:3]:  # Show first 3
                        agency_name = link.text.strip()
                        href = link.get('href', '')
                        agencies_found.append({
                            'name': agency_name,
                            'url': href,
                            'section': letter
                        })
                        print(f'    • {agency_name}')
                    break
                current = current.find_next_sibling()
    
    print(f'\n\nTotal agencies found: {len(agencies_found)}')
    return agencies_found

if __name__ == "__main__":
    analyze()