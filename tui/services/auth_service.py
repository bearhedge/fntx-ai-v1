"""
Authentication service for FNTX TUI
Manages user sessions, token storage, and authentication state
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from .api_client import get_api_client, APIError

logger = logging.getLogger(__name__)

class AuthService:
    """Manages authentication state and session persistence"""
    
    def __init__(self):
        """Initialize auth service"""
        self.api_client = get_api_client()
        self.current_user: Optional[Dict[str, Any]] = None
        self.session_file = Path.home() / ".fntx" / "session.json"
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize auth service and check for existing session"""
        await self.load_session()
        
    async def load_session(self) -> bool:
        """
        Load session from disk
        
        Returns:
            True if valid session loaded, False otherwise
        """
        if not self.session_file.exists():
            return False
            
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
                
            # Check if session is expired
            expires_at = datetime.fromisoformat(session_data.get("expires_at", ""))
            if datetime.now() >= expires_at:
                logger.info("Session expired")
                await self.clear_session()
                return False
                
            # Set tokens in API client
            self.api_client.set_auth_tokens(
                session_data["access_token"],
                session_data["refresh_token"]
            )
            
            # Try to get profile to verify session is still valid
            try:
                self.current_user = await self.api_client.get_profile()
                logger.info(f"Session restored for user: {self.current_user['username']}")
                return True
            except APIError as e:
                if e.status_code == 401:
                    # Token might be expired, try to refresh
                    try:
                        await self.refresh_token()
                        self.current_user = await self.api_client.get_profile()
                        return True
                    except:
                        logger.info("Failed to refresh token")
                        await self.clear_session()
                        return False
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            await self.clear_session()
            return False
            
    async def save_session(self, access_token: str, refresh_token: str, expires_in: int):
        """Save session to disk"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        session_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            # Set restrictive permissions (Unix-like systems)
            if hasattr(os, 'chmod'):
                os.chmod(self.session_file, 0o600)
                
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            
    async def clear_session(self):
        """Clear session from disk and memory"""
        self.current_user = None
        self.api_client.clear_auth_tokens()
        
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception as e:
                logger.error(f"Failed to delete session file: {e}")
                
    async def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        Login user
        
        Args:
            username_or_email: Username or email
            password: Password
            
        Returns:
            User data
            
        Raises:
            APIError: If login fails
        """
        try:
            # Call login API
            response = await self.api_client.login(username_or_email, password)
            
            # Save session
            await self.save_session(
                response["access_token"],
                response["refresh_token"],
                response["expires_in"]
            )
            
            # Get user profile
            self.current_user = await self.api_client.get_profile()
            
            return self.current_user
            
        except APIError as e:
            logger.error(f"Login failed: {e}")
            raise
            
    async def register(self, username: str, email: str, password: str, 
                      full_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Register new user
        
        Args:
            username: Username
            email: Email
            password: Password
            full_name: Optional full name
            
        Returns:
            User data
            
        Raises:
            APIError: If registration fails
        """
        try:
            # Call register API
            user_data = await self.api_client.register(username, email, password, full_name)
            
            # Auto-login after registration
            await self.login(username, password)
            
            return user_data
            
        except APIError as e:
            logger.error(f"Registration failed: {e}")
            raise
            
    async def logout(self):
        """Logout current user"""
        try:
            # Call logout API if we have a token
            if self.api_client.auth_token:
                await self.api_client.logout()
        except Exception as e:
            logger.error(f"Logout API call failed: {e}")
            
        # Clear local session regardless
        await self.clear_session()
        
    async def refresh_token(self):
        """Refresh access token"""
        try:
            response = await self.api_client.refresh_access_token()
            
            # Update saved session
            await self.save_session(
                response["access_token"],
                response["refresh_token"],
                response["expires_in"]
            )
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise
            
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.current_user is not None
        
    def get_username(self) -> Optional[str]:
        """Get current username"""
        if self.current_user:
            return self.current_user.get("username")
        return None
        
    def get_user_data(self) -> Optional[Dict[str, Any]]:
        """Get current user data"""
        return self.current_user


# Singleton instance
_auth_service: Optional[AuthService] = None

def get_auth_service() -> AuthService:
    """Get singleton auth service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service

async def initialize_auth_service():
    """Initialize the auth service"""
    auth_service = get_auth_service()
    await auth_service.initialize()