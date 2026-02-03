from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional
from datetime import datetime
from src.executions.execution_models import TestExecutionStatus
from src.users.user_schemas import CertaUserResponse


class TestExecutionBase(BaseModel):
    id: str = Field(..., min_length=1, max_length=255)
    requested_roles: Dict[str, int] = Field(
        ...,
        description="Role requirements",
        example={"client": 2, "vendor": 1}
    )


class TestExecutionCreate(TestExecutionBase):
    pass


class TestExecutionResponse(TestExecutionBase):
    model_config = ConfigDict(from_attributes=True)
    
    status: TestExecutionStatus
    created_at: datetime
    acquired_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TestExecutionDetail(TestExecutionResponse):
    """Execution details with assigned users"""
    assigned_users: List[CertaUserResponse] = []
    duration_seconds: Optional[float] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.acquired_at and self.completed_at:
            return (self.completed_at - self.acquired_at).total_seconds()
        return None


class CertaUserAcquisitionRequest(BaseModel):
    test_execution_id: str = Field(..., min_length=1, max_length=255)
    role_requirements: Dict[str, int] = Field(
        ...,
        description="Role requirements",
        example={"client": 2, "vendor": 1}
    )
    max_retries: int = Field(default=10, ge=1, le=50)


class CertaUserAcquisitionResponse(BaseModel):
    test_execution_id: str
    users: List[CertaUserResponse]
    acquired_at: datetime
    status: str


class CertaUserReleaseRequest(BaseModel):
    test_execution_id: str


class CertaUserReleaseResponse(BaseModel):
    test_execution_id: str
    released_count: int
    released_at: datetime