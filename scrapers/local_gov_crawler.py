#!/usr/bin/env python3
"""
Local Government Site Discovery Crawler - Botasaurus Powered
Discovers and scrapes local government websites at city, county, and state levels
"""

import re
import csv
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Set, Optional
from urllib.parse import urljoin, urlparse, urlencode
from botasaurus.request import request, Request as BotasaurusRequest
from botasaurus.browser import browser, Driver as BotasaurusDriver
from bs4 import BeautifulSoup
import logging

class LocalGovernmentCrawler:
    """Advanced crawler for discovering local government websites."""
    
    def __init__(self, output_dir: str = "local_gov_sites"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Local government search patterns
        self.search_terms = [
            # Cities
            "city government official website",
            "municipal government contact",
            "mayor office contact information",
            "city council contact",
            
            # Counties 
            "county government official website",
            "county commissioner contact",
            "county clerk office",
            "county administration contact",
            
            # States
            "state government official website", 
            "governor office contact",
            "state legislature contact",
            "state agency directory",
            
            # Other local governments
            "township government contact",
            "village government website",
            "parish government contact"
        ]
        
        # Government site validation patterns
        self.gov_site_patterns = [
            r'^https?://.*\.gov(/.*)?$',
            r'^https?://.*\.us(/.*)?$',
            r'^https?://.*city\..*(/.*)?$',
            r'^https?://.*county\..*(/.*)?$',
            r'^https?://.*state\..*(/.*)?$'
        ]
        
        self.discovered_sites = set()
        self.validated_gov_sites = set()
        self.logger = logging.getLogger(__name__)
        
    @staticmethod
    @request(
        cache=True,
        max_retry=2,
        parallel=3
    )
    def search_government_sites(request: BotasaurusRequest, search_term: str, location: str = "") -> Dict[str, Any]:
        """
        Search for government websites using search engines.
        
        Args:
            request: Botasaurus request object
            search_term: Search query for government sites
            location: Specific location to search (optional)
            
        Returns:
            Dictionary with discovered government sites
        """
        try:
            # Construct search query
            query = f"{search_term}"
            if location:
                query += f" {location}"
            
            # Use DuckDuckGo for searching (more permissive than Google)
            search_url = f"https://html.duckduckgo.com/html/?q={urlencode({'q': query})}"
            
            response = request.get(search_url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search result links
            gov_links = set()
            
            # DuckDuckGo result links
            for link in soup.find_all('a', class_='result__a'):
                href = link.get('href')
                if href:
                    # Clean DuckDuckGo redirect URL
                    if 'uddg=' in href:
                        import urllib.parse
                        href = urllib.parse.unquote(href.split('uddg=')[1].split('&')[0])
                    
                    # Validate government site
                    if LocalGovernmentCrawler.is_government_site(href):
                        gov_links.add(href)
            
            return {
                'search_term': search_term,
                'location': location,
                'success': True,
                'gov_links': list(gov_links),
                'total_found': len(gov_links)
            }
            
        except Exception as e:
            return {
                'search_term': search_term,
                'location': location,
                'success': False,
                'error': str(e),
                'gov_links': [],
                'total_found': 0
            }
    
    @staticmethod
    def is_government_site(url: str) -> bool:
        """
        Validate if a URL is a government website.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL appears to be a government site
        """
        if not url or not url.startswith(('http://', 'https://')):
            return False
        
        patterns = [
            r'\.gov(/|$)',
            r'\.us(/|$)',  
            r'city\.',
            r'county\.',
            r'state\.',
            r'municipal\.',
            r'township\.'
        ]
        
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns)
    
    @staticmethod
    @request(
        cache=True,
        max_retry=3,
        parallel=5
    )
    def crawl_site_for_contacts(request: BotasaurusRequest, url: str) -> Dict[str, Any]:
        """
        Crawl a government site for contact information and related sites.
        
        Args:
            request: Botasaurus request object
            url: Government site URL to crawl
            
        Returns:
            Dictionary with contact information and discovered links
        """
        try:
            response = request.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic site information
            title = soup.title.string.strip() if soup.title else ''
            
            # Extract contact information
            emails = set()
            phones = set()
            
            text_content = soup.get_text()
            
            # Email extraction
            email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content, re.IGNORECASE)
            emails.update(email_matches)
            
            # Phone extraction
            phone_patterns = [
                r'\b\d{3}-\d{3}-\d{4}\b',
                r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',
                r'\b\d{3}\.\d{3}\.\d{4}\b'
            ]
            
            for pattern in phone_patterns:
                phone_matches = re.findall(pattern, text_content)
                phones.update(phone_matches)
            
            # Discover related government sites
            related_gov_sites = set()
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    if LocalGovernmentCrawler.is_government_site(full_url) and full_url != url:
                        related_gov_sites.add(full_url)
            
            # Extract address information
            address_patterns = [
                r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Circle|Cir|Court|Ct|Place|Pl)\b',
                r'\b[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b'
            ]
            
            addresses = set()
            for pattern in address_patterns:
                address_matches = re.findall(pattern, text_content)
                addresses.update(address_matches)
            
            return {
                'url': url,
                'success': True,
                'title': title,
                'emails': list(emails),
                'phones': list(phones),
                'addresses': list(addresses),
                'related_gov_sites': list(related_gov_sites)[:20],  # Limit to prevent overload
                'site_type': LocalGovernmentCrawler.classify_gov_site(url, title)
            }
            
        except Exception as e:
            return {
                'url': url,
                'success': False,
                'error': str(e),
                'title': '',
                'emails': [],
                'phones': [],
                'addresses': [],
                'related_gov_sites': [],
                'site_type': 'unknown'
            }
    
    @staticmethod
    def classify_gov_site(url: str, title: str) -> str:
        """
        Classify the type of government site.
        
        Args:
            url: Site URL
            title: Site title
            
        Returns:
            Classification string
        """
        url_lower = url.lower()
        title_lower = title.lower()
        
        if any(term in url_lower or term in title_lower for term in ['city', 'municipal']):
            return 'city'
        elif any(term in url_lower or term in title_lower for term in ['county', 'parish']):
            return 'county'
        elif any(term in url_lower or term in title_lower for term in ['state', 'gov']):
            return 'state'
        elif any(term in url_lower or term in title_lower for term in ['township', 'village']):
            return 'local'
        else:
            return 'government'
    
    def discover_by_search(self, locations: List[str] = None) -> Dict[str, Any]:
        """
        Discover government sites through search queries.
        
        Args:
            locations: List of specific locations to search
            
        Returns:
            Dictionary with discovery results
        """
        if locations is None:
            locations = [''] # Empty string for general searches
        
        all_results = []
        discovered_sites = set()
        
        self.logger.info(f"Starting government site discovery with {len(self.search_terms)} search terms")
        
        for location in locations:
            for search_term in self.search_terms:
                self.logger.info(f"Searching: {search_term} {location}".strip())
                
                result = self.search_government_sites(search_term, location)
                all_results.append(result)
                
                if result['success']:
                    discovered_sites.update(result['gov_links'])
                    
                # Small delay to be respectful
                time.sleep(1)
        
        self.discovered_sites.update(discovered_sites)
        
        # Export discovery results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        discovery_file = os.path.join(self.output_dir, f'gov_site_discovery_{timestamp}.json')
        
        with open(discovery_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Discovery complete. Found {len(discovered_sites)} unique government sites")
        
        return {
            'success': True,
            'sites_discovered': len(discovered_sites),
            'discovery_file': discovery_file,
            'discovered_sites': list(discovered_sites)[:50]  # Sample
        }
    
    def crawl_discovered_sites(self, max_sites: int = 100) -> Dict[str, Any]:
        """
        Crawl discovered government sites for contact information.
        
        Args:
            max_sites: Maximum number of sites to crawl
            
        Returns:
            Dictionary with crawling results
        """
        sites_to_crawl = list(self.discovered_sites)[:max_sites]
        self.logger.info(f"Crawling {len(sites_to_crawl)} discovered government sites")
        
        all_results = []
        all_contacts = []
        
        for i, url in enumerate(sites_to_crawl):
            self.logger.info(f"Crawling site {i+1}/{len(sites_to_crawl)}: {url}")
            
            result = self.crawl_site_for_contacts(url)
            all_results.append(result)
            
            if result['success']:
                # Collect contact information
                for email in result['emails']:
                    all_contacts.append({
                        'site_url': url,
                        'site_title': result['title'],
                        'site_type': result['site_type'],
                        'contact_type': 'email',
                        'contact_value': email
                    })
                
                for phone in result['phones']:
                    all_contacts.append({
                        'site_url': url,
                        'site_title': result['title'],
                        'site_type': result['site_type'],
                        'contact_type': 'phone',
                        'contact_value': phone
                    })
                
                # Discover more sites from crawled pages
                self.discovered_sites.update(result['related_gov_sites'])
        
        # Export crawling results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        crawl_file = os.path.join(self.output_dir, f'gov_site_crawl_{timestamp}.json')
        contacts_file = os.path.join(self.output_dir, f'local_gov_contacts_{timestamp}.csv')
        
        with open(crawl_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        # Export contacts to CSV
        with open(contacts_file, 'w', newline='', encoding='utf-8') as f:
            if all_contacts:
                writer = csv.DictWriter(f, fieldnames=all_contacts[0].keys())
                writer.writeheader()
                writer.writerows(all_contacts)
        
        self.logger.info(f"Crawling complete. Found {len(all_contacts)} contacts")
        
        return {
            'success': True,
            'sites_crawled': len(sites_to_crawl),
            'contacts_found': len(all_contacts),
            'crawl_file': crawl_file,
            'contacts_file': contacts_file
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive crawling statistics."""
        return {
            'total_discovered_sites': len(self.discovered_sites),
            'validated_gov_sites': len(self.validated_gov_sites),
            'sample_sites': list(self.discovered_sites)[:20]
        }


def main():
    """Main entry point for local government discovery."""
    logging.basicConfig(level=logging.INFO)
    
    crawler = LocalGovernmentCrawler()
    
    print("🏛️ Local Government Site Discovery - Botasaurus Powered")
    print("=" * 60)
    
    # Major US locations for targeted discovery
    locations = [
        "New York",
        "Los Angeles", 
        "Chicago",
        "Houston",
        "Phoenix",
        "Philadelphia",
        "San Antonio",
        "San Diego",
        "Dallas",
        "Austin"
    ]
    
    # Phase 1: Discover government sites
    print(f"🔍 Phase 1: Discovering Government Sites in {len(locations)} Major Cities...")
    discovery_results = crawler.discover_by_search(locations[:3])  # Start with 3 cities
    
    if discovery_results['success']:
        print(f"✅ Discovery complete!")
        print(f"   • Sites discovered: {discovery_results['sites_discovered']}")
        print(f"   • Sample sites: {discovery_results['discovered_sites'][:5]}")
        
        # Phase 2: Crawl discovered sites
        print(f"\n🔍 Phase 2: Crawling {discovery_results['sites_discovered']} Discovered Sites...")
        crawl_results = crawler.crawl_discovered_sites(max_sites=25)  # Limit for demo
        
        if crawl_results['success']:
            print(f"✅ Crawling complete!")
            print(f"   • Sites crawled: {crawl_results['sites_crawled']}")
            print(f"   • Contacts found: {crawl_results['contacts_found']}")
    
    # Print final statistics
    stats = crawler.get_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   • Total discovered sites: {stats['total_discovered_sites']}")
    print(f"   • Sample discovered sites:")
    for site in stats['sample_sites'][:5]:
        print(f"     - {site}")


if __name__ == "__main__":
    main()