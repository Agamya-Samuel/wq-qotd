from datetime import datetime, date, timezone
from sqlalchemy.orm import Session
from app.database.models import Quote
from typing import Optional, List, Any
from sqlalchemy import func
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_quote_to_db(db: Session, quote_data: dict) -> Quote:
    featured_date = datetime.fromisoformat(quote_data['featured_date']).date()
    current_time = datetime.now(timezone.utc)
    
    quote = Quote(
        id=quote_data['id'],
        quote=quote_data['quote'],
        author=quote_data['author'],
        featured_date=featured_date,
        created_at=current_time,
        updated_at=current_time
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    
    return quote

def get_quote_by_date(db: Session, target_date: str):
    if isinstance(target_date, (datetime, date)):
        target_date = target_date.isoformat()
    
    target_date_obj = datetime.fromisoformat(target_date).date()
    return db.query(Quote).filter(Quote.featured_date == target_date_obj).first()

def get_all_quotes(db: Session, page: int, limit: int, author: Optional[str] = None) -> List[Quote]:
    query = db.query(Quote)
    if author:
        query = query.filter(Quote.author.ilike(f"%{author}%"))
    return query.offset((page - 1) * limit).limit(limit).all()

def create_multiple_quotes(db: Session, quotes: List[Any]) -> List[Quote]:
    """
    Create multiple quotes in the database from a list of Pydantic QuoteCreate objects.
    
    This function handles:
    - Converting string dates to date objects
    - Checking for duplicates by featured_date (skips existing quotes)
    - Generating IDs for quotes that don't have them
    - Proper error handling and logging
    
    Args:
        db: SQLAlchemy database session
        quotes: List of QuoteCreate objects or dictionaries
        
    Returns:
        List of created Quote objects (excluding duplicates)
    """
    try:
        # Create SQLAlchemy model instances from Pydantic models
        current_time = datetime.now(timezone.utc)
        db_quotes = []
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for quote in quotes:
            try:
                # Convert Pydantic model to dict
                try:
                    quote_dict = quote.model_dump()
                except AttributeError:
                    # If it's already a dict
                    quote_dict = quote
                
                # Convert featured_date from string to date object if needed
                # This handles dates coming from parsers as "YYYY-MM-DD" strings
                if isinstance(quote_dict.get('featured_date'), str):
                    try:
                        # Try parsing ISO format string (YYYY-MM-DD)
                        quote_dict['featured_date'] = datetime.fromisoformat(quote_dict['featured_date']).date()
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Failed to parse date '{quote_dict.get('featured_date')}': {e}")
                        error_count += 1
                        continue
                
                # Check for duplicate by featured_date before processing
                # This prevents unique constraint violations
                existing_quote = db.query(Quote).filter(
                    Quote.featured_date == quote_dict['featured_date']
                ).first()
                
                if existing_quote:
                    logger.debug(f"Skipping duplicate quote for date {quote_dict['featured_date']}")
                    skipped_count += 1
                    continue
                
                # Generate an ID if not provided
                if 'id' not in quote_dict:
                    # Create a hash based on quote text, author, and date to ensure uniqueness
                    unique_id = hashlib.md5(
                        f"{quote_dict['quote']}_{quote_dict['author']}_{quote_dict['featured_date']}".encode()
                    ).hexdigest()
                    quote_dict['id'] = unique_id
                
                # Set timestamps if not provided
                if 'created_at' not in quote_dict:
                    quote_dict['created_at'] = current_time
                if 'updated_at' not in quote_dict:
                    quote_dict['updated_at'] = current_time
                
                # Create Quote instance with properly converted date
                db_quote = Quote(**quote_dict)
                db_quotes.append(db_quote)
                created_count += 1
                
            except Exception as e:
                # Log error for individual quote but continue processing others
                logger.error(f"Error processing quote: {str(e)}")
                error_count += 1
                continue
            
        # Add all quotes to the session and commit
        if db_quotes:
            db.add_all(db_quotes)
            db.commit()
            logger.info(f"Created {created_count} quote(s), skipped {skipped_count} duplicate(s), {error_count} error(s)")
        else:
            logger.info(f"No quotes to create. Skipped {skipped_count} duplicate(s), {error_count} error(s)")
        
        return db_quotes
        
    except Exception as e:
        db.rollback()  # Roll back on error
        logger.error(f"Error creating quotes: {str(e)}")
        raise