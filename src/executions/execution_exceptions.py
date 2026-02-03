from src.users.user_exceptions import UserPoolException

class UserAcquisitionTimeoutException(UserPoolException):
    """Raised when user acquisition times out"""
    pass

class TestExecutionNotFoundException(UserPoolException):
    """Raised when test execution is not found"""
    pass