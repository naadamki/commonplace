"""
Recategorize all existing quotes with updated categories.
"""

from models import Session, Quote, Category
import json
from datetime import datetime

def load_categories_from_json():
    """Load categories from JSON file"""
    with open('categories.json', 'r') as f:
        return json.load(f)

def update_database_categories():
    """Update categories in database from JSON"""
    session = Session()
    categories_data = load_categories_from_json()
    
    print(f"\nLoading {len(categories_data)} categories into database...")
    
    for name, keywords in categories_data.items():
        category = session.query(Category).filter_by(name=name).first()
        
        if not category:
            # Create new category
            category = Category(name=name)
            session.add(category)
            print(f"  + Created: {name}")
        
        # Always update keywords
        category.set_keywords(keywords)
    
    session.commit()
    print("✓ Categories updated in database\n")
    session.close()

def recategorize_all():
    """Recategorize all quotes"""
    session = Session()
    
    # Get all categories
    all_categories = session.query(Category).all()
    print(f"Using {len(all_categories)} categories\n")
    
    # Get total quotes
    total = session.query(Quote).count()
    print(f"Found {total:,} quotes to process\n")
    
    if total == 0:
        print("No quotes found!")
        session.close()
        return
    
    # Confirm
    response = input(f"Recategorize {total:,} quotes? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        session.close()
        return
    
    print("\nProcessing quotes...\n")
    
    start = datetime.now()
    processed = 0
    updated = 0
    new_cats_added = 0
    
    # Process in batches
    batch_size = 500
    offset = 0
    
    while offset < total:
        # Get batch
        quotes = session.query(Quote).limit(batch_size).offset(offset).all()
        
        if not quotes:
            break
        
        # Process each quote
        for quote in quotes:
            if not quote.text:
                processed += 1
                continue
            
            quote_lower = quote.text.lower()
            original_count = len(quote.categories)
            
            # Check each category
            for category in all_categories:
                keywords = category.get_keywords()
                
                # If any keyword matches and category not already assigned
                if any(keyword in quote_lower for keyword in keywords):
                    if category not in quote.categories:
                        quote.categories.append(category)
                        new_cats_added += 1
            
            # Track if quote was updated
            if len(quote.categories) > original_count:
                updated += 1
            
            processed += 1
            
            # Progress update
            if processed % 1000 == 0:
                elapsed = (datetime.now() - start).total_seconds()
                rate = processed / elapsed if elapsed > 0 else 0
                print(f"  {processed:,}/{total:,} ({processed/total*100:.1f}%) - {rate:.0f} quotes/sec")
        
        # Commit batch
        try:
            session.commit()
        except Exception as e:
            print(f"Error: {e}")
            session.rollback()
        
        offset += batch_size
    
    # Final stats
    elapsed = (datetime.now() - start).total_seconds()
    
    print(f"\n{'='*60}")
    print(f"COMPLETE!")
    print(f"{'='*60}")
    print(f"Processed: {processed:,} quotes")
    print(f"Updated: {updated:,} quotes ({updated/processed*100:.1f}%)")
    print(f"New categories added: {new_cats_added:,}")
    print(f"Time: {elapsed/60:.1f} minutes ({processed/elapsed:.0f} quotes/sec)")
    print(f"{'='*60}\n")
    
    session.close()

def show_stats():
    """Show category statistics"""
    session = Session()
    categories = session.query(Category).all()
    
    print(f"\n{'='*60}")
    print(f"CATEGORY STATISTICS")
    print(f"{'='*60}\n")
    
    stats = []
    for cat in categories:
        stats.append({
            'name': cat.name,
            'count': len(cat.quotes),
            'keywords': len(cat.get_keywords())
        })
    
    # Sort by count
    stats.sort(key=lambda x: x['count'], reverse=True)
    
    print("Top 15 categories:\n")
    for i, s in enumerate(stats[:15], 1):
        print(f"{i:2}. {s['name']:<20} {s['count']:>8,} quotes ({s['keywords']} keywords)")
    
    print("\nBottom 10 categories:\n")
    for i, s in enumerate(stats[-10:], len(stats)-9):
        print(f"{i:2}. {s['name']:<20} {s['count']:>8,} quotes ({s['keywords']} keywords)")
    
    # Empty categories
    empty = [s['name'] for s in stats if s['count'] == 0]
    if empty:
        print(f"\nCategories with 0 quotes: {', '.join(empty)}")
    
    print(f"\n{'='*60}\n")
    
    session.close()

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("QUOTE RECATEGORIZATION")
    print("="*60)
    
    # Check for command
    if len(sys.argv) > 1 and sys.argv[1] == 'stats':
        show_stats()
        sys.exit(0)
    
    # Main process
    print("\nSteps:")
    print("1. Update categories from categories.json")
    print("2. Recategorize all quotes with new keywords")
    print("3. Show statistics\n")
    
    # Step 1: Update categories
    update_database_categories()
    
    # Step 2: Show current stats
    show_stats()
    
    # Step 3: Recategorize
    recategorize_all()
    
    # Step 4: Show new stats
    show_stats()