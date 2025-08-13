#!/usr/bin/env python3
"""
Unified Options Trading System
"""
from ib_insync import *
from ib_insync import util
from datetime import datetime, timedelta
import logging
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
# from trade_logger import TradeLogger, TradeRecord  # Comment out for now

@dataclass
class TradeResult:
    success: bool
    symbol: str
    strike: float
    right: str
    entry_price: float
    stop_loss: float
    credit: float
    max_risk: float
    message: str

class OptionsTrader:
    def __init__(self, host='127.0.0.1', port=4001):
        self.host = host
        self.port = port
        self.ib = None
        # Generate unique client ID to avoid conflicts - use larger range
        self.client_id = random.randint(1000, 9999)
        
    def connect(self) -> bool:
        """Connect to IB Gateway"""
        try:
            # Clear any ghost CLOSE_WAIT connections first
            import subprocess
            import socket
            import struct
            logging.info("Clearing any ghost connections...")
            
            # Get list of CLOSE_WAIT connections
            try:
                result = subprocess.run("ss -tn state close-wait | grep 4001 | awk '{print $4}'", 
                                      shell=True, capture_output=True, text=True)
                if result.stdout:
                    connections = result.stdout.strip().split('\n')
                    for conn in connections:
                        if ':4001' in conn:
                            logging.info(f"Found ghost connection: {conn}")
                            # Force close by creating and immediately closing a socket with SO_LINGER
                            try:
                                # Parse the local address
                                parts = conn.rsplit(':', 1)
                                if len(parts) == 2:
                                    local_port = int(parts[1])
                                    # Create socket with SO_LINGER to force RST
                                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                    # Set SO_LINGER with 0 timeout to force RST
                                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 
                                                  struct.pack('ii', 1, 0))
                                    try:
                                        sock.bind(('127.0.0.1', local_port))
                                    except:
                                        pass  # Port might be in use
                                    sock.close()
                            except Exception as e:
                                logging.debug(f"Could not force close {conn}: {e}")
            except Exception as e:
                logging.debug(f"Error checking ghost connections: {e}")
            
            # Also try ss -K without sudo (might work on some systems)
            subprocess.run("ss -K dst :4001 state close-wait 2>/dev/null || true", 
                         shell=True, capture_output=True)
            
            time.sleep(5)  # Give system more time to clean up
            
            self.ib = IB()
            logging.info(f"Connecting to {self.host}:{self.port} with clientId {self.client_id}...")
            
            # Connect to IB Gateway with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=30)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"Connection attempt {attempt + 1} failed: {e}")
                        logging.info(f"Retrying with new client ID in 10 seconds...")
                        if self.ib:
                            try:
                                self.ib.disconnect()
                            except:
                                pass
                        time.sleep(10)
                        # Generate new client ID for retry
                        self.client_id = random.randint(1000, 9999)
                        logging.info(f"Retry attempt {attempt + 2} with clientId {self.client_id}")
                    else:
                        raise
            
            # Verify connection is established
            if self.ib.isConnected():
                logging.info(f"✅ Connected to IB Gateway (clientId: {self.client_id})")
                return True
            else:
                logging.error("Connection failed - not fully connected")
                return False
                
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IB Gateway"""
        if self.ib:
            self.ib.disconnect()
    
    def get_option_price(self, symbol: str, strike: float, right: str, expiry: str = None) -> Optional[Tuple[float, float]]:
        """Get option bid/ask prices"""
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
            
        contract = Option(
            symbol=symbol,
            lastTradeDateOrContractMonth=expiry,
            strike=strike,
            right=right,
            exchange='SMART',
            currency='USD'
        )
        
        try:
            self.ib.qualifyContracts(contract)
            self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(2)
            
            ticker = self.ib.ticker(contract)
            if ticker.bid and ticker.ask:
                return ticker.bid, ticker.ask
            return None
        except Exception as e:
            logging.error(f"Error getting price for {symbol} {strike}{right}: {e}")
            return None
    
    def sell_option_with_stop(self, symbol: str, strike: float, right: str, 
                             stop_multiple: float = 3.0, quantity: int = 1, expiry: str = None) -> TradeResult:
        """
        Sell option with stop loss
        
        Args:
            symbol: Stock symbol (e.g., 'SPY')
            strike: Strike price
            right: 'C' for call, 'P' for put
            stop_multiple: Stop loss as multiple of premium (default 3x)
            quantity: Number of contracts to trade (default 1)
            expiry: Expiration date (default today)
        """
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
            
        # Get current price
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
        
        # Create contract
        contract = Option(
            symbol=symbol,
            lastTradeDateOrContractMonth=expiry,
            strike=strike,
            right=right,
            exchange='SMART',
            currency='USD'
        )
        
        try:
            # Place sell order
            logging.info(f"Placing SELL order for {quantity} {symbol} {strike}{right}")
            sell_order = MarketOrder('SELL', quantity)
            trade = self.ib.placeOrder(contract, sell_order)
            self.ib.sleep(3)
            
            if trade.orderStatus.status == 'Filled':
                fill_price = trade.orderStatus.avgFillPrice
                stop_loss_price = fill_price * stop_multiple
                
                logging.info(f"Sell order FILLED at ${fill_price:.2f}, placing stop loss at ${stop_loss_price:.2f}")
                
                # Place stop loss
                stop_order = StopOrder('BUY', quantity, stopPrice=stop_loss_price)
                logging.info(f"Creating stop order: BUY {quantity} at ${stop_loss_price:.2f}")
                stop_trade = self.ib.placeOrder(contract, stop_order)
                
                # Wait for stop order to be processed
                self.ib.sleep(2)
                
                # Verify stop order was placed successfully
                if not stop_trade or stop_trade.orderStatus.status in ['Cancelled', 'ApiCancelled']:
                    logging.error(f"CRITICAL: Stop loss order failed for {symbol} {strike}{right}")
                    logging.error(f"Stop order status: {stop_trade.orderStatus.status if stop_trade else 'None'}")
                    # Cancel the sell order since we couldn't place the stop
                    self.ib.cancelOrder(trade.order)
                    return TradeResult(
                        success=False,
                        symbol=symbol,
                        strike=strike,
                        right=right,
                        entry_price=fill_price,
                        stop_loss=0,
                        credit=0,
                        max_risk=0,
                        message=f"CRITICAL: Failed to place stop loss for {symbol} {strike}{right} - position closed"
                    )
                
                logging.info(f"Stop loss placed successfully for {symbol} {strike}{right} at ${stop_loss_price:.2f}")
                
                return TradeResult(
                    success=True,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=fill_price,
                    stop_loss=stop_loss_price,
                    credit=fill_price * 100 * quantity,
                    max_risk=(stop_loss_price - fill_price) * 100 * quantity,
                    message=f"Successfully sold {quantity} {symbol} {strike}{right} at ${fill_price:.2f}"
                )
            else:
                return TradeResult(
                    success=False,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=0,
                    stop_loss=0,
                    credit=0,
                    max_risk=0,
                    message=f"Order not filled: {trade.orderStatus.status}"
                )
                
        except Exception as e:
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
    
    def sell_strangle(self, symbol: str, put_strike: float, call_strike: float, 
                     stop_multiple: float = 3.0, quantity: int = 1, expiry: str = None) -> List[TradeResult]:
        """
        Sell a strangle (put + call) with stop losses
        """
        results = []
        
        # Sell put
        put_result = self.sell_option_with_stop(
            symbol, put_strike, 'P', stop_multiple, quantity, expiry
        )
        results.append(put_result)
        
        # Sell call
        call_result = self.sell_option_with_stop(
            symbol, call_strike, 'C', stop_multiple, quantity, expiry
        )
        results.append(call_result)
        
        return results
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.ib:
            return []
            
        try:
            positions = self.ib.positions()
            position_list = []
            
            for pos in positions:
                if pos.position == 0:  # Skip zero positions
                    continue
                    
                # Get market price from portfolio items
                market_price = 0
                portfolio_items = self.ib.portfolio()
                for item in portfolio_items:
                    if (item.contract.symbol == pos.contract.symbol and 
                        getattr(item.contract, 'strike', None) == getattr(pos.contract, 'strike', None) and
                        getattr(item.contract, 'right', None) == getattr(pos.contract, 'right', None)):
                        market_price = item.marketPrice
                        break
                
                position_data = {
                    'symbol': pos.contract.symbol,
                    'strike': getattr(pos.contract, 'strike', None),
                    'right': getattr(pos.contract, 'right', None),
                    'expiry': getattr(pos.contract, 'lastTradeDateOrContractMonth', None),
                    'position': pos.position,
                    'avgCost': pos.avgCost,
                    'marketPrice': market_price,
                    'marketValue': market_price * abs(pos.position) * 100 if market_price else 0  # 100 shares per contract
                }
                position_list.append(position_data)
                
            return position_list
        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return []
    
    def close_option_position(self, symbol: str, strike: float, right: str, 
                            expiry: str = None) -> Optional[float]:
        """
        Close an option position
        
        Returns:
            Fill price if successful, None if failed
        """
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
            
        try:
            # Get current position
            positions = self.get_positions()
            position = None
            
            for pos in positions:
                if (pos['symbol'] == symbol and 
                    pos['strike'] == strike and 
                    pos['right'] == right):
                    position = pos
                    break
                    
            if not position:
                logging.warning(f"No position found for {symbol} {strike}{right}")
                return None
                
            # Create contract
            contract = Option(
                symbol=symbol,
                lastTradeDateOrContractMonth=expiry,
                strike=strike,
                right=right,
                exchange='SMART',
                currency='USD'
            )
            
            # Qualify contract
            self.ib.qualifyContracts(contract)
            
            # Determine action and quantity
            quantity = abs(position['position'])
            action = 'BUY' if position['position'] < 0 else 'SELL'
            
            # Place market order to close
            order = MarketOrder(action, quantity)
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for fill
            self.ib.sleep(5)
            
            if trade.orderStatus.status == 'Filled':
                fill_price = trade.orderStatus.avgFillPrice
                logging.info(f"Closed {symbol} {strike}{right} at ${fill_price:.2f}")
                return fill_price
            else:
                logging.error(f"Failed to close position: {trade.orderStatus.status}")
                return None
                
        except Exception as e:
            logging.error(f"Error closing position: {e}")
            return None
            
    def convert_stop_to_market(self, order_id: int) -> bool:
        """
        Convert a stop order to market order
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get open orders
            open_orders = self.ib.openOrders()
            
            # Find the specific order
            target_order = None
            for order in open_orders:
                if order.orderId == order_id:
                    target_order = order
                    break
                    
            if not target_order:
                logging.warning(f"Order {order_id} not found")
                return False
                
            if target_order.orderType != 'STP':
                logging.warning(f"Order {order_id} is not a stop order")
                return False
                
            # Cancel the stop order
            self.ib.cancelOrder(target_order)
            self.ib.sleep(2)
            
            # Place market order with same parameters
            market_order = MarketOrder(
                action=target_order.action,
                totalQuantity=target_order.totalQuantity
            )
            
            new_trade = self.ib.placeOrder(target_order.contract, market_order)
            logging.info(f"Converted stop order {order_id} to market order")
            
            return True
            
        except Exception as e:
            logging.error(f"Error converting stop to market: {e}")
            return False
            
    def get_option_moneyness(self, symbol: str, strike: float, right: str, 
                           spot_price: float) -> float:
        """
        Calculate moneyness for an option
        
        Args:
            symbol: Underlying symbol
            strike: Strike price
            right: 'C' for call, 'P' for put
            spot_price: Current spot price
            
        Returns:
            Moneyness as decimal (positive = ITM, negative = OTM)
        """
        if right == 'C':  # Call
            return (spot_price - strike) / strike
        else:  # Put
            return (strike - spot_price) / strike
            
    def emergency_close_all(self) -> Dict[str, float]:
        """
        Emergency close all option positions
        
        Returns:
            Dictionary of {position_key: fill_price}
        """
        results = {}
        
        try:
            positions = self.get_positions()
            options_positions = [p for p in positions if p.get('right') in ['C', 'P']]
            
            logging.warning(f"EMERGENCY CLOSE: Closing {len(options_positions)} positions")
            
            for position in options_positions:
                key = f"{position['symbol']}_{position['strike']}{position['right']}"
                
                fill_price = self.close_option_position(
                    symbol=position['symbol'],
                    strike=position['strike'],
                    right=position['right'],
                    expiry=position.get('expiry')
                )
                
                results[key] = fill_price
                
                # Small delay between orders
                self.ib.sleep(1)
                
            # Also cancel all open orders
            open_orders = self.ib.openOrders()
            for order in open_orders:
                self.ib.cancelOrder(order)
                logging.info(f"Cancelled order {order.orderId}")
                
            return results
            
        except Exception as e:
            logging.error(f"Error in emergency close: {e}")
            return results