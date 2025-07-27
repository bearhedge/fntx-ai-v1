#!/usr/bin/env python3
"""
Integrated Trade Capture Service
Ensures all trades executed through the system are automatically logged
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json

logger = logging.getLogger(__name__)

class IntegratedTradeCapture:
    """Captures trades from all sources - UI, chatbot, and automated systems"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
    
    def capture_trade_entry(self, trade_details: Dict[str, Any]) -> Optional[str]:
        """Capture a new trade entry from any source"""
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Insert trade entry
                    query = """
                    INSERT INTO trading.trades (
                        ibkr_order_id, symbol, strike_price, option_type,
                        expiration, quantity, entry_time, entry_price,
                        entry_commission, market_snapshot, 
                        stop_loss_order_id, stop_loss_price,
                        take_profit_order_id, take_profit_price
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING trade_id
                    """
                    
                    params = (
                        trade_details.get('order_id'),
                        trade_details.get('symbol', 'SPY'),
                        trade_details.get('strike'),
                        trade_details.get('option_type'),
                        trade_details.get('expiration'),
                        trade_details.get('quantity'),
                        datetime.now(),
                        trade_details.get('entry_price'),
                        trade_details.get('commission', 0),
                        json.dumps(trade_details.get('market_snapshot', {})),
                        trade_details.get('stop_loss_order_id'),
                        trade_details.get('stop_loss_price'),
                        trade_details.get('take_profit_order_id'),
                        trade_details.get('take_profit_price')
                    )
                    
                    cur.execute(query, params)
                    trade_id = cur.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"Captured new trade entry: {trade_id}")
                    return str(trade_id)
                    
        except Exception as e:
            logger.error(f"Failed to capture trade entry: {e}")
            return None
    
    def capture_trade_exit(self, order_id: int, exit_details: Dict[str, Any]) -> bool:
        """Capture trade exit/closure"""
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Update trade with exit details
                    query = """
                    UPDATE trading.trades
                    SET exit_time = %s, exit_price = %s, exit_commission = %s,
                        exit_reason = %s, status = 'closed',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE ibkr_order_id = %s AND status = 'open'
                    RETURNING trade_id
                    """
                    
                    params = (
                        datetime.now(),
                        exit_details.get('exit_price'),
                        exit_details.get('commission', 0),
                        exit_details.get('exit_reason', 'manual'),
                        order_id
                    )
                    
                    cur.execute(query, params)
                    result = cur.fetchone()
                    
                    if result:
                        conn.commit()
                        logger.info(f"Captured trade exit for order {order_id}")
                        return True
                    else:
                        logger.warning(f"No open trade found for order {order_id}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to capture trade exit: {e}")
            return False
    
    def get_open_positions(self) -> list:
        """Get all currently open positions"""
        try:
            with self._get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                    SELECT * FROM trading.trades
                    WHERE status = 'open'
                    ORDER BY entry_time DESC
                    """
                    cur.execute(query)
                    return cur.fetchall()
                    
        except Exception as e:
            logger.error(f"Failed to get open positions: {e}")
            return []
    
    def link_orders(self, parent_order_id: int, child_order_id: int, order_type: str):
        """Link stop loss or take profit orders to parent trade"""
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                    INSERT INTO trading.order_links (
                        parent_order_id, child_order_id, order_type
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT (parent_order_id, child_order_id) DO NOTHING
                    """
                    
                    cur.execute(query, (parent_order_id, child_order_id, order_type))
                    conn.commit()
                    
                    logger.info(f"Linked {order_type} order {child_order_id} to parent {parent_order_id}")
                    
        except Exception as e:
            logger.error(f"Failed to link orders: {e}")
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)


# Integration hook for ExecutorAgent
def create_trade_capture_hook(db_config: Dict[str, Any]):
    """Create a hook function for the ExecutorAgent to capture trades"""
    capture_service = IntegratedTradeCapture(db_config)
    
    def capture_hook(trade_event: str, trade_data: Dict[str, Any]):
        """Hook function to be called by ExecutorAgent"""
        if trade_event == "trade_placed":
            # Capture new trade entry
            trade_id = capture_service.capture_trade_entry(trade_data)
            trade_data['db_trade_id'] = trade_id
            
        elif trade_event == "trade_closed":
            # Capture trade exit
            capture_service.capture_trade_exit(
                trade_data.get('order_id'),
                trade_data
            )
            
        elif trade_event == "stop_loss_placed":
            # Link stop loss order
            capture_service.link_orders(
                trade_data.get('parent_order_id'),
                trade_data.get('stop_loss_order_id'),
                'stop_loss'
            )
            
        elif trade_event == "take_profit_placed":
            # Link take profit order
            capture_service.link_orders(
                trade_data.get('parent_order_id'),
                trade_data.get('take_profit_order_id'),
                'take_profit'
            )
    
    return capture_hook