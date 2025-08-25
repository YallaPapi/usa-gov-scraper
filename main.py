"""
Main Application Entry Point for USA.gov Agency Index Scraper
Provides CLI interface and coordinates the entire scraping process
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from orchestrator import AgencyIndexOrchestratorSystem
from scraper.botasaurus_scraper import AgencyIndexScraper
import json


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Set up timestamp for log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"logs/scraper_{timestamp}.log"
    
    # Configure logging
    logger = logging.getLogger('usa_gov_scraper')
    logger.setLevel(getattr(logging, log_level))
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger


def run_with_orchestration(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Run the scraper with full Agency Swarm orchestration.
    
    Args:
        args: Command line arguments
        logger: Logger instance
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("Starting USA.gov Agency Index Scraper with Agency Swarm orchestration")
    
    try:
        # Initialize orchestration system
        orchestrator = AgencyIndexOrchestratorSystem(use_openai=not args.no_openai)
        
        # Run the scraping process
        result = orchestrator.run_scraping_process(target_url=args.url)
        
        if result['success']:
            # Log success
            logger.info(f"Scraping completed successfully!")
            logger.info(f"Total agencies scraped: {result['statistics']['total_agencies']}")
            logger.info(f"Duration: {result['statistics']['duration_seconds']:.2f} seconds")
            
            # Save statistics if requested
            if args.save_stats:
                stats_file = f"output/statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                os.makedirs("output", exist_ok=True)
                with open(stats_file, 'w') as f:
                    json.dump(result['statistics'], f, indent=2)
                logger.info(f"Statistics saved to: {stats_file}")
            
            # Print orchestration report
            if args.verbose:
                report = orchestrator.get_orchestration_report()
                print("\n" + report)
            
            return 0
        else:
            logger.error(f"Scraping failed: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return 1


def run_simple_scrape(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Run a simple scrape without orchestration (direct Botasaurus).
    
    Args:
        args: Command line arguments
        logger: Logger instance
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("Starting simple Botasaurus scrape (no orchestration)")
    
    try:
        # Initialize scraper
        scraper = AgencyIndexScraper()
        
        # Run scraping
        if args.section:
            # Scrape specific section
            logger.info(f"Scraping section: {args.section}")
            result = scraper.scrape_section(args.section)
        else:
            # Scrape all sections
            logger.info("Scraping all sections")
            result = scraper.scrape_agency_index()
        
        if result['success']:
            agencies = result['agencies']
            logger.info(f"Scraped {len(agencies)} agencies")
            
            # Validate if requested
            if args.validate:
                validation = scraper.validate_agencies()
                logger.info(f"Validation: {validation['valid_agencies']}/{validation['total_agencies']} valid")
                
                if not validation['validation_passed']:
                    logger.warning(f"Validation issues found: {validation['issues'][:5]}")
            
            # Export data
            if args.export:
                from scraper_agents.base_agents import ExportDataTool
                
                formats = args.formats.split(',') if args.formats else ['csv', 'json']
                
                export_tool = ExportDataTool(
                    data=agencies,
                    formats=formats,
                    output_dir=args.output_dir
                )
                
                export_result = json.loads(export_tool.run())
                
                if export_result['success']:
                    for file_info in export_result['exported_files']:
                        logger.info(f"Exported to {file_info['format']}: {file_info['path']}")
                else:
                    logger.error(f"Export failed: {export_result.get('error')}")
            
            return 0
        else:
            logger.error(f"Scraping failed: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return 1


def main():
    """Main entry point for the USA.gov Agency Index scraper."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='USA.gov Agency Index Scraper - Extract federal agency information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with full orchestration (default)
  python main.py
  
  # Run simple scrape without orchestration
  python main.py --simple
  
  # Scrape a specific section
  python main.py --simple --section A
  
  # Use custom output directory and formats
  python main.py --output-dir results --formats csv,json
  
  # Run with verbose output and save statistics
  python main.py --verbose --save-stats
  
  # Run without OpenAI (limited orchestration)
  python main.py --no-openai
        """
    )
    
    # General arguments
    parser.add_argument(
        '--url',
        default='https://www.usa.gov/agency-index',
        help='URL of the USA.gov Agency Index (default: %(default)s)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Directory to store output files (default: %(default)s)'
    )
    
    parser.add_argument(
        '--formats',
        default='csv,json',
        help='Output formats (comma-separated) (default: %(default)s)'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: %(default)s)'
    )
    
    # Orchestration options
    parser.add_argument(
        '--simple',
        action='store_true',
        help='Run simple scrape without Agency Swarm orchestration'
    )
    
    parser.add_argument(
        '--no-openai',
        action='store_true',
        help='Run without OpenAI API (limited orchestration capabilities)'
    )
    
    # Scraping options
    parser.add_argument(
        '--section',
        help='Scrape only a specific section (A-Z)'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='Validate scraped data (default: True)'
    )
    
    parser.add_argument(
        '--export',
        action='store_true',
        default=True,
        help='Export data to files (default: True)'
    )
    
    # Output options
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--save-stats',
        action='store_true',
        help='Save scraping statistics to JSON file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without actually scraping'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.section and len(args.section) != 1:
        parser.error("Section must be a single letter (A-Z)")
    
    if args.section and args.section.upper() not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        parser.error("Section must be a letter from A to Z")
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    # Print banner
    print("\n" + "=" * 60)
    print("USA.gov Agency Index Scraper")
    print("Powered by Botasaurus + Agency Swarm")
    print("=" * 60 + "\n")
    
    # Check for dry run
    if args.dry_run:
        logger.info("DRY RUN MODE - No actual scraping will be performed")
        print("\nConfiguration:")
        print(f"  URL: {args.url}")
        print(f"  Output Directory: {args.output_dir}")
        print(f"  Formats: {args.formats}")
        print(f"  Mode: {'Simple' if args.simple else 'Orchestrated'}")
        print(f"  OpenAI: {'Disabled' if args.no_openai else 'Enabled'}")
        print(f"  Section: {args.section if args.section else 'All'}")
        print("\nDry run complete. No data was scraped.")
        return 0
    
    # Run the appropriate scraping mode
    try:
        if args.simple:
            exit_code = run_simple_scrape(args, logger)
        else:
            exit_code = run_with_orchestration(args, logger)
        
        if exit_code == 0:
            print("\n✓ Scraping completed successfully!")
        else:
            print("\n✗ Scraping failed. Check the logs for details.")
        
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        print("\n\nScraping interrupted by user.")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n✗ Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())