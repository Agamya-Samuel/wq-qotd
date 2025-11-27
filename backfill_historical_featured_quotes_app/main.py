import asyncio
import logging
from backfill_historical_featured_quotes_app.core.utils import load_quotes_config, is_valid_url, check_url_accessibility_and_get_quote_data, parse_monthly_quote_data, parse_monthly_quote_data_Feb2012_and_later, parse_monthly_quote_data_April2012_and_later
from app.database.crud import create_multiple_quotes
from app.schemas.schemas import QuoteCreate
from datetime import datetime
import json
from app.database.models import SessionLocal
from app.database.init_db import init_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_quote_url(url: str):
    """Process a single quote URL."""
    if not is_valid_url(url):
        logger.warning(f"Invalid URL format: {url}")
        return

    monthly_quote_data = check_url_accessibility_and_get_quote_data(url)
    if not monthly_quote_data["success"]:
        logger.warning(f"URL not accessible: {url}")
        return

    # Get year and month from URL
    url_parts = url.split('/')[-1].split('_')
    month = url_parts[0]
    year = url_parts[1] if len(url_parts) > 1 else monthly_quote_data["year"]
    
    # Determine which parser to use based on date
    parser_type = "old"  # Default to old parser
    
    try:
        int_year = int(year)
        month_name = month.lower()
        
        # Use the appropriate parser based on year and month
        if int_year > 2012:
            # For years after 2012, use April 2012 parser (most advanced)
            parser_type = "april_2012"
        elif int_year == 2012:
            if month_name == "january":
                # January 2012 uses the old format
                parser_type = "old"
            elif month_name in ["february", "march"]:
                # February and March 2012 use the Feb 2012 format
                parser_type = "feb_2012"
            else:
                # April 2012 and later months in 2012 use the April 2012 format
                parser_type = "april_2012"
    except ValueError:
        # If we can't parse the year as an int, use the old parser
        parser_type = "old"
    
    logger.info(f"Processing {month} {year} with {parser_type} parser")
    
    # Parse the quote data using the appropriate function
    if parser_type == "april_2012":
        quote_data = parse_monthly_quote_data_April2012_and_later(monthly_quote_data["data"], year)
    elif parser_type == "feb_2012":
        quote_data = parse_monthly_quote_data_Feb2012_and_later(monthly_quote_data["data"], year)
    else:
        quote_data = parse_monthly_quote_data(monthly_quote_data["data"], year)

    if quote_data:
        # Use proper session management instead of next(get_db())
        # This ensures the session is properly closed after use
        db = SessionLocal()
        try:
            # Process quotes to handle missing fields
            processed_quotes = []
            for quote in quote_data:
                # Ensure author field is never None (replace with empty string if missing)
                if quote["author"] is None:
                    quote["author"] = "Unknown"
                    
                # Ensure quote field is never None
                if quote["quote"] is None:
                    quote["quote"] = "(No quote text available)"
                    
                processed_quotes.append(QuoteCreate(**quote))
            
            if processed_quotes:
                # print(f'quote => {processed_quotes[0].model_dump()["quote"][0:60]}... (using {parser_type} parser)')
                print("-" * 100)
                create_multiple_quotes(db, processed_quotes)
                logger.info(f"Successfully processed {len(processed_quotes)} quote(s) from {url}")
            else:
                logger.warning(f"No quotes created from {url}")
        except Exception as e:
            # Log any errors that occur during processing
            logger.error(f"Error processing quotes from {url}: {str(e)}")
            db.rollback()
        finally:
            # Always close the database session
            db.close()
    else:
        logger.warning(f"Failed to extract quotes from {url}")

async def main():
    """Main function to process all quotes."""
    # Initialize the database
    init_database()

    # Load the quotes config
    config = load_quotes_config()

    # Create tasks for processing each URL
    tasks = []

    for year_key, year_value in config["urls"].items():
        for month_key, month_url in year_value.items():
            # Create tasks for processing each URL
            tasks.append(process_quote_url(month_url))

    await asyncio.gather(*tasks)
    logger.info("Quote processing completed")

if __name__ == "__main__":
    asyncio.run(main())
