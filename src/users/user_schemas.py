from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional


class CertaUserBase(BaseModel):
    email: EmailStr
    role: str = Field(..., min_length=1, max_length=50)
    tenant: Optional[str] = None
    domain: Optional[str] = None
    tags: Optional[str] = None


class CertaUserCreate(CertaUserBase):
    password: str = Field(..., min_length=6)


class CertaUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[str] = Field(None, min_length=1, max_length=50)
    tenant: Optional[str] = None
    domain: Optional[str] = None
    tags: Optional[str] = None
    is_healthy: Optional[bool] = None


class CertaUserResponse(CertaUserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_locked: bool
    is_healthy: bool
    role: str
    password: str
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CertaUserAvailability(BaseModel):
    role: str
    available_count: int
    locked_count: int
    total_count: int