"""Authentication router for user registration, login, and session management."""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm

from models.user import UserCreate, UserLogin, UserResponse, Token
from services.auth_service import (
    create_user,
    authenticate_user,
    create_access_token,
    get_user_by_email,
    decode_token
)
from api.dependencies import get_current_user, get_token_from_request
from config.settings import settings


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user account."""
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = await create_user(user_data)
    return user


@router.post("/login", response_model=Token)
async def login(response: Response, user_data: UserLogin):
    """Authenticate user and return JWT token."""
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "email": user["email"]},
        expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return Token(access_token=access_token)


@router.post("/login/form", response_model=Token)
async def login_form(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user via OAuth2 form and return JWT token (for Swagger UI)."""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "email": user["email"]},
        expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return Token(access_token=access_token)


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing the session cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@router.get("/verify")
async def verify_token(token: str = Depends(get_token_from_request)):
    """Verify if the current token is valid."""
    if not token:
        return {"valid": False, "message": "No token provided"}
    
    token_data = decode_token(token)
    if token_data is None:
        return {"valid": False, "message": "Invalid or expired token"}
    
    return {"valid": True, "user_id": token_data.user_id, "email": token_data.email}
