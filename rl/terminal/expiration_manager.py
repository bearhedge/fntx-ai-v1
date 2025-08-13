"""
Expiration Manager - Handles option expiration dates
"""
from datetime import datetime, timedelta
import psycopg2
from typing import List, Optional, Tuple, Dict
import os


class ExpirationManager:
    """Manages option expiration dates and database connections"""
    
    def __init__(self):
        self.conn = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to database"""
        try:
            # Try to get connection details from environment
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', 5432),
                'dbname': os.getenv('DB_NAME', 'trading_db'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', '')
            }
            
            self.conn = psycopg2.connect(**db_config)
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to database: {e}")
            self.connected = False
            return False
    
    def get_next_expiration(self, date: Optional[datetime] = None) -> Optional[str]:
        """Get next option expiration date"""
        if date is None:
            date = datetime.now()
            
        # Simple logic - options expire on Fridays
        # Find next Friday
        days_ahead = 4 - date.weekday()  # Friday is 4
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
            
        next_friday = date + timedelta(days=days_ahead)
        return next_friday.strftime('%Y%m%d')
    
    def is_expiring_today(self, expiration: str) -> bool:
        """Check if option expires today"""
        today = datetime.now().strftime('%Y%m%d')
        return expiration == today
    
    def get_recent_expirations(self, days: int = 7, days_back: int = None) -> List[Dict]:
        """Get recent option expirations from backend.data.database"""
        # Support both parameter names for compatibility
        if days_back is not None:
            days = days_back
        # Stub implementation - return empty list for now
        return []
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.connected = False