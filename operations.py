"""
Complete examples of how to use the refactored database layer.
Shows CRUD operations, favorites, searching, and error handling.
"""

from db import DB, ValidationError, NotFoundError, DuplicateError
from models import Quote, Author, Category

# ============================================================================
# QUOTES: CREATE, READ, UPDATE, DELETE
# ============================================================================

def quote_examples():
    """Examples of working with quotes"""
    
    with DB() as db:
        # ===== RETRIEVE QUOTES =====
        
        # Get a specific quote by ID
        try:
            quote = db.quotes.get_or_raise(1)
            print(f"Quote: {quote.text}")
            print(f"Author: {quote.author.name}")
            print(f"Categories: {[c.name for c in quote.categories]}")
        except NotFoundError:
            print("Quote not found")
        
        # Get all quotes
        all_quotes = db.quotes.all()
        print(f"Total quotes in database: {len(all_quotes)}")
        
        # Search quotes by text
        quotes = db.quotes.search(text="courage", limit=10)
        print(f"Found {len(quotes)} quotes about courage")
        
        # Search with multiple terms (ANY match)
        quotes = db.quotes.search(text=["courage", "brave"], limit=5)
        
        # Search with multiple terms (ALL must match)
        quotes = db.quotes.search(text=["courage", "fear"], match_all_text=True)
        
        # Search by author
        quotes = db.quotes.by_author("Einstein", limit=5)
        
        # Search by category
        quotes = db.quotes.by_category("Success", limit=10)
        
        # Advanced search with scoring (most relevant first)
        quotes = db.quotes.advanced_search(
            text_terms=["success", "failure"],
            categories="Work",
            author="Jobs",
            limit=5
        )
        
        # Get random quotes
        random_quote = db.quotes.random()  # Single quote
        random_quotes = db.quotes.random(count=5)  # 5 random quotes
        random_from_category = db.quotes.random(category="Courage", count=3)
        
        # Get quotes by length
        short_quotes = db.quotes.shortest(limit=10)
        long_quotes = db.quotes.longest(limit=10)
        
        # Get most favorited quotes
        top_quotes = db.quotes.most_favorited(limit=10)
        for item in top_quotes:
            quote = item['quote']
            favorites = item['favorites']
            print(f"{quote.text} - Favorited {favorites} times")
        
        # Get recently added quotes
        recent = db.quotes.recent(limit=10)
        
        # ===== CREATE QUOTE =====
        
        # First, get or create author
        author = db.authors.get_or_create("Steve Jobs")
        
        # Get category
        try:
            category = db.categories.get_by_name("Success")
        except ValidationError:
            print("Invalid category name")
        
        # Create a new quote
        new_quote = Quote(
            text="The only way to do great work is to love what you do.",
            author=author,
            year=1997,
            source="Stanford Commencement",
            verified=True
        )
        new_quote.categories.append(category)
        new_quote.set_tags(["work", "passion", "success"])
        
        db.session.add(new_quote)
        db.commit()
        print(f"Created quote with ID: {new_quote.id}")
        
        # ===== UPDATE QUOTE =====
        
        quote = db.quotes.get_or_raise(1)
        quote.text = "Updated quote text"
        quote.verified = True
        db.commit()
        
        # Add categories to existing quote
        category = db.categories.get_by_name("Inspiration")
        if category and category not in quote.categories:
            quote.categories.append(category)
            db.commit()
        
        # Update tags
        quote.set_tags(["wisdom", "life", "inspiration"])
        db.commit()
        
        # ===== MARK FOR EDITING =====
        
        db.quotes.mark_for_edit(1)  # Mark quote 1 for review
        db.quotes.unmark_for_edit(1)  # Unmark it
        
        # Get quotes that need editing
        needs_edit = db.quotes.needs_edit(limit=10)
        
        # Count quotes needing edits
        count = db.quotes.count_needs_edit()
        
        # ===== DELETE QUOTE =====
        
        quote = db.quotes.get_or_raise(1)
        db.session.delete(quote)
        db.commit()
        print("Quote deleted")


# ============================================================================
# AUTHORS: CREATE, READ, UPDATE, DELETE
# ============================================================================

