"""
Authentication API endpoints for FNTX trading system
Handles user registration, login, logout, and session management
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import logging
import re
from ipaddress import ip_address

from ..core.auth.jwt_utils import get_jwt_manager
from ..core.auth.password_utils import password_manager
from ..data.data.trade_db import get_trade_db_connection

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Security scheme
security = HTTPBearer()

# Pydantic models for request/response
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        is_valid, issues = password_manager.validate_password_strength(v)
        if not is_valid:
            raise ValueError('; '.join(issues))
        return v

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Helper functions
def hash_token(token: str) -> str:
    """Create a hash of the token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def log_auth_attempt(conn, username_or_email: str, ip: str, user_agent: str, 
                    attempt_type: str, success: bool, failure_reason: Optional[str] = None):
    """Log authentication attempt for security monitoring"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO auth_attempts 
                (username_or_email, ip_address, user_agent, attempt_type, success, failure_reason)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username_or_email, ip, user_agent, attempt_type, success, failure_reason))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log auth attempt: {e}")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return current user"""
    token = credentials.credentials
    jwt_manager = get_jwt_manager()
    
    payload = jwt_manager.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload

# API Endpoints
@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, request: Request):
    """Register a new user"""
    conn = get_trade_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Get client info
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # Check if username or email already exists
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (user_data.username, user_data.email)
            )
            if cursor.fetchone():
                log_auth_attempt(conn, user_data.username, client_ip, user_agent, 
                               "register", False, "Username or email already exists")
                raise HTTPException(status_code=400, detail="Username or email already exists")
        
        # Hash password
        password_hash = password_manager.hash_password(user_data.password)
        
        # Create user
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, username, email, is_active, is_verified, created_at, last_login
            """, (user_data.username, user_data.email, password_hash))
            
            user = cursor.fetchone()
            user_id = user[0]
            
            # Create user profile if full_name provided
            if user_data.full_name:
                cursor.execute("""
                    INSERT INTO user_profiles (user_id, full_name)
                    VALUES (%s, %s)
                """, (user_id, user_data.full_name))
            
            conn.commit()
            
            # Log successful registration
            log_auth_attempt(conn, user_data.username, client_ip, user_agent, 
                           "register", True)
            
            # Return user response
            return UserResponse(
                id=user[0],
                username=user[1],
                email=user[2],
                full_name=user_data.full_name,
                is_active=user[3],
                is_verified=user[4],
                created_at=user[5],
                last_login=user[6]
            )
            
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")
    finally:
        conn.close()

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
    """Authenticate user and return JWT tokens"""
    conn = get_trade_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Get client info
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # Find user by username or email
        with conn.cursor() as cursor:
            if "@" in user_data.username_or_email:
                cursor.execute(
                    "SELECT id, username, email, password_hash, is_active FROM users WHERE email = %s",
                    (user_data.username_or_email,)
                )
            else:
                cursor.execute(
                    "SELECT id, username, email, password_hash, is_active FROM users WHERE username = %s",
                    (user_data.username_or_email,)
                )
            
            user = cursor.fetchone()
            
            if not user:
                log_auth_attempt(conn, user_data.username_or_email, client_ip, user_agent, 
                               "login", False, "User not found")
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            user_id, username, email, password_hash, is_active = user
            
            # Check if user is active
            if not is_active:
                log_auth_attempt(conn, user_data.username_or_email, client_ip, user_agent, 
                               "login", False, "Account inactive")
                raise HTTPException(status_code=401, detail="Account is inactive")
            
            # Verify password
            if not password_manager.verify_password(user_data.password, password_hash):
                log_auth_attempt(conn, user_data.username_or_email, client_ip, user_agent, 
                               "login", False, "Invalid password")
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Create JWT tokens
            jwt_manager = get_jwt_manager()
            access_token = jwt_manager.create_access_token(
                user_id=str(user_id),
                email=email,
                additional_claims={"username": username}
            )
            refresh_token = jwt_manager.create_refresh_token(user_id=str(user_id))
            
            # Store session
            expires_at = datetime.utcnow() + timedelta(days=7)
            cursor.execute("""
                INSERT INTO user_sessions 
                (user_id, token_hash, refresh_token_hash, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id, 
                hash_token(access_token), 
                hash_token(refresh_token),
                client_ip,
                user_agent,
                expires_at
            ))
            
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user_id,)
            )
            
            conn.commit()
            
            # Log successful login
            log_auth_attempt(conn, user_data.username_or_email, client_ip, user_agent, 
                           "login", True)
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=7 * 24 * 3600  # 7 days in seconds
            )
            
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")
    finally:
        conn.close()

@router.post("/logout")
async def logout(current_user: Dict = Depends(get_current_user), 
                credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user and invalidate token"""
    conn = get_trade_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        token_hash = hash_token(credentials.credentials)
        
        with conn.cursor() as cursor:
            # Revoke the session
            cursor.execute("""
                UPDATE user_sessions 
                SET revoked_at = CURRENT_TIMESTAMP 
                WHERE token_hash = %s AND revoked_at IS NULL
            """, (token_hash,))
            
            conn.commit()
            
            return {"message": "Successfully logged out"}
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")
    finally:
        conn.close()

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    conn = get_trade_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        jwt_manager = get_jwt_manager()
        
        # Verify refresh token
        payload = jwt_manager.verify_token(refresh_request.refresh_token, expected_type="refresh")
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_id = payload.get("sub")
        
        # Check if session exists and is valid
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.email, u.username 
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.refresh_token_hash = %s 
                AND s.expires_at > CURRENT_TIMESTAMP 
                AND s.revoked_at IS NULL
            """, (hash_token(refresh_request.refresh_token),))
            
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid or expired session")
            
            # Create new access token
            new_access_token = jwt_manager.create_access_token(
                user_id=str(user[0]),
                email=user[1],
                additional_claims={"username": user[2]}
            )
            
            # Update session with new access token
            cursor.execute("""
                UPDATE user_sessions 
                SET token_hash = %s 
                WHERE refresh_token_hash = %s
            """, (hash_token(new_access_token), hash_token(refresh_request.refresh_token)))
            
            conn.commit()
            
            return TokenResponse(
                access_token=new_access_token,
                refresh_token=refresh_request.refresh_token,
                expires_in=7 * 24 * 3600
            )
            
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")
    finally:
        conn.close()

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: Dict = Depends(get_current_user)):
    """Get current user profile"""
    conn = get_trade_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        user_id = current_user.get("sub")
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, u.is_active, u.is_verified, 
                       u.created_at, u.last_login, p.full_name
                FROM users u
                LEFT JOIN user_profiles p ON u.id = p.user_id
                WHERE u.id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return UserResponse(
                id=user[0],
                username=user[1],
                email=user[2],
                is_active=user[3],
                is_verified=user[4],
                created_at=user[5],
                last_login=user[6],
                full_name=user[7]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")
    finally:
        conn.close()

# Health check endpoint
@router.get("/health")
async def health_check():
    """Check if auth service is running"""
    return {"status": "healthy", "service": "authentication"}