"""
Scraper module for USA.gov Agency Index
Contains Botasaurus-based scraping implementation
"""

from .botasaurus_scraper import AgencyIndexScraper, BatchScraper

__all__ = ['AgencyIndexScraper', 'BatchScraper']