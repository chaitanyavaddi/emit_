from typing import Generator
from sqlalchemy.orm import Session
from core.database import db
from src.pools.pool_service import UserPoolService


def get_db_session() -> Generator[Session, None, None]:
    """Dependency for database session"""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()


def get_user_pool_service(
    session: Session = None
) -> UserPoolService:
    """Dependency for user pool service"""
    return UserPoolService(session)