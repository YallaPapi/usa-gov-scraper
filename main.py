#!/usr/bin/env python3
"""
USA.gov Government Agency Scraper - CLI Interface
Clean command-line interface with proper flag handling
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from scraper.botasaurus_core import GovernmentAgencyScraper


def setup_logging(log_level: str = "INFO", quiet: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    os.makedirs("logs", exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"logs/scraper_{timestamp}.log"
    
    logger = logging.getLogger('usa_gov_scraper')
    logger.setLevel(getattr(logging, log_level))
    
    # File handler (always enabled)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level))
    
    # Console handler (disabled in quiet mode)
    if not quiet:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File formatter
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger


def run_simple_scrape(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Run simple scrape without orchestration."""
    logger.info("Starting simple government agency scrape")
    
    try:
        scraper = GovernmentAgencyScraper(
            rate_limit=0.5,
            max_retries=3
        )
        
        if args.section:
            # Scrape specific section
            logger.info(f"Scraping section: {args.section}")
            result = scraper.scrape_section(args.section.upper())
            
            if result['success']:
                agencies = result['agencies']
            else:
                logger.error(f"Failed to scrape section {args.section}: {result.get('error')}")
                return 1
        else:
            # Scrape all sections
            logger.info("Scraping all sections A-Z")
            result = scraper.scrape_all_sections()
            
            if result['success']:
                agencies = result['agencies']
                if args.verbose:
                    stats = result['statistics']
                    logger.info(f"Scraping completed in {stats['duration_seconds']:.2f} seconds")
                    logger.info(f"Found {len(agencies)} agencies across {stats['sections_scraped']} sections")
            else:
                logger.error("Failed to scrape agencies")
                return 1
        
        # Validate data
        validation = scraper.validate_data(agencies)
        logger.info(f"Validation: {validation['valid_agencies']}/{validation['total_agencies']} valid agencies")
        
        if not validation['validation_passed']:
            logger.warning(f"Found {len(validation['issues'])} validation issues")
            if args.verbose:
                for issue in validation['issues'][:5]:
                    logger.warning(f"  - {issue}")
        
        # Export data
        export_paths = scraper.export_data(agencies)
        logger.info(f"Data exported to:")
        logger.info(f"  CSV: {export_paths['csv']}")
        logger.info(f"  JSON: {export_paths['json']}")
        
        # Save statistics if requested
        if args.save_stats:
            stats_file = f"logs/stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import json
            with open(stats_file, 'w') as f:
                json.dump(result.get('statistics', {}), f, indent=2, default=str)
            logger.info(f"Statistics saved to: {stats_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='USA.gov Government Agency Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple scrape of all agencies
  python main.py --simple
  
  # Scrape specific section with verbose output
  python main.py --simple --section A --verbose
  
  # Quiet mode with statistics
  python main.py --simple --quiet --save-stats
        """
    )
    
    # Mode selection
    parser.add_argument(
        '--simple',
        action='store_true',
        help='Run simple scrape without orchestration (recommended)'
    )
    
    # Scraping options
    parser.add_argument(
        '--section',
        type=str,
        help='Scrape only a specific section (A-Z)'
    )
    
    # Output options
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output with detailed statistics'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress console output (logs still saved to file)'
    )
    
    parser.add_argument(
        '--save-stats',
        action='store_true',
        help='Save scraping statistics to JSON file'
    )
    
    # Logging options
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.section and (len(args.section) != 1 or not args.section.isalpha()):
        parser.error("Section must be a single letter (A-Z)")
    
    if not args.simple:
        parser.error("Currently only --simple mode is supported. Full orchestration mode coming soon.")
    
    # Set up logging
    logger = setup_logging(args.log_level, args.quiet)
    
    # Print banner (unless quiet)
    if not args.quiet:
        print("\n" + "=" * 60)
        print("USA.gov Government Agency Scraper")
        print("=" * 60)
    
    # Run scraper
    try:
        exit_code = run_simple_scrape(args, logger)
        
        if not args.quiet:
            if exit_code == 0:
                print("\n✓ Scraping completed successfully!")
            else:
                print("\n✗ Scraping failed. Check logs for details.")
        
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        if not args.quiet:
            print("\n\nScraping interrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())