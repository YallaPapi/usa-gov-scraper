"""
USA.gov Government Agency Scraper - Botasaurus Core Module
Complete replacement for core.py with proper Botasaurus integration
"""

from botasaurus.request import request, Request as BotasaurusRequest
from botasaurus.browser import browser, Driver as BotasaurusDriver
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import json
import csv
import os
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
import logging


class GovernmentAgencyScraper:
    """Unified scraper for USA.gov agency index using Botasaurus with proper error handling."""
    
    def __init__(self, rate_limit: float = 0.5, max_retries: int = 3):
        self.base_url = "https://www.usa.gov/agency-index"
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        
        # Initialize statistics
        self.stats = {
            'sections_scraped': 0,
            'agencies_found': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def parse_agency_section(soup: BeautifulSoup, section_id: str) -> List[Dict[str, Any]]:
        """
        Parse a specific alphabetical section and extract agency information.
        
        Args:
            soup: BeautifulSoup object of the page
            section_id: Single letter ID of the section (A-Z)
            
        Returns:
            List of agency dictionaries with name, URL, and parent department
        """
        # Find the main content area
        main_content = soup.find('main') or soup.find('div', class_='usa-grid') or soup.find('div', class_='usa-layout-docs-main_content')
        
        if not main_content:
            return []
        
        # Find all H2 headers - each represents an agency
        agency_headers = main_content.find_all('h2')
        
        agencies = []
        current_section_letter = None
        
        for header in agency_headers:
            header_text = header.text.strip()
            
            # Skip letter headers (single letters A-Z that mark sections)
            if len(header_text) == 1 and header_text.isalpha() and header_text.isupper():
                current_section_letter = header_text
                continue
            
            # Skip non-agency headers
            if len(header_text) < 3:
                continue
            
            # Only include agencies that start with the target section letter
            if not header_text.upper().startswith(section_id.upper()):
                continue
            
            # Find the next element that contains links for this agency
            next_element = header.find_next_sibling()
            
            if not next_element:
                continue
            
            # Look for the main agency website link
            links = next_element.find_all('a', href=True)
            
            if not links:
                continue
            
            # Get the first external link (skip internal USA.gov links)
            homepage_url = None
            for link in links:
                url = link.get('href', '')
                if url and not url.startswith('https://www.usa.gov'):
                    # Make URL absolute if it's relative
                    if not url.startswith(('http://', 'https://')):
                        url = urljoin('https://www.usa.gov', url)
                    homepage_url = url
                    break
            
            # Skip if no external URL found
            if not homepage_url:
                continue
            
            # Extract parent department if available
            parent_dept = None
            parent_text = next_element.get_text()
            if '(' in header_text and ')' in header_text:
                # Department abbreviation in parentheses might indicate parent
                abbrev = header_text[header_text.find('(')+1:header_text.find(')')]
                if len(abbrev) <= 10:  # Reasonable abbreviation length
                    parent_dept = abbrev
            
            agencies.append({
                'agency_name': header_text,
                'homepage_url': homepage_url,
                'parent_department': parent_dept,
                'section': section_id
            })
        
        return agencies
    
    @staticmethod
    @request(
        cache=True,
        max_retry=3,
        parallel=5  # Parallel processing for efficiency
    )
    def scrape_section_static(request: BotasaurusRequest, section_id: str, data: Any = None) -> Dict[str, Any]:
        """
        Static method to scrape a single alphabetical section using Botasaurus.
        
        Args:
            request: Botasaurus request object
            section_id: Single letter ID (A-Z)
            
        Returns:
            Dictionary with section data and agencies
        """
        try:
            # Get the page HTML
            response = request.get("https://www.usa.gov/agency-index")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse the specific section
            agencies = GovernmentAgencyScraper.parse_agency_section(soup, section_id)
            
            return {
                'section': str(section_id),
                'success': True,
                'agency_count': len(agencies),
                'agencies': agencies
            }
            
        except Exception as e:
            error_msg = f"Error scraping section {section_id}: {str(e)}"
            return {
                'section': str(section_id),
                'success': False,
                'error': error_msg,
                'agencies': []
            }
    
    def scrape_section(self, section_id: str) -> Dict[str, Any]:
        """
        Instance method to scrape a single alphabetical section.
        
        Args:
            section_id: Single letter ID (A-Z)
            
        Returns:
            Dictionary with section data and agencies
        """
        self.logger.info(f"Scraping section {section_id}")
        
        # Use the static Botasaurus method
        result = self.scrape_section_static(section_id)
        
        # Update instance statistics
        if result['success']:
            self.stats['sections_scraped'] += 1
            self.stats['agencies_found'] += result['agency_count']
        else:
            self.stats['errors'].append(result.get('error', f'Unknown error in section {section_id}'))
        
        # Rate limiting
        time.sleep(self.rate_limit)
        
        return result
    
    @staticmethod
    @request(
        cache=True,
        max_retry=3,
        parallel=1  # Single thread for comprehensive scrape to avoid overloading
    )
    def scrape_all_sections_static(request: BotasaurusRequest, data: Any = None) -> Dict[str, Any]:
        """
        Static method to scrape all alphabetical sections using Botasaurus.
        
        Args:
            request: Botasaurus request object
            
        Returns:
            Dictionary with all agencies and statistics
        """
        try:
            # Get the main page
            response = request.get("https://www.usa.gov/agency-index")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            all_agencies = []
            sections_scraped = 0
            
            # Scrape each section A-Z
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                agencies = GovernmentAgencyScraper.parse_agency_section(soup, letter)
                if agencies:
                    all_agencies.extend(agencies)
                    sections_scraped += 1
                
                # Small delay to be respectful
                time.sleep(0.1)
            
            return {
                'success': True,
                'total_agencies': len(all_agencies),
                'sections_scraped': sections_scraped,
                'agencies': all_agencies
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agencies': []
            }
    
    def scrape_all_sections(self) -> Dict[str, Any]:
        """Scrape all alphabetical sections A-Z."""
        self.stats['start_time'] = datetime.now()
        
        self.logger.info("Starting comprehensive government agency scraping with Botasaurus")
        
        # Use the static Botasaurus method
        result = self.scrape_all_sections_static()
        
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        if result['success']:
            agencies = result['agencies']
            self.stats['sections_scraped'] = result['sections_scraped']
            self.stats['agencies_found'] = len(agencies)
            
            return {
                'success': True,
                'total_agencies': len(agencies),
                'agencies': agencies,
                'statistics': {
                    **self.stats,
                    'duration_seconds': duration
                }
            }
        else:
            self.stats['errors'].append(result.get('error', 'Unknown error'))
            return {
                'success': False,
                'error': result.get('error'),
                'agencies': [],
                'statistics': {
                    **self.stats,
                    'duration_seconds': duration
                }
            }
    
    def export_data(self, agencies: List[Dict[str, Any]], output_dir: str = 'scraped_data') -> Dict[str, str]:
        """Export agencies to CSV and JSON formats."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export paths
        csv_path = os.path.join(output_dir, f'usa_gov_agencies_{timestamp}.csv')
        json_path = os.path.join(output_dir, f'usa_gov_agencies_{timestamp}.json')
        
        # Export CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['section', 'agency_name', 'homepage_url', 'parent_department'])
            writer.writeheader()
            if agencies:
                writer.writerows(agencies)
        
        # Export JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(agencies, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Exported {len(agencies)} agencies to {csv_path} and {json_path}")
        
        return {
            'csv': csv_path,
            'json': json_path
        }
    
    def validate_data(self, agencies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate scraped agency data."""
        issues = []
        valid_count = 0
        
        for i, agency in enumerate(agencies):
            agency_issues = []
            
            # Check required fields
            if not agency.get('agency_name'):
                agency_issues.append(f"Empty agency name at index {i}")
            
            if not agency.get('homepage_url'):
                agency_issues.append(f"Empty URL at index {i}")
            elif not agency['homepage_url'].startswith(('http://', 'https://')):
                agency_issues.append(f"Invalid URL format at index {i}")
                
            if not agency.get('section'):
                agency_issues.append(f"Missing section at index {i}")
                
            if agency_issues:
                issues.extend(agency_issues)
            else:
                valid_count += 1
        
        return {
            'total_agencies': len(agencies),
            'valid_agencies': valid_count,
            'invalid_agencies': len(agencies) - valid_count,
            'issues': issues[:20],  # Limit to first 20 issues
            'validation_passed': len(issues) == 0
        }


# Browser-based scraping for dynamic content (advanced use cases)
@browser(
    headless=True,
    block_images=True
)
def scrape_with_browser(driver: BotasaurusDriver, section_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Alternative scraping method using browser automation for dynamic content.
    
    Args:
        driver: Botasaurus browser driver
        section_id: Optional specific section to scrape
        
    Returns:
        Dictionary with scraped agencies
    """
    try:
        # Navigate to the page
        driver.get("https://www.usa.gov/agency-index")
        
        # Wait for content to load
        driver.wait_for_element('main', timeout=10)
        
        # Get page source and parse
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        agencies = []
        
        if section_id:
            # Scrape specific section
            agencies = GovernmentAgencyScraper.parse_agency_section(soup, section_id)
        else:
            # Scrape all sections
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                section_agencies = GovernmentAgencyScraper.parse_agency_section(soup, letter)
                agencies.extend(section_agencies)
        
        return {
            'success': True,
            'agencies': agencies,
            'agency_count': len(agencies),
            'method': 'browser'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'agencies': [],
            'method': 'browser'
        }