#!/usr/bin/env python3
"""
IBKR Singleton Service - Single connection instance for all services
Prevents multiple client ID conflicts
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from ib_insync import IB, Stock, Option, Contract, util
import nest_asyncio

# Apply nest_asyncio to handle event loop issues
try:
    nest_asyncio.apply()
except ValueError:
    # Already patched or using uvloop
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IBKRSingletonService')

class IBKRSingletonService:
    """Singleton service for IBKR connection management"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.host = os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = int(os.getenv("IBKR_PORT", "4001"))
        self.client_id = 999  # Use a high client ID to avoid conflicts
        self.ib = IB()
        self._connected = False
        self._last_connection_attempt = None
        self._connection_retry_delay = 30  # seconds
        self._spy_contract = None
        self._last_spy_price = 0
        self._last_spy_update = None
        self._price_cache_duration = 5  # seconds
        self._initialized = True
        
        logger.info(f"IBKRSingletonService initialized for {self.host}:{self.port} with client ID {self.client_id}")
    
    def _ensure_connected(self) -> bool:
        """Ensure we have a valid connection"""
        if self.ib.isConnected():
            return True
            
        # Check if we should retry
        now = datetime.now()
        if self._last_connection_attempt:
            time_since_last_attempt = (now - self._last_connection_attempt).total_seconds()
            if time_since_last_attempt < self._connection_retry_delay:
                logger.debug(f"Skipping connection attempt, last attempt was {time_since_last_attempt:.1f}s ago")
                return False
        
        self._last_connection_attempt = now
        return self._connect()
    
    def _connect(self) -> bool:
        """Establish connection to IBKR"""
        try:
            logger.info(f"Connecting to IBKR at {self.host}:{self.port} with client ID {self.client_id}")
            
            # Disconnect if already connected
            if self.ib.isConnected():
                self.ib.disconnect()
            
            # Connect with timeout
            self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10)
            
            if self.ib.isConnected():
                self._connected = True
                logger.info("✅ Successfully connected to IBKR")
                
                # Initialize SPY contract
                self._spy_contract = Stock('SPY', 'SMART', 'USD')
                self.ib.qualifyContracts(self._spy_contract)
                
                return True
            else:
                logger.error("Failed to connect to IBKR")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._connected = False
            return False
    
    def get_spy_price(self) -> Dict[str, Any]:
        """Get current SPY price with caching"""
        try:
            # Check cache first
            if self._last_spy_update and self._last_spy_price > 0:
                cache_age = (datetime.now() - self._last_spy_update).total_seconds()
                if cache_age < self._price_cache_duration:
                    return {
                        'price': self._last_spy_price,
                        'timestamp': self._last_spy_update.isoformat(),
                        'cached': True
                    }
            
            if not self._ensure_connected():
                logger.error("Cannot connect to IBKR")
                return {'price': 0, 'error': 'Cannot connect to IBKR'}
            
            # Request market data
            self.ib.reqMktData(self._spy_contract, '', False, False)
            
            # Wait for data with timeout
            start_time = time.time()
            timeout = 5  # seconds
            
            while time.time() - start_time < timeout:
                ticker = self.ib.ticker(self._spy_contract)
                if ticker and ticker.last and ticker.last > 0:
                    self._last_spy_price = ticker.last
                    self._last_spy_update = datetime.now()
                    
                    logger.info(f"Got SPY price: ${ticker.last}")
                    return {
                        'price': ticker.last,
                        'bid': ticker.bid if ticker.bid else 0,
                        'ask': ticker.ask if ticker.ask else 0,
                        'timestamp': datetime.now().isoformat(),
                        'cached': False
                    }
                
                self.ib.sleep(0.1)
            
            logger.error("Timeout waiting for SPY price")
            return {'price': 0, 'error': 'Timeout waiting for price data'}
            
        except Exception as e:
            logger.error(f"Error getting SPY price: {e}")
            return {'price': 0, 'error': str(e)}
    
    def get_spy_options_chain(self, expiration: Optional[str] = None, max_strikes: int = 20) -> List[Dict[str, Any]]:
        """Get SPY options chain"""
        try:
            if not self._ensure_connected():
                logger.error("Cannot connect to IBKR")
                return []
            
            # Get SPY price first
            spy_data = self.get_spy_price()
            spy_price = spy_data.get('price', 0)
            
            if spy_price == 0:
                logger.error("Cannot get SPY price for options chain")
                return []
            
            # Get next trading day expiration if not specified
            if not expiration:
                from datetime import date
                today = date.today()
                # For now, use today's date - in production, calculate next trading day
                expiration = today.strftime('%Y%m%d')
            
            # Calculate strike range around current price
            strike_spacing = 1  # SPY typically has $1 strikes
            atm_strike = round(spy_price)
            
            # Get strikes around ATM
            strikes = []
            for i in range(-max_strikes//2, max_strikes//2 + 1):
                strike = atm_strike + (i * strike_spacing)
                if strike > 0:
                    strikes.append(strike)
            
            # Request options data
            options_list = []
            
            for strike in strikes:
                for right in ['P', 'C']:
                    try:
                        contract = Option('SPY', expiration, strike, right, 'SMART')
                        self.ib.qualifyContracts(contract)
                        
                        if contract.conId:
                            # Request market data
                            self.ib.reqMktData(contract, '', False, False)
                            
                            # Wait for market data to populate with timeout
                            start_time = time.time()
                            timeout = 3  # 3 seconds for option data
                            ticker = None
                            
                            while time.time() - start_time < timeout:
                                ticker = self.ib.ticker(contract)
                                if ticker and (ticker.bid or ticker.ask or ticker.last):
                                    elapsed = time.time() - start_time
                                    logger.debug(f"Got option data for {strike}{right} in {elapsed:.2f}s")
                                    break
                                self.ib.sleep(0.1)
                            
                            # If no ticker data, try one more time
                            if not ticker:
                                ticker = self.ib.ticker(contract)
                                
                            # Log if we still don't have market data
                            if not ticker or not (ticker.bid or ticker.ask or ticker.last):
                                logger.warning(f"No market data received for {strike}{right} after {timeout}s timeout")
                            
                            # Helper function to handle NaN values
                            def safe_float(value, default=0.0):
                                if value is None:
                                    return default
                                if isinstance(value, float) and (value != value or abs(value) == float('inf')):
                                    return default
                                return float(value)
                            
                            option_data = {
                                'contract_symbol': f"SPY{expiration[2:]}{right}{int(strike*1000):08d}",
                                'strike': strike,
                                'expiration': expiration,
                                'right': right,
                                'bid': safe_float(ticker.bid if ticker else None),
                                'ask': safe_float(ticker.ask if ticker else None),
                                'last': safe_float(ticker.last if ticker else None),
                                'volume': int(safe_float(ticker.volume if ticker else 0)),
                                'open_interest': 0,  # Would need historical data request
                                'implied_volatility': 0.2,  # Placeholder
                                'in_the_money': (right == 'P' and strike > spy_price) or (right == 'C' and strike < spy_price)
                            }
                            
                            options_list.append(option_data)
                            
                    except Exception as e:
                        logger.debug(f"Error getting option {strike}{right}: {e}")
                        continue
            
            logger.info(f"Retrieved {len(options_list)} option contracts")
            return options_list
            
        except Exception as e:
            logger.error(f"Error getting options chain: {e}")
            return []
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            'connected': self.ib.isConnected(),
            'client_id': self.client_id,
            'host': self.host,
            'port': self.port,
            'last_spy_price': self._last_spy_price,
            'last_update': self._last_spy_update.isoformat() if self._last_spy_update else None
        }
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.ib.isConnected():
            logger.info("Disconnecting from IBKR...")
            self.ib.disconnect()
            self._connected = False

# Create singleton instance
ibkr_singleton = IBKRSingletonService()