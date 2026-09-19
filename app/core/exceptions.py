# app/core/exceptions.py
from fastapi import HTTPException, status

class InvalidCredentialsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

class RoleMismatchException(HTTPException):
    def __init__(self, expected_role: str, actual_role: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role mismatch. Expected {expected_role}, but account is {actual_role}."
        )

class AccountLockedException(HTTPException):
    def __init__(self, remaining_seconds: int):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCOUNT_LOCKED",
                "message": f"Account locked due to too many failed attempts. Try again in {remaining_seconds} seconds.",
                "remaining_seconds": remaining_seconds
            }
        )