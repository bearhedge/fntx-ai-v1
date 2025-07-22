#!/usr/bin/env python3
"""
Unified Options Trading System
"""
from ib_insync import *
from datetime import datetime, timedelta
import logging
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
        self.client_id = 10  # Use higher ID to avoid conflicts
        
    def connect(self) -> bool:
        """Connect to IB Gateway"""
        try:
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            return True
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
                             stop_multiple: float = 3.0, expiry: str = None) -> TradeResult:
        """
        Sell option with stop loss
        
        Args:
            symbol: Stock symbol (e.g., 'SPY')
            strike: Strike price
            right: 'C' for call, 'P' for put
            stop_multiple: Stop loss as multiple of premium (default 3x)
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
            sell_order = MarketOrder('SELL', 1)
            trade = self.ib.placeOrder(contract, sell_order)
            self.ib.sleep(3)
            
            if trade.orderStatus.status == 'Filled':
                fill_price = trade.orderStatus.avgFillPrice
                stop_loss_price = fill_price * stop_multiple
                
                # Place stop loss
                stop_order = StopOrder('BUY', 1, stopPrice=stop_loss_price)
                self.ib.placeOrder(contract, stop_order)
                
                return TradeResult(
                    success=True,
                    symbol=symbol,
                    strike=strike,
                    right=right,
                    entry_price=fill_price,
                    stop_loss=stop_loss_price,
                    credit=fill_price * 100,
                    max_risk=(stop_loss_price - fill_price) * 100,
                    message=f"Successfully sold {symbol} {strike}{right} at ${fill_price:.2f}"
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
                     stop_multiple: float = 3.0, expiry: str = None) -> List[TradeResult]:
        """
        Sell a strangle (put + call) with stop losses
        """
        results = []
        
        # Sell put
        put_result = self.sell_option_with_stop(
            symbol, put_strike, 'P', stop_multiple, expiry
        )
        results.append(put_result)
        
        # Sell call
        call_result = self.sell_option_with_stop(
            symbol, call_strike, 'C', stop_multiple, expiry
        )
        results.append(call_result)
        
        return results
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.ib:
            return []
            
        try:
            positions = self.ib.positions()
            return [
                {
                    'symbol': pos.contract.symbol,
                    'strike': getattr(pos.contract, 'strike', None),
                    'right': getattr(pos.contract, 'right', None),
                    'position': pos.position,
                    'avgCost': pos.avgCost,
                    'marketValue': pos.marketValue
                }
                for pos in positions
            ]
        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return []