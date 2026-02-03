from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from core.database import Base
from enum import Enum
from typing import Dict
from datetime import datetime


class TestExecutionStatus(str, Enum):
    ACQUIRING = "acquiring"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TestExecution(Base):
    __tablename__ = "certa_test_executions"
    
    id = Column(String(255), primary_key=True)
    requested_roles = Column(JSONB, nullable=False)
    status = Column(
        SQLEnum(TestExecutionStatus),
        default=TestExecutionStatus.ACQUIRING,
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acquired_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def mark_acquiring(self) -> None:
        """Mark test as acquiring users"""
        self.status = TestExecutionStatus.ACQUIRING
    
    def mark_running(self) -> None:
        """Mark test as running with acquired users"""
        self.status = TestExecutionStatus.RUNNING
        self.acquired_at = datetime.utcnow()
    
    def mark_completed(self) -> None:
        """Mark test as completed"""
        self.status = TestExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self) -> None:
        """Mark test as failed"""
        self.status = TestExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
    
    @property
    def duration(self) -> float:
        """Get execution duration in seconds"""
        if self.acquired_at and self.completed_at:
            return (self.completed_at - self.acquired_at).total_seconds()
        return 0.0
    
    def __repr__(self) -> str:
        return f"<TestExecution(id={self.id}, status={self.status})>"