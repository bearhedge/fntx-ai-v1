"""
Trading Mode Management
Simplified to WEEKDAY and WEEKEND modes only
"""
from enum import Enum
from datetime import datetime
import pytz


class TradingMode(Enum):
    """Trading environment modes"""
    WEEKDAY = "weekday"   # Weekday trading with real data
    WEEKEND = "weekend"   # Weekend with mock data
    
    
def detect_trading_mode(force_mock: bool = False) -> TradingMode:
    """
    Automatically detect appropriate trading mode based on day of week
    
    Args:
        force_mock: Force weekend mode regardless of day
        
    Returns:
        Appropriate TradingMode
    """
    if force_mock:
        return TradingMode.WEEKEND
        
    # Check if it's a weekday
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    
    # Monday=0, Sunday=6
    is_weekday = now.weekday() < 5  # 0-4 are Monday-Friday
    
    if is_weekday:
        return TradingMode.WEEKDAY
    else:
        return TradingMode.WEEKEND
        

class ModeConfig:
    """Configuration for different trading modes"""
    
    CONFIGS = {
        TradingMode.WEEKDAY: {
            'update_rate': 3.0,       # Update every 3 seconds
            'use_database': True,     # Use real database
            'position_tracking': 'database',
            'data_source': 'theta',   # Real market data
            'enable_trading': True,   # Can execute trades
            'display_mode': 'production'
        },
        TradingMode.WEEKEND: {
            'update_rate': 3.0,       # Update every 3 seconds
            'use_database': False,    # No database in mock
            'position_tracking': 'memory',
            'data_source': 'mock',    # Mock data generator
            'enable_trading': False,  # No real trades
            'display_mode': 'development'
        }
    }
    
    @classmethod
    def get_config(cls, mode: TradingMode) -> dict:
        """Get configuration for specified mode"""
        return cls.CONFIGS.get(mode, cls.CONFIGS[TradingMode.WEEKEND])