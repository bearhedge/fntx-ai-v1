#!/usr/bin/env python3
"""
Trade Logging System
"""
import json
import os
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict

@dataclass
class TradeRecord:
    timestamp: str
    symbol: str
    strike: float
    right: str  # 'C' or 'P'
    action: str  # 'SELL', 'BUY'
    quantity: int
    entry_price: float
    stop_loss: float
    credit: float
    max_risk: float
    expiry: str
    status: str  # 'FILLED', 'CANCELLED', 'PENDING'
    trade_id: str

class TradeLogger:
    def __init__(self, log_file='trade_history.json'):
        self.log_file = log_file
        self.trades = self.load_trades()
    
    def load_trades(self) -> List[TradeRecord]:
        """Load existing trades from file"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    return [TradeRecord(**trade) for trade in data]
            except:
                return []
        return []
    
    def save_trades(self):
        """Save trades to file"""
        with open(self.log_file, 'w') as f:
            json.dump([asdict(trade) for trade in self.trades], f, indent=2)
    
    def log_trade(self, trade_record: TradeRecord):
        """Add new trade to log"""
        self.trades.append(trade_record)
        self.save_trades()
    
    def get_trades_by_date(self, date: str) -> List[TradeRecord]:
        """Get trades for specific date (YYYY-MM-DD)"""
        return [t for t in self.trades if t.timestamp.startswith(date)]
    
    def get_daily_pnl(self, date: str) -> Dict:
        """Calculate P&L for a specific date"""
        trades = self.get_trades_by_date(date)
        total_credit = sum(t.credit for t in trades if t.action == 'SELL')
        total_risk = sum(t.max_risk for t in trades if t.action == 'SELL')
        
        return {
            'date': date,
            'trades_count': len(trades),
            'total_credit': total_credit,
            'total_max_risk': total_risk,
            'net_position': total_credit  # Assuming options expire worthless
        }
    
    def print_trade_summary(self):
        """Print formatted trade summary"""
        if not self.trades:
            print("No trades recorded")
            return
            
        print("=== TRADE HISTORY ===")
        for trade in sorted(self.trades, key=lambda x: x.timestamp, reverse=True):
            print(f"{trade.timestamp[:10]} {trade.symbol} {trade.strike}{trade.right} "
                  f"{trade.action} @${trade.entry_price:.2f} "
                  f"Credit: ${trade.credit:.2f} Risk: ${trade.max_risk:.2f}")