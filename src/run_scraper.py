#!/usr/bin/env python3
"""Script to run the EUR-Lex scraper for a specific date range."""

from datetime import datetime, timedelta
from loguru import logger

from scraper import EURLexScraper

def scrape_date_range(start_date: datetime, end_date: datetime):
    """Scrape documents for a range of dates."""
    scraper = EURLexScraper()
    
    current_date = start_date
    while current_date <= end_date:
        try:
            logger.info(f"Scraping documents for date: {current_date.strftime('%Y-%m-%d')}")
            scraper.scrape_journal(current_date)
            
        except Exception as e:
            logger.error(f"Error scraping date {current_date}: {str(e)}")
            
        current_date += timedelta(days=1)

if __name__ == "__main__":
    # Set date range: January 19th to January 26th, 2025
    start_date = datetime(2025, 1, 19)
    end_date = datetime(2025, 1, 26)
    
    logger.info(f"Starting scraper for date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    scrape_date_range(start_date, end_date)
