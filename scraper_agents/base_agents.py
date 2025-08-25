"""
Base Agent Classes for USA.gov Agency Index Scraper
These are the four core agents required for the scraping system.
"""

from agency_swarm import Agent
from agency_swarm.tools import BaseTool
from pydantic import Field
import requests
from bs4 import BeautifulSoup
import json
import csv
from typing import List, Dict, Any
import os
from datetime import datetime


class PlannerAgent(Agent):
    """Agent responsible for confirming scope and identifying target sections (A-Z)."""
    
    def __init__(self):
        super().__init__(
            name="Planner",
            description="Plans the scraping process and identifies target sections.",
            instructions="""
            You are the Planner Agent responsible for:
            1. Analyzing the USA.gov Agency Index page structure
            2. Identifying all alphabetical sections (A-Z)
            3. Creating a scraping plan with clear steps
            4. Determining the best approach for each section
            5. Reporting the structure to other agents
            
            Your analysis should include:
            - Number of sections found
            - Estimated number of agencies per section
            - Any special cases or irregularities
            - Recommended scraping strategy
            """,
            tools=[IdentifyTargetSectionsTool],
            temperature=0.3,
            max_prompt_tokens=25000
        )


class CrawlerAgent(Agent):
    """Agent responsible for executing Botasaurus scraper logic."""
    
    def __init__(self):
        super().__init__(
            name="Crawler",
            description="Executes scraping operations using Botasaurus.",
            instructions="""
            You are the Crawler Agent responsible for:
            1. Executing web scraping using Botasaurus framework
            2. Extracting agency information from each section
            3. Handling dynamic content if present
            4. Managing rate limiting and polite scraping
            5. Reporting scraping progress and issues
            
            For each agency, extract:
            - agency_name (the text of the agency link)
            - homepage_url (the href attribute)
            - parent_department (if available in the hierarchy)
            
            Follow best practices:
            - Respect rate limits
            - Handle errors gracefully
            - Report any issues to the orchestrator
            """,
            tools=[ScrapeSectionTool],
            temperature=0.3,
            max_prompt_tokens=25000
        )


class ValidatorAgent(Agent):
    """Agent responsible for ensuring completeness and correctness of dataset."""
    
    def __init__(self):
        super().__init__(
            name="Validator",
            description="Validates scraped data for completeness and correctness.",
            instructions="""
            You are the Validator Agent responsible for:
            1. Validating all scraped data for completeness
            2. Checking for empty or malformed agency names
            3. Verifying URL formats and validity
            4. Detecting and flagging duplicates
            5. Ensuring data quality standards are met
            
            Validation criteria:
            - Agency names must not be empty
            - URLs must be valid and properly formatted
            - No duplicate agencies should exist
            - Parent departments should be properly associated
            - All required fields must be present
            
            Report validation results with:
            - Number of valid records
            - List of issues found
            - Recommendations for fixing issues
            """,
            tools=[ValidateDataTool],
            temperature=0.3,
            max_prompt_tokens=25000
        )


class ExporterAgent(Agent):
    """Agent responsible for outputting data to CSV/JSON."""
    
    def __init__(self):
        super().__init__(
            name="Exporter",
            description="Exports validated data to CSV/JSON formats.",
            instructions="""
            You are the Exporter Agent responsible for:
            1. Exporting validated agency data to multiple formats
            2. Creating well-structured CSV files with proper headers
            3. Generating properly formatted JSON files
            4. Adding metadata (timestamp, record count, etc.)
            5. Ensuring data is properly encoded and escaped
            
            Export requirements:
            - CSV with headers: agency_name, homepage_url, parent_department
            - JSON with proper structure and indentation
            - Include metadata about the export
            - Use timestamp in filenames
            - Create output directory if it doesn't exist
            
            Report export results:
            - Files created and their paths
            - Number of records exported
            - File sizes
            """,
            tools=[ExportDataTool],
            temperature=0.3,
            max_prompt_tokens=25000
        )


# Tool definitions for base agents

