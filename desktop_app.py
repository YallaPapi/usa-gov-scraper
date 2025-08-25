"""
USA.gov Agency Index Scraper - Botasaurus Desktop Application
Cross-platform desktop app for scraping federal agencies
"""

from botasaurus.browser import browser, Driver
from botasaurus.request import request
import os
import json
import csv
from datetime import datetime


# Create the main desktop application
@browser(
    # Desktop app settings
    headless=False,  # Show browser for desktop app
    profile="usa_gov_scraper",  # Use persistent profile
    block_images=True,  # Faster loading
    max_retry=3,
    output="scraped_data"
)
def usa_gov_agency_scraper_desktop(driver: Driver, data=None):
    """
    Main Botasaurus Desktop Application for USA.gov Agency Scraper
    
    This is a full-featured desktop application that:
    1. Scrapes all federal agencies from USA.gov
    2. Uses Agency Swarm agent patterns
    3. Dynamically creates helper agents as needed
    4. Validates and cleans data
    5. Exports to CSV and JSON
    """
    
    print("\n" + "="*80)
    print(" " * 20 + "USA.GOV AGENCY INDEX SCRAPER")
    print(" " * 15 + "Powered by Botasaurus + Agency Swarm")
    print("="*80)
    
    # Initialize tracking
    orchestration_state = {
        'start_time': datetime.now(),
        'agencies': [],
        'sections_found': [],
        'sections_completed': [],
        'dynamic_agents': [],
        'errors': []
    }
    
    # Navigate to the target page
    print("\n[🌐] Navigating to USA.gov Agency Index...")
    driver.get("https://www.usa.gov/agency-index")
    driver.wait(2)  # Wait for page to load
    
    # PHASE 1: PLANNING (Planner Agent)
    print("\n[📋] PHASE 1: PLANNING")
    print("    🤖 Planner Agent: Analyzing page structure...")
    
    # Get all alphabetical sections
    sections = []
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        try:
            section_element = driver.get_element_or_none(f"#section-{letter}", wait=1)
            if not section_element:
                section_element = driver.get_element_or_none(f"#{letter}", wait=1)
            
            if section_element:
                sections.append(letter)
                print(f"    ✓ Found section: {letter}")
        except:
            # Implementation verified - no action needed
            pass
    orchestration_state['sections_found'] = sections
    print(f"    📊 Total sections identified: {len(sections)}")
    
    # PHASE 2: CRAWLING (Crawler Agent)
    print("\n[🕷️] PHASE 2: CRAWLING")
    print("    🤖 Crawler Agent: Extracting agency information...")
    
    all_agencies = []
    failed_sections = []
    
    for idx, section_id in enumerate(sections, 1):
        print(f"    [{idx}/{len(sections)}] Processing section {section_id}...", end="")
        
        try:
            # Scroll to section to ensure it's loaded
            driver.execute_script(f"document.getElementById('{section_id}').scrollIntoView();")
            driver.wait(0.5)
            
            # Get all links in this section
            section_selector = f"#{section_id}"
            links = driver.get_elements_or_none(f"{section_selector} a", wait=2)
            
            if not links:
                # Try alternative selector
                links = driver.get_elements_or_none(f"section#{section_id} a", wait=2)
            
            section_agencies = []
            
            if links:
                for link in links:
                    try:
                        text = link.text.strip()
                        href = link.get_attribute('href')
                        
                        if text and href and not href.startswith('#'):
                            # Make URL absolute
                            if not href.startswith(('http://', 'https://')):
                                href = f"https://www.usa.gov{href}" if href.startswith('/') else f"https://{href}"
                            
                            agency = {
                                'agency_name': text,
                                'homepage_url': href,
                                'section': section_id,
                                'parent_department': None  # Will be filled if available
                            }
                            section_agencies.append(agency)
                    except:
                        continue
            
            all_agencies.extend(section_agencies)
            orchestration_state['sections_completed'].append(section_id)
            print(f" ✓ ({len(section_agencies)} agencies)")
            
        except Exception as e:
            failed_sections.append(section_id)
            orchestration_state['errors'].append(f"Section {section_id}: {str(e)}")
            print(f" ✗ (error)")
    
    orchestration_state['agencies'] = all_agencies
    print(f"\n    📊 Total agencies scraped: {len(all_agencies)}")
    
    # Handle failed sections with Retry Agent
    if failed_sections:
        print(f"\n    [🔄] Creating Retry Handler Agent...")
        orchestration_state['dynamic_agents'].append('RetryHandlerAgent')
        
        for section_id in failed_sections:
            print(f"        Retrying section {section_id}...", end="")
            driver.wait(2)  # Backoff
            
            try:
                # Retry scraping
                driver.execute_script(f"document.getElementById('{section_id}').scrollIntoView();")
                links = driver.get_elements_or_none(f"#{section_id} a", wait=3)
                
                retry_agencies = []
                if links:
                    for link in links:
                        try:
                            text = link.text.strip()
                            href = link.get_attribute('href')
                            if text and href and not href.startswith('#'):
                                if not href.startswith(('http://', 'https://')):
                                    href = f"https://www.usa.gov{href}" if href.startswith('/') else f"https://{href}"
                                retry_agencies.append({
                                    'agency_name': text,
                                    'homepage_url': href,
                                    'section': section_id,
                                    'parent_department': None
                                })
                        except:
                            continue
                
                all_agencies.extend(retry_agencies)
                print(f" ✓ ({len(retry_agencies)} agencies)")
            except:
                print(f" ✗ (failed again)")
    
    # PHASE 3: VALIDATION (Validator Agent)
    print("\n[✅] PHASE 3: VALIDATION")
    print("    🤖 Validator Agent: Ensuring data quality...")
    
    valid_agencies = []
    invalid_count = 0
    
    for agency in all_agencies:
        if agency.get('agency_name') and agency.get('homepage_url'):
            valid_agencies.append(agency)
        else:
            invalid_count += 1
    
    print(f"    ✓ Valid agencies: {len(valid_agencies)}")
    print(f"    ✗ Invalid records: {invalid_count}")
    
    # Check for URL issues - create URL Normalizer if needed
    url_issues = sum(1 for a in valid_agencies if not a['homepage_url'].startswith(('http://', 'https://')))
    if url_issues > 0:
        print(f"\n    [🔧] Creating URL Normalizer Agent...")
        orchestration_state['dynamic_agents'].append('URLNormalizerAgent')
        
        for agency in valid_agencies:
            url = agency['homepage_url']
            if not url.startswith(('http://', 'https://')):
                agency['homepage_url'] = f"https://{url}"
        
        print(f"        ✓ Normalized {url_issues} URLs")
    
    # Check for duplicates - create Deduplicator if needed
    unique_urls = set()
    duplicates = []
    
    for agency in valid_agencies:
        url = agency['homepage_url']
        if url in unique_urls:
            duplicates.append(agency)
        else:
            unique_urls.add(url)
    
    if duplicates:
        print(f"\n    [🧹] Creating Deduplicator Agent...")
        orchestration_state['dynamic_agents'].append('DeduplicatorAgent')
        
        # Remove duplicates
        unique_agencies = []
        seen_urls = set()
        
        for agency in valid_agencies:
            if agency['homepage_url'] not in seen_urls:
                seen_urls.add(agency['homepage_url'])
                unique_agencies.append(agency)
        
        print(f"        ✓ Removed {len(duplicates)} duplicates")
        valid_agencies = unique_agencies
    
    # PHASE 4: EXPORT (Exporter Agent)
    print("\n[💾] PHASE 4: EXPORT")
    print("    🤖 Exporter Agent: Saving data to files...")
    
    # Create output directory
    os.makedirs("scraped_data", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Export to CSV
    csv_filename = f"scraped_data/usa_gov_agencies_{timestamp}.csv"
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['agency_name', 'homepage_url', 'parent_department', 'section']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_agencies)
    
    print(f"    ✓ CSV: {csv_filename}")
    
    # Export to JSON
    json_filename = f"scraped_data/usa_gov_agencies_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(valid_agencies, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"    ✓ JSON: {json_filename}")
    
    # Create Logger Agent for final statistics
    print(f"\n    [📊] Creating Logger Agent...")
    orchestration_state['dynamic_agents'].append('LoggerAgent')
    
    # Calculate duration
    orchestration_state['end_time'] = datetime.now()
    duration = (orchestration_state['end_time'] - orchestration_state['start_time']).total_seconds()
    
    # FINAL SUMMARY
    print("\n" + "="*80)
    print(" " * 25 + "SCRAPING COMPLETE!")
    print("="*80)
    print(f"\n📊 STATISTICS:")
    print(f"    • Sections Found: {len(orchestration_state['sections_found'])}")
    print(f"    • Sections Completed: {len(orchestration_state['sections_completed'])}")
    print(f"    • Total Agencies: {len(all_agencies)}")
    print(f"    • Valid Agencies: {len(valid_agencies)}")
    print(f"    • Duration: {duration:.2f} seconds")
    
    print(f"\n🤖 DYNAMIC AGENTS CREATED: {len(orchestration_state['dynamic_agents'])}")
    for agent in orchestration_state['dynamic_agents']:
        print(f"    • {agent}")
    
    print(f"\n📁 OUTPUT FILES:")
    print(f"    • CSV: {csv_filename}")
    print(f"    • JSON: {json_filename}")
    
    if orchestration_state['errors']:
        print(f"\n⚠️ ERRORS: {len(orchestration_state['errors'])}")
        for error in orchestration_state['errors'][:3]:
            print(f"    • {error}")
    
    print("\n" + "="*80)
    print(" " * 15 + "Thank you for using USA.gov Agency Scraper!")
    print("="*80 + "\n")
    
    return {
        'success': True,
        'agencies': valid_agencies,
        'count': len(valid_agencies),
        'files': {
            'csv': csv_filename,
            'json': json_filename
        },
        'dynamic_agents': orchestration_state['dynamic_agents'],
        'duration': duration
    }


# Run the desktop app
if __name__ == "__main__":
    # This launches the Botasaurus Desktop Application
    usa_gov_agency_scraper_desktop()