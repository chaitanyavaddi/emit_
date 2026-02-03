import time
import random
from typing import Dict, List
from sqlalchemy.orm import Session
from src.users.user_models import CertaUser
from src.executions.execution_models import TestExecution
from src.users.user_repository import UserRepository
from src.executions.execution_repository import TestExecutionRepository
from src.users.user_exceptions import InsufficientUsersException
from src.executions.execution_exceptions import UserAcquisitionTimeoutException
from core.settings import get_settings

settings = get_settings()


class UserPoolService:
    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.test_exec_repo = TestExecutionRepository(session)
    
    def acquire_users(
        self,
        test_execution_id: str,
        role_requirements: Dict[str, int],
        max_retries: int = None
    ) -> List[CertaUser]:
        """
        Acquire users for a test execution with retry logic
        
        Args:
            test_execution_id: Unique test execution ID
            role_requirements: Dict of role -> count
            max_retries: Maximum retry attempts
            
        Returns:
            List of acquired User objects
            
        Raises:
            InsufficientUsersException: If users cannot be acquired
            UserAcquisitionTimeoutException: If acquisition times out
        """
        if max_retries is None:
            max_retries = settings.default_max_retries
        
        # Create test execution record
        test_execution = self.test_exec_repo.create_execution(
            test_execution_id=test_execution_id,
            requested_roles=role_requirements
        )
        self.session.commit()
        
        # Attempt acquisition with retries
        for attempt in range(max_retries):
            try:
                acquired_users = self._attempt_acquisition(
                    test_execution_id=test_execution_id,
                    role_requirements=role_requirements
                )
                
                # Success - mark as running
                test_execution.mark_running()
                self.session.commit()
                
                return acquired_users
                
            except InsufficientUsersException as e:
                if attempt < max_retries - 1:
                    # Wait with exponential backoff + jitter
                    wait_time = self._calculate_backoff(attempt)
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    test_execution.mark_failed()
                    self.session.commit()
                    raise UserAcquisitionTimeoutException(
                        f"Could not acquire users after {max_retries} attempts: {e}"
                    )
        
        raise UserAcquisitionTimeoutException("Unexpected error in user acquisition")
    
    def _attempt_acquisition(
        self,
        test_execution_id: str,
        role_requirements: Dict[str, int]
    ) -> List[CertaUser]:
        """Single acquisition attempt"""
        acquired_users = []
        
        try:
            for role, count in role_requirements.items():
                users = self.user_repo.acquire_users_atomic(
                    role=role,
                    count=count,
                    test_execution_id=test_execution_id
                )
                
                if len(users) < count:
                    # Not enough users, rollback
                    self.session.rollback()
                    raise InsufficientUsersException(
                        message=f"Insufficient {role} users",
                        role=role,
                        required=count,
                        available=len(users)
                    )
                
                acquired_users.extend(users)
            
            self.session.commit()
            return acquired_users
            
        except Exception as e:
            self.session.rollback()
            raise
    
    def release_users(self, test_execution_id: str) -> int:
        """
        Release all users locked by a test execution
        
        Args:
            test_execution_id: Test execution ID
            
        Returns:
            Number of users released
        """
        released_count = self.user_repo.release_by_test_execution(test_execution_id)
        
        # Update test execution status
        test_execution = self.test_exec_repo.get_by_id(test_execution_id)
        if test_execution:
            test_execution.mark_completed()
        
        self.session.commit()
        
        return released_count
    
    def get_availability(self) -> Dict[str, int]:
        """Get availability count by role"""
        return self.user_repo.get_availability_by_role()
    
    @staticmethod
    def _calculate_backoff(attempt: int) -> float:
        """Calculate exponential backoff with jitter"""
        base_wait = min(2 ** attempt, settings.max_retry_wait_seconds)
        jitter = random.uniform(0.5, 1.5)
        return base_wait * jitter