def author_examples():
    """Examples of working with authors"""
    
    with DB() as db:
        # ===== RETRIEVE AUTHORS =====
        
        # Get author by ID
        try:
            author = db.authors.get_or_raise(1)
            print(f"Author: {author.name}")
        except NotFoundError:
            print("Author not found")
        
        # Get author by exact name
        try:
            author = db.authors.get_by_name("Albert Einstein")
        except ValidationError:
            print("Invalid author name")
        
        # Search authors (partial match)
        authors = db.authors.search("Einstein")
        
        # Get all authors
        all_authors = db.authors.all()
        
        # Get most quoted authors
        top_authors = db.authors.top_quoted(limit=10)
        for item in top_authors:
            print(f"{item['author']}: {item['count']} quotes")
        
        # Count authors
        total = db.authors.count()
        
        # ===== CREATE AUTHOR =====
        
        # Simple creation (returns existing if already present)
        author = db.authors.get_or_create("Marie Curie")
        
        # Or create with more details
        author = Author(
            name="Alan Turing",
            birth_year=1912,
            death_year=1954,
            nationality="British",
            profession="Computer Scientist",
            bio="Pioneer of theoretical computer science and AI"
        )
        db.session.add(author)
        db.commit()
        print(f"Created author with ID: {author.id}")
        
        # ===== UPDATE AUTHOR =====
        
        author = db.authors.get_or_raise(1)
        author.bio = "Updated biography"
        author.nationality = "American"
        db.commit()
        
        # ===== MARK FOR EDITING =====
        
        db.authors.mark_for_edit(1)
        db.authors.unmark_for_edit(1)
        
        # Get authors needing editing
        needs_edit = db.authors.needs_edit(limit=10)
        
        # ===== DELETE AUTHOR =====
        
        # This will cascade delete all their quotes!
        author = db.authors.get_or_raise(1)
        db.session.delete(author)
        db.commit()
        print("Author deleted (and all their quotes)")


# ============================================================================
# USERS: MANAGE ACCOUNTS
# ============================================================================

def user_examples():
    """Examples of working with users"""
    
    with DB() as db:
        # ===== CREATE USER =====
        
        try:
            user = db.users.create(
                username="john_doe",
                email="john@example.com",
                password="SecurePassword123"
            )
            print(f"User created: {user.username}")
        except ValidationError as e:
            print(f"Invalid input: {e}")
        except DuplicateError:
            print("Username or email already exists")
        
        # ===== RETRIEVE USER =====
        
        # Get by ID
        try:
            user = db.users.get_or_raise(1)
        except NotFoundError:
            print("User not found")
        
        # Get by username
        try:
            user = db.users.get_by_username("john_doe")
        except ValidationError:
            print("Invalid username")
        
        # Get by email
        try:
            user = db.users.get_by_email("john@example.com")
        except ValidationError:
            print("Invalid email")
        
        # Get all users
        all_users = db.users.all()
        
        # Count users
        total = db.users.count()
        
        # ===== AUTHENTICATION =====
        
        # Authenticate user (returns None if failed)
        user = db.users.authenticate("john_doe", "SecurePassword123")
        if user:
            print(f"Authentication successful for {user.username}")
            print(f"Last login: {user.last_login}")
        else:
            print("Invalid credentials")
        
        # ===== UPDATE USER =====
        
        user = db.users.get_or_raise(1)
        
        # Change password
        try:
            db.users.update_password(user, "NewPassword456")
            print("Password updated")
        except ValidationError as e:
            print(f"Invalid password: {e}")
        
        # Deactivate account
        db.users.deactivate(user)
        print("User deactivated")
        
        # Reactivate account
        db.users.activate(user)
        print("User activated")
        
        # ===== DELETE USER =====
        
        user = db.users.get_or_raise(1)
        db.session.delete(user)
        db.commit()
        print("User deleted")


# ============================================================================
# FAVORITES: ADD & REMOVE QUOTES AND AUTHORS
# ============================================================================

