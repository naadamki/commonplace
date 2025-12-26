"""Check which categories have no quotes and why"""

from models import Session, Quote, Category
import json

session = Session()

print("\n" + "="*60)
print("EMPTY CATEGORIES ANALYSIS")
print("="*60 + "\n")

# Get all categories
categories = session.query(Category).all()

# Find empty ones
empty_cats = []
for cat in categories:
    if len(cat.quotes) == 0:
        empty_cats.append(cat)

print(f"Found {len(empty_cats)} categories with 0 quotes:\n")

for cat in empty_cats:
    keywords = cat.get_keywords()
    print(f"📂 {cat.name}")
    print(f"   Keywords: {', '.join(keywords[:10])}")
    if len(keywords) > 10:
        print(f"   ... and {len(keywords) - 10} more")
    
    # Test if keywords would match ANY quotes
    matching_quotes = 0
    for keyword in keywords[:5]:  # Just test first 5 keywords
        count = session.query(Quote).filter(
            Quote.text.ilike(f'%{keyword}%')
        ).count()
        if count > 0:
            print(f"   ⚠️  Found {count:,} quotes containing '{keyword}'")
            matching_quotes += count
    
    if matching_quotes == 0:
        print(f"   ℹ️  No quotes found with tested keywords")
    
    print()

# Check if these are the new categories
with open('categories.json', 'r') as f:
    json_cats = json.load(f)

json_cat_names = set(json_cats.keys())
db_cat_names = set([c.name for c in categories])

new_cats = json_cat_names - db_cat_names
missing_cats = db_cat_names - json_cat_names

if new_cats:
    print(f"\n📥 Categories in JSON but NOT in database:")
    for cat in new_cats:
        print(f"   - {cat}")

if missing_cats:
    print(f"\n📤 Categories in database but NOT in JSON:")
    for cat in missing_cats:
        print(f"   - {cat}")

print("\n" + "="*60)

session.close()