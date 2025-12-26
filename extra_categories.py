from db import DB
import json

with DB() as db:
    # Get all categories from database
    db_categories = db.categories.all()
    db_cat_names = [c.name for c in db_categories]
    
    # Get categories from JSON
    with open('categories.json', 'r') as f:
        json_cats = json.load(f)
    
    json_cat_names = list(json_cats.keys())
    
    # Find extras
    extras = set(db_cat_names) - set(json_cat_names)
    missing = set(json_cat_names) - set(db_cat_names)
    
    print(f"Total in DB: {len(db_cat_names)}")
    print(f"Total in JSON: {len(json_cat_names)}")
    print(f"\nExtra categories in DB (not in JSON):")
    for cat in extras:
        print(f"  - {cat}")
    
    print(f"\nMissing categories in DB (in JSON but not DB):")
    for cat in missing:
        print(f"  - {cat}")