class IdentifyTargetSectionsTool(BaseTool):
    """
    Identifies and analyzes all alphabetical sections (A-Z) on the USA.gov Agency Index page.
    Returns a list of sections with their IDs and estimated agency counts.
    """
    
    url: str = Field(
        default="https://www.usa.gov/agency-index",
        description="The URL of the USA.gov Agency Index page"
    )
    
    def run(self):
        """Identify all alphabetical sections on the page."""
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all alphabetical sections
            sections = []
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                section = soup.find('section', {'id': letter})
                if section:
                    # Count agencies in this section
                    agency_links = section.find_all('a', href=True)
                    sections.append({
                        'id': letter,
                        'agency_count': len(agency_links),
                        'has_subsections': bool(section.find_all('h3'))
                    })
            
            result = {
                'total_sections': len(sections),
                'sections': sections,
                'total_agencies_estimated': sum(s['agency_count'] for s in sections)
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return f"Error identifying sections: {str(e)}"


class ScrapeSectionTool(BaseTool):
    """
    Scrapes a specific alphabetical section of the USA.gov Agency Index.
    Extracts agency names, URLs, and parent departments.
    """
    
    section_id: str = Field(
        ..., 
        description="The alphabetical section ID (A-Z) to scrape"
    )
    url: str = Field(
        default="https://www.usa.gov/agency-index",
        description="The URL of the USA.gov Agency Index page"
    )
    
    def run(self):
        """Scrape agencies from a specific section."""
        try:
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the specific section
            section = soup.find('section', {'id': self.section_id})
            if not section:
                return json.dumps({'error': f'Section {self.section_id} not found', 'agencies': []})
            
            agencies = []
            
            # Extract agencies from the section
            # Check for subsections (departments)
            subsections = section.find_all('div', class_='usa-width-one-third')
            
            if subsections:
                for subsection in subsections:
                    # Check if there's a parent department heading
                    parent_heading = subsection.find_previous_sibling('h3')
                    parent_dept = parent_heading.text.strip() if parent_heading else None
                    
                    # Extract all agency links in this subsection
                    for link in subsection.find_all('a', href=True):
                        agencies.append({
                            'agency_name': link.text.strip(),
                            'homepage_url': link['href'],
                            'parent_department': parent_dept
                        })
            else:
                # No subsections, extract all links directly
                for link in section.find_all('a', href=True):
                    agencies.append({
                        'agency_name': link.text.strip(),
                        'homepage_url': link['href'],
                        'parent_department': None
                    })
            
            return json.dumps({
                'section': self.section_id,
                'agency_count': len(agencies),
                'agencies': agencies
            }, indent=2)
            
        except Exception as e:
            return json.dumps({'error': str(e), 'agencies': []})


class ValidateDataTool(BaseTool):
    """
    Validates scraped agency data for completeness and correctness.
    Checks for empty values, malformed URLs, and duplicates.
    """
    
    data: List[Dict[str, Any]] = Field(
        ..., 
        description="List of agency records to validate"
    )
    
    def run(self):
        """Validate the agency data."""
        issues = []
        valid_records = []
        seen_names = set()
        seen_urls = set()
        
        for i, record in enumerate(self.data):
            record_issues = []
            
            # Check agency name
            name = record.get('agency_name', '').strip()
            if not name:
                record_issues.append(f"Empty agency name at index {i}")
            elif name in seen_names:
                record_issues.append(f"Duplicate agency name: {name}")
            else:
                seen_names.add(name)
            
            # Check URL
            url = record.get('homepage_url', '').strip()
            if not url:
                record_issues.append(f"Empty URL for agency: {name}")
            elif not url.startswith(('http://', 'https://')):
                record_issues.append(f"Invalid URL format for {name}: {url}")
            elif url in seen_urls:
                record_issues.append(f"Duplicate URL: {url}")
            else:
                seen_urls.add(url)
            
            # If no issues, add to valid records
            if not record_issues:
                valid_records.append(record)
            else:
                issues.extend(record_issues)
        
        result = {
            'total_records': len(self.data),
            'valid_records': len(valid_records),
            'invalid_records': len(self.data) - len(valid_records),
            'issues': issues[:20],  # Limit to first 20 issues
            'validation_passed': len(issues) == 0
        }
        
        return json.dumps(result, indent=2)


class ExportDataTool(BaseTool):
    """
    Exports validated agency data to CSV and JSON formats.
    Creates timestamped files in the output directory.
    """
    
    data: List[Dict[str, Any]] = Field(
        ..., 
        description="List of validated agency records to export"
    )
    formats: List[str] = Field(
        default=["csv", "json"],
        description="Export formats (csv, json)"
    )
    output_dir: str = Field(
        default="output",
        description="Directory to save exported files"
    )
    
    def run(self):
        """Export the data to specified formats."""
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exported_files = []
        
        try:
            # Export to CSV
            if "csv" in self.formats:
                csv_filename = os.path.join(self.output_dir, f"usa_gov_agencies_{timestamp}.csv")
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['agency_name', 'homepage_url', 'parent_department']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for record in self.data:
                        writer.writerow({
                            'agency_name': record.get('agency_name', ''),
                            'homepage_url': record.get('homepage_url', ''),
                            'parent_department': record.get('parent_department', '')
                        })
                
                exported_files.append({
                    'format': 'csv',
                    'path': csv_filename,
                    'size': os.path.getsize(csv_filename)
                })
            
            # Export to JSON
            if "json" in self.formats:
                json_filename = os.path.join(self.output_dir, f"usa_gov_agencies_{timestamp}.json")
                with open(json_filename, 'w', encoding='utf-8') as jsonfile:
                    json.dump(self.data, jsonfile, indent=2, ensure_ascii=False)
                
                exported_files.append({
                    'format': 'json',
                    'path': json_filename,
                    'size': os.path.getsize(json_filename)
                })
            
            result = {
                'success': True,
                'record_count': len(self.data),
                'exported_files': exported_files,
                'timestamp': timestamp
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({
                'success': False,
                'error': str(e)
            })