def favorites_examples():
    """Examples of working with favorites"""
    
    with DB() as db:
        # Get a user
        user = db.users.get_by_username("john_doe")
        
        # ===== ADD FAVORITE QUOTE =====
        
        try:
            quote = db.quotes.get_or_raise(5)
            db.favorites.add(user, quote.id, item_type='quote')
            print(f"Added quote to favorites")
        except NotFoundError as e:
            print(f"Error: {e}")
        except DuplicateError:
            print("Quote is already in favorites")
        
        # ===== ADD FAVORITE AUTHOR =====
        
        try:
            author = db.authors.get_or_raise(3)
            db.favorites.add(user, author.id, item_type='author')
            print("Added author to favorites")
        except NotFoundError as e:
            print(f"Error: {e}")
        except DuplicateError:
            print("Author is already in favorites")
        
        # ===== CHECK IF FAVORITED =====
        
        try:
            is_fav = db.favorites.is_favorited(user, 5, item_type='quote')
            print(f"Quote is favorited: {is_fav}")
        except NotFoundError as e:
            print(f"Error: {e}")
        
        # ===== GET FAVORITE QUOTES =====
        
        favorite_quotes = db.favorites.get(user, item_type='quote')
        print(f"User has {len(favorite_quotes)} favorite quotes")
        for quote in favorite_quotes:
            print(f"  - {quote.text[:50]}...")
        
        # Get limited number
        recent_favorites = db.favorites.get(user, item_type='quote', limit=5)
        
        # ===== GET FAVORITE AUTHORS =====
        
        favorite_authors = db.favorites.get(user, item_type='author')
        print(f"User has {len(favorite_authors)} favorite authors")
        for author in favorite_authors:
            print(f"  - {author.name}")
        
        # ===== COUNT FAVORITES =====
        
        quote_count = db.favorites.count(user, item_type='quote')
        author_count = db.favorites.count(user, item_type='author')
        print(f"Favorites: {quote_count} quotes, {author_count} authors")
        
        # ===== REMOVE FROM FAVORITES =====
        
        try:
            quote = db.quotes.get_or_raise(5)
            db.favorites.remove(user, quote.id, item_type='quote')
            print("Removed quote from favorites")
        except NotFoundError as e:
            print(f"Error: {e}")
        
        try:
            author = db.authors.get_or_raise(3)
            db.favorites.remove(user, author.id, item_type='author')
            print("Removed author from favorites")
        except NotFoundError as e:
            print(f"Error: {e}")
        
        # ===== GET MOST FAVORITED ITEMS =====
        
        # Most favorited quotes
        top_quotes = db.favorites.get_most(item_type='quote', limit=10)
        for item in top_quotes:
            quote = item['quote']
            count = item['favorites']
            print(f"{quote.text[:40]}... - {count} favorites")
        
        # Most favorited authors
        top_authors = db.favorites.get_most(item_type='author', limit=10)
        for item in top_authors:
            author = item['author']
            count = item['favorites']
            print(f"{author.name} - {count} favorites")


# ============================================================================
# CATEGORIES: MANAGE QUOTE CATEGORIES
# ============================================================================

def category_examples():
    """Examples of working with categories"""
    
    with DB() as db:
        # ===== RETRIEVE CATEGORIES =====
        
        # Get category by ID
        try:
            category = db.categories.get_or_raise(1)
            print(f"Category: {category.name}")
        except NotFoundError:
            print("Category not found")
        
        # Get by name
        try:
            category = db.categories.get_by_name("Success")
        except ValidationError:
            print("Invalid category name")
        
        # Get all categories
        all_categories = db.categories.all()
        
        # Get categories with quote counts
        categories_with_counts = db.categories.with_counts()
        for cat in categories_with_counts:
            print(f"{cat['category']}: {cat['count']} quotes")
        
        # Get most popular categories
        popular = db.categories.most_popular(limit=10)
        
        # ===== CREATE CATEGORY =====
        
        category = Category(name="Wisdom")
        category.set_keywords(["knowledge", "wise", "understanding", "insight"])
        db.session.add(category)
        db.commit()
        print(f"Created category: {category.name}")
        
        # ===== UPDATE CATEGORY =====
        
        category = db.categories.get_or_raise(1)
        category.set_keywords(["new", "keywords", "here"])
        db.commit()
        
        # ===== DELETE CATEGORY =====
        
        category = db.categories.get_or_raise(1)
        # This removes the association but doesn't delete quotes
        db.session.delete(category)
        db.commit()
        print("Category deleted")


# ============================================================================
# COMPLEX OPERATIONS
# ============================================================================

