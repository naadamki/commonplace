"""
Database access layer with managers for quotes, users, authors, and categories.
Provides a clean OOP interface for all database operations with proper error handling.
"""

from models import Session, Quote, Category, User, Author, user_quote_favorites, user_author_favorites
from sqlalchemy import or_, and_, func, desc
from sqlalchemy.orm import joinedload
from datetime import datetime
from typing import Optional, List, Dict, Union
import re


# Custom Exceptions
class DatabaseError(Exception):
    """Base exception for database errors"""
    pass


class NotFoundError(DatabaseError):
    """Raised when a requested item is not found"""
    pass


class ValidationError(DatabaseError):
    """Raised when input validation fails"""
    pass


class DuplicateError(DatabaseError):
    """Raised when attempting to create a duplicate record"""
    pass


# Configuration
class Config:
    """Application configuration constants"""
    DEFAULT_SEARCH_LIMIT = 20
    DEFAULT_RANDOM_COUNT = 1
    MAX_RESULTS = 100
    MIN_PASSWORD_LENGTH = 6


class QuoteManager:
    """Manager for Quote queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self) -> List[Quote]:
        """Get all quotes"""
        return self.session.query(Quote).all()
    
    def get(self, quote_id: int) -> Optional[Quote]:
        """Get quote by ID"""
        return self.session.query(Quote).filter_by(id=quote_id).first()
    
    def get_or_raise(self, quote_id: int) -> Quote:
        """Get quote by ID, raise if not found"""
        quote = self.get(quote_id)
        if not quote:
            raise NotFoundError(f"Quote {quote_id} not found")
        return quote
    
    def count(self) -> int:
        """Get total number of quotes"""
        return self.session.query(Quote).count()
    
    def search(self, text: Optional[Union[str, List[str]]] = None, 
               author: Optional[str] = None, 
               category: Optional[Union[str, List[str]]] = None, 
               limit: Optional[int] = None, 
               match_all_text: bool = False, 
               match_all_categories: bool = False) -> List[Quote]:
        """
        Search quotes with flexible filtering.
        
        Args:
            text: Single string or list of strings to search
            author: Author name (partial match)
            category: Single category name or list of names
            limit: Maximum results
            match_all_text: If True, quote must contain ALL text terms (AND logic)
            match_all_categories: If True, quote must be in ALL categories (AND logic)
        
        Returns:
            List of matching Quote objects
        """
        query = self.session.query(Quote).options(
            joinedload(Quote.author),
            joinedload(Quote.categories)
        )
        
        # Handle author search
        if author:
            if not isinstance(author, str):
                raise ValidationError("Author must be a string")
            query = query.filter(Quote.author.has(Author.name.ilike(f'%{author}%')))
        
        # Handle category search
        if category:
            if isinstance(category, str):
                category = [category]
            elif not isinstance(category, list):
                raise ValidationError("Category must be string or list")
            
            if match_all_categories:
                for cat_name in category:
                    query = query.filter(Quote.categories.any(Category.name == cat_name))
            else:
                query = query.filter(Quote.categories.any(Category.name.in_(category)))
        
        # Handle text search
        if text:
            if isinstance(text, str):
                text = [text]
            elif not isinstance(text, list):
                raise ValidationError("Text must be string or list")
            
            if match_all_text:
                for term in text:
                    query = query.filter(Quote.text.ilike(f'%{term}%'))
            else:
                text_conditions = [Quote.text.ilike(f'%{term}%') for term in text]
                query = query.filter(or_(*text_conditions))
        
        query = query.distinct()
        
        if limit:
            if not isinstance(limit, int) or limit < 1:
                raise ValidationError("Limit must be a positive integer")
            query = query.limit(limit)
        
        return query.all()
    
    def advanced_search(self, text_terms: Optional[Union[str, List[str]]] = None, 
                       categories: Optional[Union[str, List[str]]] = None, 
                       author: Optional[str] = None, 
                       limit: int = Config.DEFAULT_SEARCH_LIMIT,
                       match_all_text: bool = False, 
                       match_all_categories: bool = False) -> List[Quote]:
        """
        Advanced search with relevance scoring and full filtering support.
        Returns results sorted by relevance (most matches first).
        
        Args:
            text_terms: String or list of strings to search for
            categories: String or list of category names
            author: Author name to filter by
            limit: Maximum results to return
            match_all_text: If True, quote must contain ALL text terms (AND)
            match_all_categories: If True, quote must be in ALL categories (AND)
        
        Returns:
            List of Quote objects sorted by relevance
        
        Examples:
            advanced_search(text_terms=['courage', 'brave'], categories='Courage')
            advanced_search(text_terms=['love', 'heart'], categories=['Love', 'Happiness'])
            advanced_search(text_terms=['success', 'failure'], 
                          categories=['Success', 'Work'], author='Jobs')
        """
        if not text_terms:
            text_terms = []
        if isinstance(text_terms, str):
            text_terms = [text_terms]
        
        # Use regular search method with all filters
        results = self.search(
            text=text_terms, 
            category=categories, 
            author=author,
            match_all_text=match_all_text,
            match_all_categories=match_all_categories
        )
        
        # If no text terms, just return filtered results (no scoring needed)
        if not text_terms:
            return results[:limit]
        
        # Score each result by how many text terms it contains
        scored_results = []
        for quote in results:
            score = sum(1 for term in text_terms if term.lower() in quote.text.lower())
            scored_results.append((quote, score))
        
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return [quote for quote, score in scored_results[:limit]]
    
    def random(self, category: Optional[str] = None, count: int = Config.DEFAULT_RANDOM_COUNT) -> Union[Quote, List[Quote]]:
        """
        Get random quote(s), optionally from a specific category
        
        Args:
            category: Optional category name to filter by
            count: Number of random quotes to return (default: 1)
        
        Returns:
            Single Quote object if count=1, otherwise list of Quote objects
        """
        if not isinstance(count, int) or count < 1:
            raise ValidationError("Count must be a positive integer")
        
        query = self.session.query(Quote).options(
            joinedload(Quote.author),
            joinedload(Quote.categories)
        )
        
        if category:
            if not isinstance(category, str):
                raise ValidationError("Category must be a string")
            query = query.filter(Quote.categories.any(Category.name == category))
        
        query = query.order_by(func.random())
        
        if count == 1:
            return query.first()
        else:
            return query.limit(count).all()
    
    def by_author(self, author_name: str, limit: Optional[int] = None) -> List[Quote]:
        """Get all quotes by an author (partial name match)"""
        if not author_name or not isinstance(author_name, str):
            raise ValidationError("Author name must be a non-empty string")
        
        query = self.session.query(Quote).filter(
            Quote.author.has(Author.name.ilike(f'%{author_name}%'))
        ).options(joinedload(Quote.author), joinedload(Quote.categories))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def by_category(self, category_name: str, limit: Optional[int] = None) -> List[Quote]:
        """Get all quotes in a category"""
        if not category_name or not isinstance(category_name, str):
            raise ValidationError("Category name must be a non-empty string")
        
        query = self.session.query(Quote).filter(
            Quote.categories.any(Category.name == category_name)
        ).options(joinedload(Quote.author), joinedload(Quote.categories))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def shortest(self, limit: int = 10) -> List[Quote]:
        """Get the shortest quotes"""
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("Limit must be a positive integer")
        
        return self.session.query(Quote).order_by(
            func.length(Quote.text)
        ).options(joinedload(Quote.author), joinedload(Quote.categories)).limit(limit).all()
    
    def longest(self, limit: int = 10) -> List[Quote]:
        """Get the longest quotes"""
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("Limit must be a positive integer")
        
        return self.session.query(Quote).order_by(
            func.length(Quote.text).desc()
        ).options(joinedload(Quote.author), joinedload(Quote.categories)).limit(limit).all()
    
    def most_favorited(self, limit: int = 10) -> List[Dict]:
        """Get the most favorited quotes"""
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("Limit must be a positive integer")
        
        results = self.session.query(
            Quote,
            func.count(user_quote_favorites.c.user_id).label('favorite_count')
        ).outerjoin(user_quote_favorites).group_by(Quote.id).order_by(
            desc('favorite_count')
        ).options(joinedload(Quote.author), joinedload(Quote.categories)).limit(limit).all()
        
        return [{'quote': quote, 'favorites': count} for quote, count in results]
    
    def recent(self, limit: int = 10) -> List[Quote]:
        """Get the most recently added quotes"""
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("Limit must be a positive integer")
        
        return self.session.query(Quote).order_by(
            Quote.created_at.desc()
        ).options(joinedload(Quote.author), joinedload(Quote.categories)).limit(limit).all()

    def needs_edit(self, limit: Optional[int] = None) -> List[Quote]:
        """Get all quotes marked for editing"""
        query = self.session.query(Quote).filter_by(edit=True).options(
            joinedload(Quote.author), joinedload(Quote.categories)
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def mark_for_edit(self, quote_id: int) -> None:
        """Mark a quote for editing"""
        quote = self.get_or_raise(quote_id)
        quote.mark_for_edit()
        self.session.commit()
    
    def unmark_for_edit(self, quote_id: int) -> None:
        """Remove edit flag from quote"""
        quote = self.get_or_raise(quote_id)
        quote.unmark_for_edit()
        self.session.commit()
    
    def count_needs_edit(self) -> int:
        """Count quotes that need editing"""
        return self.session.query(Quote).filter_by(edit=True).count()


class UserManager:
    """Manager for User queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self) -> List[User]:
        """Get all users"""
        return self.session.query(User).all()
    
    def get(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.session.query(User).filter_by(id=user_id).first()
    
    def get_or_raise(self, user_id: int) -> User:
        """Get user by ID, raise if not found"""
        user = self.get(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user
    
    def count(self) -> int:
        """Get total number of users"""
        return self.session.query(User).count()
    
    def create(self, username: str, email: str, password: str) -> User:
        """
        Create a new user
        
        Args:
            username: Unique username
            email: Unique email address
            password: User password (min 6 chars)
        
        Returns:
            User object
        
        Raises:
            ValidationError: If input is invalid
            DuplicateError: If username or email already exists
        """
        # Validate inputs
        if not username or not isinstance(username, str) or len(username) < 3:
            raise ValidationError("Username must be at least 3 characters")
        if not email or not isinstance(email, str) or '@' not in email:
            raise ValidationError("Email must be valid")
        if not password or len(password) < Config.MIN_PASSWORD_LENGTH:
            raise ValidationError(f"Password must be at least {Config.MIN_PASSWORD_LENGTH} characters")
        
        # Check if username or email already exists
        existing = self.session.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if existing:
            raise DuplicateError(f"Username or email already exists")
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        self.session.add(user)
        self.session.commit()
        
        return user
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        if not username or not isinstance(username, str):
            raise ValidationError("Username must be a non-empty string")
        return self.session.query(User).filter_by(username=username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        if not email or not isinstance(email, str):
            raise ValidationError("Email must be a non-empty string")
        return self.session.query(User).filter_by(email=email).first()
    
    def authenticate(self, username_or_email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username/email and password
        
        Returns:
            User object if authentication successful, None otherwise
        """
        if not username_or_email or not password:
            return None
        
        user = self.session.query(User).filter(
            or_(User.username == username_or_email, User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            self.session.commit()
            return user
        
        return None
    
    def update_password(self, user: Union[int, User], new_password: str) -> None:
        """Update a user's password"""
        if isinstance(user, int):
            user = self.get_or_raise(user)
        
        if not new_password or len(new_password) < Config.MIN_PASSWORD_LENGTH:
            raise ValidationError(f"Password must be at least {Config.MIN_PASSWORD_LENGTH} characters")
        
        user.set_password(new_password)
        self.session.commit()
    
    def deactivate(self, user: Union[int, User]) -> None:
        """Deactivate a user account"""
        if isinstance(user, int):
            user = self.get_or_raise(user)
        
        user.is_active = False
        self.session.commit()
    
    def activate(self, user: Union[int, User]) -> None:
        """Activate a user account"""
        if isinstance(user, int):
            user = self.get_or_raise(user)
        
        user.is_active = True
        self.session.commit()


class FavoritesManager:
    """Manager for user favorites operations (quotes and authors)"""
    
    def __init__(self, session):
        self.session = session
    
    def add(self, user: Union[int, User], item_id: int, item_type: str = 'quote') -> None:
        """
        Add a quote or author to user's favorites
        
        Args:
            user: User object or user_id
            item_id: ID of the quote or author
            item_type: 'quote' or 'author' (default: 'quote')
        
        Raises:
            ValidationError: If item_type is invalid
            NotFoundError: If user or item doesn't exist
            DuplicateError: If already favorited
        """
        # Get user if ID was passed
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                raise NotFoundError("User not found")
        
        if item_type == 'quote':
            quote = self.session.query(Quote).filter_by(id=item_id).first()
            if not quote:
                raise NotFoundError(f"Quote {item_id} not found")
            
            if quote in user.favorite_quotes:
                raise DuplicateError("Quote already favorited")
            
            user.add_favorite_quote(quote)
        
        elif item_type == 'author':
            author = self.session.query(Author).filter_by(id=item_id).first()
            if not author:
                raise NotFoundError(f"Author {item_id} not found")
            
            if author in user.favorite_authors:
                raise DuplicateError("Author already favorited")
            
            user.add_favorite_author(author)
        
        else:
            raise ValidationError(f"Invalid item_type: {item_type}. Must be 'quote' or 'author'")
        
        self.session.commit()
    
    def remove(self, user: Union[int, User], item_id: int, item_type: str = 'quote') -> None:
        """
        Remove a quote or author from user's favorites
        
        Args:
            user: User object or user_id
            item_id: ID of the quote or author
            item_type: 'quote' or 'author' (default: 'quote')
        
        Raises:
            ValidationError: If item_type is invalid
            NotFoundError: If user, item doesn't exist, or not favorited
        """
        # Get user if ID was passed
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                raise NotFoundError("User not found")
        
        if item_type == 'quote':
            quote = self.session.query(Quote).filter_by(id=item_id).first()
            if not quote:
                raise NotFoundError(f"Quote {item_id} not found")
            
            if not user.remove_favorite_quote(quote):
                raise NotFoundError("Quote not in favorites")
        
        elif item_type == 'author':
            author = self.session.query(Author).filter_by(id=item_id).first()
            if not author:
                raise NotFoundError(f"Author {item_id} not found")
            
            if not user.remove_favorite_author(author):
                raise NotFoundError("Author not in favorites")
        
        else:
            raise ValidationError(f"Invalid item_type: {item_type}. Must be 'quote' or 'author'")
        
        self.session.commit()
    
    def is_favorited(self, user: Union[int, User], item_id: int, item_type: str = 'quote') -> bool:
        """Check if a user has favorited a specific quote or author"""
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                raise NotFoundError("User not found")
        
        if item_type == 'quote':
            quote = self.session.query(Quote).filter_by(id=item_id).first()
            if not quote:
                raise NotFoundError(f"Quote {item_id} not found")
            return user.is_favorite_quote(quote)
        
        elif item_type == 'author':
            author = self.session.query(Author).filter_by(id=item_id).first()
            if not author:
                raise NotFoundError(f"Author {item_id} not found")
            return user.is_favorite_author(author)
        
        else:
            raise ValidationError(f"Invalid item_type: {item_type}. Must be 'quote' or 'author'")
    
    def get(self, user: Union[int, User], item_type: str = 'quote', limit: Optional[int] = None) -> List:
        """Get all favorite quotes or authors for a user"""
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                raise NotFoundError("User not found")
        
        if item_type == 'quote':
            favorites = user.favorite_quotes
        elif item_type == 'author':
            favorites = user.favorite_authors
        else:
            raise ValidationError(f"Invalid item_type: {item_type}. Must be 'quote' or 'author'")
        
        if limit:
            return favorites[:limit]
        
        return favorites
    
    def count(self, user: Union[int, User], item_type: str = 'quote') -> int:
        """Get the count of a user's favorite quotes or authors"""
        if isinstance(user, int):
            user = self.session.query(User).filter_by(id=user).first()
            if not user:
                raise NotFoundError("User not found")
        
        if item_type == 'quote':
            return user.get_favorite_quotes_count()
        elif item_type == 'author':
            return user.get_favorite_authors_count()
        else:
            raise ValidationError(f"Invalid item_type: {item_type}. Must be 'quote' or 'author'")
    
    def get_most(self, item_type: str = 'quote', limit: int = 10) -> List[Dict]:
        """Get the most favorited quotes or authors"""
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("Limit must be a positive integer")
        
        if item_type == 'quote':
            results = self.session.query(
                Quote,
                func.count(user_quote_favorites.c.user_id).label('favorite_count')
            ).outerjoin(user_quote_favorites).group_by(Quote.id).order_by(
                desc('favorite_count')
            ).limit(limit).all()
            
            return [{'quote': quote, 'favorites': count} for quote, count in results]
        
        elif item_type == 'author':
            results = self.session.query(
                Author,
                func.count(user_author_favorites.c.user_id).label('favorite_count')
            ).outerjoin(user_author_favorites).group_by(Author.id).order_by(
                desc('favorite_count')
            ).limit(limit).all()
            
            return [{'author': author, 'favorites': count} for author, count in results]
        
        else:
            raise ValidationError(f"Invalid item_type: {item_type}. Must be 'quote' or 'author'")


class AuthorManager:
    """Manager for Author queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self) -> List[Author]:
        """Get all authors"""
        return self.session.query(Author).all()
    
    def get(self, author_id: int) -> Optional[Author]:
        """Get author by ID"""
        return self.session.query(Author).filter_by(id=author_id).first()
    
    def get_or_raise(self, author_id: int) -> Author:
        """Get author by ID, raise if not found"""
        author = self.get(author_id)
        if not author:
            raise NotFoundError(f"Author {author_id} not found")
        return author
    
    def get_by_name(self, name: str) -> Optional[Author]:
        """Get author by exact name"""
        if not name or not isinstance(name, str):
            raise ValidationError("Author name must be a non-empty string")
        return self.session.query(Author).filter_by(name=name).first()
    
    def search(self, name: str) -> List[Author]:
        """Search authors by partial name match"""
        if not name or not isinstance(name, str):
            raise ValidationError("Author name must be a non-empty string")
        
        return self.session.query(Author).filter(
            Author.name.ilike(f'%{name}%')
        ).all()
    
    def count(self) -> int:
        """Get total number of authors"""
        return self.session.query(Author).count()
    
    def top_quoted(self, limit: int = 10) -> List[Dict]:
        """Get the most quoted authors"""
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("Limit must be a positive integer")
        
        results = self.session.query(
            Author.name,
            func.count(Quote.id).label('quote_count')
        ).join(Quote).group_by(Author.id).order_by(
            desc('quote_count')
        ).limit(limit).all()
        
        return [{'author': name, 'count': count} for name, count in results]
    
    def get_or_create(self, name: str) -> Author:
        """Get existing author or create new one"""
        if not name or not isinstance(name, str):
            raise ValidationError("Author name must be a non-empty string")
        
        author = self.get_by_name(name)
        if not author:
            author = Author(name=name)
            self.session.add(author)
            self.session.commit()
        return author

    def needs_edit(self, limit: Optional[int] = None) -> List[Author]:
        """Get all authors marked for editing"""
        query = self.session.query(Author).filter_by(edit=True)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def mark_for_edit(self, author_id: int) -> None:
        """Mark an author for editing"""
        author = self.get_or_raise(author_id)
        author.mark_for_edit()
        self.session.commit()
    
    def unmark_for_edit(self, author_id: int) -> None:
        """Remove edit flag from author"""
        author = self.get_or_raise(author_id)
        author.unmark_for_edit()
        self.session.commit()
    
    def count_needs_edit(self) -> int:
        """Count authors that need editing"""
        return self.session.query(Author).filter_by(edit=True).count()


class CategoryManager:
    """Manager for Category queries and operations"""
    
    def __init__(self, session):
        self.session = session
    
    def all(self) -> List[Category]:
        """Get all categories"""
        return self.session.query(Category).all()
    
    def get(self, category_id: int) -> Optional[Category]:
        """Get category by ID"""
        return self.session.query(Category).filter_by(id=category_id).first()
    
    def get_or_raise(self, category_id: int) -> Category:
        """Get category by ID, raise if not found"""
        category = self.get(category_id)
        if not category:
            raise NotFoundError(f"Category {category_id} not found")
        return category
    
    def get_by_name(self, name: str) -> Optional[Category]:
        """Get category by name"""
        if not name or not isinstance(name, str):
            raise ValidationError("Category name must be a non-empty string")
        return self.session.query(Category).filter_by(name=name).first()
    
    def count(self) -> int:
        """Get total number of categories"""
        return self.session.query(Category).count()
    
    def with_counts(self) -> List[Dict]:
        """Get all categories with their quote counts"""
        categories = self.all()
        return [
            {'category': cat.name, 'count': len(cat.quotes), 'id': cat.id}
            for cat in categories
        ]
    
    def most_popular(self, limit: int = 10) -> List[Dict]:
        """Get categories with the most quotes"""
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("Limit must be a positive integer")
        
        results = self.with_counts()
        results.sort(key=lambda x: x['count'], reverse=True)
        return results[:limit]


class DB:
    """
    Main database access object with managers for all entities.
    Provides context manager support for automatic resource cleanup.
    
    Usage:
        # Simple usage
        db = DB()
        try:
            quotes = db.quotes.search(text='courage', limit=10)
        finally:
            db.close()
        
        # With context manager (recommended - auto-closes)
        with DB() as db:
            user = db.users.authenticate('john', 'password')
            quote = db.quotes.random()
            db.favorites.add(user, quote.id)
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
        """Context manager exit - auto rollback on error, close session"""
        if exc_type is not None:
            self.session.rollback()
        self.session.close()
    
    def commit(self) -> None:
        """Commit the current transaction"""
        self.session.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction"""
        self.session.rollback()
    
    def close(self) -> None:
        """Close the database session"""
        self.session.close()
    
    def get_stats(self) -> Dict:
        """Get overall database statistics"""
        return {
            'total_quotes': self.quotes.count(),
            'total_users': self.users.count(),
            'total_authors': self.authors.count(),
            'total_categories': self.categories.count()
        }


# Utility functions for display
def print_quote(quote: Quote, show_categories: bool = True, show_source: bool = True) -> None:
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


def print_quotes(quotes: List[Quote], max_results: int = 10, show_search_terms: Optional[List[str]] = None) -> None:
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


def print_stats(db: DB) -> None:
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