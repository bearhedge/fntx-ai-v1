"""
API Client for communicating with FNTX backend
Handles HTTP requests to the authentication and trading APIs
"""
import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class APIClient:
    """Async HTTP client for FNTX API"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client
        
        Args:
            base_url: Base URL for API (defaults to environment variable or localhost)
        """
        # Use Supabase URL
        self.base_url = base_url or os.getenv("API_BASE_URL", "https://xzfjhhnmnlsgbrmwojyi.supabase.co")
        self.anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh6ZmpoaG5tbmxzZ2JybXdvanlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwMDc1MjcsImV4cCI6MjA3MTU4MzUyN30.uVNx-RAB9ZnI4T-Vh5ZEaTSMR9JWYkkrG4xjLhP-1vE"
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
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
            
    def set_auth_tokens(self, access_token: str, refresh_token: str):
        """Set authentication tokens"""
        self.auth_token = access_token
        self.refresh_token = refresh_token
        
    def clear_auth_tokens(self):
        """Clear authentication tokens"""
        self.auth_token = None
        self.refresh_token = None
        
    async def _request(self, method: str, endpoint: str, 
                      data: Optional[Dict] = None, 
                      authenticated: bool = False) -> Dict[str, Any]:
        """
        Make HTTP request to API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request data (for POST/PUT)
            authenticated: Whether to include auth token
            
        Returns:
            Response data as dictionary
        """
        if not self.session:
            await self.start()
            
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "apikey": self.anon_key  # Add Supabase API key
        }
        
        if authenticated and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        try:
            async with self.session.request(
                method, url, 
                json=data if data else None,
                headers=headers
            ) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    error_detail = response_data.get("detail", "Unknown error")
                    raise APIError(response.status, error_detail)
                    
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise APIError(500, f"Network error: {str(e)}")
            
    # Authentication endpoints
    async def register(self, username: str, email: str, password: str, 
                      full_name: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user"""
        data = {
            "username": username,
            "email": email,
            "password": password
        }
        if full_name:
            data["full_name"] = full_name
            
        # Use Supabase signup endpoint
        supabase_data = {
            "email": email,
            "password": password,
            "data": {  # Store extra data in user metadata
                "username": username,
                "full_name": full_name
            }
        }
        return await self._request("POST", "/auth/v1/signup", supabase_data)
        
    async def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """Login user and get tokens"""
        # Supabase only accepts email for login, not username
        # For now, assume username_or_email is an email
        data = {
            "email": username_or_email,
            "password": password,
            "grant_type": "password"
        }
        
        response = await self._request("POST", "/auth/v1/token?grant_type=password", data)
        
        # Store tokens
        self.set_auth_tokens(
            response["access_token"],
            response["refresh_token"]
        )
        
        return response
        
    async def logout(self) -> Dict[str, Any]:
        """Logout current user"""
        response = await self._request("POST", "/auth/v1/logout", 
                                     authenticated=True)
        self.clear_auth_tokens()
        return response
        
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            raise APIError(401, "No refresh token available")
            
        data = {"refresh_token": self.refresh_token}
        response = await self._request("POST", "/api/auth/refresh", data)
        
        # Update access token
        self.auth_token = response["access_token"]
        
        return response
        
    async def get_profile(self) -> Dict[str, Any]:
        """Get current user profile"""
        return await self._request("GET", "/api/auth/profile", 
                                 authenticated=True)
        
    # Trading endpoints (placeholder for future integration)
    async def get_positions(self) -> Dict[str, Any]:
        """Get current trading positions"""
        return await self._request("GET", "/api/positions", 
                                 authenticated=True)
        
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        return await self._request("GET", "/api/portfolio/summary", 
                                 authenticated=True)


class APIError(Exception):
    """Custom exception for API errors"""
    
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error {status_code}: {detail}")


# Singleton instance
_api_client: Optional[APIClient] = None

def get_api_client() -> APIClient:
    """Get singleton API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client

async def close_api_client():
    """Close the singleton API client"""
    global _api_client
    if _api_client:
        await _api_client.close()
        _api_client = None