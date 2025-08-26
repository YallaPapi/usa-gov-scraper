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
        
        NOTE: The USA.gov agency index structure has changed. Instead of sections with IDs A-Z,
        agencies are now organized as H2 headers. This method is kept for backward compatibility
        but now delegates to parse_all_agencies and filters by section.
        
        Args:
            soup: BeautifulSoup object of the page
            section_id: Single letter ID of the section (A-Z)
            
        Returns:
            List of agency dictionaries with name, URL, and parent department
        """
        # Parse all agencies using the new method and filter by section
        all_agencies = AgencyIndexScraper.parse_all_agencies(soup)
        section_agencies = [agency for agency in all_agencies if agency.get('section') == section_id]
        return section_agencies
    
    @staticmethod
    def parse_all_agencies(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse all agencies from the USA.gov agency index using the correct HTML structure.
        
        The page structure uses H2 headers for each agency, with the first link in the 
        following element being the main agency website.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of agency dictionaries with name, URL, and section
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
            
            # Skip non-agency headers like "Have a question?"
            if len(header_text) < 3:
                continue
            
            # Find the next element that contains links for this agency
            next_element = header.find_next_sibling()
            
            if not next_element:
                continue
            
            # Look for the main agency website link
            # The pattern is: first link is usually the main website
            links = next_element.find_all('a', href=True)
            
            if not links:
                continue
            
            # Get the first link which should be the main agency website
            main_link = links[0]
            agency_name = header_text
            homepage_url = main_link.get('href', '')
            
            # Skip empty URLs
            if not homepage_url:
                continue
            
            # Make URL absolute if it's relative
            if not homepage_url.startswith(('http://', 'https://')):
                homepage_url = urljoin('https://www.usa.gov', homepage_url)
            
            # Only include external links (actual agency websites)
            # Skip internal USA.gov links (these are "More information" links)
            if homepage_url.startswith('https://www.usa.gov'):
                continue
            
            # Determine the section letter
            section_letter = current_section_letter
            if not section_letter and agency_name:
                section_letter = agency_name[0].upper()
            
            agencies.append({
                'agency_name': agency_name,
                'homepage_url': homepage_url,
                'parent_department': None,  # This information is not readily available in the new structure
                'section': section_letter
            })
        
        return agencies
    
    @staticmethod
    @request(
        # Cache responses to avoid redundant requests
        cache=True,
        # Retry on failure
        max_retry=3,
        # Parallel processing for efficiency
        parallel=5
    )
    def scrape_section(request: BotasaurusRequest, section_id: str) -> Dict[str, Any]:
        """
        Scrape a single alphabetical section.
        
        Args:
            request: Botasaurus request object
            section_id: Single letter ID (A-Z)
            
        Returns:
            Dictionary with section data and agencies
        """
        try:
            # Get the page HTML
            base_url = "https://www.usa.gov/agency-index"
            response = request.get(base_url)
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse the specific section
            agencies = AgencyIndexScraper.parse_agency_section(soup, section_id)
            
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
    
    @staticmethod
    @request(
        cache=True,
        max_retry=3
    )
    def scrape_agency_index(request: BotasaurusRequest, data: Any = None) -> Dict[str, Any]:
        """
        Scrape the entire USA.gov Agency Index.
        
        Args:
            request: Botasaurus request object
            
        Returns:
            Dictionary with all agencies and scraping statistics
        """
        try:
            print("DEBUG: Starting scrape_agency_index")
            # Get the main page
            base_url = "https://www.usa.gov/agency-index"
            response = request.get(base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            print("DEBUG: Got HTML response")
            
            # Find all alphabetical sections (A-Z)
            alphabet_sections = []
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                section = soup.find('section', {'id': letter})
                if section:
                    alphabet_sections.append(letter)
            
            # Scrape each section
            all_agencies = []
            scraping_stats = {'sections_scraped': 0, 'agencies_found': 0, 'errors': []}
            
            for section_id in alphabet_sections:
                agencies = AgencyIndexScraper.parse_agency_section(soup, section_id)
                all_agencies.extend(agencies)
                
                # Update stats
                scraping_stats['sections_scraped'] += 1
                scraping_stats['agencies_found'] += len(agencies)
                
                # Add small delay to be polite
                time.sleep(0.5)
            
            return {
                'success': True,
                'total_agencies': len(all_agencies),
                'sections_found': len(alphabet_sections),
                'agencies': all_agencies,
                'stats': scraping_stats
            }
            
        except Exception as e:
            error_msg = f"Error scraping agency index: {str(e)}"
            scraping_stats = {'sections_scraped': 0, 'agencies_found': 0, 'errors': [error_msg]}
            
            return {
                'success': False,
                'error': error_msg,
                'agencies': [],
                'stats': scraping_stats
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
                # Scrape all agencies using the new method
                agencies = self.parse_all_agencies(soup)
            
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
    
    def scrape_section_instance(self, section_id: str) -> Dict[str, Any]:
        """
        Instance wrapper for scrape_section static method that updates instance stats.
        
        Args:
            section_id: Single letter ID (A-Z)
            
        Returns:
            Dictionary with section data and agencies
        """
        result = self.scrape_section(section_id)
        
        # Update instance stats
        if result['success']:
            self.scraping_stats['sections_scraped'] += 1
            self.scraping_stats['agencies_found'] += result['agency_count']
            # Add agencies to instance storage
            self.all_agencies.extend(result['agencies'])
        else:
            self.scraping_stats['errors'].append(result.get('error', 'Unknown error'))
        
        return result
    
    def scrape_agency_index_instance(self) -> Dict[str, Any]:
        """
        Instance wrapper for scrape_agency_index static method that updates instance data.
        
        Returns:
            Dictionary with all agencies and scraping statistics
        """
        result = self.scrape_agency_index()
        
        if result['success']:
            # Update instance data
            self.all_agencies = result['agencies']
            self.scraping_stats.update(result['stats'])
        
        return result
    
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