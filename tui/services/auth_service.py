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

from .supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class AuthService:
    """Manages authentication state and session persistence"""
    
    def __init__(self):
        """Initialize auth service"""
        self.supabase_client = get_supabase_client()
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
                
            # Set tokens in Supabase client
            self.supabase_client.access_token = session_data["access_token"]
            self.supabase_client.refresh_token = session_data["refresh_token"]
            
            # Try to get user to verify session is still valid
            try:
                self.current_user = await self.supabase_client.get_user()
                if self.current_user:
                    username = self.supabase_client.get_username() or self.current_user.get("email")
                    logger.info(f"Session restored for user: {username}")
                    return True
                else:
                    logger.info("Session invalid or expired")
                    await self.clear_session()
                    return False
            except Exception as e:
                logger.info(f"Failed to verify session: {e}")
                await self.clear_session()
                return False
                    
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
        self.supabase_client.access_token = None
        self.supabase_client.refresh_token = None
        
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception as e:
                logger.error(f"Failed to delete session file: {e}")
                
    async def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        Login user
        
        Args:
            username_or_email: Username or email (Supabase requires email)
            password: Password
            
        Returns:
            User data
            
        Raises:
            Exception: If login fails
        """
        try:
            # Call Supabase login (requires email, not username)
            response = await self.supabase_client.login(username_or_email, password)
            
            # Save session
            await self.save_session(
                response.get("access_token"),
                response.get("refresh_token"),
                response.get("expires_in", 3600)  # Default to 1 hour if not provided
            )
            
            # Get user data
            self.current_user = response.get("user")
            
            return self.current_user
            
        except Exception as e:
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
            Exception: If registration fails
        """
        try:
            # Call Supabase register
            response = await self.supabase_client.register(email, password, username, full_name)
            
            # Save session if tokens are returned (Supabase auto-logs in after registration)
            if response.get("access_token"):
                await self.save_session(
                    response.get("access_token"),
                    response.get("refresh_token"),
                    response.get("expires_in", 3600)
                )
                self.current_user = response.get("user")
            else:
                # If no auto-login, try to login
                await self.login(email, password)
            
            return self.current_user or response.get("user")
            
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            raise
            
    async def logout(self):
        """Logout current user"""
        try:
            # Call Supabase logout if we have a token
            if self.supabase_client.access_token:
                await self.supabase_client.logout()
        except Exception as e:
            logger.error(f"Logout API call failed: {e}")
            
        # Clear local session regardless
        await self.clear_session()
        
    # Token refresh is handled by Supabase automatically
            
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.current_user is not None
        
    def get_username(self) -> Optional[str]:
        """Get current username"""
        if self.current_user:
            # Try to get username from user metadata first
            if "user_metadata" in self.current_user:
                username = self.current_user["user_metadata"].get("username")
                if username:
                    return username
            # Fall back to email
            return self.current_user.get("email")
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