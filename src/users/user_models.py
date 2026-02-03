from sqlalchemy import Boolean, Column, String, BigInteger, DateTime, Text
from sqlalchemy.sql import func
from core.database import Base
from datetime import datetime
from typing import Optional

class CertaUser(Base):
    __tablename__ = "certa_users"

    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(Text, nullable=False, unique=True)
    password = Column(Text, nullable=False)
    role = Column(Text, nullable=False, index=True)
    tenant = Column(Text)
    domain = Column(Text)
    tags = Column(Text)
    is_locked = Column(Boolean, default=False, nullable=False, index=True)
    is_healthy = Column(Boolean, default=True, nullable=False)
    locked_by = Column(String(255), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def lock(self, test_execution_id: str) -> None:
        self.is_locked = True
        self.locked_by = test_execution_id
        self.locked_at = datetime.utcnow()
    
    def unlock(self) -> None:
        self.is_locked = False
        self.locked_by = None
        self.locked_at = None
    
    @property
    def is_available(self) -> bool:
        return not self.is_locked and self.is_healthy
    
    def __repr__(self) -> str:
        return f"<CertaUser(id={self.id}, email={self.email}, role={self.role}, locked={self.is_locked})>"