#!/usr/bin/env python3
"""
Interactive Brokers REST API Client
High-level client for trading operations using IB REST API
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from .ib_rest_auth import IBRestAuth

@dataclass
class Contract:
    """IB Contract representation"""
    conid: int
    symbol: str
    secType: str
    exchange: str = "SMART"
    currency: str = "USD"
    lastTradeDateOrContractMonth: str = None
    strike: float = None
    right: str = None  # C or P
    multiplier: str = "100"

@dataclass
class Order:
    """IB Order representation"""
    acctId: str
    conid: int
    orderType: str  # MKT, LMT, STP
    side: str  # BUY, SELL
    quantity: int
    price: Optional[float] = None  # For limit orders
    auxPrice: Optional[float] = None  # For stop orders
    tif: str = "DAY"  # Time in force
    outsideRTH: bool = False

@dataclass
class TradeResult:
    """Result of a trading operation"""
    success: bool
    symbol: str
    strike: float
    right: str
    entry_price: float
    stop_loss: float
    credit: float
    max_risk: float
    message: str
    order_id: Optional[str] = None
    contract_id: Optional[int] = None

class IBRestClient:
    """
    High-level IB REST API client for trading operations
    """
    
    def __init__(self, consumer_key: str = None, realm: str = "limited_poa"):
        """
        Initialize IB REST API client
        
        Args:
            consumer_key: OAuth consumer key
            realm: Authentication realm
        """
        self.auth = IBRestAuth(consumer_key=consumer_key, realm=realm)
        self.base_url = self.auth.base_url
        self.logger = logging.getLogger(__name__)
        
        # Cache
        self.account_id = None
        self.contracts_cache = {}
        
    def connect(self) -> bool:
        """
        Connect to IB REST API (authenticate)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.auth.authenticate():
                # Get primary account
                accounts = self.get_accounts()
                if accounts and len(accounts) > 0:
                    self.account_id = accounts[0].get('accountId')
                    self.logger.info(f"Connected to IB REST API. Primary account: {self.account_id}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    def get_accounts(self) -> Optional[List[Dict]]:
        """Get list of accounts"""
        return self.auth.get_accounts()
    
    def search_option_contracts(self, symbol: str, expiry: str = None) -> Optional[List[Dict]]:
        """
        Search for option contracts
        
        Args:
            symbol: Underlying symbol (e.g., 'SPY')
            expiry: Expiration date (YYYYMMDD format)
            
        Returns:
            List of option contracts
        """
        try:
            # First search for the underlying
            results = self.auth.search_contracts(symbol, "STK")
            if not results:
                self.logger.error(f"No results for {symbol}")
                return None
            
            # Get the conid of the underlying
            underlying_conid = None
            for result in results:
                if result.get('symbol') == symbol:
                    underlying_conid = result.get('conid')
                    break
            
            if not underlying_conid:
                self.logger.error(f"Could not find conid for {symbol}")
                return None
            
            # Get option chain
            url = f"{self.base_url}/iserver/secdef/strikes"
            params = {
                'conid': underlying_conid,
                'sectype': 'OPT',
                'month': expiry[:6] if expiry else datetime.now().strftime('%Y%m')
            }
            
            response = self.auth._make_authenticated_request('GET', url, params=params)
            if response and response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error searching option contracts: {e}")
            return None
    
    def get_option_contract(self, symbol: str, strike: float, right: str, expiry: str = None) -> Optional[Contract]:
        """
        Get specific option contract
        
        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' for call, 'P' for put
            expiry: Expiration date (YYYYMMDD)
            
        Returns:
            Contract object or None
        """
        try:
            # Check cache first
            cache_key = f"{symbol}_{strike}_{right}_{expiry}"
            if cache_key in self.contracts_cache:
                return self.contracts_cache[cache_key]
            
            # Search for option contracts
            if not expiry:
                expiry = datetime.now().strftime('%Y%m%d')
            
            # Use contract search endpoint
            url = f"{self.base_url}/iserver/secdef/search"
            params = {
                'symbol': f"{symbol} {expiry} {strike} {right}",
                'secType': 'OPT'
            }
            
            response = self.auth._make_authenticated_request('GET', url, params=params)
            if response and response.status_code == 200:
                results = response.json()
                for result in results:
                    if (result.get('symbol') == symbol and 
                        abs(float(result.get('strike', 0)) - strike) < 0.01 and
                        result.get('right') == right):
                        
                        contract = Contract(
                            conid=result.get('conid'),
                            symbol=symbol,
                            secType='OPT',
                            strike=strike,
                            right=right,
                            lastTradeDateOrContractMonth=expiry
                        )
                        
                        # Cache it
                        self.contracts_cache[cache_key] = contract
                        return contract
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting option contract: {e}")
            return None
    
    def get_market_data(self, conid: int) -> Optional[Dict]:
        """
        Get market data for a contract
        
        Args:
            conid: Contract ID
            
        Returns:
            Market data dict with bid, ask, last prices
        """
        try:
            url = f"{self.base_url}/iserver/marketdata/snapshot"
            params = {'conids': str(conid), 'fields': '31,84,85,86'}  # Last, Bid, Ask, Bid Size
            
            response = self.auth._make_authenticated_request('GET', url, params=params)
            if response and response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    snapshot = data[0]
                    return {
                        'bid': snapshot.get('84', 0),
                        'ask': snapshot.get('85', 0),
                        'last': snapshot.get('31', 0),
                        'bidSize': snapshot.get('86', 0)
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return None
    
    def place_order(self, order: Order) -> Optional[str]:
        """
        Place an order
        
        Args:
            order: Order object
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            if not self.account_id:
                self.logger.error("No account ID set")
                return None
            
            url = f"{self.base_url}/iserver/account/{self.account_id}/orders"
            
            # Build order payload
            payload = {
                'orders': [{
                    'acctId': order.acctId or self.account_id,
                    'conid': order.conid,
                    'orderType': order.orderType,
                    'side': order.side,
                    'quantity': order.quantity,
                    'tif': order.tif,
                    'outsideRTH': order.outsideRTH
                }]
            }
            
            # Add price fields if applicable
            if order.orderType == 'LMT' and order.price:
                payload['orders'][0]['price'] = order.price
            elif order.orderType == 'STP' and order.auxPrice:
                payload['orders'][0]['auxPrice'] = order.auxPrice
            
            # Make request
            response = self.auth._make_authenticated_request('POST', url, data=json.dumps(payload))
            
            if response and response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    order_id = result[0].get('orderId')
                    self.logger.info(f"Order placed successfully: {order_id}")
                    return order_id
            else:
                self.logger.error(f"Order placement failed: {response.text if response else 'No response'}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def get_orders(self) -> Optional[List[Dict]]:
        """Get list of orders"""
        try:
            url = f"{self.base_url}/iserver/account/{self.account_id}/orders"
            response = self.auth._make_authenticated_request('GET', url)
            
            if response and response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting orders: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/iserver/account/{self.account_id}/order/{order_id}"
            response = self.auth._make_authenticated_request('DELETE', url)
            
            if response and response.status_code == 200:
                self.logger.info(f"Order {order_id} cancelled")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_positions(self) -> Optional[List[Dict]]:
        """Get current positions"""
        try:
            url = f"{self.base_url}/portfolio/{self.account_id}/positions"
            response = self.auth._make_authenticated_request('GET', url)
            
            if response and response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return None
    
    def sell_option_with_stop(self, symbol: str, strike: float, right: str, 
                             stop_multiple: float = 3.0, quantity: int = 1, 
                             expiry: str = None) -> TradeResult:
        """
        Sell option with automatic stop loss (main trading method)
        
        Args:
            symbol: Stock symbol (e.g., 'SPY')
            strike: Strike price
            right: 'C' for call, 'P' for put
            stop_multiple: Stop loss as multiple of premium (default 3x)
            quantity: Number of contracts to trade (default 1)
            expiry: Expiration date (default today)
            
        Returns:
            TradeResult with execution details
        """
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
        
        try:
            # Get option contract
            contract = self.get_option_contract(symbol, strike, right, expiry)
            if not contract:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message=f"Could not find option contract for {symbol} {strike}{right}"
                )
            
            # Get current market data
            market_data = self.get_market_data(contract.conid)
            if not market_data:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message="Could not get market data"
                )
            
            bid = market_data['bid']
            ask = market_data['ask']
            
            if bid <= 0 or ask <= 0:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message="Invalid market data (bid/ask <= 0)"
                )
            
            # Use bid price for selling
            premium = bid
            stop_price = premium * stop_multiple
            
            self.logger.info(f"Selling {quantity} {symbol} {strike}{right} at ${premium:.2f}")
            self.logger.info(f"Setting stop loss at ${stop_price:.2f} ({stop_multiple}x premium)")
            
            # Place sell order
            sell_order = Order(
                acctId=self.account_id,
                conid=contract.conid,
                orderType="MKT",
                side="SELL",
                quantity=quantity
            )
            
            sell_order_id = self.place_order(sell_order)
            if not sell_order_id:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message="Failed to place sell order"
                )
            
            # Wait a moment for fill
            time.sleep(2)
            
            # Place stop loss order
            stop_order = Order(
                acctId=self.account_id,
                conid=contract.conid,
                orderType="STP",
                side="BUY",
                quantity=quantity,
                auxPrice=stop_price
            )
            
            stop_order_id = self.place_order(stop_order)
            if not stop_order_id:
                self.logger.error(f"CRITICAL: Failed to place stop loss for {symbol} {strike}{right}")
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=premium,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message=f"CRITICAL: Failed to place stop loss for {symbol} {strike}{right}",
                    order_id=sell_order_id
                )
            
            # Calculate trade metrics
            credit = premium * 100 * quantity  # Options are $100 per point
            max_risk = (stop_price - premium) * 100 * quantity
            
            return TradeResult(
                success=True,
                symbol=symbol,
                strike=strike,
                right=right,
                entry_price=premium,
                stop_loss=stop_price,
                credit=credit,
                max_risk=max_risk,
                message=f"Successfully sold {quantity} {symbol} {strike}{right} at ${premium:.2f}",
                order_id=sell_order_id,
                contract_id=contract.conid
            )
            
        except Exception as e:
            self.logger.error(f"Error in sell_option_with_stop: {e}")
            return TradeResult(
                success=False,
                symbol=symbol,
                strike=strike,
                right=right,
                entry_price=0,
                stop_loss=0,
                credit=0,
                max_risk=0,
                message=f"Trade failed: {str(e)}"
            )


def test_client():
    """Test REST API client"""
    logging.basicConfig(level=logging.INFO)
    
    client = IBRestClient()
    
    print("Testing IB REST API Client...")
    
    # Connect
    if not client.connect():
        print("❌ Failed to connect")
        return False
    
    print("✅ Connected to IB REST API")
    
    # Test getting SPY option
    contract = client.get_option_contract('SPY', 630, 'C')
    if contract:
        print(f"✅ Found option contract: {contract.symbol} {contract.strike}{contract.right}")
        
        # Get market data
        market_data = client.get_market_data(contract.conid)
        if market_data:
            print(f"✅ Market data: Bid=${market_data['bid']:.2f}, Ask=${market_data['ask']:.2f}")
    else:
        print("❌ Could not find option contract")
    
    return True


if __name__ == "__main__":
    test_client()