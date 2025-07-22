"""
Stop Loss Enforcer - Monitors and enforces stop loss rules
"""
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime


class StopLossEnforcer:
    """Enforces stop loss rules for trading positions"""
    
    def __init__(self, stop_loss_multiple: float = 3.5):
        self.stop_loss_multiple = stop_loss_multiple
        self.logger = logging.getLogger(__name__)
        self.positions = {}
        self.violations = []
        
    def update_positions(self, positions: Dict) -> None:
        """Update tracked positions"""
        self.positions = positions
        
    def check_violations(self, current_prices: Dict) -> List[Dict]:
        """Check for stop loss violations"""
        violations = []
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                entry_price = position.get('entry_price', 0)
                
                if entry_price > 0:
                    loss = abs(current_price - entry_price)
                    stop_loss_level = entry_price * self.stop_loss_multiple
                    
                    if loss >= stop_loss_level:
                        violations.append({
                            'symbol': symbol,
                            'entry_price': entry_price,
                            'current_price': current_price,
                            'loss': loss,
                            'stop_loss_level': stop_loss_level,
                            'timestamp': datetime.now()
                        })
                        
        self.violations = violations
        return violations
    
    def get_risk_status(self) -> str:
        """Get current risk status"""
        if self.violations:
            return "STOP_LOSS_TRIGGERED"
        elif self.positions:
            return "MONITORING"
        else:
            return "NO_POSITIONS"
    
    def should_close_position(self, symbol: str, current_price: float) -> bool:
        """Check if position should be closed"""
        if symbol not in self.positions:
            return False
            
        position = self.positions[symbol]
        entry_price = position.get('entry_price', 0)
        
        if entry_price > 0:
            loss = abs(current_price - entry_price)
            stop_loss_level = entry_price * self.stop_loss_multiple
            return loss >= stop_loss_level
            
        return False