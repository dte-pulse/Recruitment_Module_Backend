"""
Simplified Admin Authentication Module
- Single admin login from .env credentials
- No user table verification
- JWT token with role (hr)
- 7-day cookie expiry
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# CONFIGURATION FROM .ENV
# ============================================================
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

# Admin credentials from .env (NO DATABASE LOOKUP)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@pulsepharma.com").lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "SecurePassword@2025")

# ============================================================
# SECURITY SETUP
# ============================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ============================================================
# PYDANTIC MODELS
# ============================================================
class Token(BaseModel):
    """JWT Token Response"""
    access_token: str
    token_type: str
    role: str
    email: str
    expires_in: int


class TokenData(BaseModel):
    """Decoded JWT Token Data"""
    email: Optional[str] = None
    role: Optional[str] = None


class AdminLoginRequest(BaseModel):
    """Admin login request"""
    email: str
    password: str


# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================
def verify_admin_credentials(email: str, password: str) -> bool:
    """Verify admin email and password against .env credentials"""
    email_match = email.strip().lower() == ADMIN_EMAIL
    password_match = password.strip() == ADMIN_PASSWORD
    return email_match and password_match


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        
        if email is None:
            raise credentials_exception
        
        return TokenData(email=email, role=role)
    
    except JWTError:
        raise credentials_exception


# ============================================================
# DEPENDENCY INJECTIONS
# ============================================================
async def get_current_admin(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Get current admin from JWT token"""
    token_data = decode_token(token)
    
    if token_data.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return token_data


# ============================================================
# COOKIE CONFIGURATION FOR FRONTEND
# ============================================================
COOKIE_CONFIG = {
    "key": "access_token",
    "max_age": 7 * 24 * 60 * 60,  # 7 days in seconds
    "expires": 7 * 24 * 60 * 60,
    "path": "/",
    "domain": None,
    "secure": False,  # Set to True in production with HTTPS
    "httponly": True,  # Prevent JavaScript access for security
    "samesite": "lax",  # CSRF protection
}

ROLE_COOKIE_CONFIG = {
    "key": "user_role",
    "max_age": 7 * 24 * 60 * 60,
    "expires": 7 * 24 * 60 * 60,
    "path": "/",
    "domain": None,
    "secure": False,
    "httponly": False,  # Allow JavaScript to read role
    "samesite": "lax",
}

EMAIL_COOKIE_CONFIG = {
    "key": "user_email",
    "max_age": 7 * 24 * 60 * 60,
    "expires": 7 * 24 * 60 * 60,
    "path": "/",
    "domain": None,
    "secure": False,
    "httponly": False,  # Allow JavaScript to read email
    "samesite": "lax",
}
