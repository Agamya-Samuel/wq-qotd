#!/usr/bin/env python
from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
import requests
from typing import Dict, List
from urllib.parse import urlparse
from backfill_historical_featured_quotes_app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QOTD_API = 'https://en.wikiquote.org/w/api.php'
PARAMS = {
    "action": "parse",
    "format": "json",
    # "page": "Wikiquote:Quote_of_the_day",
    "prop": "text",
    "formatversion": "2"
}

# Headers to identify the client and avoid 403 errors
API_HEADERS = {
    "User-Agent": "QuoteOfTheDayBot/1.0 (https://github.com/your-repo; contact@example.com)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9"
}

def load_quotes_config() -> Dict:
    """Load the quotes configuration from JSON file."""
    try:
        with open(settings.QUOTES_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading quotes config: {e}")
        raise

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid and accessible."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def extract_quotes_from_api_response(api_response: Dict) -> List[Dict[str, str]] | None:
    """
    Extract quotes directly from a MediaWiki API response.
    
    This function takes the full API response dictionary and extracts quotes from it.
    It automatically determines the year from the page title and selects the appropriate parser.
    
    Arguments:
        api_response (Dict): The full MediaWiki API response dictionary with structure:
            {
                "parse": {
                    "title": str,  # e.g., "Wikiquote:Quote of the day/November 2007"
                    "pageid": int,
                    "text": str    # HTML content containing quotes
                }
            }
    
    Returns:
        Optional[List[Dict[str, str]]]: List of dictionaries containing quote information with the structure:
            {
                "featured_date": str,  # Format: YYYY-MM-DD
                "quote": str | None,   # None if quote is missing
                "author": str | None   # None if author is missing
            }
        Returns None if an error occurs during processing.
    """
    try:
        # Validate API response structure
        if 'parse' not in api_response:
            logger.error("API response does not contain 'parse' field")
            return None
        
        parse_data = api_response['parse']
        
        if 'text' not in parse_data:
            logger.error("API response does not contain 'parse.text' field")
            return None
        
        # Extract HTML content
        html_content = parse_data['text']
        
        # Extract year from title (e.g., "Wikiquote:Quote of the day/November 2007")
        year = None
        if 'title' in parse_data:
            title = parse_data['title']
            # Try to extract year from title
            year_match = re.search(r'(\d{4})', title)
            if year_match:
                year = year_match.group(1)
            else:
                # If no year in title, try to extract from month name pattern
                # For November 2007 format, we need to parse differently
                month_year_match = re.search(r'/(\w+)\s+(\d{4})', title)
                if month_year_match:
                    year = month_year_match.group(2)
        
        # If we still don't have a year, try to infer from the HTML content
        if not year:
            # Look for year patterns in the HTML
            year_match = re.search(r'(\d{4})', html_content)
            if year_match:
                year = year_match.group(1)
            else:
                logger.warning("Could not determine year from API response, defaulting to 2007")
                year = "2007"  # Default fallback
        
        logger.info(f"Extracting quotes for year: {year}")
        
        # Determine which parser to use based on year
        parser_type = "old"  # Default to old parser
        
        try:
            int_year = int(year)
            # Extract month name from title if available
            month_name = None
            if 'title' in parse_data:
                title_lower = parse_data['title'].lower()
                months = ['january', 'february', 'march', 'april', 'may', 'june',
                         'july', 'august', 'september', 'october', 'november', 'december']
                for month in months:
                    if month in title_lower:
                        month_name = month
                        break
            
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
        
        logger.info(f"Using {parser_type} parser for extraction")
        
        # Parse the quote data using the appropriate function
        if parser_type == "april_2012":
            quote_data = parse_monthly_quote_data_April2012_and_later(html_content, year)
        elif parser_type == "feb_2012":
            quote_data = parse_monthly_quote_data_Feb2012_and_later(html_content, year)
        else:
            quote_data = parse_monthly_quote_data(html_content, year)
        
        return quote_data
        
    except Exception as e:
        logger.error(f"Error extracting quotes from API response: {str(e)}")
        return None


def check_url_accessibility_and_get_quote_data(url: str) -> Dict:
    """Check if a URL is accessible and fetch quote data from Wikiquote API."""
    try:
        # get path from url
        path = urlparse(url).path.replace('/wiki/', '')
        
        # get year from path
        year = path.split('/')[-1].split('_')[-1]
        
        # set page to path
        PARAMS["page"] = path
        
        # get quote data from api with proper headers to avoid 403 errors
        response = requests.get(QOTD_API, params=PARAMS, headers=API_HEADERS, timeout=settings.TIMEOUT_SECONDS)
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"API returned status code {response.status_code} for URL: {url}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "info": response.text[:200] if response.text else "No response content"
            }
        
        # Check if response contains valid JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content (first 500 chars): {response.text[:500]}")
            return {
                "success": False,
                "error": "Invalid JSON response",
                "info": f"JSON decode error: {str(e)}"
            }

        if 'error' in data:
            logger.error(f"API error: {data['error']['code']} - {data['error']['info']}")
            return {
                "success": False,
                "error": data["error"]["code"],
                "info": data["error"]["info"]
            }
        
        # Return the HTML content from data["parse"]["text"]
        if 'parse' in data and 'text' in data['parse']:
            return {
                "success": True,
                "data": data["parse"]["text"],
                "year": year,
                "url": url
            }
        else:
            logger.error("API response does not contain expected 'parse.text' field")
            return {
                "success": False,
                "error": "Invalid API response format",
                "data": data  # Include full data for debugging
            }
    except Exception as e:
        logger.error(f"Error checking URL {url}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def parse_monthly_quote_data(quote_data: str, year: str) -> List[Dict[str, str]] | None:
    """
    Extract quotes from the Wikiquote HTML content and format them with standardized dates.
    
    This function parses HTML content containing quotes and their associated dates.
    It handles cases where quotes may be missing or null by setting those entries to None.
    
    Arguments:
        quote_data (str): HTML content containing the quotes
        year (str): The year to use for date formatting
    
    Returns:
        Optional[List[Dict[str, str]]]: List of dictionaries containing quote information with the structure:
            {
                "featured_date": str,  # Format: YYYY-MM-DD
                "quote": str | None,   # None if quote is missing
                "author": str | None   # None if author is missing
            }
        Returns None if an error occurs during processing.
    """
    if not isinstance(quote_data, str):
        logger.error("Invalid input format: Expected string")
        return None

    try:
        soup = BeautifulSoup(quote_data, 'html.parser')
        quotes_data = []
        
        # Find all dt elements containing dates
        date_elements = soup.find_all('dt')
        
        if not date_elements:
            logger.warning("No date elements found in the HTML content")
            return None
            
        # logger.info(f"Found {len(date_elements)} date elements")
        
        for dt in date_elements:
            # Extract and clean the date text
            date_str = dt.text.strip()
            
            # Skip if no valid date found
            if not date_str:
                continue
                
            logger.debug(f"Processing date: {date_str}")
            
            # Parse the date into standardized format (YYYY-MM-DD)
            try:
                month_day = datetime.strptime(date_str, "%B %d")
                formatted_date = f"{year}-{month_day.strftime('%m-%d')}"
            except ValueError as e:
                logger.debug(f"Could not parse date '{date_str}': {e}")
                continue
            
            # Find the next table after this dt element
            next_table = dt.find_next('table')
            
            if not next_table:
                logger.debug(f"No table found for date {date_str}")
                # Add an entry with None values if no table is found
                quotes_data.append({
                    "featured_date": formatted_date,
                    "quote": None,
                    "author": None
                })
                continue
            
            # Find the quote text which is typically in the 3rd td element
            td_elements = next_table.find_all('td')
            if len(td_elements) >= 3:
                quote_td = td_elements[2]  # The third td usually contains the quote
                
                # Get the text content of the quote cell
                content = quote_td.get_text(strip=True)
                
                # Try to extract quote and author
                if '~' in content:
                    # Split on first '~' to separate quote from author
                    parts = content.split('~', 1)
                    quote = parts[0].strip()
                    
                    # Handle the author part
                    if len(parts) > 1:
                        # Clean up author text
                        author = parts[1].split('Past months')[0].strip()
                        # Remove reference markers and clean up
                        author = re.sub(r'\s*[\[(][^\])]*[\])]', '', author).replace('~', '').strip()
                    else:
                        author = None
                else:
                    # If no tilde separator, try to find the author by looking for links
                    quote = content
                    author_link = quote_td.find('a')
                    author = author_link.text.strip() if author_link else None
                
                quotes_data.append({
                    "featured_date": formatted_date,
                    "quote": quote or None,  # Convert empty string to None
                    "author": author or None  # Convert empty string to None
                })
            else:
                # If we couldn't find the quote, add an entry with None values
                quotes_data.append({
                    "featured_date": formatted_date,
                    "quote": None,
                    "author": None
                })
        
        if not quotes_data:
            logger.warning("No valid quotes were extracted from the provided HTML content")
            return None

        logger.info(f'Extracted {len(quotes_data)} quotes for {year}')
        return quotes_data

    except Exception as e:
        logger.error(f"Error extracting quote data: {str(e)}")
        return None

def parse_monthly_quote_data_Feb2012_and_later(quote_data: str, year: str) -> List[Dict[str, str]] | None:
    """
    Extract quotes from newer format Wikiquote HTML content (February 2012 and later).
    
    This function is optimized for the newer format where quotes are contained in paragraph 
    elements rather than tables. It extracts quotes and their associated dates.
    
    Arguments:
        quote_data (str): HTML content containing the quotes
        year (str): The year to use for date formatting
    
    Returns:
        Optional[List[Dict[str, str]]]: List of dictionaries containing quote information with the structure:
            {
                "featured_date": str,  # Format: YYYY-MM-DD
                "quote": str | None,   # None if quote is missing
                "author": str | None   # None if author is missing
            }
        Returns None if an error occurs during processing.
    """
    if not isinstance(quote_data, str):
        logger.error("Invalid input format: Expected string")
        return None

    try:
        soup = BeautifulSoup(quote_data, 'html.parser')
        quotes_data = []
        
        # Find all dt elements containing dates
        date_elements = soup.find_all('dt')
        
        if not date_elements:
            logger.warning("No date elements found in the HTML content")
            return None
            
        logger.info(f"Found {len(date_elements)} date elements")
        
        for dt in date_elements:
            # Extract and clean the date text
            date_str = dt.text.strip()
            
            # Skip if no valid date found
            if not date_str:
                continue
                
            logger.debug(f"Processing date: {date_str}")
            
            # Parse the date into standardized format (YYYY-MM-DD)
            try:
                month_day = datetime.strptime(date_str, "%B %d")
                formatted_date = f"{year}-{month_day.strftime('%m-%d')}"
            except ValueError as e:
                logger.debug(f"Could not parse date '{date_str}': {e}")
                continue
            
            # The quote is typically in the paragraph after the dt element
            quote_p = dt.find_next('p')
            author_p = None
            
            if quote_p:
                # Next paragraph might contain the author
                author_p = quote_p.find_next('p')
                
                # Extract quote text
                quote_text = quote_p.get_text(strip=True)
                
                # Extract author text if available
                author_text = None
                if author_p and author_p.find('small'):
                    author_text = author_p.get_text(strip=True)
                    # Clean up the author text - typically contains a tilde
                    if '~' in author_text:
                        author_text = author_text.split('~')[1].strip()
                        # Remove any trailing tildes
                        author_text = author_text.rstrip('~').strip()
                
                quotes_data.append({
                    "featured_date": formatted_date,
                    "quote": quote_text or None,  # Convert empty string to None
                    "author": author_text or None  # Convert empty string to None
                })
            else:
                # If no paragraph found, check for other element types
                next_element = dt.find_next()
                if next_element and next_element.name != 'dt':
                    quote_text = next_element.get_text(strip=True)
                    # Try to find author in the text with tilde separator
                    if '~' in quote_text:
                        parts = quote_text.split('~', 1)
                        quote_part = parts[0].strip()
                        author_part = parts[1].strip() if len(parts) > 1 else None
                        # Clean up author part
                        if author_part:
                            author_part = author_part.split('Past months')[0].strip()
                            author_part = re.sub(r'\s*[\[(][^\])]*[\])]', '', author_part).replace('~', '').strip()
                            
                        quotes_data.append({
                            "featured_date": formatted_date,
                            "quote": quote_part or None,
                            "author": author_part or None
                        })
                    else:
                        # If no author found, just use the whole text as the quote
                        quotes_data.append({
                            "featured_date": formatted_date,
                            "quote": quote_text or None,
                            "author": None
                        })
                else:
                    # If we couldn't find any quote content
                    quotes_data.append({
                        "featured_date": formatted_date,
                        "quote": None,
                        "author": None
                    })
        
        if not quotes_data:
            logger.warning("No valid quotes were extracted from the provided HTML content")
            return None

        logger.info(f'Extracted {len(quotes_data)} quotes for {year}')
        return quotes_data

    except Exception as e:
        logger.error(f"Error extracting quote data: {str(e)}")
        return None

def parse_monthly_quote_data_April2012_and_later(quote_data: str, year: str) -> List[Dict[str, str]] | None:
    """
    Extract quotes from newer format Wikiquote HTML content (April 2012 and later).
    
    This function is optimized for the April 2012+ format where quotes are directly
    after date elements (<dt>), with the quote text in a paragraph element and 
    author information in a subsequent paragraph with <small> tags.
    
    Arguments:
        quote_data (str): HTML content containing the quotes
        year (str): The year to use for date formatting
    
    Returns:
        Optional[List[Dict[str, str]]]: List of dictionaries containing quote information with the structure:
            {
                "featured_date": str,  # Format: YYYY-MM-DD
                "quote": str | None,   # None if quote is missing
                "author": str | None   # None if author is missing
            }
        Returns None if an error occurs during processing.
    """
    if not isinstance(quote_data, str):
        logger.error("Invalid input format: Expected string")
        return None

    try:
        soup = BeautifulSoup(quote_data, 'html.parser')
        quotes_data = []
        
        # Find all dt elements containing dates
        date_elements = soup.find_all('dt')
        
        if not date_elements:
            logger.warning("No date elements found in the HTML content")
            return None
            
        logger.info(f"Found {len(date_elements)} date elements in April 2012+ format")
        
        # Navigation patterns to filter out
        navigation_patterns = [
            "view", "talk", "discussion", "history", "view-talk", "view-discussion",
            "view-history", "talk-history", "view-talk-history", "view-discussion-history"
        ]
        
        for i, dt in enumerate(date_elements):
            # Extract and clean the date text
            date_str = dt.text.strip()
            
            # Skip if no valid date found
            if not date_str:
                continue
                
            logger.debug(f"Processing date: {date_str}")
            
            # Parse the date into standardized format (YYYY-MM-DD)
            try:
                # Try standard "Month Day" format first
                month_day = datetime.strptime(date_str, "%B %d")
                formatted_date = f"{year}-{month_day.strftime('%m-%d')}"
            except ValueError:
                # Try alternative formats if standard format fails
                try:
                    if re.search(r"\w+ \d+", date_str):
                        # Extract month and day using regex for more flexibility
                        match = re.search(r"(\w+)\s+(\d+)", date_str)
                        if match:
                            month_str, day_str = match.groups()
                            try:
                                month_num = {
                                    'january': '01', 'february': '02', 'march': '03', 'april': '04',
                                    'may': '05', 'june': '06', 'july': '07', 'august': '08',
                                    'september': '09', 'october': '10', 'november': '11', 'december': '12'
                                }.get(month_str.lower(), '')
                                
                                if month_num and day_str.isdigit():
                                    day_num = day_str.zfill(2)
                                    formatted_date = f"{year}-{month_num}-{day_num}"
                                else:
                                    logger.debug(f"Could not map '{month_str}' to a month number")
                                    continue
                            except Exception as e:
                                logger.debug(f"Error parsing date components: {e}")
                                continue
                        else:
                            logger.debug(f"Regex pattern match failed for '{date_str}'")
                            continue
                    else:
                        logger.debug(f"Date string '{date_str}' does not match expected pattern")
                        continue
                except Exception as e:
                    logger.debug(f"Could not parse alternative date format '{date_str}': {e}")
                    continue
            
            # Find the next dt or hr element to determine the boundary of this quote section
            next_dt = dt.find_next('dt')
            next_hr = dt.find_next('hr')
            
            # Determine the end boundary for this quote section
            if next_dt and next_hr:
                # Use whichever comes first
                end_element = next_dt if next_dt.sourceline < next_hr.sourceline else next_hr
            elif next_dt:
                end_element = next_dt
            elif next_hr:
                end_element = next_hr
            else:
                # If no next boundary, this is the last quote
                end_element = None
            
            # Collect all paragraph elements between this dt and the boundary
            paragraphs = []
            current = dt.find_next('p')
            
            while current and (not end_element or (hasattr(current, 'sourceline') and current.sourceline < end_element.sourceline)):
                paragraphs.append(current)
                current = current.find_next('p')
                if not current or (end_element and hasattr(current, 'sourceline') and current.sourceline >= end_element.sourceline):
                    break
            
            if paragraphs:
                # The first paragraph typically contains the quote
                quote_text = paragraphs[0].get_text(strip=True)
                # Clean up excessive whitespace
                quote_text = re.sub(r'\s+', ' ', quote_text)
                author_text = None
                
                # Skip navigation elements that are not real quotes
                is_navigation = False
                for pattern in navigation_patterns:
                    if pattern.lower() in quote_text.lower():
                        logger.debug(f"Skipping navigation element: {quote_text}")
                        is_navigation = True
                        break
                
                if is_navigation:
                    # Try to find a real quote by checking other paragraphs
                    for p in paragraphs[1:]:
                        potential_quote = p.get_text(strip=True)
                        potential_quote = re.sub(r'\s+', ' ', potential_quote)
                        
                        is_nav = False
                        for pattern in navigation_patterns:
                            if pattern.lower() in potential_quote.lower():
                                is_nav = True
                                break
                        
                        if not is_nav and len(potential_quote) > 10:  # Minimum length for a reasonable quote
                            quote_text = potential_quote
                            is_navigation = False
                            break
                
                if is_navigation:
                    # If we still only have navigation elements, set to None
                    quote_text = None
                
                # Look for the author in paragraphs with <small> tags
                for p in paragraphs:
                    small_tag = p.find('small')
                    if small_tag:
                        author_content = small_tag.get_text(strip=True)
                        # Clean up excessive whitespace
                        author_content = re.sub(r'\s+', ' ', author_content)
                        
                        if '~' in author_content:
                            # Extract author text between tildes
                            parts = author_content.split('~')
                            if len(parts) >= 3:
                                # Format is typically "~ Author ~"
                                author_text = parts[1].strip()
                            elif len(parts) == 2:
                                # Or sometimes "~ Author" or "Author ~"
                                author_text = parts[1].strip() if parts[0].strip() == "" else parts[0].strip()
                        else:
                            # If no tildes, just use the content
                            author_text = author_content.strip()
                        break
                
                # If no author found in <small> tags, check if the quote contains the author
                if not author_text and quote_text and '~' in quote_text:
                    parts = quote_text.split('~')
                    quote_text = parts[0].strip()
                    if len(parts) > 1:
                        author_text = parts[1].strip()
                
                # Clean up any reference markers in author or quote
                if author_text:
                    author_text = re.sub(r'\s*[\[(][^\])]*[\])]', '', author_text).strip()
                    
                    # Check if author is just a navigation element
                    is_nav_author = False
                    for pattern in navigation_patterns:
                        if pattern.lower() in author_text.lower():
                            is_nav_author = True
                            break
                    
                    if is_nav_author:
                        author_text = None
                
                quotes_data.append({
                    "featured_date": formatted_date,
                    "quote": quote_text or None,
                    "author": author_text or None
                })
                
                logger.debug(f"Extracted quote for {formatted_date} by {author_text or 'unknown author'}")
            else:
                # If no paragraphs were found
                logger.warning(f"No paragraphs found for date {formatted_date}")
                quotes_data.append({
                    "featured_date": formatted_date,
                    "quote": None,
                    "author": None
                })
        
        if not quotes_data:
            logger.warning("No valid quotes were extracted from the provided HTML content")
            return None

        logger.info(f'Successfully extracted {len(quotes_data)} quotes for {year} using April 2012+ parser')
        return quotes_data

    except Exception as e:
        logger.error(f"Error extracting quote data: {str(e)}")
        return None
