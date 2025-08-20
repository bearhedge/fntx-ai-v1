"""
Demo Data Generator for FNTX Terminal

Generates realistic-looking demo data for the dashboard.
"""

import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any

class DemoDataGenerator:
    """Generates demo trading data."""
    
    def __init__(self):
        """Initialize demo data generator."""
        self.base_price = 450.0  # SPY price
        self.positions = self._generate_positions()
        self.trades = self._generate_trades()
        
    def _generate_positions(self) -> List[Dict[str, Any]]:
        """Generate demo positions."""
        positions = []
        strikes = [445, 450, 455]
        types = ['P', 'C']
        
        for i in range(3):
            strike = random.choice(strikes)
            option_type = random.choice(types)
            positions.append({
                'symbol': f'SPY {strike}{option_type}',
                'quantity': random.choice([-1, -2, -5]),
                'entry_price': random.uniform(2.0, 5.0),
                'current_price': random.uniform(1.5, 5.5),
                'pnl': random.uniform(-200, 500),
                'delta': random.uniform(-0.5, 0.5),
            })
        
        return positions
    
    def _generate_trades(self) -> List[Dict[str, Any]]:
        """Generate demo trade history."""
        trades = []
        for i in range(10):
            trades.append({
                'time': datetime.now() - timedelta(hours=i),
                'symbol': f'SPY {445 + i*5}P',
                'action': random.choice(['BUY', 'SELL']),
                'quantity': random.choice([1, 2, 5, 10]),
                'price': random.uniform(2.0, 5.0),
                'pnl': random.uniform(-100, 300),
            })
        return trades
    
    def get_options_chain(self) -> Dict[str, Any]:
        """Get demo options chain data."""
        chain = []
        base = self.base_price
        
        for strike in range(int(base - 10), int(base + 11), 1):
            chain.append({
                'strike': strike,
                'call_bid': random.uniform(0.5, 5.0),
                'call_ask': random.uniform(0.6, 5.1),
                'call_volume': random.randint(100, 5000),
                'call_oi': random.randint(1000, 50000),
                'put_bid': random.uniform(0.5, 5.0),
                'put_ask': random.uniform(0.6, 5.1),
                'put_volume': random.randint(100, 5000),
                'put_oi': random.randint(1000, 50000),
            })
        
        return {'chain': chain, 'underlying': base}
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get demo market data."""
        return {
            'vix': 18.5 + random.uniform(-0.5, 0.5),
            'spy': self.base_price + random.uniform(-1, 1),
            'volume': random.randint(50000000, 100000000),
            'pc_ratio': 0.65 + random.uniform(-0.1, 0.1),
            'rsi': random.randint(30, 70),
            'macd': random.choice(['Bullish', 'Bearish', 'Neutral']),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get demo statistics."""
        return {
            'daily_pnl': random.uniform(-1000, 3000),
            'weekly_pnl': random.uniform(-2000, 8000),
            'monthly_pnl': random.uniform(5000, 20000),
            'win_rate': random.uniform(0.6, 0.8),
            'sharpe': random.uniform(1.0, 2.5),
            'max_dd': random.uniform(-0.05, -0.15),
            'trades_today': random.randint(5, 20),
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass

def get_demo_options_chain() -> str:
    """Get formatted demo options chain for display."""
    lines = []
    lines.append("Strike  Call Bid/Ask    Put Bid/Ask")
    lines.append("─" * 40)
    
    base = 450
    for strike in range(base - 5, base + 6):
        call_bid = random.uniform(0.5, 5.0)
        call_ask = call_bid + 0.05
        put_bid = random.uniform(0.5, 5.0)
        put_ask = put_bid + 0.05
        
        if strike == base:
            # ATM strike in green
            line = f"[green]{strike:3d}[/]    "
        elif strike < base:
            # ITM puts
            line = f"{strike:3d}    "
        else:
            # ITM calls
            line = f"{strike:3d}    "
        
        line += f"{call_bid:.2f}/{call_ask:.2f}    "
        line += f"{put_bid:.2f}/{put_ask:.2f}"
        
        lines.append(line)
    
    return "\n".join(lines)