# First, set up your session
from models import Session, Quote, Category, Author
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





# Always close when done!
session.close()
