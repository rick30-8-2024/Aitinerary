"""Authentication service for password hashing and JWT token management."""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from bson import ObjectId

from config.settings import settings
from config.database import database
from models.user import UserCreate, UserInDB, UserResponse, TokenData


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        return None


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get a user from database by email."""
    collection = database.get_collection("users")
    user = await collection.find_one({"email": email})
    return user


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get a user from database by ID."""
    collection = database.get_collection("users")
    try:
        user = await collection.find_one({"_id": ObjectId(user_id)})
        return user
    except:
        return None


async def create_user(user_data: UserCreate) -> UserResponse:
    """Create a new user in the database."""
    collection = database.get_collection("users")
    
    user_doc = {
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "created_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(user_doc)
    
    return UserResponse(
        id=str(result.inserted_id),
        email=user_data.email,
        created_at=user_doc["created_at"]
    )


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate a user with email and password."""
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


async def create_email_index():
    """Create unique index on email field for fast lookups."""
    try:
        collection = database.get_collection("users")
        await collection.create_index("email", unique=True)
        return True
    except Exception as e:
        print(f"Warning: Could not create email index: {e}")
        return False
