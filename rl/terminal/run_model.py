"""
Autonomous trading script for SPY 0DTE options
Runs independently with predefined rules and position sizing
"""
import time
import json
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
from stable_baselines3 import PPO
import argparse


class AutonomousTrader:
    def __init__(self, model_path: str, capital: float, max_contracts: int):
        self.model = PPO.load(model_path)
        self.capital = capital
        self.max_contracts = max_contracts
        
        # Trading state
        self.last_trade_time = None
        self.position = None
        self.trades_log = []
        
        # Risk parameters from training
        self.wait_times = {
            0.2: 2,  # Low risk: wait 2 hours
            0.5: 3,  # Medium risk: wait 3 hours  
            0.8: 4   # High risk: wait 4 hours
        }
        
    def can_trade(self, risk_score: float) -> bool:
        """Check if enough time has passed based on risk"""
        if self.last_trade_time is None:
            # First trade - wait 30 min after open
            market_open = datetime.now().replace(hour=9, minute=30)
            return datetime.now() > market_open + timedelta(minutes=30)
            
        # Check wait time based on risk
        wait_hours = self.wait_times.get(round(risk_score, 1), 3)
        time_since_trade = (datetime.now() - self.last_trade_time).seconds / 3600
        
        return time_since_trade >= wait_hours
    
    def get_position_size(self, risk_score: float) -> int:
        """Position sizing based on capital and risk"""
        # With $80k capital, max 1 contract
        if self.capital < 100000:
            return 1 if risk_score < 0.5 else 0
        
        # Original Kelly sizing for larger accounts
        if risk_score < 0.3:
            return min(self.max_contracts, 3)
        elif risk_score < 0.6:
            return min(self.max_contracts, 2)
        elif risk_score < 0.8:
            return min(self.max_contracts, 1)
        else:
            return 0
    
    def log_action(self, action: str, details: dict):
        """Log actions with timestamp"""
        log_entry = {
            'time': datetime.now().strftime('%H:%M'),
            'action': action,
            'spy_price': details.get('spy_price', 0),
            'details': details
        }
        
        self.trades_log.append(log_entry)
        
        # Print to console
        if action == 'TRADE':
            print(f"[{log_entry['time']}] {action}: "
                  f"Sold {details['contracts']} SPY {details['strike']} "
                  f"{details['type'].upper()} @ ${details['premium']:.2f}")
        elif action == 'WAITING':
            print(f"[{log_entry['time']}] SPY at {details['spy_price']:.0f}, "
                  f"IV {details.get('iv', 'normal')} - {action} ({details['reason']})")
        else:
            print(f"[{log_entry['time']}] {action}: {details}")
    
    def run(self):
        """Main autonomous trading loop"""
        print(f"Starting autonomous trading")
        print(f"Capital: ${self.capital:,.0f}")
        print(f"Max contracts: {self.max_contracts}")
        print("-" * 50)
        
        while self.is_market_open():
            try:
                # Get market state (simplified for example)
                state = self.get_market_state()
                
                # Get model prediction
                obs = self.prepare_observation(state)
                action, _ = self.model.predict(obs, deterministic=True)
                
                # Model says hold (0) or we can't trade yet
                if action == 0 or not self.can_trade(state['risk_score']):
                    reason = 'model says hold' if action == 0 else 'cooldown period'
                    self.log_action('WAITING', {
                        'spy_price': state['spy_price'],
                        'reason': reason,
                        'risk_score': state['risk_score']
                    })
                    
                # Model wants to trade and we can
                elif action in [1, 2]:  # 1=sell call, 2=sell put
                    contracts = self.get_position_size(state['risk_score'])
                    
                    if contracts > 0:
                        # Execute trade
                        trade_type = 'call' if action == 1 else 'put'
                        strike = self.get_strike(state['spy_price'], trade_type)
                        premium = self.get_premium_estimate(strike, trade_type)
                        
                        self.log_action('TRADE', {
                            'type': trade_type,
                            'strike': strike,
                            'contracts': contracts,
                            'premium': premium,
                            'spy_price': state['spy_price']
                        })
                        
                        self.last_trade_time = datetime.now()
                        self.position = {
                            'type': trade_type,
                            'strike': strike,
                            'contracts': contracts,
                            'entry_price': premium
                        }
                
                # Manage existing position
                if self.position:
                    self.manage_position(state)
                
                # Sleep 5 minutes
                time.sleep(300)
                
            except KeyboardInterrupt:
                print("\nStopping autonomous trading...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)
        
        self.end_of_day_summary()
    
    def get_market_state(self) -> dict:
        """Simplified market state for example"""
        # In production, connect to real data feed
        current_time = datetime.now()
        minutes_since_open = (current_time.hour - 9) * 60 + (current_time.minute - 30)
        
        # Mock data for example
        return {
            'spy_price': 630 + np.random.randn() * 2,
            'iv': 0.15 + np.random.rand() * 0.1,
            'risk_score': 0.2 if minutes_since_open < 120 else 0.5,
            'minutes_since_open': minutes_since_open,
            'minutes_until_close': 390 - minutes_since_open
        }
    
    def prepare_observation(self, state: dict) -> np.ndarray:
        """Convert state to model input"""
        has_position = 1 if self.position else 0
        position_pnl = 0
        time_in_position = 0
        
        if self.position and self.last_trade_time:
            time_in_position = (datetime.now() - self.last_trade_time).seconds / 60
            # Simplified P&L calculation
            position_pnl = self.position['contracts'] * 100 * 0.5  # Mock
        
        return np.array([
            state['minutes_since_open'] / 390,
            state['spy_price'] / 1000,
            state['iv'],
            has_position,
            position_pnl / 1000,
            time_in_position / 390,
            state['risk_score'],
            state['minutes_until_close'] / 390
        ], dtype=np.float32)
    
    def get_strike(self, spy_price: float, option_type: str) -> int:
        """Get appropriate strike price"""
        if option_type == 'call':
            return int(spy_price + 2)  # 2 points OTM
        else:
            return int(spy_price - 2)  # 2 points OTM
    
    def get_premium_estimate(self, strike: float, option_type: str) -> float:
        """Estimate option premium"""
        # Simplified - in production use real quotes
        return np.random.uniform(2.0, 4.0)
    
    def manage_position(self, state: dict):
        """Monitor and close positions"""
        if not self.position:
            return
            
        time_held = (datetime.now() - self.last_trade_time).seconds / 3600
        
        # Close near end of day
        if state['minutes_until_close'] < 10:
            profit = self.position['contracts'] * 100 * (
                self.position['entry_price'] * 0.8  # Mock 80% profit
            )
            self.log_action('CLOSED', {
                'profit': profit,
                'time_held': f"{time_held:.1f} hours"
            })
            self.position = None
    
    def is_market_open(self) -> bool:
        """Check if market is open"""
        now = datetime.now()
        if now.weekday() > 4:  # Weekend
            return False
        return now.hour >= 9 and (now.hour < 16 or (now.hour == 16 and now.minute == 0))
    
    def end_of_day_summary(self):
        """Summary for RLHF feedback"""
        trades = [t for t in self.trades_log if t['action'] == 'TRADE']
        
        print("\n" + "="*50)
        print("END OF DAY SUMMARY - RATE THESE TRADES")
        print("="*50)
        
        for i, trade in enumerate(trades, 1):
            print(f"\nTrade {i}:")
            print(f"  Time: {trade['time']}")
            print(f"  Type: {trade['details']['type']}")
            print(f"  Strike: {trade['details']['strike']}")
            print(f"  SPY was at: {trade['details']['spy_price']:.2f}")
            print(f"  Premium: ${trade['details']['premium']:.2f}")
            print(f"  Rating: [GOOD/BAD] ← Your feedback here")
        
        # Save for RLHF training
        with open(f"logs/trades_{datetime.now().strftime('%Y%m%d')}.json", 'w') as f:
            json.dump(self.trades_log, f, indent=2)
        
        print(f"\nTotal trades: {len(trades)}")
        print("Logs saved for RLHF training")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--capital', type=float, default=80000)
    parser.add_argument('--contracts', type=int, default=1)
    parser.add_argument('--model', type=str, default='models/gpu_trained/ppo_gpu_test_latest')
    
    args = parser.parse_args()
    
    trader = AutonomousTrader(args.model, args.capital, args.contracts)
    trader.run()