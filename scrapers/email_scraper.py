#!/usr/bin/env python3
"""
Government Email Scraper - Botasaurus Powered
Scrapes contact information from federal agency websites and discovers local government sites
"""

import re
import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Set, Optional
from urllib.parse import urljoin, urlparse
from botasaurus.request import request, Request as BotasaurusRequest
from botasaurus.browser import browser, Driver as BotasaurusDriver
from bs4 import BeautifulSoup
import logging

class GovernmentEmailScraper:
    """Advanced email scraper for government websites using Botasaurus."""
    
    def __init__(self, output_dir: str = "scraped_contacts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Email patterns for extraction
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+\s*\[at\]\s*[A-Za-z0-9.-]+\s*\[dot\]\s*[A-Za-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\s*\.\s*[A-Za-z]{2,}\b'
        ]
        
        # Government domain patterns for local site discovery
        self.gov_domain_patterns = [
            r'\.gov$',
            r'\.us$', 
            r'city\.',
            r'county\.',
            r'state\.',
            r'municipal\.',
            r'township\.'
        ]
        
        self.scraped_emails = set()
        self.discovered_gov_sites = set()
        self.logger = logging.getLogger(__name__)
        
    @staticmethod
    @request(
        cache=True,
        max_retry=3,
        parallel=5
    )
    def scrape_website_emails(request: BotasaurusRequest, url: str) -> Dict[str, Any]:
        """
        Scrape emails and contact information from a government website.
        
        Args:
            request: Botasaurus request object
            url: Website URL to scrape
            
        Returns:
            Dictionary with scraped emails and contact info
        """
        try:
            response = request.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract emails using multiple patterns
            emails = set()
            text_content = soup.get_text()
            
            # Standard email pattern
            email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content, re.IGNORECASE)
            emails.update(email_matches)
            
            # Obfuscated email patterns
            obfuscated_matches = re.findall(r'\b[A-Za-z0-9._%+-]+\s*\[at\]\s*[A-Za-z0-9.-]+\s*\[dot\]\s*[A-Za-z]{2,}\b', text_content, re.IGNORECASE)
            for match in obfuscated_matches:
                clean_email = match.replace('[at]', '@').replace('[dot]', '.').replace(' ', '')
                emails.add(clean_email)
            
            # Extract contact page links
            contact_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text = link.get_text().lower()
                if any(keyword in href or keyword in text for keyword in ['contact', 'about', 'staff', 'directory', 'leadership']):
                    full_url = urljoin(url, link.get('href'))
                    contact_links.append(full_url)
            
            # Discover government links
            gov_links = set()
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and any(re.search(pattern, href, re.IGNORECASE) for pattern in [r'\.gov', r'\.us$']):
                    full_url = urljoin(url, href)
                    parsed = urlparse(full_url)
                    if parsed.netloc and parsed.netloc not in ['usa.gov', 'www.usa.gov']:
                        gov_links.add(full_url)
            
            return {
                'url': url,
                'success': True,
                'emails': list(emails),
                'contact_links': contact_links[:10],  # Limit to avoid overload
                'discovered_gov_sites': list(gov_links),
                'title': soup.title.string if soup.title else '',
                'phone_numbers': GovernmentEmailScraper.extract_phone_numbers(text_content)
            }
            
        except Exception as e:
            return {
                'url': url,
                'success': False,
                'error': str(e),
                'emails': [],
                'contact_links': [],
                'discovered_gov_sites': [],
                'title': '',
                'phone_numbers': []
            }
    
    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """Extract phone numbers from text."""
        phone_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',  # (123) 456-7890
            r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
            r'\b1-\d{3}-\d{3}-\d{4}\b'  # 1-123-456-7890
        ]
        
        phones = set()
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phones.update(matches)
        
        return list(phones)
    
    @staticmethod
    @browser(
        headless=True,
        block_images=True
    )
    def scrape_contact_page(driver: BotasaurusDriver, url: str) -> Dict[str, Any]:
        """
        Use browser automation to scrape contact pages with JavaScript.
        
        Args:
            driver: Botasaurus browser driver
            url: Contact page URL
            
        Returns:
            Dictionary with contact information
        """
        try:
            driver.get(url, timeout=30)
            
            # Wait for content to load
            driver.sleep(2)
            
            # Look for email links and contact forms
            emails = set()
            
            # Find email links
            email_links = driver.find_elements('a[href^="mailto:"]')
            for link in email_links:
                href = link.get_attribute('href')
                if href and href.startswith('mailto:'):
                    email = href.replace('mailto:', '').split('?')[0]
                    emails.add(email)
            
            # Extract from page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            text_content = soup.get_text()
            
            # Extract emails from text
            email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content, re.IGNORECASE)
            emails.update(email_matches)
            
            return {
                'url': url,
                'success': True,
                'emails': list(emails),
                'phone_numbers': GovernmentEmailScraper.extract_phone_numbers(text_content),
                'method': 'browser'
            }
            
        except Exception as e:
            return {
                'url': url,
                'success': False,
                'error': str(e),
                'emails': [],
                'phone_numbers': [],
                'method': 'browser'
            }
    
    def scrape_federal_agencies(self, agencies_csv_path: str) -> Dict[str, Any]:
        """
        Scrape emails from all federal agencies in the CSV file.
        
        Args:
            agencies_csv_path: Path to CSV file with agency URLs
            
        Returns:
            Dictionary with scraping results
        """
        self.logger.info(f"Starting federal agency email scraping from {agencies_csv_path}")
        
        # Load agency URLs
        agency_urls = []
        try:
            with open(agencies_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('homepage_url', '').strip()
                    if url and url.startswith('http') and url != 'See USA.gov':
                        agency_urls.append({
                            'name': row.get('agency_name', ''),
                            'url': url,
                            'section': row.get('section', '')
                        })
        except Exception as e:
            self.logger.error(f"Error loading agencies CSV: {e}")
            return {'success': False, 'error': str(e)}
        
        self.logger.info(f"Loaded {len(agency_urls)} agency URLs for scraping")
        
        # Scrape emails from each agency
        all_results = []
        for i, agency in enumerate(agency_urls):
            self.logger.info(f"Scraping {i+1}/{len(agency_urls)}: {agency['name']}")
            
            result = self.scrape_website_emails(agency['url'])
            result['agency_name'] = agency['name']
            result['section'] = agency['section']
            
            all_results.append(result)
            
            # Update statistics
            if result['success']:
                self.scraped_emails.update(result['emails'])
                self.discovered_gov_sites.update(result['discovered_gov_sites'])
        
        # Export results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = os.path.join(self.output_dir, f'federal_emails_{timestamp}.json')
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        # Export consolidated emails
        emails_csv = os.path.join(self.output_dir, f'consolidated_emails_{timestamp}.csv')
        self.export_emails_csv(emails_csv, all_results)
        
        self.logger.info(f"Federal agency scraping completed. Found {len(self.scraped_emails)} unique emails")
        
        return {
            'success': True,
            'agencies_scraped': len(agency_urls),
            'unique_emails_found': len(self.scraped_emails),
            'gov_sites_discovered': len(self.discovered_gov_sites),
            'results_file': results_file,
            'emails_csv': emails_csv
        }
    
    def scrape_discovered_gov_sites(self, max_sites: int = 100) -> Dict[str, Any]:
        """
        Scrape emails from discovered government sites.
        
        Args:
            max_sites: Maximum number of sites to scrape
            
        Returns:
            Dictionary with scraping results
        """
        sites_to_scrape = list(self.discovered_gov_sites)[:max_sites]
        self.logger.info(f"Scraping {len(sites_to_scrape)} discovered government sites")
        
        all_results = []
        for i, url in enumerate(sites_to_scrape):
            self.logger.info(f"Scraping discovered site {i+1}/{len(sites_to_scrape)}: {url}")
            
            result = self.scrape_website_emails(url)
            all_results.append(result)
            
            if result['success']:
                self.scraped_emails.update(result['emails'])
        
        # Export results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = os.path.join(self.output_dir, f'local_gov_emails_{timestamp}.json')
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        return {
            'success': True,
            'sites_scraped': len(sites_to_scrape),
            'results_file': results_file
        }
    
    def export_emails_csv(self, filepath: str, results: List[Dict]) -> None:
        """Export all scraped emails to CSV format."""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['agency_name', 'website', 'email', 'phone', 'contact_type'])
            
            for result in results:
                if result['success']:
                    agency_name = result.get('agency_name', 'Unknown')
                    website = result['url']
                    
                    # Write emails
                    for email in result.get('emails', []):
                        writer.writerow([agency_name, website, email, '', 'email'])
                    
                    # Write phone numbers
                    for phone in result.get('phone_numbers', []):
                        writer.writerow([agency_name, website, '', phone, 'phone'])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive scraping statistics."""
        return {
            'total_unique_emails': len(self.scraped_emails),
            'discovered_gov_sites': len(self.discovered_gov_sites),
            'scraped_emails': list(self.scraped_emails)[:50],  # Sample
            'discovered_sites_sample': list(self.discovered_gov_sites)[:20]
        }


def main():
    """Main entry point for email scraping."""
    logging.basicConfig(level=logging.INFO)
    
    scraper = GovernmentEmailScraper()
    
    print("🏛️ Government Email Scraper - Botasaurus Powered")
    print("=" * 60)
    
    # Find the most recent agencies CSV
    agencies_files = [
        'scraped_data/all_agencies_20250825_150513.csv',
        'scraped_data/usa_gov_agencies_20250825_225741.csv'
    ]
    
    agencies_file = None
    for file_path in agencies_files:
        if os.path.exists(file_path):
            agencies_file = file_path
            break
    
    if not agencies_file:
        print("❌ No agencies CSV file found!")
        return
    
    print(f"📄 Using agencies file: {agencies_file}")
    
    # Scrape federal agencies
    print("\n🔍 Phase 1: Scraping Federal Agency Emails...")
    federal_results = scraper.scrape_federal_agencies(agencies_file)
    
    if federal_results['success']:
        print(f"✅ Federal scraping complete!")
        print(f"   • Agencies scraped: {federal_results['agencies_scraped']}")
        print(f"   • Unique emails found: {federal_results['unique_emails_found']}")
        print(f"   • Gov sites discovered: {federal_results['gov_sites_discovered']}")
        
        # Scrape discovered government sites
        if federal_results['gov_sites_discovered'] > 0:
            print(f"\n🔍 Phase 2: Scraping {federal_results['gov_sites_discovered']} Discovered Gov Sites...")
            local_results = scraper.scrape_discovered_gov_sites(max_sites=50)
            
            if local_results['success']:
                print(f"✅ Local government scraping complete!")
                print(f"   • Sites scraped: {local_results['sites_scraped']}")
    
    # Print final statistics
    stats = scraper.get_statistics()
    print(f"\n📊 Final Statistics:")
    print(f"   • Total unique emails: {stats['total_unique_emails']}")
    print(f"   • Sample emails: {stats['scraped_emails'][:5]}")
    print(f"   • Discovered sites: {len(stats['discovered_sites_sample'])}")


if __name__ == "__main__":
    main()