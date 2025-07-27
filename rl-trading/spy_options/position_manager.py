"""
Position Manager - Manages trading positions
"""
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import json


class PositionManager:
    """Manages trading positions and their state"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.positions = {}
        self.position_history = []
        
    def add_position(self, symbol: str, quantity: int, entry_price: float, 
                    position_type: str = 'LONG', **kwargs) -> Dict:
        """Add a new position"""
        position = {
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'type': position_type,
            'timestamp': datetime.now().isoformat(),
            'status': 'OPEN',
            **kwargs
        }
        
        self.positions[symbol] = position
        self.position_history.append(position.copy())
        self.logger.info(f"Added position: {symbol} - {quantity} @ ${entry_price}")
        
        return position
    
    def update_position(self, symbol: str, updates: Dict) -> Optional[Dict]:
        """Update an existing position"""
        if symbol in self.positions:
            self.positions[symbol].update(updates)
            self.positions[symbol]['last_updated'] = datetime.now().isoformat()
            return self.positions[symbol]
        return None
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[Dict]:
        """Close a position"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position['exit_price'] = exit_price
            position['status'] = 'CLOSED'
            position['closed_at'] = datetime.now().isoformat()
            
            # Calculate P&L
            if position['type'] == 'LONG':
                position['pnl'] = (exit_price - position['entry_price']) * position['quantity']
            else:  # SHORT
                position['pnl'] = (position['entry_price'] - exit_price) * position['quantity']
            
            # Move to history
            self.position_history.append(position.copy())
            del self.positions[symbol]
            
            self.logger.info(f"Closed position: {symbol} @ ${exit_price}, P&L: ${position['pnl']:.2f}")
            return position
        return None
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get a specific position"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Get all open positions"""
        return self.positions.copy()
    
    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self.positions)
    
    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in this symbol"""
        return symbol in self.positions
    
    def get_total_value(self, current_prices: Dict) -> float:
        """Calculate total position value"""
        total = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                value = current_prices[symbol] * position['quantity']
                total += value
        return total
    
    def get_unrealized_pnl(self, current_prices: Dict) -> float:
        """Calculate unrealized P&L"""
        total_pnl = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                if position['type'] == 'LONG':
                    pnl = (current_price - position['entry_price']) * position['quantity']
                else:  # SHORT
                    pnl = (position['entry_price'] - current_price) * position['quantity']
                total_pnl += pnl
        return total_pnl
    
    def save_state(self, filepath: str):
        """Save position state to file"""
        state = {
            'positions': self.positions,
            'history': self.position_history,
            'timestamp': datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, filepath: str):
        """Load position state from file"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
                self.positions = state.get('positions', {})
                self.position_history = state.get('history', [])
                self.logger.info(f"Loaded {len(self.positions)} positions from state")
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")