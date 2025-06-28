#!/usr/bin/env python3
"""
IBKR Trade Logger Service
Automatically captures and logs all trades executed through Interactive Brokers
"""

import os
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid

from ib_insync import IB, Trade, Order, Execution, CommissionReport, Position
from ib_insync.contract import Option, Stock

logger = logging.getLogger(__name__)

class IBKRTradeLogger:
    """Automated trade logging service for IBKR trades"""
    
    def __init__(self, db_config: Dict[str, Any], websocket_manager=None):
        self.db_config = db_config
        self.websocket_manager = websocket_manager
        self.ib = IB()
        self.active_orders = {}  # Track orders being processed
        self.position_tracker = {}  # Track open positions
        
        # IBKR connection settings
        self.host = os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = int(os.getenv("IBKR_PORT", "4001"))
        self.client_id = 10  # Unique client ID for trade logger
        
    def connect(self):
        """Connect to IBKR and set up event handlers"""
        try:
            logger.info(f"Connecting Trade Logger to IBKR at {self.host}:{self.port}")
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            
            # Set up event handlers for automated capture
            self.ib.orderStatusEvent += self.on_order_status
            self.ib.execDetailsEvent += self.on_execution
            self.ib.commissionReportEvent += self.on_commission
            self.ib.positionEvent += self.on_position_update
            
            logger.info("Trade Logger connected and event handlers registered")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect Trade Logger: {e}")
            return False
    
    def on_order_status(self, trade: Trade):
        """Handle order status updates"""
        try:
            order = trade.order
            contract = trade.contract
            
            # Only process SPY options
            if contract.symbol != 'SPY' or contract.secType != 'OPT':
                return
            
            logger.info(f"Order Status: {order.orderId} - {trade.orderStatus.status}")
            
            # Track active orders
            if trade.orderStatus.status in ['PreSubmitted', 'Submitted']:
                self.active_orders[order.orderId] = {
                    'trade': trade,
                    'contract': contract,
                    'timestamp': datetime.now()
                }
            
            # Handle filled orders
            elif trade.orderStatus.status == 'Filled':
                asyncio.create_task(self._process_filled_order(trade))
                
        except Exception as e:
            logger.error(f"Error in order status handler: {e}")
    
    def on_execution(self, trade: Trade, execution: Execution):
        """Handle execution details"""
        try:
            contract = trade.contract
            
            # Only process SPY options
            if contract.symbol != 'SPY' or contract.secType != 'OPT':
                return
            
            logger.info(f"Execution: {execution.execId} for order {execution.orderId}")
            
            # Store execution details
            asyncio.create_task(self._log_execution(trade, execution))
            
        except Exception as e:
            logger.error(f"Error in execution handler: {e}")
    
    def on_commission(self, trade: Trade, commission: CommissionReport):
        """Handle commission reports"""
        try:
            logger.info(f"Commission: ${commission.commission} for execution {commission.execId}")
            
            # Update commission in database
            asyncio.create_task(self._update_commission(commission))
            
        except Exception as e:
            logger.error(f"Error in commission handler: {e}")
    
    def on_position_update(self, position: Position):
        """Track position changes for exit detection"""
        try:
            contract = position.contract
            
            # Only track SPY options
            if contract.symbol != 'SPY' or contract.secType != 'OPT':
                return
            
            key = f"{contract.symbol}_{contract.strike}_{contract.right}_{contract.lastTradeDateOrContractMonth}"
            
            # Detect position closure
            if key in self.position_tracker and position.position == 0:
                asyncio.create_task(self._handle_position_closed(key, position))
            
            # Update tracker
            self.position_tracker[key] = position
            
        except Exception as e:
            logger.error(f"Error in position update handler: {e}")
    
    async def _process_filled_order(self, trade: Trade):
        """Process a filled order and log to database"""
        order = trade.order
        contract = trade.contract
        status = trade.orderStatus
        
        # Determine if this is entry or exit
        if order.action == 'SELL' and order.orderType in ['LMT', 'MKT']:
            # This is an entry (selling options)
            await self._log_trade_entry(trade)
        elif order.action == 'BUY' and order.orderType in ['LMT', 'MKT']:
            # This is an exit (buying back)
            await self._log_trade_exit(trade)
        elif order.orderType == 'STP':
            # Stop loss order
            await self._link_stop_loss(trade)
    
    async def _log_trade_entry(self, trade: Trade):
        """Log a new trade entry to database"""
        order = trade.order
        contract = trade.contract
        status = trade.orderStatus
        
        # Capture market snapshot
        market_snapshot = await self._capture_market_snapshot()
        
        # Insert into database
        query = """
        INSERT INTO trading.trades (
            ibkr_order_id, ibkr_perm_id, symbol, strike_price, option_type,
            expiration, quantity, entry_time, entry_price, market_snapshot
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING trade_id
        """
        
        params = (
            order.orderId,
            order.permId,
            contract.symbol,
            contract.strike,
            contract.right,
            contract.lastTradeDateOrContractMonth,
            status.filled,
            datetime.now(),
            status.avgFillPrice,
            json.dumps(market_snapshot)
        )
        
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    trade_id = cur.fetchone()[0]
                    conn.commit()
                    
            logger.info(f"Logged new trade entry: {trade_id}")
            
            # Broadcast to frontend
            await self._broadcast_trade_update('new_trade', {
                'trade_id': str(trade_id),
                'strike': contract.strike,
                'type': contract.right,
                'quantity': status.filled,
                'entry_price': status.avgFillPrice
            })
            
        except Exception as e:
            logger.error(f"Failed to log trade entry: {e}")
    
    async def _log_trade_exit(self, trade: Trade):
        """Log trade exit and calculate P&L"""
        order = trade.order
        contract = trade.contract
        status = trade.orderStatus
        
        # Find the matching open trade
        query = """
        UPDATE trading.trades
        SET exit_time = %s, exit_price = %s, status = 'closed',
            exit_reason = %s, updated_at = CURRENT_TIMESTAMP
        WHERE symbol = %s AND strike_price = %s AND option_type = %s
            AND expiration = %s AND status = 'open'
            AND quantity = %s
        ORDER BY entry_time DESC
        LIMIT 1
        RETURNING trade_id, entry_price, quantity
        """
        
        # Determine exit reason
        exit_reason = 'manual'  # Default
        if order.orderType == 'STP':
            exit_reason = 'stopped_out'
        
        params = (
            datetime.now(),
            status.avgFillPrice,
            exit_reason,
            contract.symbol,
            contract.strike,
            contract.right,
            contract.lastTradeDateOrContractMonth,
            status.filled
        )
        
        try:
            with self._get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    conn.commit()
                    
                    if result:
                        # Calculate P&L
                        pnl = self._calculate_pnl(
                            result['entry_price'],
                            status.avgFillPrice,
                            result['quantity']
                        )
                        
                        logger.info(f"Closed trade {result['trade_id']} with P&L: ${pnl}")
                        
                        # Broadcast to frontend
                        await self._broadcast_trade_update('trade_closed', {
                            'trade_id': str(result['trade_id']),
                            'exit_price': status.avgFillPrice,
                            'pnl': pnl,
                            'exit_reason': exit_reason
                        })
                        
        except Exception as e:
            logger.error(f"Failed to log trade exit: {e}")
    
    async def _log_execution(self, trade: Trade, execution: Execution):
        """Log execution details"""
        query = """
        INSERT INTO trading.executions (
            trade_id, ibkr_exec_id, ibkr_order_id,
            execution_time, quantity, price
        )
        SELECT trade_id, %s, %s, %s, %s, %s
        FROM trading.trades
        WHERE ibkr_order_id = %s
        LIMIT 1
        """
        
        params = (
            execution.execId,
            execution.orderId,
            execution.time,
            execution.shares,
            execution.price,
            execution.orderId
        )
        
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
    
    async def _update_commission(self, commission: CommissionReport):
        """Update commission for execution"""
        query = """
        UPDATE trading.executions
        SET commission = %s
        WHERE ibkr_exec_id = %s
        """
        
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (commission.commission, commission.execId))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update commission: {e}")
    
    async def _capture_market_snapshot(self):
        """Capture current market conditions"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'spy_price': 0,
            'vix_level': 0,
            'market_hours': self._is_market_hours()
        }
        
        try:
            # Get current SPY price
            spy = Stock('SPY', 'SMART', 'USD')
            self.ib.qualifyContracts(spy)
            ticker = self.ib.reqTickers(spy)[0]
            if ticker.last:
                snapshot['spy_price'] = ticker.last
                
        except Exception as e:
            logger.error(f"Failed to capture market snapshot: {e}")
            
        return snapshot
    
    async def _broadcast_trade_update(self, event_type: str, data: Dict):
        """Broadcast trade updates to frontend via WebSocket"""
        if self.websocket_manager:
            message = {
                'type': 'trade_update',
                'event': event_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            await self.websocket_manager.broadcast(message)
    
    def _calculate_pnl(self, entry_price: float, exit_price: float, quantity: int) -> float:
        """Calculate P&L for options trade"""
        # For sold options: (entry_price - exit_price) * quantity * 100
        return (entry_price - exit_price) * quantity * 100
    
    def _is_market_hours(self) -> bool:
        """Check if market is open"""
        now = datetime.now()
        if now.weekday() >= 5:  # Weekend
            return False
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        return market_open <= now <= market_close
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    async def start(self):
        """Start the trade logger service"""
        if self.connect():
            logger.info("IBKR Trade Logger service started")
            
            # Keep service running
            while self.ib.isConnected():
                await asyncio.sleep(1)
        else:
            logger.error("Failed to start Trade Logger service")
    
    def stop(self):
        """Stop the trade logger service"""
        if self.ib.isConnected():
            self.ib.disconnect()
        logger.info("IBKR Trade Logger service stopped")