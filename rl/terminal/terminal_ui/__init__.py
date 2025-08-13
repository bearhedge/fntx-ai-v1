"""
Terminal UI Package
Interactive trading dashboard and UI components
"""

# Import only core components to avoid circular dependencies
from .dashboard import TradingDashboard
from .trading_mode import TradingMode, detect_trading_mode, ModeConfig

__all__ = [
    'TradingDashboard',
    'TradingMode', 
    'detect_trading_mode',
    'ModeConfig'
]