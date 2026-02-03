
class UserPoolException(Exception):
    """Base exception for user pool operations"""
    pass


class InsufficientUsersException(UserPoolException):
    """Raised when not enough users are available"""
    def __init__(self, message: str, role: str = None, required: int = None, available: int = None):
        super().__init__(message)
        self.role = role
        self.required = required
        self.available = available