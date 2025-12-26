from sqlalchemy import create_engine, Column, Integer, String, Text, Table, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

Base = declarative_base()

# Many-to-many relationship table for quotes and categories
quote_categories = Table('quote_categories', Base.metadata,
    Column('quote_id', Integer, ForeignKey('quotes.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

# Many-to-many relationship table for users and favorite quotes
user_favorites = Table('user_favorites', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('quote_id', Integer, ForeignKey('quotes.id')),
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
    
    # Relationship to favorite quotes
    favorite_quotes = relationship('Quote', secondary=user_favorites, backref='favorited_by')
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def add_favorite(self, quote):
        """Add a quote to user's favorites"""
        if quote not in self.favorite_quotes:
            self.favorite_quotes.append(quote)
            return True
        return False
    
    def remove_favorite(self, quote):
        """Remove a quote from user's favorites"""
        if quote in self.favorite_quotes:
            self.favorite_quotes.remove(quote)
            return True
        return False
    
    def is_favorite(self, quote):
        """Check if a quote is in user's favorites"""
        return quote in self.favorite_quotes
    
    def get_favorites_count(self):
        """Get total number of favorites"""
        return len(self.favorite_quotes)

class Author(Base):
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    birth_year = Column(Integer)
    death_year = Column(Integer)
    nationality = Column(String(100))
    profession = Column(String(200))
    bio = Column(Text)
    
    # Relationship to quotes
    quotes = relationship('Quote', back_populates='author')
    
    def __repr__(self):
        return f"<Author(id={self.id}, name='{self.name}')>"

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    keywords = Column(Text)  # Store as JSON string
    
    # Relationship to quotes
    quotes = relationship('Quote', secondary=quote_categories, back_populates='categories')
    
    def __repr__(self):
        return f"<Category(name='{self.name}')>"
    
    def get_keywords(self):
        return json.loads(self.keywords) if self.keywords else []
    
    def set_keywords(self, keyword_list):
        self.keywords = json.dumps(keyword_list)

class Quote(Base):
    __tablename__ = 'quotes'
    
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('authors.id'))
    year = Column(Integer)
    source = Column(String(300))
    context = Column(Text)  # Additional background info
    tags = Column(Text)  # Store as JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)
    
    # Relationships
    author = relationship('Author', back_populates='quotes')
    categories = relationship('Category', secondary=quote_categories, back_populates='quotes')
    
    def __repr__(self):
        author_name = self.author.name if self.author else "Unknown"
        return f"<Quote(id={self.id}, author='{author_name}')>"
    
    def get_tags(self):
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tag_list):
        self.tags = json.dumps(tag_list)
    
    def get_favorites_count(self):
        """Get how many users have favorited this quote"""
        return len(self.favorited_by)

# Database setup
engine = create_engine('sqlite:///quotes.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)