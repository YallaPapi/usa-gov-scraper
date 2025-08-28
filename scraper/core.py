"""
USA.gov Government Agency Scraper - Core Module
Consolidated single source of truth for all scraping operations
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Optional
import logging

class GovernmentAgencyScraper:
    """Unified scraper for USA.gov agency index with proper error handling."""
    
    def __init__(self, rate_limit: float = 0.5, max_retries: int = 3):
        self.base_url = "https://www.usa.gov/agency-index"
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
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
    
    def parse_agency_section(self, soup: BeautifulSoup, section_id: str) -> List[Dict[str, Any]]:
        """
        Parse a specific alphabetical section and extract agency information.
        
        Args:
            soup: BeautifulSoup object of the page
            section_id: Single letter ID of the section (A-Z)
            
        Returns:
            List of agency dictionaries with name, URL, and parent department
        """
        agencies = []
        
        # Find all H2 elements which represent individual agencies
        h2_elements = soup.find_all('h2')
        
        for h2 in h2_elements:
            # Get the agency name from the H2 text
            agency_name = h2.text.strip()

            # Skip letter headers (single letters A-Z that mark sections)
            if len(agency_name) == 1 and agency_name.isalpha() and agency_name.isupper():
                continue
            
            # Skip if agency name doesn't start with the target section letter
            if not agency_name.upper().startswith(section_id.upper()):
                continue
            
            # Find the first link after this H2 (should be the homepage)
            link = h2.find_next('a', href=True)
            
            if link and link.get('href'):
                homepage_url = link.get('href')
                
                # Make URL absolute if relative
                if not homepage_url.startswith(('http://', 'https://')):
                    homepage_url = urljoin(self.base_url, homepage_url)
                
                # Skip internal USA.gov links (keep only external agency websites)
                if homepage_url.startswith('https://www.usa.gov'):
                    continue
                
                agencies.append({
                    'agency_name': agency_name,
                    'homepage_url': homepage_url,
                    'parent_department': None,  # Parent department extraction handled in Botasaurus core
                    'section': section_id
                })
        
        return agencies
    
    def scrape_section(self, section_id: str) -> Dict[str, Any]:
        """
        Scrape a single alphabetical section.
        
        Args:
            section_id: Single letter ID (A-Z)
            
        Returns:
            Dictionary with section data and agencies
        """
        self.logger.info(f"Scraping section {section_id}")
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(self.base_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                agencies = self.parse_agency_section(soup, section_id)
                
                # Update statistics
                self.stats['sections_scraped'] += 1
                self.stats['agencies_found'] += len(agencies)
                
                # Rate limiting
                time.sleep(self.rate_limit)
                
                return {
                    'section': section_id,
                    'success': True,
                    'agency_count': len(agencies),
                    'agencies': agencies
                }
                
            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed for section {section_id}: {str(e)}"
                self.logger.warning(error_msg)
                
                if attempt == self.max_retries - 1:
                    self.stats['errors'].append(error_msg)
                    return {
                        'section': section_id,
                        'success': False,
                        'error': error_msg,
                        'agencies': []
                    }
                
                # Exponential backoff
                time.sleep(2 ** attempt)
    
    def scrape_all_sections(self) -> Dict[str, Any]:
        """Scrape all alphabetical sections A-Z."""
        self.stats['start_time'] = datetime.now()
        all_agencies = []
        
        self.logger.info("Starting comprehensive government agency scraping")
        
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            result = self.scrape_section(letter)
            if result['success']:
                all_agencies.extend(result['agencies'])
            
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        return {
            'success': True,
            'total_agencies': len(all_agencies),
            'agencies': all_agencies,
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
