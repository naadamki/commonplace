from sqlalchemy import create_engine, Column, Integer, String, Text, Table, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, List
import json

Base = declarative_base()

# Many-to-many relationship table for quotes and categories
quote_categories = Table('quote_categories', Base.metadata,
    Column('quote_id', Integer, ForeignKey('quotes.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

# Many-to-many relationship table for users and favorite quotes
user_quote_favorites = Table('user_quote_favorites', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('quote_id', Integer, ForeignKey('quotes.id')),
    Column('favorited_at', DateTime, default=datetime.utcnow)
)

# Many-to-many relationship table for users and favorite authors
user_author_favorites = Table('user_author_favorites', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('author_id', Integer, ForeignKey('authors.id')),
    Column('favorited_at', DateTime, default=datetime.utcnow)
)


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships to favorites
    favorite_quotes = relationship('Quote', secondary=user_quote_favorites, backref='favorited_by')
    favorite_authors = relationship('Author', secondary=user_author_favorites, backref='favorited_by')
    
    def __repr__(self) -> str:
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password"""
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    # Quote favorites
    def add_favorite_quote(self, quote: 'Quote') -> bool:
        """Add a quote to user's favorites"""
        if quote not in self.favorite_quotes:
            self.favorite_quotes.append(quote)
            return True
        return False
    
    def remove_favorite_quote(self, quote: 'Quote') -> bool:
        """Remove a quote from user's favorites"""
        if quote in self.favorite_quotes:
            self.favorite_quotes.remove(quote)
            return True
        return False
    
    def is_favorite_quote(self, quote: 'Quote') -> bool:
        """Check if a quote is in user's favorites"""
        return quote in self.favorite_quotes
    
    # Author favorites
    def add_favorite_author(self, author: 'Author') -> bool:
        """Add an author to user's favorites"""
        if author not in self.favorite_authors:
            self.favorite_authors.append(author)
            return True
        return False
    
    def remove_favorite_author(self, author: 'Author') -> bool:
        """Remove an author from user's favorites"""
        if author in self.favorite_authors:
            self.favorite_authors.remove(author)
            return True
        return False
    
    def is_favorite_author(self, author: 'Author') -> bool:
        """Check if an author is in user's favorites"""
        return author in self.favorite_authors
    
    # Counts
    def get_favorite_quotes_count(self) -> int:
        """Get total number of favorite quotes"""
        return len(self.favorite_quotes)
    
    def get_favorite_authors_count(self) -> int:
        """Get total number of favorite authors"""
        return len(self.favorite_authors)


class Author(Base):
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    birth_year = Column(Integer)
    death_year = Column(Integer)
    nationality = Column(String(100))
    profession = Column(String(200))
    bio = Column(Text)
    edit = Column(Boolean, default=False)
    
    # Relationship to quotes
    quotes = relationship('Quote', back_populates='author')
    
    def __repr__(self) -> str:
        return f"<Author(id={self.id}, name='{self.name}')>"
    
    def get_favorites_count(self) -> int:
        """Get how many users have favorited this author"""
        return len(self.favorited_by)

    def mark_for_edit(self) -> None:
        """Mark this author as needing editing"""
        self.edit = True
    
    def unmark_for_edit(self) -> None:
        """Clear the edit flag"""
        self.edit = False
    
    def needs_editing(self) -> bool:
        """Check if author is marked for editing"""
        return self.edit


class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    keywords = Column(Text)  # Stores JSON array of keywords
    
    quotes = relationship('Quote', secondary=quote_categories, back_populates='categories')
    
    def __repr__(self) -> str:
        return f"<Category(name='{self.name}')>"
    
    def get_keywords(self) -> List[str]:
        """Get keywords as a list"""
        return json.loads(self.keywords) if self.keywords else []
    
    def set_keywords(self, keyword_list: List[str]) -> None:
        """Set keywords from a list"""
        self.keywords = json.dumps(keyword_list)


class Quote(Base):
    __tablename__ = 'quotes'
    
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('authors.id'), nullable=False)
    year = Column(Integer)
    source = Column(String(300))
    context = Column(Text)  # Additional background info
    tags = Column(Text)  # Store as JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)
    edit = Column(Boolean, default=False)
    
    # Relationships
    author = relationship('Author', back_populates='quotes')
    categories = relationship('Category', secondary=quote_categories, back_populates='quotes')
    
    def __repr__(self) -> str:
        author_name = self.author.name if self.author else "Unknown"
        text_preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        text_preview = text_preview.replace('\n', ' ').replace('\r', ' ')
        return f"<Quote(id={self.id}, author='{author_name}', text='{text_preview}')>"
    
    def get_tags(self) -> List[str]:
        """Get tags as a list"""
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tag_list: List[str]) -> None:
        """Set tags from a list"""
        self.tags = json.dumps(tag_list)
    
    def get_favorites_count(self) -> int:
        """Get how many users have favorited this quote"""
        return len(self.favorited_by)

    def mark_for_edit(self) -> None:
        """Mark this quote as needing editing"""
        self.edit = True
    
    def unmark_for_edit(self) -> None:
        """Clear the edit flag"""
        self.edit = False
    
    def needs_editing(self) -> bool:
        """Check if quote is marked for editing"""
        return self.edit


# Database setup
engine = create_engine('sqlite:///quotes.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)