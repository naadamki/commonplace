"""
Database access layer with managers for quotes, users, authors, and categories.
Provides a clean OOP interface for all database operations.
"""

from models import Session, Quote, Author, Category, User, user_favorites
from sqlalchemy import or_, and_, func, desc
from datetime import datetime
import re


class QuoteManager:
    """Manager for Quote queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self):
        """Get all quotes"""
        return self.session.query(Quote).all()
    
    def get(self, quote_id):
        """Get quote by ID"""
        return self.session.query(Quote).filter_by(id=quote_id).first()
    
    def count(self):
        """Get total number of quotes"""
        return self.session.query(Quote).count()
    
    def search(self, text=None, author=None, category=None, limit=None, 
               match_all_text=False, match_all_categories=False):
        """
        Search quotes with various filters
        
        Args:
            text: String or list of strings to search for in quote text
            author: String to search by author name (partial match)
            category: String or list of category names to filter by
            limit: Maximum results to return
            match_all_text: If True, quote must contain ALL text terms (AND)
            match_all_categories: If True, quote must be in ALL categories (AND)
        
        Returns:
            List of Quote objects
        """
        query = self.session.query(Quote)
        
        # Handle author search
        if author:
            query = query.join(Author).filter(Author.name.ilike(f'%{author}%'))
        
        # Handle category search
        if category:
            if isinstance(category, str):
                category = [category]
            
            if match_all_categories:
                for cat_name in category:
                    query = query.join(Quote.categories, aliased=True).filter(
                        Category.name == cat_name
                    )
            else:
                query = query.join(Quote.categories).filter(
                    Category.name.in_(category)
                )
        
        # Handle text search
        if text:
            if isinstance(text, str):
                text = [text]
            
            if match_all_text:
                for term in text:
                    query = query.filter(Quote.text.ilike(f'%{term}%'))
            else:
                text_conditions = [Quote.text.ilike(f'%{term}%') for term in text]
                query = query.filter(or_(*text_conditions))
        
        query = query.distinct()
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def advanced_search(self, text_terms=None, categories=None, author=None, limit=20):
        """
        Search with relevance scoring based on number of matching terms.
        Returns results sorted by relevance (most matches first).
        """
        if not text_terms:
            text_terms = []
        if isinstance(text_terms, str):
            text_terms = [text_terms]
        
        # Get all matching quotes
        results = self.search(text=text_terms, category=categories, author=author)
        
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
    
    def random(self, category=None):
        """Get a random quote, optionally from a specific category"""
        query = self.session.query(Quote)
        
        if category:
            query = query.join(Quote.categories).filter(Category.name == category)
        
        return query.order_by(func.random()).first()
    
    def by_author(self, author_name, limit=None):
        """Get all quotes by an author (partial name match)"""
        query = self.session.query(Quote).join(Author).filter(
            Author.name.ilike(f'%{author_name}%')
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def by_category(self, category_name, limit=None):
        """Get all quotes in a category"""
        query = self.session.query(Quote).join(Quote.categories).filter(
            Category.name == category_name
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def shortest(self, limit=10):
        """Get the shortest quotes"""
        return self.session.query(Quote).order_by(
            func.length(Quote.text)
        ).limit(limit).all()
    
    def longest(self, limit=10):
        """Get the longest quotes"""
        return self.session.query(Quote).order_by(
            func.length(Quote.text).desc()
        ).limit(limit).all()
    
    def most_favorited(self, limit=10):
        """Get the most favorited quotes"""
        results = self.session.query(
            Quote,
            func.count(user_favorites.c.user_id).label('favorite_count')
        ).outerjoin(user_favorites).group_by(Quote.id).order_by(
            desc('favorite_count')
        ).limit(limit).all()
        
        return [{'quote': quote, 'favorites': count} for quote, count in results]
    
    def recent(self, limit=10):
        """Get the most recently added quotes"""
        return self.session.query(Quote).order_by(
            Quote.created_at.desc()
        ).limit(limit).all()


class UserManager:
    """Manager for User queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self):
        """Get all users"""
        return self.session.query(User).all()
    
    def get(self, user_id):
        """Get user by ID"""
        return self.session.query(User).filter_by(id=user_id).first()
    
    def count(self):
        """Get total number of users"""
        return self.session.query(User).count()
    
    def create(self, username, email, password):
        """
        Create a new user
        
        Returns:
            User object if successful, None if username/email already exists
        """
        # Check if username or email already exists
        existing = self.session.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if existing:
            return None
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        self.session.add(user)
        self.session.commit()
        
        return user
    
    def get_by_username(self, username):
        """Get user by username"""
        return self.session.query(User).filter_by(username=username).first()
    
    def get_by_email(self, email):
        """Get user by email"""
        return self.session.query(User).filter_by(email=email).first()
    
    def authenticate(self, username_or_email, password):
        """
        Authenticate a user with username/email and password
        
        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.session.query(User).filter(
            or_(User.username == username_or_email, User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            self.session.commit()
            return user
        
        return None
    
    def update_password(self, user, new_password):
        """Update a user's password"""
        if isinstance(user, int):
            user = self.get(user)
        
        if not user:
            return False
        
        user.set_password(new_password)
        self.session.commit()
        return True
    
    def deactivate(self, user):
        """Deactivate a user account"""
        if isinstance(user, int):
            user = self.get(user)
        
        if not user:
            return False
        
        user.is_active = False
        self.session.commit()
        return True
    
    def activate(self, user):
        """Activate a user account"""
        if isinstance(user, int):
            user = self.get(user)
        
        if not user:
            return False
        
        user.is_active = True
        self.session.commit()
        return True


