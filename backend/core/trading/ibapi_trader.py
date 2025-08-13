#!/usr/bin/env python3
"""
IBAPI-based Options Trading System
Official Interactive Brokers API implementation to replace ib_insync
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from decimal import Decimal
import queue

# Official IBAPI imports
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import *
from ibapi.ticktype import TickTypeEnum, TickType
from ibapi.execution import Execution
from ibapi.commission_report import CommissionReport

@dataclass
class TradeResult:
    """Result of a trading operation - maintains compatibility with ib_insync version"""
    success: bool
    symbol: str
    strike: float
    right: str
    entry_price: float
    stop_loss: float
    credit: float
    max_risk: float
    message: str
    order_id: Optional[int] = None
    contract_id: Optional[int] = None

class IBAPITrader(EWrapper, EClient):
    """
    Official IBAPI-based options trader
    Inherits from both EWrapper (for callbacks) and EClient (for requests)
    """
    
    def __init__(self, host='127.0.0.1', port=4001):
        EClient.__init__(self, self)
        
        self.host = host
        self.port = port
        self.client_id = None
        self.next_order_id = None
        
        # Threading for IBAPI event loop
        self.api_thread = None
        self.is_connected = False
        
        # Data storage
        self.positions = {}
        self.orders = {}
        self.executions = {}
        self.market_data = {}
        self.account_summary = {}
        self.managed_accounts = []
        
        # Request tracking
        self.next_req_id = 1000
        self.pending_requests = {}
        
        # Event queues for synchronous operations
        self.connection_event = threading.Event()
        self.data_events = {}
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def get_next_req_id(self) -> int:
        """Get next unique request ID"""
        req_id = self.next_req_id
        self.next_req_id += 1
        return req_id
    
    def connect_api(self, client_id: int = None, timeout: int = 15) -> bool:
        """
        Connect to IB Gateway/TWS with improved threading
        
        Args:
            client_id: Unique client identifier (auto-generated if None)
            timeout: Connection timeout in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if client_id is None:
                # Generate unique client ID to avoid conflicts
                client_id = int(time.time() % 10000) + 1000
                
            self.client_id = client_id
            self.logger.info(f"Connecting to {self.host}:{self.port} with client ID {client_id}")
            
            # Reset connection state
            self.is_connected = False
            self.next_order_id = None
            self.connection_event.clear()
            
            # Connect to IB Gateway
            self.connect(self.host, self.port, client_id)
            
            # Start API thread
            self.api_thread = threading.Thread(target=self.run, daemon=True)
            self.api_thread.start()
            
            # Wait for connection with shorter timeout and polling
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                if self.is_connected and self.next_order_id is not None:
                    self.logger.info("✅ Successfully connected to IB Gateway")
                    
                    # Small delay to ensure connection is stable
                    time.sleep(1)
                    
                    # Request initial data
                    try:
                        self.reqAccountUpdates(True, "")
                        self.reqPositions()
                    except:
                        pass  # Don't fail connection if data requests fail
                    
                    return True
                
                time.sleep(0.1)  # Poll every 100ms
            
            self.logger.error(f"❌ Connection timeout after {timeout} seconds")
            self.disconnect()
            return False
                
        except Exception as e:
            self.logger.error(f"❌ Connection error: {e}")
            self.disconnect()
            return False
    
    def disconnect_api(self):
        """Disconnect from IB Gateway"""
        if self.is_connected:
            self.disconnect()
            if self.api_thread and self.api_thread.is_alive():
                self.api_thread.join(timeout=5)
            self.logger.info("Disconnected from IB Gateway")
    
    # ================================
    # EWrapper Callback Methods
    # ================================
    
    def connectAck(self):
        """Connection acknowledgment callback"""
        self.logger.info("Received connection acknowledgment from IB Gateway")
        
    def nextValidId(self, orderId: int):
        """Callback with next valid order ID"""
        self.next_order_id = orderId
        self.is_connected = True
        self.connection_event.set()
        self.logger.info(f"Received next valid order ID: {orderId}")
    
    def managedAccounts(self, accountsList: str):
        """Callback with managed accounts"""
        self.managed_accounts = accountsList.split(',')
        self.logger.info(f"Managed accounts: {self.managed_accounts}")
    
    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Error callback"""
        if errorCode == 2104 or errorCode == 2106:
            # Market data farm connection messages - informational
            self.logger.debug(f"Market data: {errorString}")
        elif errorCode == 2158:
            # Sec-def data farm - informational
            self.logger.debug(f"Security definition: {errorString}")
        elif errorCode >= 2100 and errorCode <= 2200:
            # Informational messages
            self.logger.info(f"Info ({errorCode}): {errorString}")
        else:
            # Actual errors
            self.logger.error(f"Error {errorCode} (reqId: {reqId}): {errorString}")
    
    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib):
        """Market data price callback"""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        tick_name = TickTypeEnum.to_str(tickType)
        self.market_data[reqId][tick_name] = price
        
        # Signal data received if someone is waiting
        if reqId in self.data_events:
            self.data_events[reqId].set()
    
    def tickSize(self, reqId: TickerId, tickType: TickType, size: Decimal):
        """Market data size callback"""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        tick_name = TickTypeEnum.to_str(tickType)
        self.market_data[reqId][f"{tick_name}_size"] = size
    
    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        """Position callback"""
        key = f"{contract.symbol}_{contract.strike}_{contract.right}"
        self.positions[key] = {
            'account': account,
            'contract': contract,
            'position': float(position),
            'avgCost': avgCost,
            'symbol': contract.symbol,
            'strike': getattr(contract, 'strike', None),
            'right': getattr(contract, 'right', None),
            'expiry': getattr(contract, 'lastTradeDateOrContractMonth', None)
        }
    
    def positionEnd(self):
        """End of position data callback"""
        self.logger.debug(f"Received {len(self.positions)} positions")
    
    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState):
        """Open order callback"""
        self.orders[orderId] = {
            'contract': contract,
            'order': order,
            'orderState': orderState,
            'symbol': contract.symbol,
            'strike': getattr(contract, 'strike', None),
            'right': getattr(contract, 'right', None)
        }
    
    def orderStatus(self, orderId: OrderId, status: str, filled: Decimal, remaining: Decimal,
                   avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float,
                   clientId: int, whyHeld: str, mktCapPrice: float):
        """Order status callback"""
        if orderId in self.orders:
            self.orders[orderId].update({
                'status': status,
                'filled': float(filled),
                'remaining': float(remaining),
                'avgFillPrice': avgFillPrice,
                'lastFillPrice': lastFillPrice
            })
        
        # Signal order status update if someone is waiting
        if orderId in self.data_events:
            self.data_events[orderId].set()
    
    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        """Execution details callback"""
        self.executions[execution.execId] = {
            'contract': contract,
            'execution': execution,
            'symbol': contract.symbol,
            'strike': getattr(contract, 'strike', None),
            'right': getattr(contract, 'right', None),
            'price': execution.price,
            'shares': execution.shares,
            'side': execution.side,
            'time': execution.time
        }
    
    def commissionReport(self, commissionReport: CommissionReport):
        """Commission report callback"""
        self.logger.info(f"Commission: ${commissionReport.commission:.2f} for execution {commissionReport.execId}")
    
    # ================================
    # Public Trading Methods
    # ================================
    
    def create_option_contract(self, symbol: str, strike: float, right: str, expiry: str = None) -> Contract:
        """
        Create option contract
        
        Args:
            symbol: Underlying symbol (e.g., 'SPY')
            strike: Strike price
            right: 'C' for call, 'P' for put  
            expiry: Expiration date (YYYYMMDD format, default today)
            
        Returns:
            Contract object
        """
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = expiry
        contract.strike = strike
        contract.right = right
        contract.multiplier = "100"
        
        return contract
    
    def get_option_price(self, symbol: str, strike: float, right: str, expiry: str = None) -> Optional[Tuple[float, float]]:
        """
        Get option bid/ask prices with improved reliability
        
        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' for call, 'P' for put
            expiry: Expiration date (default today)
            
        Returns:
            Tuple of (bid, ask) prices or None if failed
        """
        if not self.is_connected:
            self.logger.error("Not connected to IB Gateway")
            return None
            
        try:
            contract = self.create_option_contract(symbol, strike, right, expiry)
            req_id = self.get_next_req_id()
            
            # Clear any existing data
            if req_id in self.market_data:
                del self.market_data[req_id]
            
            # Request market data
            self.reqMktData(req_id, contract, "", False, False, [])
            
            # Wait for data with polling approach (more reliable than events)
            timeout = 8
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                if req_id in self.market_data:
                    data = self.market_data[req_id]
                    bid = data.get('BID')
                    ask = data.get('ASK')
                    
                    if bid is not None and ask is not None and bid > 0 and ask > 0:
                        # Cancel market data request
                        self.cancelMktData(req_id)
                        return float(bid), float(ask)
                
                time.sleep(0.2)  # Check every 200ms
            
            # Timeout - cancel request and return None
            self.cancelMktData(req_id)
            self.logger.warning(f"Timeout getting price for {symbol} {strike}{right}")
            return None
                
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol} {strike}{right}: {e}")
            return None
        finally:
            # Clean up
            if req_id in self.market_data:
                del self.market_data[req_id]
    
    def place_market_order(self, contract: Contract, action: str, quantity: int) -> Optional[int]:
        """
        Place market order
        
        Args:
            contract: Option contract
            action: 'BUY' or 'SELL'
            quantity: Number of contracts
            
        Returns:
            Order ID if successful, None if failed
        """
        try:
            if not self.next_order_id:
                self.logger.error("No valid order ID available")
                return None
            
            order = Order()
            order.action = action
            order.orderType = "MKT"
            order.totalQuantity = quantity
            
            order_id = self.next_order_id
            self.next_order_id += 1
            
            # Create event to wait for order status
            self.data_events[order_id] = threading.Event()
            
            self.placeOrder(order_id, contract, order)
            self.logger.info(f"Placed {action} market order for {quantity} contracts (Order ID: {order_id})")
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None
    
    def place_stop_order(self, contract: Contract, action: str, quantity: int, stop_price: float) -> Optional[int]:
        """
        Place stop order
        
        Args:
            contract: Option contract
            action: 'BUY' or 'SELL'
            quantity: Number of contracts
            stop_price: Stop trigger price
            
        Returns:
            Order ID if successful, None if failed
        """
        try:
            if not self.next_order_id:
                self.logger.error("No valid order ID available")
                return None
            
            order = Order()
            order.action = action
            order.orderType = "STP"
            order.totalQuantity = quantity
            order.auxPrice = stop_price  # Stop price
            
            order_id = self.next_order_id
            self.next_order_id += 1
            
            # Create event to wait for order status
            self.data_events[order_id] = threading.Event()
            
            self.placeOrder(order_id, contract, order)
            self.logger.info(f"Placed {action} stop order for {quantity} contracts at ${stop_price:.2f} (Order ID: {order_id})")
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"Error placing stop order: {e}")
            return None
    
    def wait_for_order_fill(self, order_id: int, timeout: int = 30) -> bool:
        """
        Wait for order to be filled with improved polling
        
        Args:
            order_id: Order ID to monitor
            timeout: Timeout in seconds
            
        Returns:
            True if filled, False if timeout or error
        """
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if order_id in self.orders:
                    status = self.orders[order_id].get('status', '')
                    filled = self.orders[order_id].get('filled', 0)
                    
                    if status == 'Filled' or filled > 0:
                        self.logger.info(f"Order {order_id} filled: status={status}, filled={filled}")
                        return True
                    elif status in ['Cancelled', 'ApiCancelled']:
                        self.logger.warning(f"Order {order_id} was cancelled: {status}")
                        return False
                    elif status in ['PreSubmitted', 'Submitted']:
                        self.logger.debug(f"Order {order_id} status: {status}")
                
                time.sleep(0.3)  # Poll more frequently
            
            # Log final status before timeout
            if order_id in self.orders:
                final_status = self.orders[order_id].get('status', 'Unknown')
                self.logger.warning(f"Order {order_id} timeout - final status: {final_status}")
            else:
                self.logger.warning(f"Order {order_id} not found in orders dict")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for order fill: {e}")
            return False
    
    def get_order_fill_price(self, order_id: int) -> Optional[float]:
        """
        Get average fill price for an order
        
        Args:
            order_id: Order ID
            
        Returns:
            Average fill price or None if not available
        """
        if order_id in self.orders:
            return self.orders[order_id].get('avgFillPrice')
        return None
    
    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancel request sent successfully
        """
        try:
            self.cancelOrder(order_id, "")
            self.logger.info(f"Sent cancel request for order {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_positions_list(self) -> List[Dict]:
        """
        Get current positions as list
        
        Returns:
            List of position dictionaries
        """
        return list(self.positions.values())
    
    def get_open_orders(self) -> List[Dict]:
        """
        Get open orders as list
        
        Returns:
            List of order dictionaries
        """
        return [order for order in self.orders.values() 
                if order.get('status') not in ['Filled', 'Cancelled', 'ApiCancelled']]
    
    # ================================
    # High-Level Trading Methods
    # (Compatible with ib_insync interface)
    # ================================
    
    def sell_option_with_stop(self, symbol: str, strike: float, right: str, 
                             stop_multiple: float = 3.0, quantity: int = 1, expiry: str = None) -> TradeResult:
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
            # Get current option prices
            prices = self.get_option_price(symbol, strike, right, expiry)
            if not prices:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message="Could not get option prices"
                )
            
            bid, ask = prices
            premium = bid  # Sell at bid
            stop_price = premium * stop_multiple
            
            self.logger.info(f"Selling {quantity} {symbol} {strike}{right} at ${premium:.2f}")
            self.logger.info(f"Setting stop loss at ${stop_price:.2f} ({stop_multiple}x premium)")
            
            # Create contract
            contract = self.create_option_contract(symbol, strike, right, expiry)
            
            # Place sell order
            sell_order_id = self.place_market_order(contract, 'SELL', quantity)
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
            
            # Wait for sell order to fill
            if not self.wait_for_order_fill(sell_order_id, timeout=30):
                self.cancel_order(sell_order_id)
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message="Sell order not filled within timeout"
                )
            
            # Get fill price
            fill_price = self.get_order_fill_price(sell_order_id)
            if not fill_price:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message="Could not get fill price"
                )
            
            # Calculate stop loss price based on actual fill
            stop_loss_price = fill_price * stop_multiple
            
            self.logger.info(f"Sell order filled at ${fill_price:.2f}")
            self.logger.info(f"Placing stop loss at ${stop_loss_price:.2f}")
            
            # Place stop loss order
            stop_order_id = self.place_stop_order(contract, 'BUY', quantity, stop_loss_price)
            if not stop_order_id:
                self.logger.error(f"CRITICAL: Failed to place stop loss for {symbol} {strike}{right}")
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=fill_price,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message=f"CRITICAL: Failed to place stop loss for {symbol} {strike}{right}"
                )
            
            # Calculate trade metrics
            credit = fill_price * 100 * quantity  # Options are $100 per point
            max_risk = (stop_loss_price - fill_price) * 100 * quantity
            
            return TradeResult(
                success=True,
                symbol=symbol,
                strike=strike,
                right=right,
                entry_price=fill_price,
                stop_loss=stop_loss_price,
                credit=credit,
                max_risk=max_risk,
                message=f"Successfully sold {quantity} {symbol} {strike}{right} at ${fill_price:.2f}",
                order_id=sell_order_id,
                contract_id=getattr(contract, 'conId', None)
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
    
    def close_option_position(self, symbol: str, strike: float, right: str, 
                            expiry: str = None) -> Optional[float]:
        """
        Close an option position at market
        
        Args:
            symbol: Stock symbol
            strike: Strike price
            right: 'C' for call, 'P' for put
            expiry: Expiration date (default today)
            
        Returns:
            Fill price if successful, None if failed
        """
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
        
        try:
            # Find position
            position_key = f"{symbol}_{strike}_{right}"
            if position_key not in self.positions:
                self.logger.warning(f"No position found for {symbol} {strike}{right}")
                return None
            
            position = self.positions[position_key]
            quantity = abs(int(position['position']))
            
            if quantity == 0:
                self.logger.info(f"Position already closed for {symbol} {strike}{right}")
                return None
            
            # Determine action (opposite of current position)
            action = 'BUY' if position['position'] < 0 else 'SELL'
            
            # Create contract and place closing order
            contract = self.create_option_contract(symbol, strike, right, expiry)
            order_id = self.place_market_order(contract, action, quantity)
            
            if not order_id:
                return None
            
            # Wait for fill
            if self.wait_for_order_fill(order_id, timeout=30):
                fill_price = self.get_order_fill_price(order_id)
                self.logger.info(f"Closed {symbol} {strike}{right} at ${fill_price:.2f}")
                return fill_price
            else:
                self.logger.error(f"Failed to close position: order not filled")
                return None
                
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return None
    
    def emergency_close_all(self) -> Dict[str, float]:
        """
        Emergency close all option positions
        
        Returns:
            Dictionary of {position_key: fill_price}
        """
        results = {}
        
        try:
            # Get all option positions
            option_positions = [p for p in self.positions.values() 
                              if p.get('right') in ['C', 'P'] and p['position'] != 0]
            
            self.logger.warning(f"EMERGENCY CLOSE: Closing {len(option_positions)} positions")
            
            for position in option_positions:
                key = f"{position['symbol']}_{position['strike']}_{position['right']}"
                fill_price = self.close_option_position(
                    symbol=position['symbol'],
                    strike=position['strike'],
                    right=position['right'],
                    expiry=position.get('expiry')
                )
                results[key] = fill_price
                
                # Small delay between orders
                time.sleep(1)
            
            # Cancel all open orders
            open_orders = self.get_open_orders()
            for order in open_orders:
                if 'order_id' in order:
                    self.cancel_order(order['order_id'])
                    self.logger.info(f"Cancelled order {order['order_id']}")
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Error in emergency close: {e}")
            return results