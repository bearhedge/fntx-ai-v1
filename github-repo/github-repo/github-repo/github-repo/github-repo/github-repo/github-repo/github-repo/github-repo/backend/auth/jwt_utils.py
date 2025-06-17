"""
JWT token utilities for FNTX.ai authentication
"""
import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

class JWTManager:
    """Manages JWT token creation and validation"""
    
    def __init__(self, secret: Optional[str] = None, algorithm: str = JWT_ALGORITHM):
        """
        Initialize JWT manager
        
        Args:
            secret: JWT secret key (defaults to environment variable)
            algorithm: JWT algorithm to use
        """
        self.secret = secret or JWT_SECRET
        self.algorithm = algorithm
        
        if self.secret == "your-secret-key-change-in-production":
            logger.warning("Using default JWT secret! Change this in production!")
    
    def create_access_token(self, user_id: str, email: str, 
                           additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Create JWT access token
        
        Args:
            user_id: User ID to encode
            email: User email
            additional_claims: Additional claims to include in token
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "iat": now,  # Issued at
            "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),  # Expiration
            "type": "access"
        }
        
        # Add any additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        logger.debug(f"Created access token for user: {email}")
        return token
    
    def create_refresh_token(self, user_id: str) -> str:
        """
        Create JWT refresh token (longer expiration)
        
        Args:
            user_id: User ID to encode
            
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=30),  # 30 days
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        logger.debug(f"Created refresh token for user: {user_id}")
        return token
    
    def verify_token(self, token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            expected_type: Expected token type (access/refresh)
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            
            # Verify token type
            if payload.get("type") != expected_type:
                logger.warning(f"Invalid token type: expected {expected_type}, got {payload.get('type')}")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """
        Extract user ID from token
        
        Args:
            token: JWT token
            
        Returns:
            User ID if token is valid, None otherwise
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")
        return None
    
    def get_email_from_token(self, token: str) -> Optional[str]:
        """
        Extract email from token
        
        Args:
            token: JWT token
            
        Returns:
            Email if token is valid, None otherwise
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("email")
        return None
    
    def refresh_access_token(self, refresh_token: str, email: str) -> Optional[str]:
        """
        Create new access token from refresh token
        
        Args:
            refresh_token: Valid refresh token
            email: User email (for new access token)
            
        Returns:
            New access token if refresh token is valid, None otherwise
        """
        payload = self.verify_token(refresh_token, expected_type="refresh")
        if payload:
            user_id = payload.get("sub")
            return self.create_access_token(user_id, email)
        return None

# Singleton instance
_jwt_manager = None

def get_jwt_manager() -> JWTManager:
    """Get singleton instance of JWTManager"""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager