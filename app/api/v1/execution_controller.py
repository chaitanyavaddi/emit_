from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.dependencies import get_db_session
from src.executions.execution_repository import TestExecutionRepository
from src.users.user_repository import UserRepository
from src.executions.execution_models import TestExecution, TestExecutionStatus
from src.executions.execution_schemas import (
    TestExecutionResponse,
    TestExecutionCreate,
    TestExecutionDetail
)
from src.users.user_schemas import CertaUserResponse

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("", response_model=List[TestExecutionResponse])
def list_executions(
    status: Optional[TestExecutionStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session)
):
    """
    Get list of all test executions with optional filters
    
    - **status**: Filter by execution status (ACQUIRING, RUNNING, COMPLETED, FAILED)
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    query = session.query(TestExecution).order_by(TestExecution.created_at.desc())
    
    if status:
        query = query.filter(TestExecution.status == status)
    
    executions = query.offset(skip).limit(limit).all()
    
    return [TestExecutionResponse.model_validate(e) for e in executions]


@router.get("/{execution_id}", response_model=TestExecutionDetail)
def get_execution(
    execution_id: str,
    session: Session = Depends(get_db_session)
):
    """
    Get detailed information about a specific test execution
    
    Includes the list of users assigned to this execution
    """
    repo = TestExecutionRepository(session)
    user_repo = UserRepository(session)
    
    execution = repo.get_by_id(execution_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with id {execution_id} not found"
        )
    
    # Get assigned users
    from src.users.user_models import CertaUser
    assigned_users = session.query(CertaUser).filter(CertaUser.locked_by == execution_id).all()
    
    response = TestExecutionDetail.model_validate(execution)
    response.assigned_users = [CertaUserResponse.model_validate(u) for u in assigned_users]
    
    return response


@router.post("", response_model=TestExecutionResponse, status_code=status.HTTP_201_CREATED)
def create_execution(
    execution_data: TestExecutionCreate,
    session: Session = Depends(get_db_session)
):
    """
    Create a new test execution record
    
    Note: This only creates the record. Use /pool/acquire to lock users.
    
    - **id**: Unique execution identifier
    - **requested_roles**: Dictionary of role requirements
    """
    repo = TestExecutionRepository(session)
    
    # Check if execution already exists
    existing = repo.get_by_id(execution_data.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Execution with id {execution_data.id} already exists"
        )
    
    # Create execution
    execution = repo.create_execution(
        test_execution_id=execution_data.id,
        requested_roles=execution_data.requested_roles
    )
    repo.commit()
    
    return TestExecutionResponse.model_validate(execution)


@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_execution(
    execution_id: str,
    force: bool = Query(False, description="Force delete even if users are locked"),
    session: Session = Depends(get_db_session)
):
    """
    Delete a test execution
    
    - **force**: If true, will also release any locked users
    """
    repo = TestExecutionRepository(session)
    user_repo = UserRepository(session)
    
    execution = repo.get_by_id(execution_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with id {execution_id} not found"
        )
    
    from src.users.user_models import CertaUser
    locked_users = session.query(CertaUser).filter(CertaUser.locked_by == execution_id).count()
    
    if locked_users > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete execution: {locked_users} users still locked. Use force=true to release them."
        )
    
    # Release users if force=true
    if force and locked_users > 0:
        user_repo.release_by_test_execution(execution_id)
    
    repo.delete(execution)
    repo.commit()


@router.get("/stats/summary")
def get_execution_stats(session: Session = Depends(get_db_session)):
    """
    Get execution statistics summary
    
    Returns counts by status and average duration
    """
    from sqlalchemy import func
    
    stats = session.query(
        TestExecution.status,
        func.count(TestExecution.id).label('count'),
        func.avg(
            func.extract('epoch', TestExecution.completed_at - TestExecution.acquired_at)
        ).label('avg_duration_seconds')
    ).group_by(TestExecution.status).all()
    
    return {
        "by_status": [
            {
                "status": stat.status.value,
                "count": stat.count,
                "avg_duration_seconds": float(stat.avg_duration_seconds) if stat.avg_duration_seconds else None
            }
            for stat in stats
        ],
        "total": sum(stat.count for stat in stats)
    }