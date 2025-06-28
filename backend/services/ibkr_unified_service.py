#!/usr/bin/env python3
"""
FNTX AI Unified IBKR Service
Single, robust service for all IBKR connections with proper event loop handling
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor
import os
import nest_asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Allow nested event loops for IBKR compatibility
try:
    nest_asyncio.apply()
except ValueError:
    # Already patched or using uvloop
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IBKRUnifiedService')

class IBKRUnifiedService:
    """
    Unified IBKR service that handles all connections properly
    - Single connection point
    - Proper event loop management
    - Thread-safe operations
    - Automatic reconnection
    """
    
    def __init__(self):
        self.host = os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = int(os.getenv("IBKR_PORT", "4001"))
        self.client_id = 1  # Use a single, dedicated client ID
        
        # Connection state
        self.ib = None
        self.connected = False
        self.last_connection_attempt = None
        self.connection_lock = threading.Lock()
        
        # Event loop management
        self.loop = None
        self.thread = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        # Data cache
        self.spy_price_cache = 0
        self.last_spy_update = None
        self.options_cache = []
        self.last_options_update = None
        
        logger.info(f"IBKRUnifiedService initialized for {self.host}:{self.port} with client ID {self.client_id}")
        
    def _run_in_thread(self, func, *args, **kwargs):
        """Run a function in the main thread - IBKR doesn't like threading"""
        # IBKR connections work best in the main thread
        # Threading causes event loop issues
        return func(*args, **kwargs)
    
    def connect(self) -> bool:
        """Establish connection to IBKR with proper error handling"""
        with self.connection_lock:
            try:
                # Check if already connected
                if self.connected and self.ib and self._check_connection():
                    logger.info("Already connected to IBKR")
                    return True
                
                # Import here to avoid issues
                from ib_insync import IB
                
                logger.info(f"Connecting to IBKR at {self.host}:{self.port} with client ID {self.client_id}")
                
                # Create new IB instance
                self.ib = IB()
                
                # Connect with timeout
                self.ib.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    timeout=5,
                    readonly=False
                )
                
                if self.ib.isConnected():
                    self.connected = True
                    self.last_connection_attempt = datetime.now()
                    logger.info("✅ Successfully connected to IBKR")
                    return True
                else:
                    self.connected = False
                    logger.error("Failed to connect to IBKR - connection not established")
                    return False
                    
            except Exception as e:
                self.connected = False
                logger.error(f"Connection error: {e}")
                return False
    
    def _check_connection(self) -> bool:
        """Check if connection is still active"""
        try:
            if self.ib and hasattr(self.ib, 'isConnected'):
                return self.ib.isConnected()
            return False
        except:
            return False
    
    def _ensure_connected(self) -> bool:
        """Ensure we have an active connection"""
        if self._check_connection():
            return True
        
        # Try to reconnect
        logger.info("Connection lost, attempting to reconnect...")
        return self.connect()
    
    def get_spy_price(self) -> Dict[str, Any]:
        """Get SPY price with caching and error handling"""
        try:
            # Check cache first (valid for 5 seconds)
            if (self.spy_price_cache > 0 and 
                self.last_spy_update and 
                (datetime.now() - self.last_spy_update).seconds < 5):
                return {
                    "price": self.spy_price_cache,
                    "source": "cache",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Get fresh data
            result = self._run_in_thread(self._get_spy_price_internal)
            if result and result.get('price', 0) > 0:
                self.spy_price_cache = result['price']
                self.last_spy_update = datetime.now()
            return result
            
        except Exception as e:
            logger.error(f"Error getting SPY price: {e}")
            return {
                "price": self.spy_price_cache if self.spy_price_cache > 0 else 0,
                "source": "error_cache",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_spy_price_internal(self) -> Dict[str, Any]:
        """Internal method to get SPY price"""
        try:
            if not self._ensure_connected():
                raise ConnectionError("Cannot connect to IBKR")
            
            from ib_insync import Stock
            
            # Create SPY contract
            spy = Stock('SPY', 'SMART', 'USD')
            self.ib.qualifyContracts(spy)
            
            # Request market data
            ticker = self.ib.reqMktData(spy, '', False, False)
            
            # Wait for data
            for i in range(10):  # Try for 5 seconds
                self.ib.sleep(0.5)
                if ticker.last and ticker.last > 0:
                    price_data = {
                        "price": float(ticker.last),
                        "bid": float(ticker.bid) if ticker.bid else 0,
                        "ask": float(ticker.ask) if ticker.ask else 0,
                        "volume": int(ticker.volume) if ticker.volume else 0,
                        "source": "ibkr_live",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Cancel market data subscription
                    self.ib.cancelMktData(spy)
                    
                    logger.info(f"Got SPY price: ${price_data['price']:.2f}")
                    return price_data
            
            # No data received
            self.ib.cancelMktData(spy)
            raise ValueError("No SPY price data received from IBKR")
            
        except Exception as e:
            logger.error(f"Failed to get SPY price: {e}")
            raise
    
    def get_spy_options_chain(self, max_strikes: int = 20) -> List[Dict[str, Any]]:
        """Get SPY options chain with proper error handling"""
        try:
            # Check cache first (valid for 60 seconds)
            if (self.options_cache and 
                self.last_options_update and 
                (datetime.now() - self.last_options_update).seconds < 60):
                return self.options_cache
            
            # Get fresh data
            result = self._run_in_thread(self._get_options_chain_internal, max_strikes)
            if result:
                self.options_cache = result
                self.last_options_update = datetime.now()
            return result
            
        except Exception as e:
            logger.error(f"Error getting options chain: {e}")
            return []
    
    def _get_options_chain_internal(self, max_strikes: int) -> List[Dict[str, Any]]:
        """Internal method to get options chain"""
        try:
            if not self._ensure_connected():
                raise ConnectionError("Cannot connect to IBKR")
            
            from ib_insync import Stock, Option
            
            # Get SPY contract
            spy = Stock('SPY', 'SMART', 'USD')
            self.ib.qualifyContracts(spy)
            
            # Get current SPY price for strike selection
            spy_price = self.spy_price_cache if self.spy_price_cache > 0 else 600
            
            # Get option chain parameters
            chains = self.ib.reqSecDefOptParams('SPY', '', 'STK', spy.conId)
            
            if not chains:
                raise ValueError("No option chain data available")
            
            chain = chains[0]
            
            # Get next 3 expirations
            expirations = sorted(chain.expirations)[:3]
            
            # Get strikes around current price
            strikes = sorted([s for s in chain.strikes if abs(s - spy_price) <= 20])[:10]
            
            options_data = []
            
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y%m%d')
                dte = (exp_date.date() - datetime.now().date()).days
                
                for strike in strikes:
                    for right in ['P', 'C']:
                        try:
                            option = Option('SPY', exp, strike, right, 'SMART')
                            self.ib.qualifyContracts(option)
                            
                            # Try to get market data
                            ticker = self.ib.reqMktData(option, '', False, False)
                            self.ib.sleep(1)
                            
                            # Build option data
                            option_data = {
                                "contract_symbol": f"SPY{exp}_{int(strike)}{right}",
                                "strike": strike,
                                "expiration": exp,
                                "right": right,
                                "dte": dte,
                                "underlying_price": spy_price,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            # Add market data if available
                            if ticker.bid and ticker.bid >= 0:
                                option_data.update({
                                    "bid": float(ticker.bid),
                                    "ask": float(ticker.ask) if ticker.ask else float(ticker.bid) * 1.1,
                                    "last": float(ticker.last) if ticker.last else float(ticker.bid),
                                    "volume": int(ticker.volume) if ticker.volume else 0,
                                    "open_interest": 0,  # Not available in real-time
                                    # Add Greeks - CRITICAL for 0DTE
                                    "delta": float(ticker.modelGreeks.delta) if ticker.modelGreeks else None,
                                    "gamma": float(ticker.modelGreeks.gamma) if ticker.modelGreeks else None,
                                    "theta": float(ticker.modelGreeks.theta) if ticker.modelGreeks else None,
                                    "vega": float(ticker.modelGreeks.vega) if ticker.modelGreeks else None,
                                    "impliedVol": float(ticker.modelGreeks.impliedVol) if ticker.modelGreeks else None
                                })
                            else:
                                # Estimate prices if no market data
                                intrinsic = max(0, (spy_price - strike) if right == 'P' else (strike - spy_price))
                                time_value = 0.50 * (dte / 30) if dte > 0 else 0.10
                                estimated_price = intrinsic + time_value
                                
                                option_data.update({
                                    "bid": estimated_price * 0.95,
                                    "ask": estimated_price * 1.05,
                                    "last": estimated_price,
                                    "volume": 0,
                                    "open_interest": 0,
                                    "estimated": True
                                })
                            
                            # Add Greeks placeholders
                            option_data.update({
                                "implied_volatility": 0.20,
                                "delta": -0.5 if right == 'P' else 0.5,
                                "gamma": 0.02,
                                "theta": -0.05,
                                "vega": 0.10
                            })
                            
                            options_data.append(option_data)
                            
                            # Cancel market data
                            self.ib.cancelMktData(option)
                            
                            if len(options_data) >= max_strikes:
                                break
                                
                        except Exception as e:
                            logger.warning(f"Error processing option {strike}{right} {exp}: {e}")
                            continue
                    
                    if len(options_data) >= max_strikes:
                        break
                
                if len(options_data) >= max_strikes:
                    break
            
            logger.info(f"Retrieved {len(options_data)} option contracts")
            return options_data
            
        except Exception as e:
            logger.error(f"Failed to get options chain: {e}")
            raise
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        return {
            "connected": self._check_connection(),
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "last_connection": self.last_connection_attempt.isoformat() if self.last_connection_attempt else None,
            "spy_price_cached": self.spy_price_cache,
            "last_spy_update": self.last_spy_update.isoformat() if self.last_spy_update else None,
            "options_cached": len(self.options_cache),
            "last_options_update": self.last_options_update.isoformat() if self.last_options_update else None
        }
    
    def disconnect(self):
        """Disconnect from IBKR"""
        with self.connection_lock:
            try:
                if self.ib and self._check_connection():
                    self.ib.disconnect()
                    logger.info("Disconnected from IBKR")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self.connected = False
                self.ib = None
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.disconnect()
            self.executor.shutdown(wait=False)
        except:
            pass

# Global instance
ibkr_unified_service = IBKRUnifiedService()