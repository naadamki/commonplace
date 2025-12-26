# First, set up your session
from models import Session, Quote, Category, Author, User
from sqlalchemy import func, or_, and_

session = Session()

# ===== SEARCH BY WORDS IN QUOTE TEXT =====

# Contains a specific word (case-insensitive)
courage_quotes = session.query(Quote).filter(Quote.text.ilike('%courage%')).all()

# Contains multiple words (OR - either word)
quotes = session.query(Quote).filter(
    or_(
        Quote.text.ilike('%love%'),
        Quote.text.ilike('%happiness%')
    )
).all()

# Contains multiple words (AND - both words)
quotes = session.query(Quote).filter(
    and_(
        Quote.text.ilike('%courage%'),
        Quote.text.ilike('%fear%')
    )
).all()

# Shorter way for AND
quotes = session.query(Quote).filter(
    Quote.text.ilike('%courage%'),
    Quote.text.ilike('%fear%')
).all()


# ===== SEARCH BY CATEGORY =====

# Get quotes in a specific category
category = session.query(Category).filter_by(name='Courage').first()
courage_quotes = category.quotes
print(f"Found {len(courage_quotes)} quotes about Courage")

# Print them
for quote in courage_quotes[:5]:  # First 5
    print(f"'{quote.text}' - {quote.author.name}")

# Get quotes in multiple categories (OR)
categories = session.query(Category).filter(
    Category.name.in_(['Courage', 'Fear', 'Success'])
).all()

quotes_in_categories = []
for cat in categories:
    quotes_in_categories.extend(cat.quotes)

# Remove duplicates if a quote is in multiple categories
unique_quotes = list(set(quotes_in_categories))

# Better way - get quotes that have ANY of these categories
quotes = session.query(Quote).join(Quote.categories).filter(
    Category.name.in_(['Courage', 'Fear', 'Success'])
).distinct().all()


# ===== SEARCH BY AUTHOR =====

# Exact author name
author = session.query(Author).filter_by(name='Steve Jobs').first()
if author:
    steve_quotes = author.quotes
    print(f"Steve Jobs has {len(steve_quotes)} quotes")
    for q in steve_quotes:
        print(f"  - {q.text[:60]}...")

# Partial author name match (contains)
authors = session.query(Author).filter(Author.name.ilike('%einstein%')).all()
for author in authors:
    print(f"{author.name}: {len(author.quotes)} quotes")

# Get all quotes by these authors
einstein_quotes = []
for author in authors:
    einstein_quotes.extend(author.quotes)

# Better way - query quotes directly by author name
quotes = session.query(Quote).join(Author).filter(
    Author.name.ilike('%einstein%')
).all()


# ===== COMBINED SEARCHES =====

# Quotes about "love" by a specific author
quotes = session.query(Quote).join(Author).filter(
    Author.name == 'Maya Angelou',
    Quote.text.ilike('%love%')
).all()

# Quotes in "Courage" category that contain "fear"
courage_cat = session.query(Category).filter_by(name='Courage').first()
quotes = session.query(Quote).join(Quote.categories).filter(
    Category.name == 'Courage',
    Quote.text.ilike('%fear%')
).all()

# Quotes by author in specific category
quotes = session.query(Quote).join(Author).join(Quote.categories).filter(
    Author.name.ilike('%Jobs%'),
    Category.name == 'Work'
).all()


# ===== USEFUL HELPER FUNCTION =====

def search_quotes(text=None, author=None, category=None, limit=None):
    """
    Flexible search function
    
    Args:
        text: Search for this text in quote
        author: Search by author name (partial match)
        category: Filter by category name
        limit: Maximum results to return
    """
    query = session.query(Quote)
    
    if author:
        query = query.join(Author).filter(Author.name.ilike(f'%{author}%'))
    
    if category:
        query = query.join(Quote.categories).filter(Category.name == category)
    
    if text:
        query = query.filter(Quote.text.ilike(f'%{text}%'))
    
    if limit:
        query = query.limit(limit)
    
    return query.all()

# Use the helper function
results = search_quotes(text='courage', author='Roosevelt', limit=10)
for q in results:
    print(f"'{q.text}' - {q.author.name}")

