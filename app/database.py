# app/database.py
"""
Database Configuration Module

This module sets up the SQLAlchemy database engine, session management, and base class
for all database models. It follows best practices for database connection management
in FastAPI applications.

Key Components:
- Base: Declarative base class for all SQLAlchemy models
- engine: SQLAlchemy engine for database connections
- SessionLocal: Session factory for creating database sessions
- get_db: Dependency function for FastAPI routes to get database sessions
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Get database URL from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create the SQLAlchemy engine
# The engine is the starting point for any SQLAlchemy application
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a SessionLocal class
# Each instance of SessionLocal will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
# All SQLAlchemy models will inherit from this Base class
Base = declarative_base()


def get_db():
    """
    Database session dependency for FastAPI.
    
    This function creates a new database session for each request and ensures
    it's properly closed after the request is complete. It's designed to be
    used as a FastAPI dependency.
    
    Yields:
        Session: A SQLAlchemy database session
        
    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine(database_url: str = SQLALCHEMY_DATABASE_URL):
    """
    Factory function to create a new SQLAlchemy engine.
    
    This is useful for testing or when you need to create engines
    with different configurations.
    
    Args:
        database_url: The database connection URL
        
    Returns:
        Engine: A SQLAlchemy engine instance
    """
    return create_engine(database_url)


def get_sessionmaker(engine):
    """
    Factory function to create a new sessionmaker bound to the given engine.
    
    Args:
        engine: A SQLAlchemy engine instance
        
    Returns:
        sessionmaker: A configured session factory
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
