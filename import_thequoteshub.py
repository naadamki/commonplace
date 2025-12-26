import requests
import json
import time
import os
from models import Session, Quote, Category, Author

session = Session()

# Progress tracking file
PROGRESS_FILE = 'import_progress.json'

def save_progress(last_page, total_imported, total_failed, total_skipped):
    """Save import progress to file"""
    progress = {
        'last_page': last_page,
        'total_imported': total_imported,
        'total_failed': total_failed,
        'total_skipped': total_skipped,
        'timestamp': time.time()
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def load_progress():
    """Load import progress from file"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return None

def clear_progress():
    """Clear the progress file"""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("Progress file cleared.")

def load_categories():
    """Load categories from JSON file"""
    with open('categories.json', 'r') as f:
        categories_data = json.load(f)
    
    print("Loading categories into database...")
    for name, keywords in categories_data.items():
        category = session.query(Category).filter_by(name=name).first()
        if not category:
            category = Category(name=name)
            category.set_keywords(keywords)
            session.add(category)
    
    session.commit()
    print(f"Loaded {len(categories_data)} categories")

def get_or_create_author(author_name):
    """Get existing author or create new one"""
    if not author_name:
        author_name = "Unknown"
    
    author = session.query(Author).filter_by(name=author_name).first()
    if not author:
        author = Author(name=author_name)
        session.add(author)
        session.commit()
    return author

def categorize_quote(quote):
    """Automatically assign categories based on keywords"""
    if not quote.text:
        return
    
    quote_lower = quote.text.lower()
    categories = session.query(Category).all()
    
    for category in categories:
        keywords = category.get_keywords()
        if any(keyword in quote_lower for keyword in keywords):
            if category not in quote.categories:
                quote.categories.append(category)

def fetch_quotes_page(page_number, page_size=100):
    """Fetch a page of quotes from thequoteshub API"""
    url = f"https://thequoteshub.com/api/quotes?page={page_number}&page_size={page_size}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {page_number}: {e}")
        return None

def quote_exists(quote_text):
    """Check if a quote already exists in the database by text"""
    return session.query(Quote).filter_by(text=quote_text).first() is not None

def import_quote(api_data):
    """Import a single quote from API data into database"""
    if not api_data:
        return None
    
    quote_text = api_data.get('text', '')
    if not quote_text:
        return None
    
    # Check if quote already exists (using text to avoid duplicates)
    if quote_exists(quote_text):
        return None  # Return None for duplicates
    
    # Get or create author
    author_name = api_data.get('author', 'Unknown')
    author = get_or_create_author(author_name)
    
    # Create quote
    api_id = api_data.get('id')
    quote = Quote(
        text=quote_text,
        author=author,
        source=f"thequoteshub.com (ID: {api_id})"
    )
    
    # Add tags from API
    api_tags = api_data.get('tags', [])
    if api_tags:
        quote.set_tags(api_tags)
    
    # Auto-categorize based on keywords
    categorize_quote(quote)
    
    session.add(quote)
    
    return quote

def import_page(page_number, page_size=100):
    """Import all quotes from a single page"""
    print(f"\nFetching page {page_number} (up to {page_size} quotes)...")
    
    # Fetch the page
    data = fetch_quotes_page(page_number, page_size)
    
    if not data:
        print(f"✗ Failed to fetch page {page_number}")
        return {'success': 0, 'skip': 0, 'error': 1, 'empty': False}
    
    # Handle different possible response formats
    quotes_data = data if isinstance(data, list) else data.get('quotes', [])
    
    if not quotes_data:
        print(f"○ Page {page_number} is empty (end of data)")
        return {'success': 0, 'skip': 0, 'error': 0, 'empty': True}
    
    print(f"Processing {len(quotes_data)} quotes from page {page_number}...")
    
    success_count = 0
    skip_count = 0
    
    for quote_data in quotes_data:
        quote = import_quote(quote_data)
        if quote:
            success_count += 1
        else:
            skip_count += 1
    
    # Commit all quotes from this page at once
    try:
        session.commit()
        print(f"✓ Page {page_number}: Added {success_count}, Skipped {skip_count} duplicates")
    except Exception as e:
        session.rollback()
        print(f"✗ Error committing page {page_number}: {e}")
        return {'success': 0, 'skip': skip_count, 'error': success_count, 'empty': False}
    
    return {'success': success_count, 'skip': skip_count, 'error': 0, 'empty': False}

def import_all_pages(page_size=100, start_page=1, max_pages=None, resume=False):
    """
    Import all quotes by iterating through pages
    
    Args:
        page_size: Number of quotes per page (100 recommended)
        start_page: Page number to start from (default 1)
        max_pages: Maximum number of pages to import (None = all)
        resume: Whether to resume from last saved progress
    """
    
    # Initialize stats
    total_imported = 0
    total_skipped = 0
    total_failed = 0
    current_page = start_page
    
    # Check for resume
    if resume:
        progress = load_progress()
        if progress:
            current_page = progress['last_page'] + 1
            total_imported = progress['total_imported']
            total_failed = progress['total_failed']
            total_skipped = progress['total_skipped']
            print(f"\n{'='*60}")
            print(f"RESUMING FROM PREVIOUS SESSION")
            print(f"{'='*60}")
            print(f"Last completed page: {progress['last_page']}")
            print(f"Previously imported: {total_imported:,}")
            print(f"Previously skipped: {total_skipped:,}")
            print(f"Previously failed: {total_failed:,}")
            print(f"Resuming from page: {current_page}")
            print(f"{'='*60}\n")
        else:
            print("No progress file found. Starting fresh import.")
    else:
        # Clear any existing progress file when starting fresh
        clear_progress()
    
    last_save_time = time.time()
    SAVE_INTERVAL = 60  # Save progress every 60 seconds
    
    consecutive_empty_pages = 0
    MAX_EMPTY_PAGES = 3  # Stop after 3 consecutive empty pages
    
    try:
        pages_processed = 0
        
        while True:
            # Check if we've hit max_pages limit
            if max_pages and pages_processed >= max_pages:
                print(f"\nReached maximum page limit ({max_pages} pages)")
                break
            
            # Import the page
            result = import_page(current_page, page_size)
            
            # Update stats
            total_imported += result['success']
            total_skipped += result['skip']
            total_failed += result['error']
            
            # Check if page was empty
            if result['empty']:
                consecutive_empty_pages += 1
                print(f"  Empty pages in a row: {consecutive_empty_pages}/{MAX_EMPTY_PAGES}")
                
                if consecutive_empty_pages >= MAX_EMPTY_PAGES:
                    print(f"\n✓ Reached end of data ({MAX_EMPTY_PAGES} consecutive empty pages)")
                    break
            else:
                consecutive_empty_pages = 0  # Reset counter
            
            # Save progress periodically
            current_time = time.time()
            if current_time - last_save_time >= SAVE_INTERVAL:
                save_progress(current_page, total_imported, total_failed, total_skipped)
                last_save_time = current_time
                print(f"  [Progress saved at page {current_page}]")
            
            # Display running totals every 10 pages
            if current_page % 10 == 0:
                print(f"\n--- Progress Update ---")
                print(f"Pages processed: {pages_processed + 1}")
                print(f"Total imported: {total_imported:,}")
                print(f"Total skipped: {total_skipped:,}")
                print(f"Total failed: {total_failed:,}")
                print(f"----------------------\n")
            
            current_page += 1
            pages_processed += 1
            
            # Small delay between pages to be respectful to the API
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print("IMPORT INTERRUPTED BY USER")
        print(f"{'='*60}")
        save_progress(current_page - 1, total_imported, total_failed, total_skipped)
        print(f"Progress has been saved at page {current_page - 1}.")
        print(f"Run with resume=True to continue from page {current_page}")
        print(f"{'='*60}\n")
        return
    
    except Exception as e:
        print(f"\n\n{'='*60}")
        print(f"UNEXPECTED ERROR: {e}")
        print(f"{'='*60}")
        save_progress(current_page - 1, total_imported, total_failed, total_skipped)
        print(f"Progress has been saved at page {current_page - 1}.")
        print(f"{'='*60}\n")
        return
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"Total pages processed: {pages_processed}")
    print(f"Successfully imported: {total_imported:,}")
    print(f"Skipped (duplicates): {total_skipped:,}")
    print(f"Failed: {total_failed:,}")
    print(f"{'='*60}\n")
    
    # Clear progress file after successful completion
    print("Import fully completed! Clearing progress file...")
    clear_progress()

def get_database_stats():
    """Display statistics about the database"""
    quote_count = session.query(Quote).count()
    author_count = session.query(Author).count()
    category_count = session.query(Category).count()
    
    print(f"\n{'='*60}")
    print(f"DATABASE STATISTICS")
    print(f"{'='*60}")
    print(f"Total Quotes: {quote_count:,}")
    print(f"Total Authors: {author_count:,}")
    print(f"Total Categories: {category_count}")
    print(f"{'='*60}\n")

def show_progress_info():
    """Show information about saved progress"""
    progress = load_progress()
    if progress:
        import datetime
        timestamp = datetime.datetime.fromtimestamp(progress['timestamp'])
        print(f"\n{'='*60}")
        print(f"SAVED PROGRESS FOUND")
        print(f"{'='*60}")
        print(f"Last completed page: {progress['last_page']:,}")
        print(f"Total imported: {progress['total_imported']:,}")
        print(f"Total skipped: {progress['total_skipped']:,}")
        print(f"Total failed: {progress['total_failed']:,}")
        print(f"Last updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Next page to import: {progress['last_page'] + 1:,}")
        print(f"{'='*60}\n")
    else:
        print("\nNo saved progress found.")

if __name__ == "__main__":
    print("="*60)
    print("THEQUOTESHUB.COM BATCH IMPORTER")
    print("="*60)
    
    # First time setup - load categories
    load_categories()
    
    # Show current stats
    get_database_stats()
    
    # Check for saved progress
    show_progress_info()
    
    # Choose your import strategy:
    
    # OPTION 1: Test with first 5 pages (500 quotes)
    # print("\nStarting test import of first 5 pages...")
    # import_all_pages(page_size=100, start_page=1, max_pages=5, resume=False)
    
    # OPTION 2: Import all pages with auto-resume
    print("\nStarting full import with auto-resume...")
    import_all_pages(page_size=10000, start_page=25, max_pages=None, resume=True)
    
    # OPTION 3: Import specific number of pages
    # import_all_pages(page_size=100, start_page=1, max_pages=100, resume=False)
    
    # Show final stats
    get_database_stats()