results = search_quotes(category='Love', author='Angelou')
results = search_quotes(text='dream')


# ===== COUNTING RESULTS =====

# Count instead of returning all
count = session.query(Quote).filter(Quote.text.ilike('%love%')).count()
print(f"Found {count:,} quotes containing 'love'")

# Count by category
courage_cat = session.query(Category).filter_by(name='Courage').first()
print(f"Courage category has {len(courage_cat.quotes)} quotes")


# ===== RANDOM RESULTS =====

# Get random quote containing a word
random_quote = session.query(Quote).filter(
    Quote.text.ilike('%courage%')
).order_by(func.random()).first()
print(f"Random courage quote: '{random_quote.text}'")


# ===== ORDERING RESULTS =====

# Alphabetically by author
quotes = session.query(Quote).join(Author).filter(
    Quote.text.ilike('%success%')
).order_by(Author.name).all()

# By quote length (shortest first)
quotes = session.query(Quote).filter(
    Quote.text.ilike('%life%')
).order_by(func.length(Quote.text)).limit(10).all()


# ===== PRETTY PRINT FUNCTION =====

def print_quotes(quotes, max_results=10):
    """Pretty print search results"""
    print(f"\nFound {len(quotes)} quotes. Showing first {min(len(quotes), max_results)}:\n")
    print("="*80)
    for i, q in enumerate(quotes[:max_results], 1):
        categories = [c.name for c in q.categories]
        print(f"\n{i}. \"{q.text}\"")
        print(f"   - {q.author.name}")
        if categories:
            print(f"   Categories: {', '.join(categories[:5])}")
    print("\n" + "="*80)

# Use it
results = search_quotes(text='courage', limit=50)
print_quotes(results)







def search_quotes(text=None, author=None, category=None, limit=None, match_all_text=False, match_all_categories=False):
    """
    Flexible search function with support for multiple terms and categories
    
    Args:
        text: String or list of strings to search for in quote text
        author: String to search by author name (partial match)
        category: String or list of category names to filter by
        limit: Maximum results to return
        match_all_text: If True, quote must contain ALL text terms (AND). If False, ANY term (OR)
        match_all_categories: If True, quote must be in ALL categories (AND). If False, ANY category (OR)
    
    Examples:
        # Single term
        search_quotes(text='courage')
        
        # Multiple text terms (OR - contains any)
        search_quotes(text=['courage', 'brave', 'fear'])
        
        # Multiple text terms (AND - contains all)
        search_quotes(text=['courage', 'fear'], match_all_text=True)
        
        # Multiple categories (OR - in any category)
        search_quotes(category=['Courage', 'Fear', 'Success'])
        
        # Multiple categories (AND - in all categories)
        search_quotes(category=['Love', 'Happiness'], match_all_categories=True)
        
        # Combined search
        search_quotes(text=['love', 'heart'], author='Angelou', category=['Love', 'Happiness'])
    """
    from sqlalchemy import and_, or_
    
    query = session.query(Quote)
    
    # Handle author search
    if author:
        query = query.join(Author).filter(Author.name.ilike(f'%{author}%'))
    
    # Handle category search
    if category:
        # Convert single category to list
        if isinstance(category, str):
            category = [category]
        
        if match_all_categories:
            # Quote must be in ALL specified categories
            for cat_name in category:
                query = query.join(Quote.categories, aliased=True).filter(Category.name == cat_name)
        else:
            # Quote must be in ANY of the specified categories (OR)
            query = query.join(Quote.categories).filter(Category.name.in_(category))
    
    # Handle text search
    if text:
        # Convert single text to list
        if isinstance(text, str):
            text = [text]
        
        if match_all_text:
            # Quote must contain ALL text terms (AND)
            for term in text:
                query = query.filter(Quote.text.ilike(f'%{term}%'))
        else:
            # Quote must contain ANY of the text terms (OR)
            text_conditions = [Quote.text.ilike(f'%{term}%') for term in text]
            query = query.filter(or_(*text_conditions))
    
    # Apply distinct to avoid duplicates when joining
    query = query.distinct()
    
    # Apply limit
    if limit:
        query = query.limit(limit)
    
    return query.all()