class FavoritesManager:
    """Manager for user favorites operations"""
    
    def __init__(self, session):
        self.session = session
    
    def add(self, user, quote_id):
        """
        Add a quote to user's favorites
        
        Returns:
            True if added, False if already favorited or quote doesn't exist
        """
        # Get user if ID was passed
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                return False
        
        # Get quote
        quote = self.session.query(Quote).filter_by(id=quote_id).first()
        if not quote:
            return False
        
        # Add to favorites
        success = user.add_favorite(quote)
        if success:
            self.session.commit()
        
        return success
    
    def remove(self, user, quote_id):
        """Remove a quote from user's favorites"""
        # Get user if ID was passed
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                return False
        
        # Get quote
        quote = self.session.query(Quote).filter_by(id=quote_id).first()
        if not quote:
            return False
        
        # Remove from favorites
        success = user.remove_favorite(quote)
        if success:
            self.session.commit()
        
        return success
    
    def get_user_favorites(self, user, limit=None):
        """
        Get all favorite quotes for a user
        
        Returns:
            List of Quote objects
        """
        # Get user if ID was passed
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                return []
        
        favorites = user.favorite_quotes
        
        if limit:
            return favorites[:limit]
        
        return favorites
    
    def is_favorited(self, user, quote_id):
        """Check if a user has favorited a specific quote"""
        # Get user if ID was passed
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                return False
        
        # Get quote
        quote = self.session.query(Quote).filter_by(id=quote_id).first()
        if not quote:
            return False
        
        return user.is_favorite(quote)
    
    def count_user_favorites(self, user):
        """Get the count of a user's favorites"""
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                return 0
        
        return user.get_favorites_count()


