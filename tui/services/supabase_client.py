"""
Supabase Client for FNTX Authentication
Handles authentication with Supabase backend
"""
import os
import aiohttp
import json
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase authentication client"""
    
    def __init__(self):
        """Initialize Supabase client with project credentials"""
        # Supabase project configuration
        self.base_url = "https://xzfjhhnmnlsgbrmwojyi.supabase.co"
        self.anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh6ZmpoaG5tbmxzZ2JybXdvanlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwMDc1MjcsImV4cCI6MjA3MTU4MzUyN30.uVNx-RAB9ZnI4T-Vh5ZEaTSMR9JWYkkrG4xjLhP-1vE"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user: Optional[Dict[str, Any]] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        
    async def start(self):
        """Start the client session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Close the client session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    def _get_headers(self, include_auth: bool = False) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "apikey": self.anon_key,
            "Content-Type": "application/json"
        }
        
        if include_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
            
        return headers
        
    async def register(self, email: str, password: str, username: str = None, 
                      full_name: str = None) -> Dict[str, Any]:
        """
        Register a new user with Supabase Auth
        
        Args:
            email: User's email
            password: User's password
            username: Optional username (stored in user metadata)
            full_name: Optional full name (stored in user metadata)
            
        Returns:
            Dict with user data and tokens
        """
        if not self.session:
            await self.start()
            
        # Prepare user metadata
        user_metadata = {}
        if username:
            user_metadata["username"] = username
        if full_name:
            user_metadata["full_name"] = full_name
            
        # Prepare request data
        data = {
            "email": email,
            "password": password,
            "data": user_metadata  # Supabase stores extra data in user metadata
        }
        
        url = f"{self.base_url}/auth/v1/signup"
        headers = self._get_headers()
        
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    result = json.loads(response_text)
                    # Store tokens and user data
                    self.access_token = result.get("access_token")
                    self.refresh_token = result.get("refresh_token")
                    self.user = result.get("user")
                    
                    logger.info(f"User registered successfully: {email}")
                    return result
                else:
                    logger.error(f"Registration failed: {response.status} - {response_text}")
                    error_data = json.loads(response_text) if response_text else {}
                    error_msg = error_data.get('msg', 'Unknown error')
                    
                    # Provide more helpful error messages
                    if "email_address_invalid" in error_data.get('error_code', ''):
                        if "@example.com" in email or "@test.com" in email:
                            error_msg = "Please use a real email address. Test emails are not allowed."
                        else:
                            error_msg = "Email address is invalid. Please check the format."
                    elif "email_exists" in error_data.get('error_code', ''):
                        error_msg = "This email is already registered. Please login or use a different email."
                    
                    raise Exception(f"Registration failed: {error_msg}")
                    
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise
            
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login user with Supabase Auth
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Dict with user data and tokens
        """
        if not self.session:
            await self.start()
            
        # Prepare request data
        data = {
            "email": email,
            "password": password,
            "grant_type": "password"
        }
        
        url = f"{self.base_url}/auth/v1/token?grant_type=password"
        headers = self._get_headers()
        
        try:
            async with self.session.post(url, json=data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    result = json.loads(response_text)
                    # Store tokens and user data
                    self.access_token = result.get("access_token")
                    self.refresh_token = result.get("refresh_token")
                    self.user = result.get("user")
                    
                    logger.info(f"User logged in successfully: {email}")
                    return result
                else:
                    logger.error(f"Login failed: {response.status} - {response_text}")
                    error_data = json.loads(response_text) if response_text else {}
                    raise Exception(f"Login failed: {error_data.get('error_description', 'Invalid credentials')}")
                    
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise
            
    async def logout(self) -> bool:
        """
        Logout current user
        
        Returns:
            True if successful
        """
        if not self.session:
            await self.start()
            
        if not self.access_token:
            logger.warning("No active session to logout")
            return True
            
        url = f"{self.base_url}/auth/v1/logout"
        headers = self._get_headers(include_auth=True)
        
        try:
            async with self.session.post(url, headers=headers) as response:
                if response.status in [200, 204]:
                    # Clear stored data
                    self.access_token = None
                    self.refresh_token = None
                    self.user = None
                    
                    logger.info("User logged out successfully")
                    return True
                else:
                    logger.warning(f"Logout returned status: {response.status}")
                    # Clear data anyway
                    self.access_token = None
                    self.refresh_token = None
                    self.user = None
                    return True
                    
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            # Clear data anyway
            self.access_token = None
            self.refresh_token = None
            self.user = None
            return False
            
    async def get_user(self) -> Optional[Dict[str, Any]]:
        """
        Get current user data
        
        Returns:
            User data if authenticated, None otherwise
        """
        if not self.access_token:
            return None
            
        if not self.session:
            await self.start()
            
        url = f"{self.base_url}/auth/v1/user"
        headers = self._get_headers(include_auth=True)
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    response_text = await response.text()
                    self.user = json.loads(response_text)
                    return self.user
                else:
                    logger.warning(f"Failed to get user: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            return None
            
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.access_token is not None
        
    def get_username(self) -> Optional[str]:
        """Get username from user metadata"""
        if self.user and "user_metadata" in self.user:
            return self.user["user_metadata"].get("username", self.user.get("email"))
        return None


# Singleton instance
_supabase_client = None

def get_supabase_client() -> SupabaseClient:
    """Get or create singleton Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client