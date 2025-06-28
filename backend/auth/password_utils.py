"""
Password hashing utilities for FNTX AI authentication
"""
import bcrypt
import re
from typing import Tuple, List


class PasswordManager:
    """Manages password hashing and validation"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Plain text password to verify
            hashed: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed.encode('utf-8')
            )
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check minimum length
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        # Check for uppercase letter
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        # Check for lowercase letter
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        # Check for digit
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        
        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        return len(issues) == 0, issues


# Singleton instance
password_manager = PasswordManager()