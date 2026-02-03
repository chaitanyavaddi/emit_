from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List
from core.dependencies import get_db_session, get_user_pool_service
from src.pools.pool_service import UserPoolService
from src.executions.execution_schemas import (
    CertaUserAcquisitionRequest,
    CertaUserAcquisitionResponse,
    CertaUserReleaseRequest,
    CertaUserReleaseResponse
)
from src.users.user_schemas import CertaUserResponse, CertaUserAvailability
from src.users.user_exceptions import InsufficientUsersException
from src.executions.execution_exceptions import UserAcquisitionTimeoutException
from datetime import datetime
from sqlalchemy import func
from src.users.user_models import CertaUser

router = APIRouter(prefix="/testdata/pool", tags=["testdata pool"])


@router.post("/acquire", response_model=CertaUserAcquisitionResponse)
def acquire_users(
    request: CertaUserAcquisitionRequest,
    session: Session = Depends(get_db_session)
):
    """
    Acquire (lock) users from the pool for a test execution
    
    This will:
    1. Create a test execution record (if not exists)
    2. Attempt to lock the required users
    3. Retry with exponential backoff if users not available
    
    - **test_execution_id**: Unique identifier for the test
    - **role_requirements**: Dictionary mapping roles to required counts
    - **max_retries**: Maximum number of retry attempts (default: 10)
    
    Example:
```json
    {
        "test_execution_id": "test_abc_123",
        "role_requirements": {"client": 2, "vendor": 1},
        "max_retries": 10
    }
```
    """
    service = get_user_pool_service(session)
    
    try:
        users = service.acquire_users(
            test_execution_id=request.test_execution_id,
            role_requirements=request.role_requirements,
            max_retries=request.max_retries
        )
        
        return CertaUserAcquisitionResponse(
            test_execution_id=request.test_execution_id,
            users=[CertaUserResponse.model_validate(u) for u in users],
            acquired_at=datetime.utcnow(),
            status="success"
        )
        
    except InsufficientUsersException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "role": e.role,
                "required": e.required,
                "available": e.available
            }
        )
    except UserAcquisitionTimeoutException as e:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=str(e)
        )


@router.post("/release", response_model=CertaUserReleaseResponse)
def release_users(
    request: CertaUserReleaseRequest,
    session: Session = Depends(get_db_session)
):
    """
    Release (unlock) users locked by a test execution
    
    This will:
    1. Unlock all users locked by the test execution
    2. Mark the test execution as completed
    
    - **test_execution_id**: Test execution identifier
    
    Example:
```json
    {
        "test_execution_id": "test_abc_123"
    }
```
    """
    service = get_user_pool_service(session)
    
    released_count = service.release_users(request.test_execution_id)
    
    if released_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No users found for execution {request.test_execution_id}"
        )
    
    return CertaUserReleaseResponse(
        test_execution_id=request.test_execution_id,
        released_count=released_count,
        released_at=datetime.utcnow()
    )


@router.get("/availability", response_model=Dict[str, int])
def get_availability(session: Session = Depends(get_db_session)):
    """
    Get count of available (unlocked) users by role
    
    Returns a dictionary mapping role names to available user counts
    
    Example response:
```json
    {
        "client": 5,
        "vendor": 3,
        "admin": 2
    }
```
    """
    service = get_user_pool_service(session)
    return service.get_availability()


@router.get("/availability/detailed", response_model=List[CertaUserAvailability])
def get_detailed_availability(session: Session = Depends(get_db_session)):
    """
    Get detailed availability statistics by role
    
    Returns counts of available, locked, and total users for each role
    """
    result = session.query(
        CertaUser.role,
        func.count(CertaUser.id).label('total_count'),
        func.sum(func.cast(CertaUser.is_locked, func.INTEGER)).label('locked_count'),
        func.sum(func.cast(~CertaUser.is_locked, func.INTEGER)).label('available_count')
    ).filter(CertaUser.is_healthy == True).group_by(CertaUser.role).all()
    
    return [
        CertaUserAvailability(
            role=row.role,
            total_count=row.total_count,
            locked_count=row.locked_count or 0,
            available_count=row.available_count or 0
        )
        for row in result
    ]


@router.get("/status")
def get_pool_status(session: Session = Depends(get_db_session)):
    """
    Get overall pool status
    
    Returns:
    - Total users count
    - Available users count
    - Locked users count
    - Unhealthy users count
    - Active executions count
    """
    total_users = session.query(func.count(CertaUser.id)).scalar()
    locked_users = session.query(func.count(CertaUser.id)).filter(CertaUser.is_locked == True).scalar()
    unhealthy_users = session.query(func.count(CertaUser.id)).filter(CertaUser.is_healthy == False).scalar()
    
    from app.models.test_execution import TestExecution, TestExecutionStatus
    active_executions = session.query(func.count(TestExecution.id)).filter(
        TestExecution.status.in_([TestExecutionStatus.ACQUIRING, TestExecutionStatus.RUNNING])
    ).scalar()
    
    return {
        "total_users": total_users,
        "available_users": total_users - locked_users - unhealthy_users,
        "locked_users": locked_users,
        "unhealthy_users": unhealthy_users,
        "active_executions": active_executions,
        "utilization_percent": round((locked_users / total_users * 100) if total_users > 0 else 0, 2)
    }