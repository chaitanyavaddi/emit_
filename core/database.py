from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from core.settings import get_settings

settings = get_settings()

Base = declarative_base()

class Database:
    def __init__(self):
        self.engine = create_engine(
            settings.database_url,
            pool_pre_ping=settings.db_pool_pre_ping,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            echo=settings.debug  # Log SQL queries in debug mode
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_all(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)


# Singleton instance
db = Database()