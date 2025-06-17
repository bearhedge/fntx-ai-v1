"""
User model for FNTX.ai authentication
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class User:
    """User model for authentication"""
    id: str
    email: str
    name: str
    password_hash: Optional[str] = None
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    google_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    def to_dict(self):
        """Convert user to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat() if isinstance(data['created_at'], datetime) else data['created_at']
        if data.get('last_login'):
            data['last_login'] = data['last_login'].isoformat() if isinstance(data['last_login'], datetime) else data['last_login']
        return data
    
    def to_json(self):
        """Convert user to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create user from dictionary"""
        # Convert ISO strings back to datetime objects if needed
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_login') and isinstance(data['last_login'], str):
            data['last_login'] = datetime.fromisoformat(data['last_login'])
        return cls(**data)