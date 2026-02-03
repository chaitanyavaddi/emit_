from typing import Optional
from sqlalchemy.orm import Session
from core.repository import BaseRepository
from src.executions.execution_models import TestExecution


class TestExecutionRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(TestExecution, session)
    
    def get_by_id(self, test_execution_id: str) -> Optional[TestExecution]:
        """Get test execution by ID"""
        return (
            self.session.query(TestExecution)
            .filter(TestExecution.id == test_execution_id)
            .first()
        )
    
    def create_execution(
        self,
        test_execution_id: str,
        requested_roles: dict
    ) -> TestExecution:
        """Create a new test execution"""
        execution = TestExecution(
            id=test_execution_id,
            requested_roles=requested_roles
        )
        execution.mark_acquiring()
        return self.create(execution)