def complex_examples():
    """More complex, real-world examples"""
    
    with DB() as db:
        # ===== CREATE COMPLETE QUOTE WITH AUTHOR AND CATEGORIES =====
        
        try:
            # Get or create author
            author = db.authors.get_or_create("Nelson Mandela")
            
            # Get categories
            courage_cat = db.categories.get_by_name("Courage")
            freedom_cat = db.categories.get_by_name("Freedom")
            
            # Create quote
            quote = Quote(
                text="I learned that courage was not the absence of fear, but the triumph over it.",
                author=author,
                year=1994,
                source="Long Walk to Freedom",
                verified=True
            )
            quote.categories.extend([courage_cat, freedom_cat])
            quote.set_tags(["courage", "fear", "triumph"])
            
            db.session.add(quote)
            db.commit()
            
            print(f"Created comprehensive quote with ID: {quote.id}")
        
        except (NotFoundError, ValidationError, DuplicateError) as e:
            print(f"Error creating quote: {e}")
            db.rollback()
        
        # ===== USER WORKFLOW: SIGNUP, BROWSE, FAVORITE, VIEW FAVORITES =====
        
        try:
            # 1. Create new user
            user = db.users.create(
                username="alice",
                email="alice@example.com",
                password="AlicePassword123"
            )
            print(f"User {user.username} created")
            
            # 2. Search for quotes
            quotes = db.quotes.advanced_search(
                text_terms=["courage"],
                categories="Courage",
                limit=5
            )
            print(f"Found {len(quotes)} courage quotes")
            
            # 3. Add favorites
            for quote in quotes[:3]:
                try:
                    db.favorites.add(user, quote.id, item_type='quote')
                    print(f"Favorited: {quote.text[:50]}...")
                except DuplicateError:
                    pass  # Already favorited
            
            # 4. View favorites
            favorites = db.favorites.get(user, item_type='quote')
            print(f"User has {len(favorites)} favorite quotes")
            
        except (ValidationError, DuplicateError) as e:
            print(f"Error in workflow: {e}")
            db.rollback()
        
        # ===== BULK OPERATIONS =====
        
        # Mark multiple quotes for review
        problem_quotes = db.quotes.search(text="review_me", limit=20)
        for quote in problem_quotes:
            db.quotes.mark_for_edit(quote.id)
        print(f"Marked {len(problem_quotes)} quotes for editing")
        
        # Get all items needing edit
        quotes_to_edit = db.quotes.needs_edit(limit=50)
        authors_to_edit = db.authors.needs_edit(limit=50)
        print(f"Quotes to edit: {len(quotes_to_edit)}")
        print(f"Authors to edit: {len(authors_to_edit)}")
        
        # ===== DATABASE STATISTICS =====
        
        stats = db.get_stats()
        print(f"\n=== Database Statistics ===")
        print(f"Total Quotes: {stats['total_quotes']}")
        print(f"Total Authors: {stats['total_authors']}")
        print(f"Total Users: {stats['total_users']}")
        print(f"Total Categories: {stats['total_categories']}")


# ============================================================================
# ERROR HANDLING PATTERNS
# ============================================================================

def error_handling_examples():
    """Best practices for error handling"""
    
    with DB() as db:
        # Pattern 1: Try/except with specific exceptions
        try:
            user = db.users.get_or_raise(999)
        except NotFoundError:
            print("User doesn't exist")
        
        # Pattern 2: Using optional get() and checking for None
        user = db.users.get(999)
        if user is None:
            print("User doesn't exist")
        
        # Pattern 3: Catching validation errors
        try:
            user = db.users.create("ab", "bad", "pwd")
        except ValidationError as e:
            print(f"Validation failed: {e}")
        
        # Pattern 4: Catching duplicate errors
        try:
            user = db.users.create("john", "john@example.com", "password")
        except DuplicateError:
            print("User already exists")
        
        # Pattern 5: Chaining operations with error handling
        try:
            user = db.users.get_or_raise(1)
            quote = db.quotes.get_or_raise(5)
            db.favorites.add(user, quote.id)
            print("Successfully added favorite")
        except (NotFoundError, DuplicateError) as e:
            print(f"Operation failed: {e}")
            db.rollback()


if __name__ == "__main__":
    # Run examples
    print("=" * 80)
    print("QUOTE EXAMPLES")
    print("=" * 80)
    quote_examples()
    
    print("\n" + "=" * 80)
    print("USER & FAVORITES EXAMPLES")
    print("=" * 80)
    user_examples()
    favorites_examples()
    
    print("\n" + "=" * 80)
    print("COMPLEX EXAMPLES")
    print("=" * 80)
    complex_examples()