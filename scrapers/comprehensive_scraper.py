#!/usr/bin/env python3
"""
Comprehensive Government Contact Scraper - Botasaurus Powered
Main orchestrator that scrapes all federal agencies and discovers/scrapes local government sites
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any
import logging
from email_scraper import GovernmentEmailScraper
from local_gov_crawler import LocalGovernmentCrawler

class ComprehensiveGovernmentScraper:
    """Master scraper that coordinates federal and local government contact extraction."""
    
    def __init__(self, output_dir: str = "comprehensive_contacts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.email_scraper = GovernmentEmailScraper(os.path.join(output_dir, "federal_contacts"))
        self.local_crawler = LocalGovernmentCrawler(os.path.join(output_dir, "local_contacts"))
        
        self.logger = logging.getLogger(__name__)
        
        # Statistics tracking
        self.stats = {
            'federal_agencies_scraped': 0,
            'federal_emails_found': 0,
            'local_sites_discovered': 0,
            'local_contacts_found': 0,
            'total_unique_emails': 0,
            'start_time': None,
            'end_time': None
        }
    
    def scrape_all_federal_agencies(self, agencies_csv_path: str) -> Dict[str, Any]:
        """
        Scrape all federal agencies from the provided CSV file.
        
        Args:
            agencies_csv_path: Path to CSV file with federal agency URLs
            
        Returns:
            Dictionary with scraping results
        """
        self.logger.info("🏛️ Starting comprehensive federal agency scraping...")
        
        # Load and validate agencies CSV
        if not os.path.exists(agencies_csv_path):
            return {'success': False, 'error': f'Agencies file not found: {agencies_csv_path}'}
        
        # Count total agencies for progress tracking
        agency_count = 0
        valid_agencies = []
        
        try:
            with open(agencies_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('homepage_url', '').strip()
                    if url and url.startswith('http') and url != 'See USA.gov':
                        valid_agencies.append({
                            'name': row.get('agency_name', ''),
                            'url': url,
                            'section': row.get('section', ''),
                            'parent_department': row.get('parent_department', '')
                        })
                        agency_count += 1
        except Exception as e:
            return {'success': False, 'error': f'Error reading agencies CSV: {str(e)}'}
        
        self.logger.info(f"📊 Found {agency_count} valid federal agencies to scrape")
        
        # Scrape agencies in batches for better performance
        batch_size = 50
        all_results = []
        all_emails = set()
        all_discovered_sites = set()
        
        for i in range(0, len(valid_agencies), batch_size):
            batch = valid_agencies[i:i+batch_size]
            self.logger.info(f"🔍 Processing batch {i//batch_size + 1}/{(len(valid_agencies)-1)//batch_size + 1} ({len(batch)} agencies)")
            
            # Create temporary CSV for this batch
            batch_csv = os.path.join(self.output_dir, f'temp_batch_{i}.csv')
            with open(batch_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section', 'parent_department'])
                writer.writeheader()
                for agency in batch:
                    writer.writerow({
                        'agency_name': agency['name'],
                        'homepage_url': agency['url'],
                        'section': agency['section'],
                        'parent_department': agency['parent_department']
                    })
            
            # Scrape this batch
            batch_result = self.email_scraper.scrape_federal_agencies(batch_csv)
            
            if batch_result['success']:
                all_emails.update(self.email_scraper.scraped_emails)
                all_discovered_sites.update(self.email_scraper.discovered_gov_sites)
                self.stats['federal_agencies_scraped'] += batch_result['agencies_scraped']
            
            # Cleanup temporary file
            os.remove(batch_csv)
            
            # Small delay between batches
            time.sleep(2)
        
        self.stats['federal_emails_found'] = len(all_emails)
        
        return {
            'success': True,
            'agencies_scraped': self.stats['federal_agencies_scraped'],
            'emails_found': len(all_emails),
            'gov_sites_discovered': len(all_discovered_sites)
        }
    
    def discover_local_government_sites(self, target_states: List[str] = None) -> Dict[str, Any]:
        """
        Discover local government websites across specified states.
        
        Args:
            target_states: List of states to focus discovery on
            
        Returns:
            Dictionary with discovery results
        """
        if target_states is None:
            target_states = ['California', 'Texas', 'Florida', 'New York', 'Pennsylvania']
        
        self.logger.info(f"🌍 Discovering local government sites in {len(target_states)} states...")
        
        # Generate targeted search locations
        major_cities = [
            "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
            "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "Austin, TX",
            "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC", "San Francisco, CA",
            "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Boston, MA", "El Paso, TX"
        ]
        
        # Add state-specific searches
        for state in target_states:
            major_cities.extend([
                f"{state} government",
                f"{state} state website",
                f"{state} county governments",
                f"{state} city directories"
            ])
        
        discovery_result = self.local_crawler.discover_by_search(major_cities[:30])  # Limit to prevent timeout
        
        if discovery_result['success']:
            self.stats['local_sites_discovered'] = discovery_result['sites_discovered']
            
            # Crawl discovered sites for contacts
            crawl_result = self.local_crawler.crawl_discovered_sites(max_sites=75)
            
            if crawl_result['success']:
                self.stats['local_contacts_found'] = crawl_result['contacts_found']
                
                return {
                    'success': True,
                    'sites_discovered': discovery_result['sites_discovered'],
                    'sites_crawled': crawl_result['sites_crawled'], 
                    'contacts_found': crawl_result['contacts_found']
                }
        
        return {'success': False, 'error': 'Local government discovery failed'}
    
    def create_master_contact_database(self) -> Dict[str, Any]:
        """
        Create a comprehensive master database of all government contacts.
        
        Returns:
            Dictionary with database creation results
        """
        self.logger.info("📊 Creating master contact database...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        master_file = os.path.join(self.output_dir, f'master_gov_contacts_{timestamp}.csv')
        
        # Collect all contact files
        federal_dir = os.path.join(self.output_dir, "federal_contacts")
        local_dir = os.path.join(self.output_dir, "local_contacts")
        
        all_contacts = []
        
        # Process federal contacts
        if os.path.exists(federal_dir):
            for file in os.listdir(federal_dir):
                if file.startswith('consolidated_emails_') and file.endswith('.csv'):
                    file_path = os.path.join(federal_dir, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                row['source'] = 'federal'
                                row['source_type'] = 'agency'
                                all_contacts.append(row)
                    except Exception as e:
                        self.logger.warning(f"Error reading {file_path}: {e}")
        
        # Process local contacts  
        if os.path.exists(local_dir):
            for file in os.listdir(local_dir):
                if file.startswith('local_gov_contacts_') and file.endswith('.csv'):
                    file_path = os.path.join(local_dir, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                # Transform local format to master format
                                contact = {
                                    'agency_name': row.get('site_title', ''),
                                    'website': row.get('site_url', ''),
                                    'email': row.get('contact_value', '') if row.get('contact_type') == 'email' else '',
                                    'phone': row.get('contact_value', '') if row.get('contact_type') == 'phone' else '',
                                    'contact_type': row.get('contact_type', ''),
                                    'source': 'local',
                                    'source_type': row.get('site_type', 'government')
                                }
                                all_contacts.append(contact)
                    except Exception as e:
                        self.logger.warning(f"Error reading {file_path}: {e}")
        
        # Remove duplicates and write master file
        unique_contacts = []
        seen_emails = set()
        seen_phones = set()
        
        for contact in all_contacts:
            email = contact.get('email', '').strip().lower()
            phone = contact.get('phone', '').strip()
            
            # Skip empty contacts
            if not email and not phone:
                continue
                
            # Check for duplicates
            if email and email not in seen_emails:
                seen_emails.add(email)
                unique_contacts.append(contact)
            elif phone and phone not in seen_phones:
                seen_phones.add(phone)
                unique_contacts.append(contact)
        
        # Write master database
        if unique_contacts:
            fieldnames = ['agency_name', 'website', 'email', 'phone', 'contact_type', 'source', 'source_type']
            with open(master_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(unique_contacts)
        
        self.stats['total_unique_emails'] = len(seen_emails)
        
        self.logger.info(f"✅ Master database created: {len(unique_contacts)} unique contacts")
        
        return {
            'success': True,
            'master_file': master_file,
            'total_contacts': len(unique_contacts),
            'unique_emails': len(seen_emails),
            'unique_phones': len(seen_phones)
        }
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of all scraping activities."""
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        
        report = {
            'scraping_summary': {
                'duration_seconds': duration,
                'duration_formatted': f"{duration//3600:.0f}h {(duration%3600)//60:.0f}m {duration%60:.0f}s",
                **self.stats
            },
            'performance_metrics': {
                'agencies_per_minute': self.stats['federal_agencies_scraped'] / (duration / 60) if duration > 0 else 0,
                'emails_per_agency': self.stats['federal_emails_found'] / self.stats['federal_agencies_scraped'] if self.stats['federal_agencies_scraped'] > 0 else 0,
                'local_sites_per_minute': self.stats['local_sites_discovered'] / (duration / 60) if duration > 0 else 0
            }
        }
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.output_dir, f'scraping_report_{timestamp}.json')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str, ensure_ascii=False)
        
        return report
    
    def run_comprehensive_scraping(self, agencies_csv_path: str, target_states: List[str] = None) -> Dict[str, Any]:
        """
        Run complete government contact scraping operation.
        
        Args:
            agencies_csv_path: Path to federal agencies CSV
            target_states: States to focus local government discovery
            
        Returns:
            Dictionary with complete results
        """
        self.stats['start_time'] = datetime.now()
        
        print("🚀 Starting Comprehensive Government Contact Scraping")
        print("=" * 60)
        
        # Phase 1: Federal Agencies
        print("📡 Phase 1: Federal Agency Email Extraction...")
        federal_result = self.scrape_all_federal_agencies(agencies_csv_path)
        
        if federal_result['success']:
            print(f"✅ Federal scraping complete!")
            print(f"   • Agencies: {federal_result['agencies_scraped']}")
            print(f"   • Emails: {federal_result['emails_found']}")
            print(f"   • Gov sites discovered: {federal_result['gov_sites_discovered']}")
        else:
            print(f"❌ Federal scraping failed: {federal_result.get('error')}")
            return federal_result
        
        # Phase 2: Local Government Discovery
        print(f"\n🌍 Phase 2: Local Government Site Discovery...")
        local_result = self.discover_local_government_sites(target_states)
        
        if local_result['success']:
            print(f"✅ Local discovery complete!")
            print(f"   • Sites discovered: {local_result['sites_discovered']}")  
            print(f"   • Sites crawled: {local_result['sites_crawled']}")
            print(f"   • Local contacts: {local_result['contacts_found']}")
        else:
            print(f"⚠️ Local discovery had issues: {local_result.get('error')}")
        
        # Phase 3: Master Database
        print(f"\n📊 Phase 3: Creating Master Contact Database...")
        db_result = self.create_master_contact_database()
        
        if db_result['success']:
            print(f"✅ Master database complete!")
            print(f"   • Total contacts: {db_result['total_contacts']}")
            print(f"   • Unique emails: {db_result['unique_emails']}")
            print(f"   • Master file: {db_result['master_file']}")
        
        # Generate final report
        final_report = self.generate_comprehensive_report()
        
        print(f"\n🎯 FINAL RESULTS:")
        print(f"   • Duration: {final_report['scraping_summary']['duration_formatted']}")
        print(f"   • Federal emails: {self.stats['federal_emails_found']}")
        print(f"   • Local contacts: {self.stats['local_contacts_found']}")
        print(f"   • Total unique emails: {self.stats['total_unique_emails']}")
        
        return {
            'success': True,
            'federal_result': federal_result,
            'local_result': local_result,
            'database_result': db_result,
            'final_report': final_report
        }


