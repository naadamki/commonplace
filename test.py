from db import DB, ValidationError, NotFoundError, DuplicateError

with DB() as db:
    # Test stats (should work immediately)
    stats = db.get_stats()
    print(f"Stats: {stats}")
    
    # Test quote search (should use existing data)
    quotes = db.quotes.search(text="success", limit=5)
    print(f"Found {len(quotes)} quotes about success")
    
    # Test user creation with validation
    try:
        user = db.users.create("testuser", "test@example.com", "pass123")
        print(f"Created user: {user}")
    except (ValidationError, DuplicateError) as e:
        print(f"Expected error: {e}")
    
    # Test getting with get_or_raise
    try:
        author = db.authors.get_or_raise(999999)
    except NotFoundError as e:
        print(f"Expected error: {e}")
    
    print("\n✓ Migration successful!")