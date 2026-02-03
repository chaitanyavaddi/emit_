from typing import List, Optional, Any
from sqlalchemy.orm import Session
from core.database import Base

class BaseRepository:
    """Base repository for common CRUD operations"""
    
    def __init__(self, model, session: Session):
        """
        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session
    
    def get(self, id: int) -> Optional[Any]:
        """Get entity by ID"""
        return self.session.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self) -> List[Any]:
        """Get all entities"""
        return self.session.query(self.model).all()
    
    def create(self, entity: Any) -> Any:
        """Create new entity"""
        self.session.add(entity)
        self.session.flush()
        return entity
    
    def update(self, entity: Any) -> Any:
        """Update entity"""
        self.session.merge(entity)
        self.session.flush()
        return entity
    
    def delete(self, entity: Any) -> None:
        """Delete entity"""
        self.session.delete(entity)
        self.session.flush()
    
    def commit(self) -> None:
        """Commit transaction"""
        self.session.commit()
    
    def rollback(self) -> None:
        """Rollback transaction"""
        self.session.rollback()