"""API dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from services.auth_service import decode_token, get_user_by_id
from models.user import UserResponse


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_token_from_request(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[str]:
    """Extract token from Authorization header or cookie."""
    if token:
        return token
    
    token_from_cookie = request.cookies.get("access_token")
    if token_from_cookie:
        if token_from_cookie.startswith("Bearer "):
            return token_from_cookie[7:]
        return token_from_cookie
    
    return None


async def get_current_user(token: Optional[str] = Depends(get_token_from_request)) -> UserResponse:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception
    
    user = await get_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception
    
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        created_at=user["created_at"]
    )


async def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_request)
) -> Optional[UserResponse]:
    """Get the current user if authenticated, otherwise return None."""
    if not token:
        return None
    
    token_data = decode_token(token)
    if token_data is None:
        return None
    
    user = await get_user_by_id(token_data.user_id)
    if user is None:
        return None
    
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        created_at=user["created_at"]
    )