# ===== USAGE EXAMPLES =====

# Search for quotes containing "love" OR "heart"
results = search_quotes(text=['love', 'heart'])
print(f"Found {len(results)} quotes with 'love' OR 'heart'")

# Search for quotes containing "courage" AND "fear" (both must be present)
results = search_quotes(text=['courage', 'fear'], match_all_text=True)
print(f"Found {len(results)} quotes with both 'courage' AND 'fear'")

# Search in multiple categories (any category)
results = search_quotes(category=['Courage', 'Fear', 'Success'])
print(f"Found {len(results)} quotes in Courage, Fear, or Success categories")

# Search in multiple categories (all categories)
results = search_quotes(category=['Love', 'Happiness'], match_all_categories=True)
print(f"Found {len(results)} quotes in BOTH Love AND Happiness categories")

# Combined: multiple text terms + multiple categories
results = search_quotes(
    text=['love', 'heart', 'passion'],
    category=['Love', 'Happiness'],
    limit=20
)

# By author with multiple text terms
results = search_quotes(
    text=['success', 'failure', 'achieve'],
    author='Jobs'
)

# Complex search
results = search_quotes(
    text=['courage', 'brave'],
    author='Roosevelt',
    category=['Courage', 'Leadership'],
    match_all_text=False,  # Contains "courage" OR "brave"
    match_all_categories=False,  # In "Courage" OR "Leadership"
    limit=10
)


# ===== ENHANCED PRINT FUNCTION =====

def print_quotes(quotes, max_results=10, show_search_terms=None):
    """
    Pretty print search results with optional highlighting
    
    Args:
        quotes: List of Quote objects
        max_results: Maximum number to display
        show_search_terms: List of terms to highlight in output
    """
    print(f"\nFound {len(quotes)} quotes. Showing first {min(len(quotes), max_results)}:\n")
    print("="*80)
    
    for i, q in enumerate(quotes[:max_results], 1):
        categories = [c.name for c in q.categories]
        
        # Optionally highlight search terms
        display_text = q.text
        if show_search_terms:
            for term in show_search_terms:
                # Simple highlighting with uppercase
                import re
                display_text = re.sub(
                    f'({re.escape(term)})',
                    lambda m: m.group(1).upper(),
                    display_text,
                    flags=re.IGNORECASE
                )
        
        print(f"\n{i}. \"{display_text}\"")
        print(f"   - {q.author.name}")
        if categories:
            print(f"   Categories: {', '.join(categories[:5])}")
        if q.source and 'thequoteshub' not in q.source.lower():
            print(f"   Source: {q.source}")
    
    print("\n" + "="*80)


# Use the enhanced functions together
results = search_quotes(
    text=['courage', 'brave', 'fear'],
    category=['Courage', 'Leadership'],
    limit=50
)
print_quotes(results, max_results=10, show_search_terms=['courage', 'brave', 'fear'])


# ===== ALTERNATIVE: MORE ADVANCED SEARCH WITH WEIGHTS =====

def advanced_search(text_terms=None, categories=None, author=None, limit=20):
    """
    Search with relevance scoring based on number of matching terms
    Returns results sorted by relevance (most matches first)
    """
    if not text_terms:
        text_terms = []
    if isinstance(text_terms, str):
        text_terms = [text_terms]
    
    # Get all matching quotes
    results = search_quotes(text=text_terms, category=categories, author=author)
    
    # Score each result by how many terms it contains
    scored_results = []
    for quote in results:
        score = 0
        quote_lower = quote.text.lower()
        for term in text_terms:
            if term.lower() in quote_lower:
                score += 1
        scored_results.append((quote, score))
    
    # Sort by score (highest first)
    scored_results.sort(key=lambda x: x[1], reverse=True)
    
    # Return just the quotes, limited
    return [quote for quote, score in scored_results[:limit]]


# Use advanced search
results = advanced_search(
    text_terms=['courage', 'brave', 'fear', 'bold'],
    categories=['Courage', 'Leadership'],
    limit=10
)
print(f"Top {len(results)} most relevant quotes:")
print_quotes(results)





