#!/usr/bin/env python3
"""
FNTX AI ExecutorAgent - Autonomous Options Trading Execution
Handles paper trading with IBKR integration and MCP memory management
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from ib_insync import IB, Stock, Option, Order, Trade
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with dynamic path
from 01_backend.utils.logging import get_agent_logger
from 01_backend.utils.config import config
logger = get_agent_logger('ExecutorAgent')

class ExecutorAgent:
    """
    ExecutorAgent handles the execution of trading decisions from the planner agent.
    Supports both paper trading (development) and live trading (production).
    """
    
    def __init__(self):
        self.memory_file = config.get_memory_path("executor_memory.json")
        self.shared_context_file = config.get_memory_path("shared_context.json")
        self.ib = IB()
        self.connected = False
        self.paper_mode = os.getenv("TRADING_MODE", "paper").lower() == "paper"
        
        # IBKR Connection settings
        self.host = os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = int(os.getenv("IBKR_PORT", "4002" if self.paper_mode else "4001"))
        self.client_id = int(os.getenv("IBKR_CLIENT_ID", "2"))
        
        logger.info(f"ExecutorAgent initialized in {'PAPER' if self.paper_mode else 'LIVE'} mode")
        logger.info(f"IBKR Connection: {self.host}:{self.port} (Client ID: {self.client_id})")

    def connect_to_ibkr(self) -> bool:
        """Connect to Interactive Brokers API"""
        try:
            if self.connected:
                return True
                
            logger.info("Connecting to IBKR...")
            self.ib.connect(self.host, self.port, self.client_id)
            self.connected = True
            
            # Log account information
            account_summary = self.ib.accountSummary()
            if account_summary:
                logger.info("Successfully connected to IBKR")
                for item in account_summary:
                    if item.tag in ['TotalCashValue', 'NetLiquidation']:
                        logger.info(f"{item.tag}: {item.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False

    def disconnect_from_ibkr(self):
        """Disconnect from Interactive Brokers API"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")

    def load_memory(self) -> Dict[str, Any]:
        """Load executor memory from MCP-compatible JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
        
        return {
            "agent_id": "ExecutorAgent",
            "last_updated": datetime.now().isoformat(),
            "pending_trades": [],
            "executed_trades": [],
            "active_positions": [],
            "errors": []
        }

    def save_memory(self, memory: Dict[str, Any]):
        """Save executor memory to MCP-compatible JSON file"""
        try:
            memory["last_updated"] = datetime.now().isoformat()
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def load_trade_instructions(self) -> List[Dict[str, Any]]:
        """Load trade instructions from shared context and pending trades"""
        instructions = []
        
        # Load from executor memory
        memory = self.load_memory()
        instructions.extend(memory.get("pending_trades", []))
        
        # Load from shared context (from planner agent)
        try:
            if os.path.exists(self.shared_context_file):
                with open(self.shared_context_file, 'r') as f:
                    shared_context = json.load(f)
                    new_trades = shared_context.get("new_trade_instructions", [])
                    instructions.extend(new_trades)
        except Exception as e:
            logger.error(f"Error loading shared context: {e}")
        
        return instructions

    def create_option_contract(self, instruction: Dict[str, Any]) -> Optional[Option]:
        """Create an option contract from trade instruction"""
        try:
            contract = Option(
                symbol=instruction.get("symbol", "SPY"),
                lastTradeDateOrContractMonth=instruction["expiration"],
                strike=float(instruction["strike"]),
                right=instruction["option_type"],  # "C" for Call, "P" for Put
                exchange="SMART",
                currency="USD"
            )
            
            # Qualify the contract
            self.ib.qualifyContracts(contract)
            
            if not contract.conId:
                logger.error(f"Failed to qualify contract: {instruction}")
                return None
                
            logger.info(f"Created contract: {contract}")
            return contract
            
        except Exception as e:
            logger.error(f"Error creating contract: {e}")
            return None

    def create_bracket_order(self, instruction: Dict[str, Any]) -> Optional[List[Order]]:
        """Create bracket order with stop-loss and take-profit"""
        try:
            action = instruction.get("action", "SELL")  # Default to selling options
            quantity = int(instruction.get("quantity", 1))
            limit_price = float(instruction.get("limit_price", 0))
            
            # Calculate stop-loss and take-profit based on FNTX AI rules
            stop_loss_price = None
            take_profit_price = None
            
            if "stop_loss" in instruction:
                stop_loss_price = float(instruction["stop_loss"])
            elif limit_price > 0:
                # 3x premium loss rule
                stop_loss_price = limit_price * 3
                
            if "take_profit" in instruction:
                take_profit_price = float(instruction["take_profit"])
            elif limit_price > 0:
                # 50% premium capture rule
                take_profit_price = limit_price * 0.5
            
            bracket_orders = self.ib.bracketOrder(
                action=action,
                quantity=quantity,
                limitPrice=limit_price,
                takeProfitPrice=take_profit_price,
                stopLossPrice=stop_loss_price
            )
            
            logger.info(f"Created bracket order: Action={action}, Qty={quantity}, "
                       f"Limit=${limit_price}, TP=${take_profit_price}, SL=${stop_loss_price}")
            
            return bracket_orders
            
        except Exception as e:
            logger.error(f"Error creating bracket order: {e}")
            return None

    def execute_trade_instruction(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade instruction (alias for orchestrator compatibility)"""
        return self.execute_trade(instruction)
    
    def execute_trade(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single trade instruction"""
        trade_result = {
            "timestamp": datetime.now().isoformat(),
            "instruction": instruction,
            "mode": "paper" if self.paper_mode else "live",
            "status": "failed",
            "error": None,
            "trade_id": None,
            "order_status": None
        }
        
        try:
            if not self.connected:
                if not self.connect_to_ibkr():
                    trade_result["error"] = "Failed to connect to IBKR"
                    return trade_result
            
            # Create option contract
            contract = self.create_option_contract(instruction)
            if not contract:
                trade_result["error"] = "Failed to create option contract"
                return trade_result
            
            # Create bracket order
            orders = self.create_bracket_order(instruction)
            if not orders:
                trade_result["error"] = "Failed to create bracket order"
                return trade_result
            
            # Place the main order
            main_order = orders[0]
            trade = self.ib.placeOrder(contract, main_order)
            
            # Wait for order status update
            self.ib.sleep(2)
            
            # Update trade result
            trade_result.update({
                "status": "submitted",
                "trade_id": trade.order.orderId,
                "order_status": trade.orderStatus.status,
                "contract_details": {
                    "symbol": contract.symbol,
                    "strike": contract.strike,
                    "expiration": contract.lastTradeDateOrContractMonth,
                    "right": contract.right,
                    "conId": contract.conId
                }
            })
            
            logger.info(f"Trade executed successfully: {trade_result}")
            
        except Exception as e:
            trade_result["error"] = str(e)
            logger.error(f"Trade execution failed: {e}")
        
        return trade_result

    def monitor_active_trades(self) -> List[Dict[str, Any]]:
        """Monitor active trades and update their status"""
        updates = []
        
        try:
            if not self.connected:
                return updates
            
            # Get all open trades
            trades = self.ib.trades()
            
            for trade in trades:
                if trade.orderStatus.status in ['Submitted', 'PreSubmitted', 'PendingSubmit']:
                    update = {
                        "timestamp": datetime.now().isoformat(),
                        "trade_id": trade.order.orderId,
                        "status": trade.orderStatus.status,
                        "filled": trade.orderStatus.filled,
                        "remaining": trade.orderStatus.remaining,
                        "avg_fill_price": trade.orderStatus.avgFillPrice
                    }
                    updates.append(update)
                    
        except Exception as e:
            logger.error(f"Error monitoring trades: {e}")
        
        return updates

    def log_trade_result(self, trade_result: Dict[str, Any]):
        """Log trade result to MCP memory"""
        try:
            memory = self.load_memory()
            memory.setdefault("executed_trades", []).append(trade_result)
            
            # Keep only last 100 executed trades to prevent memory bloat
            if len(memory["executed_trades"]) > 100:
                memory["executed_trades"] = memory["executed_trades"][-100:]
            
            self.save_memory(memory)
            logger.info("Trade result logged to memory")
            
        except Exception as e:
            logger.error(f"Error logging trade result: {e}")

    def clear_pending_trades(self):
        """Clear processed pending trades from memory"""
        try:
            memory = self.load_memory()
            memory["pending_trades"] = []
            self.save_memory(memory)
        except Exception as e:
            logger.error(f"Error clearing pending trades: {e}")

    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        logger.info("Starting trading cycle...")
        
        try:
            # Load trade instructions
            instructions = self.load_trade_instructions()
            
            if not instructions:
                logger.info("No pending trade instructions")
                return
            
            logger.info(f"Found {len(instructions)} trade instructions")
            
            # Execute each instruction
            for instruction in instructions:
                logger.info(f"Processing trade instruction: {instruction}")
                
                # Add rationale and context for MCP learning
                trade_result = self.execute_trade(instruction)
                trade_result["rationale"] = instruction.get("rationale", "")
                trade_result["market_context"] = instruction.get("market_context", "")
                trade_result["strategy"] = instruction.get("strategy", "SPY_options_selling")
                
                # Log result for MCP learning
                self.log_trade_result(trade_result)
            
            # Clear processed instructions
            self.clear_pending_trades()
            
            # Monitor existing trades
            updates = self.monitor_active_trades()
            if updates:
                logger.info(f"Trade updates: {updates}")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")

    def run(self):
        """Main execution loop"""
        logger.info("ExecutorAgent starting main loop...")
        
        try:
            while True:
                self.run_trading_cycle()
                
                # Sleep for 10 seconds between cycles
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("ExecutorAgent stopped by user")
        except Exception as e:
            logger.error(f"ExecutorAgent crashed: {e}")
        finally:
            self.disconnect_from_ibkr()

def main():
    """Main entry point"""
    executor = ExecutorAgent()
    executor.run()

if __name__ == "__main__":
    main()