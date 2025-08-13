#!/usr/bin/env python3
"""
ALM NAV Service
Fetches the latest Net Asset Value (NAV) from the ALM database

This service connects to the PostgreSQL database and retrieves the most recent
closing NAV from the alm_reporting.daily_summary table.
"""

import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "dbname": "options_data",
    "user": "postgres",
    "password": "theta_data_2024",
    "host": "localhost"
}

# Timezone
HKT = pytz.timezone('Asia/Hong_Kong')
ET = pytz.timezone('US/Eastern')


class ALMNavService:
    """Service for fetching NAV data from ALM database"""
    
    def __init__(self):
        self.conn = None
        self.last_nav_data = None
        self.last_fetch_time = None
        
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(**DB_CONFIG)
                logger.info("Connected to ALM database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
            
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Disconnected from ALM database")
            
    def get_latest_nav(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest NAV from the database
        
        Args:
            force_refresh: Force a database query even if cached data exists
            
        Returns:
            Dictionary with NAV data or None if error
        """
        # Check if we should use cached data
        if not force_refresh and self.last_nav_data and self.last_fetch_time:
            # Cache for 5 minutes to avoid excessive database queries
            if datetime.now() - self.last_fetch_time < timedelta(minutes=5):
                logger.debug("Returning cached NAV data")
                return self.last_nav_data
                
        # Connect if needed
        if not self.connect():
            return None
            
        try:
            cursor = self.conn.cursor()
            
            # Query for the most recent daily summary
            query = """
                SELECT 
                    summary_date,
                    closing_nav_hkd,
                    opening_nav_hkd,
                    total_pnl_hkd,
                    net_cash_flow_hkd
                FROM alm_reporting.daily_summary
                WHERE closing_nav_hkd IS NOT NULL
                ORDER BY summary_date DESC
                LIMIT 1
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                nav_data = {
                    'date': result[0],
                    'closing_nav_hkd': float(result[1]),
                    'opening_nav_hkd': float(result[2]) if result[2] else None,
                    'daily_pnl_hkd': float(result[3]) if result[3] else 0.0,
                    'net_cash_flow_hkd': float(result[4]) if result[4] else 0.0,
                    'fetch_time': datetime.now(),
                    'source': 'ALM Database'
                }
                
                # Cache the data
                self.last_nav_data = nav_data
                self.last_fetch_time = datetime.now()
                
                logger.info(f"Fetched NAV data for {nav_data['date']}: {nav_data['closing_nav_hkd']:,.2f} HKD")
                return nav_data
            else:
                logger.warning("No NAV data found in database")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching NAV: {e}")
            return None
        finally:
            cursor.close()
            
    def should_auto_refresh(self) -> bool:
        """
        Check if we should auto-refresh the NAV
        Returns True if current time is after 12 PM HKT
        """
        now_hkt = datetime.now(HKT)
        return now_hkt.hour >= 12
        
    def get_nav_age(self) -> Optional[timedelta]:
        """Get the age of the latest NAV data"""
        if not self.last_nav_data:
            return None
            
        nav_date = self.last_nav_data.get('date')
        if nav_date:
            # Convert date to datetime at end of day ET
            nav_datetime = datetime.combine(nav_date, datetime.min.time())
            nav_datetime = ET.localize(nav_datetime).replace(hour=16)  # 4 PM ET close
            
            # Get current time in ET
            now_et = datetime.now(ET)
            
            return now_et - nav_datetime
        return None
        
    def is_nav_stale(self) -> bool:
        """
        Check if NAV data is stale (more than 1 trading day old)
        """
        age = self.get_nav_age()
        if age is None:
            return True
            
        # Consider stale if more than 24 hours old on weekdays
        # or more than 72 hours on weekends
        now_et = datetime.now(ET)
        if now_et.weekday() < 5:  # Monday-Friday
            return age > timedelta(hours=24)
        else:  # Weekend
            return age > timedelta(hours=72)


# Singleton instance
_nav_service = None


def get_nav_service() -> ALMNavService:
    """Get or create the singleton NAV service instance"""
    global _nav_service
    if _nav_service is None:
        _nav_service = ALMNavService()
    return _nav_service


# Convenience functions
def get_latest_nav() -> Optional[Dict[str, Any]]:
    """Get the latest NAV from the database"""
    service = get_nav_service()
    return service.get_latest_nav()


def get_latest_capital() -> Optional[float]:
    """Get just the capital amount (closing NAV) in HKD"""
    nav_data = get_latest_nav()
    if nav_data:
        return nav_data.get('closing_nav_hkd')
    return None


if __name__ == "__main__":
    # Test the service
    print("Testing ALM NAV Service...")
    
    service = get_nav_service()
    nav_data = service.get_latest_nav()
    
    if nav_data:
        print(f"\nLatest NAV Data:")
        print(f"Date: {nav_data['date']}")
        print(f"Closing NAV: {nav_data['closing_nav_hkd']:,.2f} HKD")
        print(f"Daily P&L: {nav_data['daily_pnl_hkd']:+,.2f} HKD")
        print(f"Fetched at: {nav_data['fetch_time']}")
        print(f"Data Age: {service.get_nav_age()}")
        print(f"Is Stale: {service.is_nav_stale()}")
        print(f"Should Auto-Refresh: {service.should_auto_refresh()}")
    else:
        print("Failed to fetch NAV data")
    
    service.disconnect()