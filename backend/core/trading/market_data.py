#!/usr/bin/env python3
"""
Market Data and Options Chain Fetcher
"""
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class OptionData:
    symbol: str
    strike: float
    right: str
    bid: float
    ask: float
    volume: int
    open_interest: int
    iv: float
    expiry: str

class MarketDataProvider:
    def __init__(self, theta_terminal_url="http://localhost:11000"):
        self.theta_url = theta_terminal_url
        
    def is_theta_available(self) -> bool:
        """Check if ThetaTerminal is available"""
        try:
            response = requests.get(f"{self.theta_url}/v2/system/status", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_spy_current_price(self) -> Optional[float]:
        """Get current SPY price"""
        # This would connect to your data source
        # For now, return None - implement based on your data provider
        return None
    
    def get_option_chain(self, symbol: str, expiry: str = None) -> List[OptionData]:
        """Get option chain for symbol"""
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
            
        # Implementation depends on data source
        # Return empty list for now
        return []
    
    def get_atm_options(self, symbol: str, num_strikes: int = 5) -> List[OptionData]:
        """Get at-the-money options"""
        current_price = self.get_spy_current_price()
        if not current_price:
            return []
            
        chain = self.get_option_chain(symbol)
        
        # Sort by distance from current price
        sorted_options = sorted(chain, key=lambda x: abs(x.strike - current_price))
        
        return sorted_options[:num_strikes * 2]  # Get calls and puts