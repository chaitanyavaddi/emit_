from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.dependencies import get_db_session
from src.users.user_repository import UserRepository
from src.users.user_models import CertaUser
from src.users.user_schemas import CertaUserResponse, CertaUserCreate, CertaUserUpdate
from datetime import datetime

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[CertaUserResponse])
def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    is_locked: Optional[bool] = Query(None, description="Filter by lock status"),
    is_healthy: Optional[bool] = Query(None, description="Filter by health status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session)
):
    """
    Get list of all users with optional filters
    
    - **role**: Filter by user role (client, vendor, admin, etc.)
    - **is_locked**: Filter by lock status
    - **is_healthy**: Filter by health status
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    repo = UserRepository(session)
    
    query = session.query(CertaUser)
    
    # Apply filters
    if role:
        query = query.filter(CertaUser.role == role)
    if is_locked is not None:
        query = query.filter(CertaUser.is_locked == is_locked)
    if is_healthy is not None:
        query = query.filter(CertaUser.is_healthy == is_healthy)
    
    # Pagination
    users = query.offset(skip).limit(limit).all()
    
    return [CertaUserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=CertaUserResponse)
def get_user(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """Get a specific user by ID"""
    repo = UserRepository(session)
    user = repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    return CertaUserResponse.model_validate(user)


@router.post("", response_model=CertaUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: CertaUserCreate,
    session: Session = Depends(get_db_session)
):
    """
    Create a new user
    
    - **email**: User email (must be unique)
    - **password**: User password
    - **role**: User role (client, vendor, admin, etc.)
    - **tenant**: Optional tenant identifier
    - **domain**: Optional domain
    - **tags**: Optional tags
    """
    repo = UserRepository(session)
    
    # Check if email already exists
    existing = session.query(CertaUser).filter(CertaUser.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists"
        )
    
    # Create user
    user = CertaUser(**user_data.model_dump())
    created_user = repo.create(user)
    repo.commit()
    
    return CertaUserResponse.model_validate(created_user)


@router.put("/{user_id}", response_model=CertaUserResponse)
def update_user(
    user_id: int,
    user_data: CertaUserUpdate,
    session: Session = Depends(get_db_session)
):
    """
    Update an existing user
    
    Only provided fields will be updated (partial update)
    """
    repo = UserRepository(session)
    user = repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Update only provided fields
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    updated_user = repo.update(user)
    repo.commit()
    
    return CertaUserResponse.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Delete a user
    
    Note: Cannot delete a user that is currently locked
    """
    repo = UserRepository(session)
    user = repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete user {user_id}: currently locked by {user.locked_by}"
        )
    
    repo.delete(user)
    repo.commit()


@router.get("/{email}", response_model=CertaUserResponse)
def get_user_by_email(
    email: str,
    session: Session = Depends(get_db_session)
):
    """Get a user by email address"""
    user = session.query(CertaUser).filter(CertaUser.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found"
        )
    
    return CertaUserResponse.model_validate(user)


@router.post("/bulk", response_model=List[CertaUserResponse], status_code=status.HTTP_201_CREATED)
def create_users_bulk(
    users_data: List[CertaUserCreate],
    session: Session = Depends(get_db_session)
):
    """
    Create multiple users at once
    
    Useful for initial setup or bulk imports
    """
    repo = UserRepository(session)
    created_users = []
    
    # Check for duplicate emails in request
    emails = [u.email for u in users_data]
    if len(emails) != len(set(emails)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate emails in request"
        )
    
    # Check for existing emails
    existing = session.query(CertaUser.email).filter(CertaUser.email.in_(emails)).all()
    if existing:
        existing_emails = [e[0] for e in existing]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Users already exist with emails: {existing_emails}"
        )
    
    # Create all users
    for user_data in users_data:
        user = CertaUser(**user_data.model_dump())
        created_user = repo.create(user)
        created_users.append(created_user)
    
    repo.commit()
    
    return [CertaUserResponse.model_validate(u) for u in created_users]