def main():
    """Main entry point for comprehensive government scraping."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    scraper = ComprehensiveGovernmentScraper()
    
    # Find the most comprehensive agencies file
    agencies_files = [
        'scraped_data/all_agencies_20250825_150513.csv',
        'scraped_data/usa_gov_agencies_20250825_225741.csv',
        'scraped_data/complete_agencies_20250825_150322.csv'
    ]
    
    agencies_file = None
    for file_path in agencies_files:
        if os.path.exists(file_path):
            agencies_file = file_path
            break
    
    if not agencies_file:
        print("❌ No agencies CSV file found!")
        return
    
    # Target states for local government discovery
    priority_states = [
        'California', 'Texas', 'Florida', 'New York', 'Pennsylvania',
        'Illinois', 'Ohio', 'Georgia', 'North Carolina', 'Michigan'
    ]
    
    # Run comprehensive scraping
    result = scraper.run_comprehensive_scraping(agencies_file, priority_states[:5])  # Limit for demo
    
    if result['success']:
        print(f"\n🏆 COMPREHENSIVE SCRAPING COMPLETE!")
        print(f"Check the 'comprehensive_contacts' directory for all results.")
    else:
        print(f"❌ Scraping encountered issues. Check logs for details.")


if __name__ == "__main__":
    main()