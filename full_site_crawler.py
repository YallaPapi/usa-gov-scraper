"""
FULL USA.GOV SITE CRAWLER
Crawls entire USA.gov website for ALL external government links:
- Federal agencies
- State governments
- Local governments
- Elected officials
- All .gov sites
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time
from collections import deque

class USAGovCrawler:
    def __init__(self):
        self.base_url = "https://www.usa.gov"
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.visited_urls = set()
        self.to_visit = deque()
        self.external_links = {}
        self.max_depth = 3  # How deep to crawl
        self.max_pages = 500  # Max pages to visit
        self.pages_visited = 0
        
    def is_external(self, url):
        """Check if URL is external"""
        parsed = urlparse(url)
        return parsed.netloc and parsed.netloc != 'www.usa.gov' and parsed.netloc != 'usa.gov'
    
    def categorize_link(self, url, text, source_page):
        """Categorize the type of government link"""
        url_lower = url.lower()
        text_lower = text.lower() if text else ""
        
        # Determine category
        if '.gov' in url_lower:
            if any(state in url_lower for state in ['.state.', '.alabama.', '.alaska.', '.arizona.', '.arkansas.', 
                                                    '.california.', '.colorado.', '.connecticut.', '.delaware.',
                                                    '.florida.', '.georgia.', '.hawaii.', '.idaho.', '.illinois.',
                                                    '.indiana.', '.iowa.', '.kansas.', '.kentucky.', '.louisiana.',
                                                    '.maine.', '.maryland.', '.massachusetts.', '.michigan.',
                                                    '.minnesota.', '.mississippi.', '.missouri.', '.montana.',
                                                    '.nebraska.', '.nevada.', '.newhampshire.', '.newjersey.',
                                                    '.newmexico.', '.newyork.', '.northcarolina.', '.northdakota.',
                                                    '.ohio.', '.oklahoma.', '.oregon.', '.pennsylvania.',
                                                    '.rhodeisland.', '.southcarolina.', '.southdakota.', '.tennessee.',
                                                    '.texas.', '.utah.', '.vermont.', '.virginia.', '.washington.',
                                                    '.westvirginia.', '.wisconsin.', '.wyoming.']):
                category = "State Government"
            elif any(local in url_lower for local in ['city', 'county', 'town', 'village', 'borough']):
                category = "Local Government"
            elif 'congress' in url_lower or 'senate' in url_lower or 'house' in url_lower:
                category = "Congress/Elected Officials"
            elif 'court' in url_lower or 'judicial' in url_lower:
                category = "Judicial/Courts"
            else:
                category = "Federal Agency/Department"
        elif '.mil' in url_lower:
            category = "Military"
        elif '.edu' in url_lower and 'gov' in text_lower:
            category = "Government Education"
        elif 'state' in source_page and 'gov' in url_lower:
            category = "State Government"
        else:
            category = "Other Government-Related"
            
        return category
    
    def crawl_page(self, url, depth=0):
        """Crawl a single page for links"""
        if url in self.visited_urls or depth > self.max_depth or self.pages_visited >= self.max_pages:
            return
        
        self.visited_urls.add(url)
        self.pages_visited += 1
        
        print(f"[{self.pages_visited}/{self.max_pages}] Crawling: {url[:80]}...")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.text.strip()
                
                # Make URL absolute
                full_url = urljoin(url, href)
                
                # Check if external
                if self.is_external(full_url):
                    # Categorize and store
                    category = self.categorize_link(full_url, text, url)
                    
                    if full_url not in self.external_links:
                        self.external_links[full_url] = {
                            'url': full_url,
                            'text': text[:200],  # Limit text length
                            'category': category,
                            'found_on': url,
                            'domain': urlparse(full_url).netloc
                        }
                        print(f"  Found [{category}]: {text[:50]}...")
                else:
                    # Internal link - add to queue if not visited
                    if full_url.startswith(self.base_url) and full_url not in self.visited_urls:
                        self.to_visit.append((full_url, depth + 1))
            
            # Special handling for key pages
            if 'state' in url.lower() or 'local' in url.lower():
                print(f"  [STATE/LOCAL PAGE] Extracting all government links...")
            elif 'elected' in url.lower() or 'official' in url.lower():
                print(f"  [ELECTED OFFICIALS PAGE] Extracting official links...")
                
        except Exception as e:
            print(f"  Error crawling {url[:50]}: {str(e)}")
        
        time.sleep(0.5)  # Be polite
    
    def crawl_site(self):
        """Main crawling function"""
        print("="*60)
        print("STARTING FULL USA.GOV SITE CRAWL")
        print("="*60)
        
        # Key pages to definitely visit
        priority_pages = [
            "/",  # Homepage
            "/agencies",
            "/agency-index",
            "/state-government",
            "/states",
            "/local-governments", 
            "/elected-officials",
            "/branches-of-government",
            "/federal-agencies",
            "/state-tribal-governments",
            "/local-gov",
            "/congress",
            "/courts",
            "/executive-branch",
            "/legislative-branch",
            "/judicial-branch"
        ]
        
        # Add priority pages to queue
        for page in priority_pages:
            full_url = self.base_url + page
            self.to_visit.append((full_url, 0))
        
        # Also get the main navigation pages
        print("\nFetching main navigation...")
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find main navigation links
            nav_links = soup.find_all('a', href=True)[:100]  # First 100 links likely include nav
            for link in nav_links:
                href = link.get('href', '')
                full_url = urljoin(self.base_url, href)
                if full_url.startswith(self.base_url) and full_url not in self.visited_urls:
                    self.to_visit.append((full_url, 0))
        except:
            pass
        
        # Start crawling
        print(f"\nStarting crawl with {len(self.to_visit)} URLs in queue...")
        
        while self.to_visit and self.pages_visited < self.max_pages:
            url, depth = self.to_visit.popleft()
            self.crawl_page(url, depth)
        
        print(f"\nCrawl complete! Visited {self.pages_visited} pages")
        print(f"Found {len(self.external_links)} unique external links")
        
        return self.external_links

def save_crawl_results(links):
    """Save the crawl results"""
    
    if not links:
        print("No links to save!")
        return
        
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Convert to list for saving
    links_list = list(links.values())
    
    # Sort by category
    links_list.sort(key=lambda x: (x['category'], x['domain']))
    
    # Save to CSV
    csv_file = f"scraped_data/full_site_links_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['category', 'domain', 'url', 'text', 'found_on']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(links_list)
    print(f"\nCSV saved: {csv_file}")
    
    # Save to JSON
    json_file = f"scraped_data/full_site_links_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(links_list, f, indent=2, ensure_ascii=False)
    print(f"JSON saved: {json_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY BY CATEGORY:")
    categories = {}
    for link in links_list:
        cat = link['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(link)
    
    for category in sorted(categories.keys()):
        print(f"\n{category}: {len(categories[category])} links")
        # Show first 5 examples
        for link in categories[category][:5]:
            print(f"  • {link['text'][:50]}...")
            print(f"    {link['url'][:60]}...")
    
    # Domain summary
    print("\n" + "="*60)
    print("TOP DOMAINS:")
    domains = {}
    for link in links_list:
        domain = link['domain']
        if domain not in domains:
            domains[domain] = 0
        domains[domain] += 1
    
    sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
    for domain, count in sorted_domains[:20]:
        print(f"  {domain}: {count} links")

def main():
    """Main execution"""
    try:
        crawler = USAGovCrawler()
        
        # You can adjust these
        crawler.max_depth = 2  # How many levels deep to crawl
        crawler.max_pages = 200  # Max pages to visit
        
        print("Configuration:")
        print(f"  Max depth: {crawler.max_depth}")
        print(f"  Max pages: {crawler.max_pages}")
        print()
        
        # Crawl the site
        external_links = crawler.crawl_site()
        
        # Save results
        if external_links:
            save_crawl_results(external_links)
            print(f"\n[COMPLETE] Found {len(external_links)} external government links!")
        else:
            print("\n[WARNING] No external links found!")
            
    except KeyboardInterrupt:
        print("\n[STOPPED] Crawl interrupted by user")
        if crawler.external_links:
            save_crawl_results(crawler.external_links)
    except Exception as e:
        print(f"\n[ERROR]: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()