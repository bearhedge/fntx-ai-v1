"""
Live trading script for SPY 0DTE options with trained RL model
REAL MONEY - Use with caution
"""
import json
import time
import asyncio
from datetime import datetime, time as dtime
import numpy as np
from pathlib import Path
from typing import Dict, Optional

from stable_baselines3 import PPO
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST
from config import ALPACA_CONFIG


class LiveOptionsTrader:
    """Live trading system for SPY 0DTE options"""
    
    def __init__(self, model_path: str, config: dict):
        # Load trained model
        self.model = PPO.load(model_path)
        
        # Alpaca API setup
        self.api = REST(
            key_id=config['API_KEY'],
            secret_key=config['SECRET_KEY'],
            base_url=config['BASE_URL']
        )
        
        # Position tracking
        self.positions = {
            'calls': {'count': 0, 'contracts': []},
            'puts': {'count': 0, 'contracts': []}
        }
        
        # Daily limits from training
        self.daily_limits = {'calls': 30, 'puts': 30}
        self.trades_today = []
        
        # Risk management
        self.stop_loss_multipliers = {0.2: 3, 0.5: 4, 0.8: 5}
        self.wait_times = {0.2: 2, 0.5: 3, 0.8: 4}  # hours
        
        # Logging
        self.log_dir = Path("logs/live_trades")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def get_0dte_options(self, option_type: str = 'call'):
        """Get today's expiring SPY options"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get SPY options chain
        options = self.api.list_options_contracts(
            underlying_symbols='SPY',
            expiration_date=today,
            status='active'
        )
        
        # Filter for 0DTE
        spy_price = self.get_spy_price()
        atm_strike = round(spy_price)
        
        # Get near ATM options with delta <= 0.20
        valid_options = []
        for opt in options:
            if opt.type == option_type:
                strike = float(opt.strike_price)
                # Simple delta approximation for filtering
                moneyness = abs(strike - spy_price) / spy_price
                if moneyness < 0.02:  # ~2% OTM
                    valid_options.append(opt)
        
        return valid_options
    
    def get_spy_price(self) -> float:
        """Get current SPY price"""
        spy_quote = self.api.get_latest_trade('SPY')
        return float(spy_quote.price)
    
    def get_market_state(self) -> Dict:
        """Get current market state for model input"""
        current_time = datetime.now()
        market_open = current_time.replace(hour=9, minute=30, second=0)
        market_close = current_time.replace(hour=16, minute=0, second=0)
        
        # Get SPY data
        spy_price = self.get_spy_price()
        
        # Get VIX for IV proxy
        vix_quote = self.api.get_latest_trade('VIXY')  # VIX ETF proxy
        iv_proxy = float(vix_quote.price) / 100  # Normalize
        
        # Calculate features
        minutes_since_open = (current_time - market_open).total_seconds() / 60
        minutes_until_close = (market_close - current_time).total_seconds() / 60
        
        # Get current P&L
        position_pnl = self._calculate_live_pnl()
        
        state = {
            'minutes_since_open': min(max(minutes_since_open, 0), 390),
            'spot_price': spy_price,
            'atm_iv': min(max(iv_proxy, 0.1), 1.0),
            'has_position': 1 if (self.positions['calls']['count'] > 0 or 
                                 self.positions['puts']['count'] > 0) else 0,
            'position_pnl': position_pnl,
            'time_in_position': self._get_time_in_position(),
            'risk_score': self._calculate_risk_score(),
            'minutes_until_close': max(minutes_until_close, 0)
        }
        
        return state
    
    def _calculate_live_pnl(self) -> float:
        """Calculate real P&L from open positions"""
        total_pnl = 0
        
        # Get P&L for each position
        positions = self.api.list_positions()
        for pos in positions:
            if 'SPY' in pos.symbol:
                total_pnl += float(pos.unrealized_pl)
        
        return total_pnl
    
    def execute_trade(self, action: int, state: dict):
        """Execute real trade based on model action"""
        action_names = ['hold', 'sell_call', 'sell_put']
        action_name = action_names[action]
        
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'action': action_name,
            'spy_price': state['spot_price'],
            'executed': False,
            'order_id': None,
            'reason': ''
        }
        
        try:
            if action == 0:  # Hold
                trade_record['executed'] = True
                trade_record['reason'] = 'Hold signal'
                
            elif action == 1:  # Sell call
                if self.positions['calls']['count'] >= self.daily_limits['calls']:
                    trade_record['reason'] = 'Daily call limit reached'
                else:
                    # Get contracts based on risk score
                    contracts = self._get_position_size(state['risk_score'])
                    if contracts > 0:
                        order = self._place_option_order('call', contracts)
                        if order:
                            trade_record['executed'] = True
                            trade_record['order_id'] = order.id
                            trade_record['contracts'] = contracts
                            trade_record['type'] = 'call'
                            self.positions['calls']['count'] += contracts
                            
            elif action == 2:  # Sell put
                if self.positions['puts']['count'] >= self.daily_limits['puts']:
                    trade_record['reason'] = 'Daily put limit reached'
                else:
                    # Get contracts based on risk score
                    contracts = self._get_position_size(state['risk_score'])
                    if contracts > 0:
                        order = self._place_option_order('put', contracts)
                        if order:
                            trade_record['executed'] = True
                            trade_record['order_id'] = order.id
                            trade_record['contracts'] = contracts
                            trade_record['type'] = 'put'
                            self.positions['puts']['count'] += contracts
                            
        except Exception as e:
            trade_record['reason'] = f'Error: {str(e)}'
            print(f"Trade execution error: {e}")
        
        # Log trade
        self.trades_today.append(trade_record)
        self._save_trade(trade_record)
        
        return trade_record
    
    def _get_position_size(self, risk_score: float) -> int:
        """Kelly criterion position sizing"""
        if risk_score < 0.3:
            return 30
        elif risk_score < 0.6:
            return 20
        elif risk_score < 0.8:
            return 10
        else:
            return 0
    
    def _place_option_order(self, option_type: str, contracts: int):
        """Place real option order"""
        # Get 0DTE options
        options = self.get_0dte_options(option_type)
        if not options:
            print(f"No {option_type} options available")
            return None
        
        # Select ATM option
        spy_price = self.get_spy_price()
        best_option = min(options, 
                         key=lambda x: abs(float(x.strike_price) - spy_price))
        
        # Place order (sell to open)
        order = self.api.submit_order(
            symbol=best_option.symbol,
            qty=contracts,
            side='sell',
            type='limit',
            time_in_force='day',
            limit_price=None,  # Use market order for now
            order_class='simple'
        )
        
        print(f"Placed order: Sell {contracts} {best_option.symbol}")
        return order
    
    def manage_positions(self):
        """Monitor and manage open positions"""
        positions = self.api.list_positions()
        
        for pos in positions:
            if 'SPY' not in pos.symbol:
                continue
                
            # Check stop loss
            unrealized_pnl_pct = float(pos.unrealized_plpc)
            
            # Determine stop loss based on risk level
            risk_score = self._calculate_risk_score()
            stop_loss_multiplier = self.stop_loss_multipliers.get(
                round(risk_score, 1), 3
            )
            
            # Close if stop loss hit
            if unrealized_pnl_pct < -stop_loss_multiplier:
                print(f"Stop loss hit for {pos.symbol}")
                self.api.close_position(pos.symbol)
    
    def run_live_trading(self):
        """Main trading loop"""
        print("="*50)
        print("LIVE TRADING STARTED - REAL MONEY")
        print("="*50)
        print(f"Model: {self.model}")
        print(f"Account: {self.api.get_account().account_number}")
        print(f"Buying Power: ${self.api.get_account().buying_power}")
        print("-"*50)
        
        last_action_time = None
        
        while self._is_market_open():
            try:
                current_time = datetime.now()
                
                # Only trade every 5 minutes
                if last_action_time and (current_time - last_action_time).seconds < 300:
                    time.sleep(10)
                    continue
                
                # Get market state
                state = self.get_market_state()
                
                # Get model prediction
                obs = self._prepare_observation(state)
                action, _ = self.model.predict(obs, deterministic=True)
                
                # Execute trade
                trade = self.execute_trade(int(action), state)
                
                # Print status
                print(f"\n[{current_time.strftime('%H:%M:%S')}]")
                print(f"SPY: ${state['spot_price']:.2f}")
                print(f"Action: {trade['action']}")
                print(f"Executed: {trade['executed']}")
                if trade['executed'] and trade.get('order_id'):
                    print(f"Order ID: {trade['order_id']}")
                print(f"P&L: ${state['position_pnl']:.2f}")
                
                # Manage existing positions
                self.manage_positions()
                
                last_action_time = current_time
                
                # Wait before next check
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\nStopping live trading...")
                break
            except Exception as e:
                print(f"Error in trading loop: {e}")
                time.sleep(60)
        
        self._end_of_day_summary()
    
    def _prepare_observation(self, state):
        """Convert state to model input format"""
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
    
    def _is_market_open(self):
        """Check if market is open"""
        clock = self.api.get_clock()
        return clock.is_open
    
    def _save_trade(self, trade):
        """Save trade record"""
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"live_trades_{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(trade) + '\n')
    
    def _end_of_day_summary(self):
        """End of day summary"""
        account = self.api.get_account()
        
        print("\n" + "="*50)
        print("END OF DAY SUMMARY")
        print("="*50)
        print(f"Total trades: {len(self.trades_today)}")
        print(f"Executed trades: {sum(1 for t in self.trades_today if t['executed'])}")
        print(f"Day P&L: ${float(account.equity) - float(account.last_equity):.2f}")
        print(f"Account Value: ${account.equity}")
        
        # Close all positions at end of day
        print("\nClosing all positions...")
        self.api.close_all_positions()


if __name__ == "__main__":
    # Safety check
    response = input("WARNING: This will trade REAL MONEY. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Exiting...")
        exit()
    
    # Load config
    config = {
        'API_KEY': ALPACA_CONFIG['API_KEY'],
        'SECRET_KEY': ALPACA_CONFIG['SECRET_KEY'],
        'BASE_URL': 'https://paper-api.alpaca.markets'  # Change to live URL for real trading
    }
    
    # Initialize trader
    trader = LiveOptionsTrader(
        model_path='models/gpu_trained/ppo_gpu_test_latest',
        config=config
    )
    
    # Run live trading
    trader.run_live_trading()