class AuthorManager:
    """Manager for Author queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self):
        """Get all authors"""
        return self.session.query(Author).all()
    
    def get(self, author_id):
        """Get author by ID"""
        return self.session.query(Author).filter_by(id=author_id).first()
    
    def get_by_name(self, name):
        """Get author by exact name"""
        return self.session.query(Author).filter_by(name=name).first()
    
    def search(self, name):
        """Search authors by partial name match"""
        return self.session.query(Author).filter(
            Author.name.ilike(f'%{name}%')
        ).all()
    
    def count(self):
        """Get total number of authors"""
        return self.session.query(Author).count()
    
    def top_quoted(self, limit=10):
        """Get the most quoted authors"""
        results = self.session.query(
            Author.name,
            func.count(Quote.id).label('quote_count')
        ).join(Quote).group_by(Author.id).order_by(
            desc('quote_count')
        ).limit(limit).all()
        
        return [{'author': name, 'count': count} for name, count in results]
    
    def get_or_create(self, name):
        """Get existing author or create new one"""
        author = self.get_by_name(name)
        if not author:
            author = Author(name=name)
            self.session.add(author)
            self.session.commit()
        return author


class CategoryManager:
    """Manager for Category queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self):
        """Get all categories"""
        return self.session.query(Category).all()
    
    def get(self, category_id):
        """Get category by ID"""
        return self.session.query(Category).filter_by(id=category_id).first()
    
    def get_by_name(self, name):
        """Get category by name"""
        return self.session.query(Category).filter_by(name=name).first()
    
    def count(self):
        """Get total number of categories"""
        return self.session.query(Category).count()
    
    def with_counts(self):
        """Get all categories with their quote counts"""
        categories = self.all()
        return [
            {'category': cat.name, 'count': len(cat.quotes), 'id': cat.id}
            for cat in categories
        ]
    
    def most_popular(self, limit=10):
        """Get categories with the most quotes"""
        results = self.with_counts()
        results.sort(key=lambda x: x['count'], reverse=True)
        return results[:limit]


class DB:
    """
    Main database access object with managers for all entities.
    
    Usage:
        # Simple usage
        db = DB()
        quotes = db.quotes.search(text='courage', limit=10)
        db.close()
        
        # With context manager (auto-closes)
        with DB() as db:
            user = db.users.authenticate('john', 'password')
            quote = db.quotes.random()
            db.favorites.add(user, quote.id)
            db.commit()
    """
    
    def __init__(self):
        self.session = Session()
        self.quotes = QuoteManager(self.session)
        self.users = UserManager(self.session)
        self.favorites = FavoritesManager(self.session)
        self.authors = AuthorManager(self.session)
        self.categories = CategoryManager(self.session)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto rollback on error"""
        if exc_type is not None:
            self.session.rollback()
        self.session.close()
    
    def commit(self):
        """Commit the current transaction"""
        self.session.commit()
    
    def rollback(self):
        """Rollback the current transaction"""
        self.session.rollback()
    
    def close(self):
        """Close the database session"""
        self.session.close()
    
    def get_stats(self):
        """Get overall database statistics"""
        return {
            'total_quotes': self.quotes.count(),
            'total_users': self.users.count(),
            'total_authors': self.authors.count(),
            'total_categories': self.categories.count()
        }


# Utility functions for display
def print_quote(quote, show_categories=True, show_source=True):
    """Pretty print a single quote"""
    print(f"\n{'='*80}")
    print(f"ID: {quote.id}")
    print(f"\"{quote.text}\"")
    print(f"- {quote.author.name}")
    
    if show_categories and quote.categories:
        categories = [c.name for c in quote.categories]
        print(f"Categories: {', '.join(categories)}")
    
    if show_source and quote.source:
        print(f"Source: {quote.source}")
    
    if quote.get_tags():
        print(f"Tags: {', '.join(quote.get_tags())}")
    
    print(f"Favorites: {quote.get_favorites_count()}")
    print(f"{'='*80}\n")


def print_quotes(quotes, max_results=10, show_search_terms=None):
    """Pretty print multiple quotes"""
    print(f"\nFound {len(quotes)} quotes. Showing first {min(len(quotes), max_results)}:\n")
    print("="*80)
    
    for i, q in enumerate(quotes[:max_results], 1):
        categories = [c.name for c in q.categories]
        
        # Optionally highlight search terms
        display_text = q.text
        if show_search_terms:
            for term in show_search_terms:
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
    
    print("\n" + "="*80)


def print_stats(db):
    """Print database statistics"""
    stats = db.get_stats()
    print(f"\n{'='*60}")
    print(f"DATABASE STATISTICS")
    print(f"{'='*60}")
    print(f"Total Quotes: {stats['total_quotes']:,}")
    print(f"Total Users: {stats['total_users']:,}")
    print(f"Total Authors: {stats['total_authors']:,}")
    print(f"Total Categories: {stats['total_categories']}")
    print(f"{'='*60}\n")