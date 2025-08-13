"""
Paper trading script for testing the trained RL model
Simulates real-time trading without actual money
"""
import json
import time
import argparse
from datetime import datetime, time as dtime
import numpy as np
from pathlib import Path
import yfinance as yf

from stable_baselines3 import PPO
from environments import SPY0DTEEnvironment
from data.market_data import get_current_market_state
from config import DB_CONFIG


class PaperTrader:
    """Paper trading system for RL model testing"""
    
    def __init__(self, model_path: str, log_dir: str = "logs/paper_trades"):
        self.model = PPO.load(model_path)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Track positions
        self.positions = {
            'calls': {'count': 0, 'strikes': [], 'entry_prices': []},
            'puts': {'count': 0, 'strikes': [], 'entry_prices': []}
        }
        
        # Daily limits (matching training environment)
        self.daily_limits = {'calls': 30, 'puts': 30}
        self.trades_today = []
        
        # State tracking
        self.last_trade_time = None
        self.current_state = None
        
    def get_market_state(self):
        """Get current market state for model input"""
        # This is a simplified version - in production, connect to real data feed
        spy = yf.Ticker("SPY")
        current_data = spy.history(period="1d", interval="1m")
        
        if len(current_data) == 0:
            return None
            
        latest = current_data.iloc[-1]
        current_time = datetime.now()
        
        # Calculate features matching training environment
        market_open = current_time.replace(hour=9, minute=30, second=0)
        market_close = current_time.replace(hour=16, minute=0, second=0)
        
        minutes_since_open = (current_time - market_open).total_seconds() / 60
        minutes_until_close = (market_close - current_time).total_seconds() / 60
        
        # Get IV proxy from recent price movement
        recent_prices = current_data['Close'].tail(20)
        returns = recent_prices.pct_change().dropna()
        iv_proxy = returns.std() * np.sqrt(252 * 78)  # Annualized
        
        state = {
            'minutes_since_open': min(max(minutes_since_open, 0), 390),
            'spot_price': latest['Close'],
            'atm_iv': min(max(iv_proxy, 0.1), 1.0),
            'has_position': 1 if (self.positions['calls']['count'] > 0 or 
                                 self.positions['puts']['count'] > 0) else 0,
            'position_pnl': self._calculate_pnl(),
            'time_in_position': self._get_time_in_position(),
            'risk_score': self._calculate_risk_score(),
            'minutes_until_close': max(minutes_until_close, 0)
        }
        
        return state
    
    def _calculate_pnl(self):
        """Calculate current P&L of open positions"""
        # Simplified - in production, get real option prices
        total_pnl = 0
        
        # For paper trading, assume 0.5% decay per hour
        if self.last_trade_time:
            hours_held = (datetime.now() - self.last_trade_time).total_seconds() / 3600
            decay = 0.005 * hours_held
            total_pnl = -(decay * (self.positions['calls']['count'] + 
                                  self.positions['puts']['count']) * 100)
        
        return total_pnl
    
    def _get_time_in_position(self):
        """Get minutes in current position"""
        if not self.last_trade_time:
            return 0
        return (datetime.now() - self.last_trade_time).total_seconds() / 60
    
    def _calculate_risk_score(self):
        """Calculate current risk score (0-1)"""
        # Based on position size and market conditions
        total_contracts = (self.positions['calls']['count'] + 
                          self.positions['puts']['count'])
        
        if total_contracts == 0:
            return 0.0
        elif total_contracts <= 10:
            return 0.2
        elif total_contracts <= 20:
            return 0.5
        else:
            return 0.8
    
    def _prepare_observation(self, state):
        """Convert state dict to model input format"""
        # Normalize features as done in training
        obs = np.array([
            state['minutes_since_open'] / 390,
            state['spot_price'] / 1000,
            state['atm_iv'],
            state['has_position'],
            state['position_pnl'] / 1000,
            state['time_in_position'] / 390,
            state['risk_score'],
            state['minutes_until_close'] / 390
        ], dtype=np.float32)
        
        return obs
    
    def execute_action(self, action: int, state: dict):
        """Execute the recommended action"""
        action_names = ['hold', 'sell_call', 'sell_put']
        action_name = action_names[action]
        
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': action_name,
            'state': state,
            'executed': False,
            'reason': ''
        }
        
        # Check if we can execute
        if action == 0:  # Hold
            trade_record['executed'] = True
            trade_record['reason'] = 'Hold signal'
            
        elif action == 1:  # Sell call
            if self.positions['calls']['count'] >= self.daily_limits['calls']:
                trade_record['reason'] = 'Daily call limit reached'
            else:
                self.positions['calls']['count'] += 10  # Sell 10 contracts
                self.positions['calls']['strikes'].append(state['spot_price'])
                self.last_trade_time = datetime.now()
                trade_record['executed'] = True
                trade_record['contracts'] = 10
                trade_record['type'] = 'call'
                
        elif action == 2:  # Sell put
            if self.positions['puts']['count'] >= self.daily_limits['puts']:
                trade_record['reason'] = 'Daily put limit reached'
            else:
                self.positions['puts']['count'] += 10  # Sell 10 contracts
                self.positions['puts']['strikes'].append(state['spot_price'])
                self.last_trade_time = datetime.now()
                trade_record['executed'] = True
                trade_record['contracts'] = 10
                trade_record['type'] = 'put'
        
        # Log trade
        self.trades_today.append(trade_record)
        self._save_trade(trade_record)
        
        return trade_record
    
    def _save_trade(self, trade):
        """Save trade to log file"""
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"trades_{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(trade) + '\n')
    
    def run_trading_session(self, interval_seconds: int = 300):
        """Run paper trading session (default 5-minute intervals)"""
        print("Starting paper trading session...")
        print(f"Model: {self.model}")
        print(f"Interval: {interval_seconds} seconds")
        print("-" * 50)
        
        while self._is_market_open():
            try:
                # Get current state
                state = self.get_market_state()
                if state is None:
                    print("Failed to get market state, retrying...")
                    time.sleep(30)
                    continue
                
                # Get model prediction
                obs = self._prepare_observation(state)
                action, _ = self.model.predict(obs, deterministic=True)
                
                # Execute action
                trade = self.execute_action(int(action), state)
                
                # Print summary
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                print(f"SPY Price: ${state['spot_price']:.2f}")
                print(f"Action: {trade['action']}")
                print(f"Executed: {trade['executed']}")
                if not trade['executed']:
                    print(f"Reason: {trade['reason']}")
                print(f"Positions - Calls: {self.positions['calls']['count']}, "
                      f"Puts: {self.positions['puts']['count']}")
                print(f"P&L: ${self._calculate_pnl():.2f}")
                
                # Wait for next interval
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("\nStopping paper trading...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(30)
        
        self._end_of_day_summary()
    
    def _is_market_open(self):
        """Check if market is open"""
        now = datetime.now()
        market_open = dtime(9, 30)
        market_close = dtime(16, 0)
        
        # Check if weekday
        if now.weekday() > 4:  # Saturday = 5, Sunday = 6
            return False
            
        return market_open <= now.time() <= market_close
    
    def _end_of_day_summary(self):
        """Print end of day summary"""
        print("\n" + "="*50)
        print("END OF DAY SUMMARY")
        print("="*50)
        print(f"Total trades: {len(self.trades_today)}")
        print(f"Executed trades: {sum(1 for t in self.trades_today if t['executed'])}")
        print(f"Final P&L: ${self._calculate_pnl():.2f}")
        print(f"Calls sold: {self.positions['calls']['count']}")
        print(f"Puts sold: {self.positions['puts']['count']}")
        
        # Save summary
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_trades': len(self.trades_today),
            'executed_trades': sum(1 for t in self.trades_today if t['executed']),
            'final_pnl': self._calculate_pnl(),
            'calls_sold': self.positions['calls']['count'],
            'puts_sold': self.positions['puts']['count']
        }
        
        summary_file = self.log_dir / f"summary_{datetime.now().strftime('%Y%m%d')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Paper trade with RL model')
    parser.add_argument('--model', type=str, default='models/gpu_trained/ppo_gpu_test_latest',
                        help='Path to trained model')
    parser.add_argument('--interval', type=int, default=300,
                        help='Trading interval in seconds (default: 300)')
    parser.add_argument('--log', type=str, default='logs/paper_trades',
                        help='Log directory')
    
    args = parser.parse_args()
    
    trader = PaperTrader(args.model, args.log)
    trader.run_trading_session(args.interval)