from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.repository import BaseRepository
from src.users.user_models import CertaUser


class UserRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(CertaUser, session)
    
    def get_available_by_role(self, role: str, limit: int) -> List[CertaUser]:
        """Get available users by role"""
        return (
            self.session.query(CertaUser)
            .filter(
                CertaUser.role == role,
                CertaUser.is_locked == False,
                CertaUser.is_healthy == True
            )
            .order_by(CertaUser.locked_at.nullsfirst())
            .limit(limit)
            .all()
        )
    
    def acquire_users_atomic(
        self,
        role: str,
        count: int,
        test_execution_id: str
    ) -> List[CertaUser]:
        """
        Atomically acquire users using FOR UPDATE SKIP LOCKED
        Returns acquired users or empty list if insufficient
        """
        result = self.session.execute(
            text("""
                UPDATE certa_users 
                SET is_locked = true,
                    locked_by = :test_id,
                    locked_at = NOW()
                WHERE id IN (
                    SELECT id 
                    FROM certa_users 
                    WHERE role = :role 
                      AND is_locked = false
                      AND is_healthy = true
                    ORDER BY locked_at NULLS FIRST
                    LIMIT :count
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id
            """),
            {
                "test_id": test_execution_id,
                "role": role,
                "count": count
            }
        )
        
        user_ids = [row.id for row in result.fetchall()]
        
        if not user_ids:
            return []
        
        return self.session.query(CertaUser).filter(CertaUser.id.in_(user_ids)).all()
    
    def release_by_test_execution(self, test_execution_id: str) -> int:
        """Release all users locked by a test execution"""
        result = self.session.execute(
            text("""
                UPDATE certa_users 
                SET is_locked = false,
                    locked_by = NULL,
                    locked_at = NULL
                WHERE locked_by = :test_id
            """),
            {"test_id": test_execution_id}
        )
        return result.rowcount
    
    def get_availability_by_role(self) -> Dict[str, int]:
        """Get count of available users by role"""
        result = self.session.execute(
            text("""
                SELECT role, COUNT(*) as count
                FROM certa_users
                WHERE is_locked = false
                  AND is_healthy = true
                GROUP BY role
            """)
        )
        return {row.role: row.count for row in result.fetchall()}