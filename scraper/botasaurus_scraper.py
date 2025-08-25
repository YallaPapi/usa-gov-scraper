"""
Botasaurus Scraper Core
Main scraping functionality using Botasaurus to extract agency information from USA.gov
"""

from botasaurus.request import request, Request as BotasaurusRequest
from botasaurus.browser import browser, Driver as BotasaurusDriver
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import time
import json
from urllib.parse import urljoin


class AgencyIndexScraper:
    """Scraper for USA.gov Agency Index using Botasaurus."""
    
    def __init__(self):
        self.base_url = "https://www.usa.gov/agency-index"
        self.all_agencies = []
        self.scraping_stats = {
            'sections_scraped': 0,
            'agencies_found': 0,
            'errors': []
        }
    
    @staticmethod
    def parse_agency_section(soup: BeautifulSoup, section_id: str) -> List[Dict[str, Any]]:
        """
        Parse a specific alphabetical section of the agency index.
        
        Args:
            soup: BeautifulSoup object of the page
            section_id: Single letter ID of the section (A-Z)
            
        Returns:
            List of agency dictionaries with name, URL, and parent department
        """
        section = soup.find('section', {'id': section_id})
        agencies = []
        
        if not section:
            return agencies
        
        # Check for different possible structures
        # Structure 1: Direct links in the section
        direct_links = section.find_all('a', href=True)
        
        # Structure 2: Links within list items
        list_items = section.find_all('li')
        
        # Structure 3: Links within divs with specific classes
        agency_divs = section.find_all('div', class_=['usa-width-one-third', 'agency-item', 'usa-media-block'])
        
        # Try to find parent department information
        current_parent = None
        
        # Process direct links
        for link in direct_links:
            # Skip navigation or non-agency links
            if link.get('href', '').startswith('#') or 'skip' in link.get('class', []):
                continue
            
            # Check if there's a parent heading before this link
            parent_heading = link.find_previous(['h3', 'h4'])
            if parent_heading and parent_heading.parent == section:
                current_parent = parent_heading.text.strip()
            
            agency_name = link.text.strip()
            homepage_url = link.get('href', '')
            
            # Skip empty entries
            if not agency_name or not homepage_url:
                continue
            
            # Make URL absolute if it's relative
            if homepage_url and not homepage_url.startswith(('http://', 'https://')):
                homepage_url = urljoin('https://www.usa.gov', homepage_url)
            
            agencies.append({
                'agency_name': agency_name,
                'homepage_url': homepage_url,
                'parent_department': current_parent,
                'section': section_id
            })
        
        # If we didn't find agencies with direct links, try list items
        if not agencies and list_items:
            for item in list_items:
                link = item.find('a', href=True)
                if link:
                    agency_name = link.text.strip()
                    homepage_url = link.get('href', '')
                    
                    if agency_name and homepage_url:
                        if not homepage_url.startswith(('http://', 'https://')):
                            homepage_url = urljoin('https://www.usa.gov', homepage_url)
                        
                        agencies.append({
                            'agency_name': agency_name,
                            'homepage_url': homepage_url,
                            'parent_department': None,
                            'section': section_id
                        })
        
        return agencies
    
    @request(
        # Cache responses to avoid redundant requests
        cache=True,
        # Retry on failure
        max_retry=3,
        # Parallel processing for efficiency
        parallel=5
    )
    def scrape_section(self, section_id: str, request: BotasaurusRequest) -> Dict[str, Any]:
        """
        Scrape a single alphabetical section.
        
        Args:
            section_id: Single letter ID (A-Z)
            request: Botasaurus request object
            
        Returns:
            Dictionary with section data and agencies
        """
        try:
            # Get the page HTML
            response = request.get(self.base_url)
            soup = response.soup
            
            # Parse the specific section
            agencies = self.parse_agency_section(soup, section_id)
            
            # Update stats
            self.scraping_stats['sections_scraped'] += 1
            self.scraping_stats['agencies_found'] += len(agencies)
            
            return {
                'section': section_id,
                'success': True,
                'agency_count': len(agencies),
                'agencies': agencies
            }
            
        except Exception as e:
            error_msg = f"Error scraping section {section_id}: {str(e)}"
            self.scraping_stats['errors'].append(error_msg)
            
            return {
                'section': section_id,
                'success': False,
                'error': error_msg,
                'agencies': []
            }
    
    @request(
        cache=True,
        max_retry=3
    )
    def scrape_agency_index(self, request: BotasaurusRequest) -> Dict[str, Any]:
        """
        Scrape the entire USA.gov Agency Index.
        
        Args:
            request: Botasaurus request object
            
        Returns:
            Dictionary with all agencies and scraping statistics
        """
        try:
            # Get the main page
            response = request.get(self.base_url)
            soup = response.soup
            
            # Find all alphabetical sections (A-Z)
            alphabet_sections = []
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                section = soup.find('section', {'id': letter})
                if section:
                    alphabet_sections.append(letter)
            
            # Scrape each section
            all_agencies = []
            for section_id in alphabet_sections:
                agencies = self.parse_agency_section(soup, section_id)
                all_agencies.extend(agencies)
                
                # Update stats
                self.scraping_stats['sections_scraped'] += 1
                self.scraping_stats['agencies_found'] += len(agencies)
                
                # Add small delay to be polite
                time.sleep(0.5)
            
            # Store all agencies
            self.all_agencies = all_agencies
            
            return {
                'success': True,
                'total_agencies': len(all_agencies),
                'sections_found': len(alphabet_sections),
                'agencies': all_agencies,
                'stats': self.scraping_stats
            }
            
        except Exception as e:
            error_msg = f"Error scraping agency index: {str(e)}"
            self.scraping_stats['errors'].append(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'agencies': [],
                'stats': self.scraping_stats
            }
    
    @browser(
        # Use browser mode for dynamic content if needed
        headless=True,
        block_images=True  # Don't load images to save bandwidth
    )
    def scrape_with_browser(self, driver: BotasaurusDriver, section_id: Optional[str] = None) -> Dict[str, Any]:
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
            driver.get(self.base_url)
            
            # Wait for content to load
            driver.wait_for_element('section', timeout=10)
            
            # Get page source and parse
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            agencies = []
            
            if section_id:
                # Scrape specific section
                agencies = self.parse_agency_section(soup, section_id)
            else:
                # Scrape all sections
                for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    section_agencies = self.parse_agency_section(soup, letter)
                    agencies.extend(section_agencies)
                    
                    # Scroll to next section for dynamic loading
                    next_section = soup.find('section', {'id': letter})
                    if next_section:
                        driver.scroll_to_element(f'section#{letter}')
                        time.sleep(0.5)  # Small delay for content to load
            
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
    
    def get_agencies_by_letter(self, letter: str) -> List[Dict[str, Any]]:
        """
        Get all agencies for a specific letter.
        
        Args:
            letter: Single letter (A-Z)
            
        Returns:
            List of agencies for that letter
        """
        return [a for a in self.all_agencies if a.get('section') == letter.upper()]
    
    def get_agencies_by_department(self, department: str) -> List[Dict[str, Any]]:
        """
        Get all agencies under a specific parent department.
        
        Args:
            department: Name of the parent department
            
        Returns:
            List of agencies under that department
        """
        return [a for a in self.all_agencies if a.get('parent_department') == department]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get scraping statistics.
        
        Returns:
            Dictionary with scraping statistics
        """
        stats = self.scraping_stats.copy()
        
        # Add additional statistics
        if self.all_agencies:
            # Count agencies by section
            section_counts = {}
            for agency in self.all_agencies:
                section = agency.get('section', 'Unknown')
                section_counts[section] = section_counts.get(section, 0) + 1
            
            stats['agencies_by_section'] = section_counts
            
            # Count parent departments
            departments = set()
            for agency in self.all_agencies:
                dept = agency.get('parent_department')
                if dept:
                    departments.add(dept)
            
            stats['unique_departments'] = len(departments)
        
        return stats
    
    def validate_agencies(self) -> Dict[str, Any]:
        """
        Validate the scraped agency data.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        valid_count = 0
        
        for i, agency in enumerate(self.all_agencies):
            agency_issues = []
            
            # Check agency name
            if not agency.get('agency_name'):
                agency_issues.append(f"Empty agency name at index {i}")
            
            # Check URL
            url = agency.get('homepage_url')
            if not url:
                agency_issues.append(f"Empty URL at index {i}")
            elif not url.startswith(('http://', 'https://')):
                agency_issues.append(f"Invalid URL format at index {i}: {url}")
            
            if agency_issues:
                issues.extend(agency_issues)
            else:
                valid_count += 1
        
        return {
            'total_agencies': len(self.all_agencies),
            'valid_agencies': valid_count,
            'invalid_agencies': len(self.all_agencies) - valid_count,
            'issues': issues[:20],  # Limit to first 20 issues
            'validation_passed': len(issues) == 0
        }


# Additional helper class for batch processing
class BatchScraper:
    """Helper class for batch processing sections with rate limiting."""
    
    def __init__(self, scraper: AgencyIndexScraper):
        self.scraper = scraper
        self.batch_size = 5
        self.delay_between_batches = 2.0
    
    def scrape_in_batches(self, sections: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape sections in batches with delays.
        
        Args:
            sections: List of section IDs to scrape
            
        Returns:
            List of results for each section
        """
        results = []
        
        for i in range(0, len(sections), self.batch_size):
            batch = sections[i:i + self.batch_size]
            
            for section_id in batch:
                result = self.scraper.scrape_section(section_id)
                results.append(result)
            
            # Delay between batches
            if i + self.batch_size < len(sections):
                time.sleep(self.delay_between_batches)
        
        return results