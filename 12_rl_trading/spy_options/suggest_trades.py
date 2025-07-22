"""
Interactive trade suggestion system with RLHF
Suggests trades, user decides, manages positions
"""
import time
import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from stable_baselines3 import PPO
import threading
import keyboard


class TradeSuggester:
    def __init__(self, model_path: str = 'models/gpu_trained/ppo_gpu_test_latest'):
        self.model = PPO.load(model_path)
        self.position = None
        self.suggestions_log = []
        self.last_suggestion_time = None
        
        # Create logs directory
        Path("logs/suggestions").mkdir(parents=True, exist_ok=True)
        
    def run(self):
        """Main interactive loop"""
        print("SPY Options Trade Suggester Started")
        print(f"Current: SPY ${self.get_spy_price():.0f}, VIX {self.get_vix():.1f}")
        print("-" * 40)
        
        while True:
            try:
                # Position management mode
                if self.position:
                    self.manage_position_mode()
                # Trade suggestion mode
                else:
                    self.suggestion_mode()
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                print("\nExiting...")
                self.save_session()
                break
    
    def suggestion_mode(self):
        """Suggest trades when no position"""
        state = self.get_market_state()
        
        # Check if we should suggest
        if not self.should_suggest(state):
            # Just show waiting message once in a while
            if datetime.now().second < 5:
                print(f"\r[{datetime.now().strftime('%H:%M')}] "
                      f"Waiting... SPY ${state['spy_price']:.0f}", end='', flush=True)
            return
        
        # Get model prediction
        obs = self.prepare_observation(state)
        action, _ = self.model.predict(obs, deterministic=True)
        
        if action == 0:  # Model says hold
            return
        
        # Model wants to trade!
        self.make_suggestion(action, state)
    
    def make_suggestion(self, action: int, state: dict):
        """Present trade suggestion to user"""
        trade_type = 'Put' if action == 2 else 'Call'
        strike = self.calculate_strike(state['spy_price'], trade_type.lower())
        premium = self.estimate_premium(strike, trade_type.lower())
        
        print(f"\n\n[{datetime.now().strftime('%I:%M %p')}]")
        print(f"SUGGESTION: Sell 1 SPY {strike} {trade_type} @ ${premium:.2f}")
        print(f"Reason: Risk {state['risk_score']:.1f}, "
              f"IV {state['iv']:.0%}, "
              f"{state['hours_since_open']:.0f}hrs since open")
        
        response = input("Execute? (y/n/skip): ").lower()
        
        # Log suggestion and response
        suggestion = {
            'time': datetime.now().isoformat(),
            'action': trade_type.lower(),
            'strike': strike,
            'spy_price': state['spy_price'],
            'suggested_premium': premium,
            'risk_score': state['risk_score'],
            'user_response': response
        }
        
        if response == 'y':
            filled = input("Did you get filled? (y/n): ").lower()
            if filled == 'y':
                fill_price = float(input("Fill price: "))
                
                # Enter position mode
                self.position = {
                    'type': trade_type.lower(),
                    'strike': strike,
                    'contracts': 1,
                    'entry_price': fill_price,
                    'entry_time': datetime.now(),
                    'entry_spy': state['spy_price']
                }
                
                suggestion['executed'] = True
                suggestion['fill_price'] = fill_price
                
                print(f"\n>>> POSITION MODE: Managing 1 SPY {strike} {trade_type} <<<")
            else:
                suggestion['executed'] = False
                suggestion['fill_failed'] = True
        else:
            suggestion['executed'] = False
            suggestion['skipped'] = response == 'skip'
        
        self.suggestions_log.append(suggestion)
        self.last_suggestion_time = datetime.now()
    
    def manage_position_mode(self):
        """Track and manage open position"""
        if not self.position:
            return
        
        state = self.get_market_state()
        
        # Calculate P&L
        current_premium = self.estimate_premium(
            self.position['strike'], 
            self.position['type']
        )
        entry = self.position['entry_price']
        pnl = (entry - current_premium) * 100  # Per contract
        pnl_pct = (pnl / (entry * 100)) * 100
        
        # Time held
        time_held = (datetime.now() - self.position['entry_time']).seconds / 3600
        
        # Stop loss check
        stop_loss = -entry * 3  # 3x premium
        
        # Display update
        print(f"\rEntry: ${entry:.2f}, Current: ${current_premium:.2f} | "
              f"P&L: ${pnl:+.0f} ({pnl_pct:+.0f}%) | "
              f"Stop: ${stop_loss:.0f} | "
              f"Time: {time_held:.1f}hrs", end='', flush=True)
        
        # Alerts
        should_alert = False
        alert_msg = ""
        
        if pnl <= stop_loss * 100:
            alert_msg = "STOP LOSS HIT!"
            should_alert = True
        elif state['minutes_until_close'] < 75:
            alert_msg = f"ALERT: {state['minutes_until_close']} min to close"
            should_alert = True
        elif time_held > 3:
            alert_msg = "ALERT: Position held >3 hours"
            should_alert = True
        
        if should_alert:
            print(f"\n\n{alert_msg}")
            print(f"Current P&L: ${pnl:+.0f} ({pnl_pct:+.0f}%)")
            response = input("Close position? (y/n): ").lower()
            
            if response == 'y':
                self.close_position(pnl)
    
    def close_position(self, final_pnl: float):
        """Close position and collect feedback"""
        print("\nPosition closed!")
        
        # Get feedback
        rating = int(input("Rate this trade (1-5): "))
        feedback = input("What was good/bad?: ")
        
        # Log the complete trade
        trade_log = {
            'position': self.position,
            'final_pnl': final_pnl,
            'rating': rating,
            'feedback': feedback,
            'closed_time': datetime.now().isoformat()
        }
        
        # Save for RLHF training
        with open(f"logs/suggestions/trades_{datetime.now().strftime('%Y%m%d')}.jsonl", 'a') as f:
            f.write(json.dumps(trade_log) + '\n')
        
        # Reset to suggestion mode
        self.position = None
        print("\nWaiting for next opportunity...\n")
    
    def should_suggest(self, state: dict) -> bool:
        """Check if we should make a suggestion"""
        # No suggestions in first/last 30 min
        if state['minutes_since_open'] < 30 or state['minutes_until_close'] < 30:
            return False
        
        # Respect wait times from last suggestion
        if self.last_suggestion_time:
            time_since = (datetime.now() - self.last_suggestion_time).seconds / 3600
            required_wait = 2  # Base 2 hours
            if time_since < required_wait:
                return False
        
        return True
    
    def get_market_state(self) -> dict:
        """Get current market conditions"""
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30)
        market_close = now.replace(hour=16, minute=0)
        
        minutes_since_open = (now - market_open).seconds / 60
        minutes_until_close = (market_close - now).seconds / 60
        
        # Mock data - replace with real feed
        spy_price = 628 + np.random.randn() * 2
        vix = 15 + np.random.randn()
        
        return {
            'spy_price': spy_price,
            'iv': vix / 100,
            'risk_score': 0.2 if minutes_since_open < 120 else 0.5,
            'minutes_since_open': minutes_since_open,
            'minutes_until_close': minutes_until_close,
            'hours_since_open': minutes_since_open / 60
        }
    
    def prepare_observation(self, state: dict) -> np.ndarray:
        """Convert state to model input"""
        has_position = 0  # We only suggest when no position
        position_pnl = 0
        time_in_position = 0
        
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
    
    def calculate_strike(self, spy_price: float, option_type: str) -> int:
        """Calculate appropriate strike"""
        if option_type == 'call':
            return int(spy_price + 2)
        else:
            return int(spy_price - 2)
    
    def estimate_premium(self, strike: float, option_type: str) -> float:
        """Estimate option premium"""
        # Mock - replace with real quotes
        return round(np.random.uniform(2.0, 3.5), 2)
    
    def get_spy_price(self) -> float:
        """Get current SPY price"""
        # Mock - replace with real feed
        return 628 + np.random.randn() * 2
    
    def get_vix(self) -> float:
        """Get current VIX"""
        # Mock - replace with real feed
        return 15 + np.random.randn()
    
    def save_session(self):
        """Save session data for RLHF training"""
        session_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'suggestions': self.suggestions_log,
            'total_suggestions': len(self.suggestions_log),
            'executed': sum(1 for s in self.suggestions_log if s.get('executed', False))
        }
        
        with open(f"logs/suggestions/session_{datetime.now().strftime('%Y%m%d_%H%M')}.json", 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"Session saved: {len(self.suggestions_log)} suggestions")


if __name__ == "__main__":
    suggester = TradeSuggester()
    suggester.run()