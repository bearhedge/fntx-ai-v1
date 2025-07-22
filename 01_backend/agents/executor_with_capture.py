#!/usr/bin/env python3
"""
Enhanced ExecutorAgent with Integrated Trade Capture
This version automatically logs all trades to the database
"""

from typing import Dict, List, Any

# Import the original ExecutorAgent
from 01_backend.agents.executor import ExecutorAgent
from 01_backend.services.integrated_trade_capture import create_trade_capture_hook
from 01_backend.database.trade_db import get_trade_db_config
import logging

logger = logging.getLogger(__name__)

class ExecutorAgentWithCapture(ExecutorAgent):
    """Enhanced ExecutorAgent that automatically captures all trades"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize trade capture hook
        try:
            db_config = get_trade_db_config()
            self.trade_capture_hook = create_trade_capture_hook(db_config)
            logger.info("Trade capture hook initialized")
        except Exception as e:
            logger.error(f"Failed to initialize trade capture: {e}")
            self.trade_capture_hook = None
    
    def execute_trade(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade with automatic capture"""
        # Execute the trade using parent method
        trade_result = super().execute_trade(instruction)
        
        # Capture the trade if successful
        if self.trade_capture_hook and trade_result.get("status") == "submitted":
            try:
                # Prepare trade data for capture
                trade_data = {
                    "order_id": trade_result.get("trade_id"),
                    "symbol": instruction.get("symbol", "SPY"),
                    "strike": instruction.get("strike"),
                    "option_type": instruction.get("option_type"),
                    "expiration": instruction.get("expiration"),
                    "quantity": instruction.get("quantity"),
                    "entry_price": instruction.get("limit_price"),
                    "market_snapshot": {
                        "timestamp": trade_result.get("timestamp"),
                        "mode": trade_result.get("mode"),
                        "strategy": instruction.get("strategy")
                    }
                }
                
                # Add stop loss and take profit info if available
                if "stop_loss" in instruction:
                    trade_data["stop_loss_price"] = instruction["stop_loss"]
                if "take_profit" in instruction:
                    trade_data["take_profit_price"] = instruction["take_profit"]
                
                # Capture the trade
                self.trade_capture_hook("trade_placed", trade_data)
                
                logger.info(f"Trade automatically captured: {trade_data['order_id']}")
                
            except Exception as e:
                logger.error(f"Failed to capture trade: {e}")
        
        return trade_result
    
    def monitor_active_trades(self) -> List[Dict[str, Any]]:
        """Monitor trades and capture closures"""
        updates = super().monitor_active_trades()
        
        # Check for filled orders that need closure capture
        if self.trade_capture_hook and self.connected:
            try:
                trades = self.ib.trades()
                
                for trade in trades:
                    if trade.orderStatus.status == 'Filled' and trade.order.action == 'BUY':
                        # This is a closing trade (buying back)
                        exit_data = {
                            "order_id": trade.order.orderId,
                            "exit_price": trade.orderStatus.avgFillPrice,
                            "exit_reason": "manual"
                        }
                        
                        self.trade_capture_hook("trade_closed", exit_data)
                        
            except Exception as e:
                logger.error(f"Error monitoring trade closures: {e}")
        
        return updates


# Integration function for the orchestrator
def get_executor_with_capture():
    """Get an executor instance with trade capture enabled"""
    return ExecutorAgentWithCapture()