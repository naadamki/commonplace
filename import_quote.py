import json
import time
import os
from quote import quote
from models import Session, Quote, Category, Author

session = Session()

# Progress tracking file
PROGRESS_FILE = 'import_quote_package_progress.json'

def save_progress(last_category_index, last_search_offset, total_imported, total_failed, total_skipped):
    """Save import progress to file"""
    progress = {
        'last_category_index': last_category_index,
        'last_search_offset': last_search_offset,
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
    """Load categories from JSON file and ensure they're in database"""
    with open('categories.json', 'r') as f:
        categories_data = json.load(f)
    
    category_names = []
    for name, keywords in categories_data.items():
        category = session.query(Category).filter_by(name=name).first()
        if not category:
            category = Category(name=name)
            category.set_keywords(keywords)
            session.add(category)
        category_names.append(name)
    
    session.commit()
    return category_names

def get_or_create_author(author_name):
    """Get existing author or create new one"""
    if not author_name or author_name.strip() == "":
        author_name = "Unknown"
    
    # Clean up author name
    author_name = author_name.strip()
    
    author = session.query(Author).filter_by(name=author_name).first()
    if not author:
        author = Author(name=author_name)
        session.add(author)
        session.commit()
    return author

def categorize_quote_obj(quote_obj):
    """Automatically assign categories based on keywords"""
    if not quote_obj.text:
        return
    
    quote_lower = quote_obj.text.lower()
    categories = session.query(Category).all()
    
    for category in categories:
        keywords = category.get_keywords()
        if any(keyword in quote_lower for keyword in keywords):
            if category not in quote_obj.categories:
                quote_obj.categories.append(category)

def quote_exists(quote_text):
    """Check if a quote already exists in the database by text"""
    return session.query(Quote).filter_by(text=quote_text).first() is not None

def import_quote_result(result_data):
    """Import a single quote from the quote package result"""
    if not result_data:
        return None
    
    quote_text = result_data.get('quote', '').strip()
    if not quote_text:
        return None
    
    # Check if quote already exists
    if quote_exists(quote_text):
        return None  # Return None for duplicates
    
    # Get or create author
    author_name = result_data.get('author', 'Unknown')
    author = get_or_create_author(author_name)
    
    # Get source from 'book' field
    source = result_data.get('book', '')
    if source:
        source = f"{source} (via quote package)"
    else:
        source = "quote package"
    
    # Create quote
    quote_obj = Quote(
        text=quote_text,
        author=author,
        source=source
    )
    
    # Auto-categorize based on keywords
    categorize_quote_obj(quote_obj)
    
    session.add(quote_obj)
    
    return quote_obj

def search_and_import(search_term, limit=1000):
    """
    Search for quotes using a term and import results
    
    Args:
        search_term: The term to search for
        limit: Maximum number of results to request
    
    Returns:
        Dictionary with success, skip, and error counts
    """
    print(f"\nSearching for '{search_term}' (limit: {limit})...")
    
    try:
        # Use the quote package to search
        results = quote(search_term, limit=limit)
        
        if not results:
            print(f"  No results found for '{search_term}'")
            return {'success': 0, 'skip': 0, 'error': 0, 'no_results': True}
        
        print(f"  Found {len(results)} results for '{search_term}'")
        
        success_count = 0
        skip_count = 0
        
        for result in results:
            imported = import_quote_result(result)
            if imported:
                success_count += 1
            else:
                skip_count += 1
        
        # Commit all quotes from this search at once
        try:
            session.commit()
            print(f"  ✓ '{search_term}': Added {success_count}, Skipped {skip_count} duplicates")
        except Exception as e:
            session.rollback()
            print(f"  ✗ Error committing '{search_term}': {e}")
            return {'success': 0, 'skip': skip_count, 'error': success_count, 'no_results': False}
        
        return {'success': success_count, 'skip': skip_count, 'error': 0, 'no_results': False}
    
    except Exception as e:
        print(f"  ✗ Error searching for '{search_term}': {e}")
        return {'success': 0, 'skip': 0, 'error': 1, 'no_results': False}

def import_by_categories(limit_per_search=1000, resume=False):
    """
    Import quotes by searching for each category name
    
    Args:
        limit_per_search: Maximum results per category search
        resume: Whether to resume from last saved progress
    """
    
    # Load category names
    category_names = load_categories()
    print(f"\nLoaded {len(category_names)} categories to search")
    
    # Initialize stats
    total_imported = 0
    total_skipped = 0
    total_failed = 0
    start_index = 0
    
    # Check for resume
    if resume:
        progress = load_progress()
        if progress:
            start_index = progress.get('last_category_index', 0) + 1
            total_imported = progress.get('total_imported', 0)
            total_failed = progress.get('total_failed', 0)
            total_skipped = progress.get('total_skipped', 0)
            print(f"\n{'='*60}")
            print(f"RESUMING FROM PREVIOUS SESSION")
            print(f"{'='*60}")
            print(f"Last category index: {progress.get('last_category_index', 0)}")
            print(f"Previously imported: {total_imported:,}")
            print(f"Previously skipped: {total_skipped:,}")
            print(f"Previously failed: {total_failed:,}")
            print(f"Resuming from category index: {start_index}")
            print(f"{'='*60}\n")
        else:
            print("No progress file found. Starting fresh import.")
    else:
        clear_progress()
    
    try:
        for idx, category_name in enumerate(category_names[start_index:], start=start_index):
            print(f"\n[{idx + 1}/{len(category_names)}] Processing category: {category_name}")
            
            # Search for quotes with this category name
            result = search_and_import(category_name.lower(), limit=limit_per_search)
            
            # Update stats
            total_imported += result['success']
            total_skipped += result['skip']
            total_failed += result['error']
            
            # Save progress after each category
            save_progress(idx, 0, total_imported, total_failed, total_skipped)
            
            # Display running totals
            print(f"  Running totals - Imported: {total_imported:,}, Skipped: {total_skipped:,}, Failed: {total_failed}")
            
            # Small delay between searches to be respectful
            time.sleep(1)
    
    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print("IMPORT INTERRUPTED BY USER")
        print(f"{'='*60}")
        print(f"Progress has been saved.")
        print(f"Run with resume=True to continue")
        print(f"{'='*60}\n")
        return
    
    except Exception as e:
        print(f"\n\n{'='*60}")
        print(f"UNEXPECTED ERROR: {e}")
        print(f"{'='*60}")
        print(f"Progress has been saved.")
        print(f"{'='*60}\n")
        return
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"IMPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"Categories searched: {len(category_names)}")
    print(f"Successfully imported: {total_imported:,}")
    print(f"Skipped (duplicates): {total_skipped:,}")
    print(f"Failed: {total_failed:,}")
    print(f"{'='*60}\n")
    
    # Clear progress file after successful completion
    print("Import fully completed! Clearing progress file...")
    clear_progress()

def import_by_custom_terms(search_terms, limit_per_search=1000):
    """
    Import quotes by searching for custom terms
    
    Args:
        search_terms: List of terms to search for
        limit_per_search: Maximum results per search
    """
    
    total_imported = 0
    total_skipped = 0
    total_failed = 0
    
    print(f"\nSearching for {len(search_terms)} custom terms...")
    
    try:
        for idx, term in enumerate(search_terms, start=1):
            print(f"\n[{idx}/{len(search_terms)}] Searching: {term}")
            
            result = search_and_import(term, limit=limit_per_search)
            
            total_imported += result['success']
            total_skipped += result['skip']
            total_failed += result['error']
            
            print(f"  Running totals - Imported: {total_imported:,}, Skipped: {total_skipped:,}")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print(f"\n\nImport interrupted. Stats so far:")
        print(f"Imported: {total_imported:,}, Skipped: {total_skipped:,}, Failed: {total_failed}")
        return
    
    print(f"\n{'='*60}")
    print(f"Custom term import complete!")
    print(f"Successfully imported: {total_imported:,}")
    print(f"Skipped (duplicates): {total_skipped:,}")
    print(f"Failed: {total_failed:,}")
    print(f"{'='*60}\n")

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
        
        # Load categories to show which one we're on
        with open('categories.json', 'r') as f:
            categories_data = json.load(f)
        category_names = list(categories_data.keys())
        
        last_idx = progress.get('last_category_index', 0)
        next_idx = last_idx + 1
        
        print(f"\n{'='*60}")
        print(f"SAVED PROGRESS FOUND")
        print(f"{'='*60}")
        print(f"Last category: {category_names[last_idx] if last_idx < len(category_names) else 'N/A'}")
        print(f"Next category: {category_names[next_idx] if next_idx < len(category_names) else 'Done'}")
        print(f"Categories completed: {last_idx + 1}/{len(category_names)}")
        print(f"Total imported: {progress.get('total_imported', 0):,}")
        print(f"Total skipped: {progress.get('total_skipped', 0):,}")
        print(f"Total failed: {progress.get('total_failed', 0):,}")
        print(f"Last updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
    else:
        print("\nNo saved progress found.")

if __name__ == "__main__":
    print("="*60)
    print("QUOTE PACKAGE IMPORTER")
    print("="*60)
    
    # Show current stats
    get_database_stats()
    
    # Check for saved progress
    show_progress_info()
    
    # Choose your import strategy:
    
    # OPTION 1: Import by searching all category names (RECOMMENDED)
    print("\nStarting import by category search...")
    import_by_categories(limit_per_search=1000, resume=True)
    
    # OPTION 2: Import by custom search terms
    # custom_terms = ['motivation', 'inspiration', 'wisdom', 'philosophy']
    # import_by_custom_terms(custom_terms, limit_per_search=1000)
    
    # OPTION 3: Single test search
    # result = search_and_import('courage', limit=100)
    # print(result)
    
    # Show final stats
    get_database_stats()