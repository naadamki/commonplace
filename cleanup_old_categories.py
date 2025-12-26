"""Remove old categories - with timeout and progress"""

from db import DB
import time

def cleanup_old_categories():
    """Remove Living, Excellence, and Today categories"""
    
    categories_to_remove = ['Living', 'Excellence', 'Today']
    
    with DB() as db:
        print("Starting cleanup...\n")
        
        for cat_name in categories_to_remove:
            print(f"Looking up '{cat_name}'...", end=' ', flush=True)
            start = time.time()
            
            cat = db.categories.get_by_name(cat_name)
            
            if cat:
                quote_count = len(cat.quotes)
                print(f"Found! ({quote_count:,} quotes)")
                
                print(f"  Deleting '{cat_name}'...", end=' ', flush=True)
                db.session.delete(cat)
                elapsed = time.time() - start
                print(f"Done in {elapsed:.2f}s")
            else:
                print(f"Not found")
        
        print("\nCommitting changes...", end=' ', flush=True)
        start = time.time()
        db.commit()
        elapsed = time.time() - start
        print(f"Done in {elapsed:.2f}s")
        
        print(f"\n✓ Cleanup complete!")
        print(f"Categories remaining: {db.categories.count()}")

if __name__ == "__main__":
    cleanup_old_categories()