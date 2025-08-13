"""
User model for FNTX AI system
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class User:
    """User data model"""
    id: str
    name: str
    email: str
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'picture': self.picture,
            'given_name': self.given_name,
            'family_name': self.family_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }