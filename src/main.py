"""Main script for running the EUR-Lex scraper across date ranges."""
from datetime import datetime, timedelta
from typing import Optional
import argparse
from loguru import logger

from scraper import EURLexScraper
from logging_config import setup_logging
from exceptions import InvalidDateError

def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """Validate the date range for scraping.
    
    Args:
        start_date: Start date for scraping
        end_date: End date for scraping
        
    Raises:
        InvalidDateError: If start_date is before October 2nd, 2023
        ValueError: If end_date is before start_date
    """
    min_allowed_date = datetime(2023, 10, 2)
    if start_date < min_allowed_date:
        raise InvalidDateError(
            f"Cannot scrape dates before October 2nd, 2023 due to website structure changes. "
            f"Provided start date: {start_date.date()}"
        )
    if end_date < start_date:
        raise ValueError(f"End date ({end_date.date()}) cannot be before start date ({start_date.date()})")

def scrape_date_range(
    start_date: datetime,
    end_date: datetime,
    scraper: Optional[EURLexScraper] = None
) -> None:
    """
    Scrape EUR-Lex documents for a range of dates, from oldest to newest.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        scraper: Optional EURLexScraper instance. If None, one will be created.
    """
    try:
        validate_date_range(start_date, end_date)
    except InvalidDateError as e:
        logger.error(str(e))
        return
    except ValueError as e:
        logger.error(str(e))
        return

    # Initialize scraper if not provided
    if scraper is None:
        scraper = EURLexScraper()
    
    current_date = start_date
    while current_date <= end_date:
        try:
            logger.info(f"Processing date: {current_date.date()}")
            stored_paths = scraper.scrape_journal(current_date)
            
            if stored_paths:
                logger.success(f"Successfully stored {len(stored_paths)} documents for {current_date.date()}")
            else:
                logger.warning(f"No documents stored for {current_date.date()} "
                             "(either no documents published or already scraped)")
                
        except Exception as e:
            logger.error(f"Error processing date {current_date.date()}: {str(e)}")
        
        finally:
            current_date += timedelta(days=1)

def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(description="EUR-Lex document scraper")
    parser.add_argument(
        "--start-date",
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        help="Start date in YYYY-MM-DD format",
        required=True
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.strptime(s, '%Y-%m-%d'),
        help="End date in YYYY-MM-DD format",
        required=True
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    logger.info(f"Starting scraping from {args.start_date.date()} to {args.end_date.date()}")
    scrape_date_range(args.start_date, args.end_date)
    logger.success("Scraping completed")

if __name__ == "__main__":
    main()
