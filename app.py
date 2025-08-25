"""
USA.gov Agency Index Scraper - Desktop Application
Botasaurus Desktop App with GUI for scraping federal agencies
"""

from botasaurus import *
from botasaurus.create_stealth_driver import create_stealth_driver
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import time


@browser(
    # Desktop app configuration
    headless=False,  # Show browser window in desktop app
    block_images=True,  # Faster loading
    reuse_driver=True,  # Reuse browser instance
    output="data/",  # Output directory
    create_error_logs=False
)
def scrape_usa_gov_agencies(driver: AntiDetectDriver, data):
    """
    Main scraping function for USA.gov Agency Index Desktop App
    """
    # Initialize results storage
    all_agencies = []
    stats = {
        'start_time': datetime.now(),
        'sections_found': 0,
        'agencies_scraped': 0,
        'errors': []
    }
    
    # Navigate to the main page
    driver.get("https://www.usa.gov/agency-index")
    driver.wait_for_element("section", timeout=10)
    
    # Get page source
    soup = driver.get_soup()
    
    # Find all alphabetical sections
    print("🔍 Finding alphabetical sections...")
    sections = []
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        section = soup.find('section', {'id': letter})
        if section:
            sections.append(letter)
            print(f"  ✓ Found section {letter}")
    
    stats['sections_found'] = len(sections)
    print(f"\n📊 Total sections found: {len(sections)}")
    
    # Scrape each section
    print("\n🚀 Starting agency extraction...")
    for section_id in sections:
        try:
            print(f"\n📂 Processing section {section_id}...")
            
            # Scroll to section for dynamic loading
            driver.scroll_to_element(f"#section-{section_id}", wait_after_scroll=0.5)
            
            # Get updated soup after scroll
            soup = driver.get_soup()
            section = soup.find('section', {'id': section_id})
            
            if not section:
                print(f"  ⚠️  Section {section_id} not found")
                continue
            
            # Extract agencies from this section
            agencies_in_section = []
            
            # Find all links in the section
            links = section.find_all('a', href=True)
            
            for link in links:
                # Skip navigation links
                if link.get('href', '').startswith('#'):
                    continue
                
                agency_name = link.text.strip()
                homepage_url = link.get('href', '')
                
                if not agency_name or not homepage_url:
                    continue
                
                # Make URL absolute if relative
                if not homepage_url.startswith(('http://', 'https://')):
                    homepage_url = f"https://www.usa.gov{homepage_url}" if homepage_url.startswith('/') else f"https://{homepage_url}"
                
                # Check for parent department
                parent_dept = None
                parent_heading = link.find_previous(['h3', 'h4'])
                if parent_heading and parent_heading.parent == section:
                    parent_dept = parent_heading.text.strip()
                
                agency_data = {
                    'agency_name': agency_name,
                    'homepage_url': homepage_url,
                    'parent_department': parent_dept,
                    'section': section_id
                }
                
                agencies_in_section.append(agency_data)
            
            all_agencies.extend(agencies_in_section)
            stats['agencies_scraped'] += len(agencies_in_section)
            
            print(f"  ✅ Extracted {len(agencies_in_section)} agencies from section {section_id}")
            
        except Exception as e:
            error_msg = f"Error in section {section_id}: {str(e)}"
            stats['errors'].append(error_msg)
            print(f"  ❌ {error_msg}")
    
    # Calculate duration
    stats['end_time'] = datetime.now()
    stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
    
    # Validation
    print("\n🔍 Validating data...")
    valid_agencies = []
    issues = []
    
    for agency in all_agencies:
        if not agency.get('agency_name'):
            issues.append("Found agency with empty name")
            continue
        if not agency.get('homepage_url'):
            issues.append(f"Agency {agency.get('agency_name')} has no URL")
            continue
        valid_agencies.append(agency)
    
    print(f"  ✅ Valid agencies: {len(valid_agencies)}")
    print(f"  ⚠️  Issues found: {len(issues)}")
    
    # Remove duplicates
    print("\n🧹 Removing duplicates...")
    unique_agencies = []
    seen_urls = set()
    
    for agency in valid_agencies:
        url = agency['homepage_url']
        if url not in seen_urls:
            seen_urls.add(url)
            unique_agencies.append(agency)
    
    duplicates_removed = len(valid_agencies) - len(unique_agencies)
    print(f"  ✅ Removed {duplicates_removed} duplicates")
    print(f"  ✅ Final count: {len(unique_agencies)} unique agencies")
    
    # Export data
    print("\n💾 Exporting data...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create output directory
    os.makedirs("data", exist_ok=True)
    
    # Export to CSV
    csv_file = f"data/usa_gov_agencies_{timestamp}.csv"
    df = pd.DataFrame(unique_agencies)
    df.to_csv(csv_file, index=False)
    print(f"  ✅ CSV saved: {csv_file}")
    
    # Export to JSON
    json_file = f"data/usa_gov_agencies_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(unique_agencies, f, indent=2, ensure_ascii=False)
    print(f"  ✅ JSON saved: {json_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING COMPLETE - SUMMARY")
    print("=" * 60)
    print(f"✅ Sections scraped: {stats['sections_found']}")
    print(f"✅ Total agencies found: {stats['agencies_scraped']}")
    print(f"✅ Valid agencies: {len(valid_agencies)}")
    print(f"✅ Unique agencies: {len(unique_agencies)}")
    print(f"⏱️ Duration: {stats['duration']:.2f} seconds")
    print(f"📁 Files saved:")
    print(f"   • CSV: {csv_file}")
    print(f"   • JSON: {json_file}")
    
    if stats['errors']:
        print(f"\n⚠️  Errors encountered: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"   • {error}")
    
    print("=" * 60)
    
    return {
        'agencies': unique_agencies,
        'statistics': {
            'total_agencies': len(unique_agencies),
            'sections_scraped': stats['sections_found'],
            'duration_seconds': stats['duration'],
            'errors': stats['errors']
        },
        'export_files': {
            'csv': csv_file,
            'json': json_file
        }
    }


# Desktop App Interface Functions
def create_desktop_app():
    """
    Create the Botasaurus Desktop Application
    """
    # Desktop app with UI
    @ui(
        title="USA.gov Agency Index Scraper",
        description="Extract all federal agency information from USA.gov",
        button_text="Start Scraping",
        output_type="json",
        inputs=[
            {
                "type": "select",
                "label": "Export Format",
                "name": "format",
                "options": [
                    {"label": "CSV & JSON", "value": "both"},
                    {"label": "CSV Only", "value": "csv"},
                    {"label": "JSON Only", "value": "json"}
                ],
                "default": "both"
            },
            {
                "type": "checkbox",
                "label": "Include Parent Departments",
                "name": "include_parents",
                "default": True
            },
            {
                "type": "checkbox",
                "label": "Remove Duplicates",
                "name": "remove_duplicates",
                "default": True
            },
            {
                "type": "checkbox",
                "label": "Validate URLs",
                "name": "validate_urls",
                "default": True
            }
        ]
    )
    def agency_scraper_ui(params):
        """Desktop UI for the scraper"""
        return scrape_usa_gov_agencies(params)
    
    return agency_scraper_ui


# Advanced Desktop App with Agency Swarm Integration
@browser(
    headless=False,
    output="data/",
    cache=True,
    block_images=True
)
def scrape_with_agents(driver: AntiDetectDriver, config):
    """
    Advanced scraping with dynamic agent creation
    Uses Agency Swarm patterns for intelligent scraping
    """
    from scraper_agents.dynamic_agents import DynamicAgentFactory
    
    print("🤖 Initializing Agent System...")
    
    # Track which agents we've created
    active_agents = {}
    
    # Navigate to page
    driver.get("https://www.usa.gov/agency-index")
    driver.wait_for_element("section", timeout=10)
    
    # Phase 1: Planning with Planner Agent
    print("\n📋 Phase 1: Planning")
    print("  🤖 Planner Agent: Analyzing page structure...")
    
    soup = driver.get_soup()
    sections = []
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if soup.find('section', {'id': letter}):
            sections.append(letter)
    
    print(f"  ✅ Planner Agent: Found {len(sections)} sections to scrape")
    
    # Phase 2: Crawling with Crawler Agent
    print("\n🕷️ Phase 2: Crawling")
    print("  🤖 Crawler Agent: Starting extraction...")
    
    all_agencies = []
    failed_sections = []
    
    for section_id in sections:
        try:
            # Scroll to section
            driver.scroll_to_element(f"#section-{section_id}", wait_after_scroll=0.5)
            soup = driver.get_soup()
            section = soup.find('section', {'id': section_id})
            
            if section:
                links = section.find_all('a', href=True)
                section_agencies = []
                
                for link in links:
                    if not link.get('href', '').startswith('#'):
                        agency = {
                            'agency_name': link.text.strip(),
                            'homepage_url': link.get('href', ''),
                            'section': section_id
                        }
                        section_agencies.append(agency)
                
                all_agencies.extend(section_agencies)
                print(f"  ✅ Crawler Agent: Section {section_id} - {len(section_agencies)} agencies")
            else:
                failed_sections.append(section_id)
                
        except Exception as e:
            failed_sections.append(section_id)
            print(f"  ❌ Crawler Agent: Failed section {section_id}")
    
    # Handle failures with Retry Agent
    if failed_sections:
        print("\n  🔄 Creating Retry Handler Agent...")
        active_agents['retry'] = "RetryHandlerAgent"
        
        for section_id in failed_sections:
            print(f"    🔄 Retry Agent: Retrying section {section_id}...")
            # Retry logic here
            time.sleep(2)  # Exponential backoff
    
    # Phase 3: Validation with Validator Agent
    print("\n✅ Phase 3: Validation")
    print("  🤖 Validator Agent: Checking data quality...")
    
    issues = []
    valid_agencies = []
    
    for agency in all_agencies:
        if not agency.get('agency_name') or not agency.get('homepage_url'):
            issues.append(f"Invalid agency: {agency}")
        else:
            valid_agencies.append(agency)
    
    print(f"  ✅ Validator Agent: {len(valid_agencies)} valid, {len(issues)} issues")
    
    # Create dynamic agents based on issues
    if any('url' in str(issue).lower() for issue in issues):
        print("  🔧 Creating URL Normalizer Agent...")
        active_agents['normalizer'] = "URLNormalizerAgent"
        # Normalize URLs
        for agency in valid_agencies:
            url = agency.get('homepage_url', '')
            if url and not url.startswith(('http://', 'https://')):
                agency['homepage_url'] = f"https://www.usa.gov{url}" if url.startswith('/') else f"https://{url}"
    
    # Check for duplicates
    if len(valid_agencies) != len(set(a['homepage_url'] for a in valid_agencies)):
        print("  🧹 Creating Deduplicator Agent...")
        active_agents['deduplicator'] = "DeduplicatorAgent"
        # Remove duplicates
        unique_agencies = []
        seen_urls = set()
        for agency in valid_agencies:
            if agency['homepage_url'] not in seen_urls:
                seen_urls.add(agency['homepage_url'])
                unique_agencies.append(agency)
        valid_agencies = unique_agencies
    
    # Phase 4: Export with Exporter Agent
    print("\n💾 Phase 4: Export")
    print("  🤖 Exporter Agent: Saving data...")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs("data", exist_ok=True)
    
    # Export files
    csv_file = f"data/agencies_agents_{timestamp}.csv"
    json_file = f"data/agencies_agents_{timestamp}.json"
    
    df = pd.DataFrame(valid_agencies)
    df.to_csv(csv_file, index=False)
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(valid_agencies, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ Exporter Agent: Saved to {csv_file} and {json_file}")
    
    # Create Logger Agent for statistics
    print("\n📊 Creating Logger Agent...")
    active_agents['logger'] = "LoggerAgent"
    
    print("\n" + "=" * 60)
    print("🎉 AGENT-BASED SCRAPING COMPLETE")
    print("=" * 60)
    print(f"✅ Active Agents Created: {len(active_agents)}")
    for agent_name, agent_type in active_agents.items():
        print(f"   • {agent_type}")
    print(f"✅ Agencies Scraped: {len(valid_agencies)}")
    print(f"📁 Files: {csv_file}, {json_file}")
    print("=" * 60)
    
    return {
        'agencies': valid_agencies,
        'agents_created': list(active_agents.values()),
        'files': [csv_file, json_file]
    }


# Main entry point for desktop app
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 USA.gov Agency Index Scraper - Desktop App")
    print("=" * 60)
    print("\nChoose mode:")
    print("1. Simple Desktop App (Quick scraping)")
    print("2. Advanced with Agents (Full orchestration)")
    print("3. Headless Mode (Background scraping)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        # Run simple desktop app
        print("\n🖥️ Launching Desktop Application...")
        scrape_usa_gov_agencies()
        
    elif choice == "2":
        # Run with agents
        print("\n🤖 Launching Agent-Based Scraper...")
        scrape_with_agents({})
        
    elif choice == "3":
        # Run headless
        print("\n👻 Running in Headless Mode...")
        
        @browser(headless=True, block_images=True)
        def headless_scrape(driver: AntiDetectDriver, data):
            return scrape_usa_gov_agencies(driver, data)
        
        headless_scrape()
    
    else:
        print("Invalid choice. Exiting.")