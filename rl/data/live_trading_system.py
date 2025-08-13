"""
Complete live trading system integrating all components:
- Theta Terminal data feed
- Feature engineering
- AI model predictions
- IB Gateway execution
- User interface
"""
import asyncio
import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np

from stable_baselines3 import PPO

from .theta_connector import ThetaDataConnector, MockThetaConnector
from .feature_engine import FeatureEngine, PositionTracker


class LiveTradingSystem:
    """Main system orchestrating live trading with AI model"""
    
    def __init__(self, 
                 model_path: str,
                 theta_api_key: Optional[str] = None,
                 use_mock_data: bool = True,
                 capital: float = 80000,
                 max_contracts: int = 1):
        
        # Load trained model
        self.model = PPO.load(model_path)
        
        # Initialize components
        self.position_tracker = PositionTracker()
        self.feature_engine = FeatureEngine(self.position_tracker)
        
        # Data connector (mock or real)
        if use_mock_data:
            self.data_connector = MockThetaConnector()
        else:
            if not theta_api_key:
                raise ValueError("Theta API key required for live data")
            self.data_connector = ThetaDataConnector(theta_api_key)
            
        # Trading parameters
        self.capital = capital
        self.max_contracts = max_contracts
        self.min_check_interval = 300  # 5 minutes
        
        # State tracking
        self.last_suggestion_time = None
        self.suggestions_log = []
        self.running = False
        
        # Logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create logs directory
        self.log_dir = Path("logs/live_trading")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    async def start(self):
        """Start the live trading system"""
        self.logger.info("Starting Live Trading System")
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Capital: ${self.capital:,.0f}")
        self.logger.info(f"Max Contracts: {self.max_contracts}")
        
        # Start data feed
        await self.data_connector.start()
        
        # Give data feed time to initialize
        await asyncio.sleep(2)
        
        # Main trading loop
        self.running = True
        await self.trading_loop()
        
    async def stop(self):
        """Stop the system gracefully"""
        self.logger.info("Stopping Live Trading System")
        self.running = False
        await self.data_connector.stop()
        self.save_session_log()
        
    async def trading_loop(self):
        """Main trading logic loop"""
        while self.running and self.is_market_open():
            try:
                # Get current market snapshot
                market_data = self.data_connector.get_current_snapshot()
                
                if not market_data['spy_price']:
                    self.logger.warning("No market data available")
                    await asyncio.sleep(30)
                    continue
                    
                # Convert to model features
                features = self.feature_engine.get_model_features(market_data)
                
                # Get model prediction
                action, _ = self.model.predict(features, deterministic=True)
                action = int(action)
                
                # Check if we should make a suggestion
                if self.should_suggest(action, features):
                    await self.make_suggestion(action, market_data, features)
                else:
                    # Just log current state
                    self.log_state(market_data, features, action)
                    
                # Wait before next check
                await asyncio.sleep(self.min_check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("User interrupted")
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(60)
                
    def should_suggest(self, action: int, features: np.ndarray) -> bool:
        """Determine if we should make a trade suggestion"""
        # Don't suggest hold actions
        if action == 0:
            return False
            
        # Check if enough time has passed since last suggestion
        if self.last_suggestion_time:
            time_since = (datetime.now() - self.last_suggestion_time).seconds / 3600
            
            # Use risk-based wait times (from training)
            risk_score = features[6]
            if risk_score < 0.3:
                required_wait = 2  # hours
            elif risk_score < 0.6:
                required_wait = 3
            else:
                required_wait = 4
                
            if time_since < required_wait:
                return False
                
        # Check market hours constraints
        minutes_since_open = features[0] * 390
        if minutes_since_open < 30 or minutes_since_open > 360:
            return False
            
        return True
        
    async def make_suggestion(self, action: int, market_data: dict, features: np.ndarray):
        """Present trade suggestion to user"""
        action_names = ['hold', 'sell_call', 'sell_put']
        action_type = action_names[action]
        
        # Get suggestion details
        spy_price = market_data['spy_price']
        atm_options = self.data_connector.get_atm_options(1)[0]
        
        if action == 1:  # Sell call
            option = atm_options['call']
            strike = atm_options['strike']
        else:  # Sell put
            option = atm_options['put']
            strike = atm_options['strike']
            
        # Calculate position size based on risk
        risk_score = features[6]
        contracts = self.calculate_position_size(risk_score)
        
        # Format suggestion
        suggestion = {
            'timestamp': datetime.now().isoformat(),
            'action': action_type,
            'strike': strike,
            'contracts': contracts,
            'option_type': 'call' if action == 1 else 'put',
            'spy_price': spy_price,
            'option_bid': option['bid'],
            'option_ask': option['ask'],
            'option_mid': (option['bid'] + option['ask']) / 2,
            'iv': option['iv'],
            'risk_score': risk_score,
            'features': self.feature_engine.features_to_dict(features)
        }
        
        # Display suggestion
        print("\n" + "="*50)
        print(f"[{datetime.now().strftime('%I:%M %p')}] TRADE SUGGESTION")
        print("="*50)
        print(f"Action: SELL {contracts} SPY {strike} {suggestion['option_type'].upper()}")
        print(f"SPY Price: ${spy_price:.2f}")
        print(f"Option Bid/Ask: ${option['bid']:.2f} / ${option['ask']:.2f}")
        print(f"Mid Price: ${suggestion['option_mid']:.2f}")
        print(f"IV: {option['iv']:.1%}")
        print(f"Risk Score: {risk_score:.2f}")
        print(f"Max Profit: ${contracts * suggestion['option_mid'] * 100:.0f}")
        print(f"Max Loss: ${contracts * 300:.0f} (3x stop)")
        
        # Get user decision
        response = input("\nExecute? (y/n/skip): ").lower().strip()
        
        suggestion['user_response'] = response
        
        if response == 'y':
            # Get execution details
            filled = input("Did you get filled? (y/n): ").lower().strip()
            
            if filled == 'y':
                fill_price = float(input("Fill price: $"))
                
                # Update position tracker
                self.position_tracker.open_position(
                    suggestion['option_type'],
                    strike,
                    contracts,
                    fill_price
                )
                
                suggestion['executed'] = True
                suggestion['fill_price'] = fill_price
                
                print(f"\n✓ Position opened: {contracts} contracts at ${fill_price:.2f}")
                print("Monitoring position...")
                
        # Get optional feedback
        if response != 'skip':
            comment = input("Comment (optional): ").strip()
            if comment:
                suggestion['user_comment'] = comment
                
        # Log suggestion
        self.suggestions_log.append(suggestion)
        self.last_suggestion_time = datetime.now()
        self.save_suggestion(suggestion)
        
    def calculate_position_size(self, risk_score: float) -> int:
        """Calculate position size based on risk and capital"""
        # For $80k account, max 1 contract
        if self.capital < 100000:
            return 1 if risk_score < 0.5 else 0
            
        # Larger accounts can use Kelly sizing
        if risk_score < 0.3:
            base_size = 3
        elif risk_score < 0.6:
            base_size = 2
        else:
            base_size = 1
            
        return min(base_size, self.max_contracts)
        
    def log_state(self, market_data: dict, features: np.ndarray, action: int):
        """Log current state without making suggestion"""
        if datetime.now().minute % 15 == 0:  # Log every 15 min
            spy_price = market_data['spy_price']
            risk_score = features[6]
            action_names = ['hold', 'sell_call', 'sell_put']
            
            self.logger.info(
                f"SPY: ${spy_price:.2f} | "
                f"Risk: {risk_score:.2f} | "
                f"Model: {action_names[action]} | "
                f"Position: {self.position_tracker.has_position()}"
            )
            
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now()
        
        # Check weekday
        if now.weekday() > 4:  # Weekend
            return False
            
        # Check time
        current_time = now.time()
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        return market_open <= current_time <= market_close
        
    def save_suggestion(self, suggestion: dict):
        """Save suggestion to file"""
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"suggestions_{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(suggestion) + '\n')
            
    def save_session_log(self):
        """Save complete session summary"""
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'start_time': self.suggestions_log[0]['timestamp'] if self.suggestions_log else None,
            'end_time': datetime.now().isoformat(),
            'total_suggestions': len(self.suggestions_log),
            'executed': sum(1 for s in self.suggestions_log if s.get('executed', False)),
            'suggestions': self.suggestions_log
        }
        
        session_file = self.log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(session_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print(f"\nSession saved to: {session_file}")


# Main entry point
async def main():
    """Run the live trading system"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live SPY Options Trading with AI')
    parser.add_argument('--model', type=str, 
                       default='models/gpu_trained/ppo_gpu_test_latest',
                       help='Path to trained model')
    parser.add_argument('--theta-key', type=str, 
                       help='Theta Terminal API key')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock data instead of live')
    parser.add_argument('--capital', type=float, default=80000,
                       help='Trading capital')
    parser.add_argument('--contracts', type=int, default=1,
                       help='Max contracts per trade')
    
    args = parser.parse_args()
    
    # Create trading system
    system = LiveTradingSystem(
        model_path=args.model,
        theta_api_key=args.theta_key,
        use_mock_data=args.mock,
        capital=args.capital,
        max_contracts=args.contracts
    )
    
    try:
        await system.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())