def create_user(username, email, password, session=None):
    """
    Create a new user
    
    Args:
        username: Unique username
        email: Unique email address
        password: Plain text password (will be hashed)
        session: Optional database session
    
    Returns:
        User object if successful, None if username/email already exists
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Check if username or email already exists
        existing_user = session.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if existing_user:
            return None
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        session.add(user)
        session.commit()
        
        return user
    
    except Exception as e:
        session.rollback()
        print(f"Error creating user: {e}")
        return None
    
    finally:
        if close_session:
            session.close()


def get_user_by_username(username, session=None):
    """Get a user by username"""
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        return session.query(User).filter_by(username=username).first()
    finally:
        if close_session:
            session.close()


def get_user_by_email(email, session=None):
    """Get a user by email"""
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        return session.query(User).filter_by(email=email).first()
    finally:
        if close_session:
            session.close()


def authenticate_user(username_or_email, password, session=None):
    """
    Authenticate a user with username/email and password
    
    Returns:
        User object if authentication successful, None otherwise
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Try to find user by username or email
        user = session.query(User).filter(
            or_(User.username == username_or_email, User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password):
            # Update last login
            user.last_login = datetime.utcnow()
            session.commit()
            return user
        
        return None
    
    finally:
        if close_session:
            session.close()


# ===== FAVORITES FUNCTIONS =====

def add_favorite(user, quote_id, session=None):
    """
    Add a quote to user's favorites
    
    Args:
        user: User object or user_id
        quote_id: ID of the quote to favorite
        session: Optional database session
    
    Returns:
        True if added, False if already favorited or quote doesn't exist
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Get user if ID was passed
        if isinstance(user, int):
            user = session.query(User).filter_by(id=user).first()
            if not user:
                return False
        
        # Get quote
        quote = session.query(Quote).filter_by(id=quote_id).first()
        if not quote:
            return False
        
        # Add to favorites
        success = user.add_favorite(quote)
        if success:
            session.commit()
        
        return success
    
    finally:
        if close_session:
            session.close()


def remove_favorite(user, quote_id, session=None):
    """Remove a quote from user's favorites"""
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Get user if ID was passed
        if isinstance(user, int):
            user = session.query(User).filter_by(id=user).first()
            if not user:
                return False
        
        # Get quote
        quote = session.query(Quote).filter_by(id=quote_id).first()
        if not quote:
            return False
        
        # Remove from favorites
        success = user.remove_favorite(quote)
        if success:
            session.commit()
        
        return success
    
    finally:
        if close_session:
            session.close()


def get_user_favorites(user, limit=None, session=None):
    """
    Get all favorite quotes for a user
    
    Args:
        user: User object or user_id
        limit: Optional limit on number of results
        session: Optional database session
    
    Returns:
        List of Quote objects
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Get user if ID was passed
        if isinstance(user, int):
            user = session.query(User).filter_by(id=user).first()
            if not user:
                return []
        
        favorites = user.favorite_quotes
        
        if limit:
            return favorites[:limit]
        
        return favorites
    
    finally:
        if close_session:
            session.close()


def is_quote_favorited(user, quote_id, session=None):
    """Check if a user has favorited a specific quote"""
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        # Get user if ID was passed
        if isinstance(user, int):
            user = session.query(User).filter_by(id=user).first()
            if not user:
                return False
        
        # Get quote
        quote = session.query(Quote).filter_by(id=quote_id).first()
        if not quote:
            return False
        
        return user.is_favorite(quote)
    
    finally:
        if close_session:
            session.close()


def get_most_favorited_quotes(limit=10, session=None):
    """Get the most favorited quotes across all users"""
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        from sqlalchemy import desc
        
        # Query quotes with favorite counts
        results = session.query(
            Quote,
            func.count(user_favorites.c.user_id).label('favorite_count')
        ).outerjoin(user_favorites).group_by(Quote.id).order_by(desc('favorite_count')).limit(limit).all()
        
        return [{'quote': quote, 'favorites': count} for quote, count in results]
    
    finally:
        if close_session:
            session.close()