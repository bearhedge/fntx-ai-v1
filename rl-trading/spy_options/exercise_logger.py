"""
Exercise Logger - Logs option exercise events
"""
import logging
from datetime import datetime
from typing import Dict, Optional
import json
import os


class ExerciseLogger:
    """Logs option exercise events to file and console"""
    
    def __init__(self, log_dir: str = "exercise_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup file logger
        self.logger = logging.getLogger("ExerciseLogger")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        log_file = os.path.join(log_dir, f"exercise_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_exercise_prevented(self, symbol: str, strike: float, option_type: str, 
                             current_price: float, reason: str):
        """Log when exercise is prevented"""
        event = {
            "event": "EXERCISE_PREVENTED",
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "strike": strike,
            "option_type": option_type,
            "current_price": current_price,
            "reason": reason
        }
        
        self.logger.info(f"Exercise prevented: {symbol} {strike} {option_type} - {reason}")
        self._save_event(event)
    
    def log_exercise_warning(self, symbol: str, strike: float, option_type: str,
                           current_price: float, time_to_expiry: float):
        """Log exercise warning"""
        event = {
            "event": "EXERCISE_WARNING",
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "strike": strike,
            "option_type": option_type,
            "current_price": current_price,
            "time_to_expiry_hours": time_to_expiry
        }
        
        self.logger.warning(f"Exercise warning: {symbol} {strike} {option_type} - "
                          f"{time_to_expiry:.1f} hours to expiry")
        self._save_event(event)
    
    def log_position_closed(self, symbol: str, strike: float, option_type: str,
                          exit_price: float, pnl: float):
        """Log position closure"""
        event = {
            "event": "POSITION_CLOSED",
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "strike": strike,
            "option_type": option_type,
            "exit_price": exit_price,
            "pnl": pnl
        }
        
        self.logger.info(f"Position closed: {symbol} {strike} {option_type} - "
                       f"Exit: ${exit_price:.2f}, P&L: ${pnl:.2f}")
        self._save_event(event)
    
    def _save_event(self, event: Dict):
        """Save event to JSON file"""
        try:
            filename = os.path.join(self.log_dir, f"events_{datetime.now().strftime('%Y%m%d')}.json")
            
            # Load existing events
            events = []
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    events = json.load(f)
            
            # Append new event
            events.append(event)
            
            # Save back
            with open(filename, 'w') as f:
                json.dump(events, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save event: {e}")


# Create singleton instance
exercise_logger = ExerciseLogger()