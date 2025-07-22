"""
SPY 0DTE Options Trading Environment
Realistic gym environment with bid-ask spreads, volume constraints, and fees
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
import logging

from data.data_loader import OptionsDataLoader
from agents.rewards import RewardCalculator, SimplePnLReward
from utils.risk_assessment import RiskAssessment
from config import TRADING_CONFIG, RISK_LEVELS

logger = logging.getLogger(__name__)


class SPY0DTEEnvironment(gym.Env):
    """
    Trading environment for 0DTE SPY options
    Designed for RLHF with comprehensive logging
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, 
                 data_loader: OptionsDataLoader,
                 reward_calculator: RewardCalculator = None,
                 episode_logger = None,
                 initial_capital: float = 125000):
        """
        Initialize trading environment
        
        Args:
            data_loader: Interface to TimescaleDB
            reward_calculator: Swappable reward system
            episode_logger: For RLHF preparation
            initial_capital: Starting cash
        """
        super().__init__()
        
        self.data_loader = data_loader
        self.reward_calculator = reward_calculator or SimplePnLReward()
        self.episode_logger = episode_logger
        self.initial_capital = initial_capital
        self.risk_assessment = RiskAssessment()
        
        # Action space: 5 discrete actions
        self.action_space = spaces.Discrete(5)
        self.action_mapping = {
            0: 'HOLD',
            1: 'SELL_PUT_15D',   # Target -0.15 delta
            2: 'SELL_PUT_10D',   # Target -0.10 delta  
            3: 'SELL_CALL_15D',  # Target 0.15 delta
            4: 'CLOSE_POSITION'
        }
        
        # State space: 8 continuous features
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, -1, 0, 0, 0]),
            high=np.array([1, 1, 1, 1, 1, 1, 1, 1]),
            dtype=np.float32
        )
        
        # Episode variables
        self.current_episode_data = None
        self.current_time_index = 0
        self.position = None
        self.cash = initial_capital
        self.episode_pnl = 0
        self.decision_history = []
        
        # Market state
        self.current_timestamp = None
        self.current_market_data = None
        self.risk_level = 'MEDIUM'
        self.risk_parameters = RISK_LEVELS['MEDIUM']
        
        # Kelly tracking
        self.trade_history = []  # Track wins/losses for Kelly
        self.kelly_confidence = 0.25  # Quarter Kelly for safety
        
        # Daily trading limits - one trade per side per day
        self.call_contracts_sold = 0  # Call contracts sold today
        self.put_contracts_sold = 0   # Put contracts sold today
        self.max_contracts_per_side = 30  # Maximum 30 contracts per side
        self.has_traded_calls_today = False  # Flag for call side trading
        self.has_traded_puts_today = False   # Flag for put side trading
        self.call_position = None  # Track call position separately
        self.put_position = None   # Track put position separately
        
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        """Reset environment for new episode"""
        super().reset(seed=seed)
        
        # Select random trading day
        if options and 'date' in options:
            episode_date = options['date']
        else:
            episode_date = np.random.choice(self.data_loader.trading_days)
            
        # Load episode data
        self.current_episode_data = self.data_loader.get_episode_data(episode_date)
        if not self.current_episode_data:
            raise ValueError(f"No data available for {episode_date}")
            
        # Reset episode state
        self.cash = self.initial_capital
        self.position = None
        self.episode_pnl = 0
        self.decision_history = []
        
        # Reset daily trading limits
        self.call_contracts_sold = 0
        self.put_contracts_sold = 0
        self.has_traded_calls_today = False
        self.has_traded_puts_today = False
        self.call_position = None
        self.put_position = None
        
        # Calculate initial risk assessment
        market_indicators = self.data_loader.get_market_indicators(episode_date)
        self.risk_level, risk_score, _ = self.risk_assessment.calculate_risk_level(market_indicators)
        self.risk_parameters = RISK_LEVELS[self.risk_level]
        
        # Start after required wait time
        wait_minutes = self.risk_parameters['wait_hours'] * 60
        self.current_time_index = self._find_time_index_after_wait(wait_minutes)
        self.current_timestamp = self.current_episode_data['timestamps'][self.current_time_index]
        
        # Get initial state
        state = self._get_state()
        info = self._get_info()
        
        logger.info(f"Episode started: {episode_date}, Risk: {self.risk_level}")
        
        return state, info
        
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute action and return next state"""
        
        # Validate action
        valid_actions = self._get_valid_actions()
        if action not in valid_actions:
            logger.warning(f"Invalid action {action}, valid: {valid_actions}")
            action = 0  # Default to HOLD
            
        # Pre-action state
        pre_state = self._get_state()
        pre_info = self._get_info()
        pre_pnl = self._calculate_total_pnl()
        
        # Execute action
        execution_result = self._execute_action(action)
        
        # Advance time (5 minutes)
        self.current_time_index += 1
        terminated = False
        
        if self.current_time_index >= len(self.current_episode_data['timestamps']):
            # End of day
            terminated = True
            self._close_all_positions()
        else:
            self.current_timestamp = self.current_episode_data['timestamps'][self.current_time_index]
            
        # Update position value
        if self.position:
            self._update_position_value()
            
        # Post-action state
        post_state = self._get_state()
        post_info = self._get_info()
        post_pnl = self._calculate_total_pnl()
        
        # Calculate reward
        reward_info = {
            'pnl_change': post_pnl - pre_pnl,
            'risk_level': self.risk_level,
            'risk_score': pre_info['risk_score'],
            'trade_executed': execution_result.get('executed', False),
            'trade_rejected': execution_result.get('rejected', False),
            'has_position': self.position is not None,
            'respected_wait_time': True,  # Always true after reset
            'position_size_appropriate': True,  # Fixed size for now
            'execution_details': execution_result,
            'kelly_sized': execution_result.get('kelly_sized', False),
            'episode_ended': terminated,
            'episode_pnl': self._calculate_total_pnl() if terminated else 0
        }
        
        reward = self.reward_calculator.calculate(
            pre_state, action, post_state, reward_info
        )
        
        # Log decision for RLHF
        if self.episode_logger:
            self._log_decision(pre_state, action, post_state, reward, reward_info)
            
        # Episode info
        info = post_info
        info['execution_result'] = execution_result
        
        # Add episode-end info for rewards
        if terminated:
            info['episode_ended'] = True
            info['episode_pnl'] = self._calculate_total_pnl()
            info['stop_loss_triggered'] = False  # Would be set if stop loss hit
            info['respected_one_trade_rule'] = True  # Always true with new implementation
            info['kelly_sized'] = (self.call_contracts_sold > 0 or self.put_contracts_sold > 0)
        
        return post_state, reward, terminated, False, info
        
    def _get_state(self) -> np.ndarray:
        """
        Build state vector (8 features)
        """
        # Time features
        market_open = datetime.combine(
            self.current_timestamp.date(),
            datetime.strptime('09:30', '%H:%M').time()
        )
        market_close = datetime.combine(
            self.current_timestamp.date(),
            datetime.strptime('16:00', '%H:%M').time()
        )
        
        minutes_since_open = (self.current_timestamp - market_open).total_seconds() / 60
        minutes_until_close = (market_close - self.current_timestamp).total_seconds() / 60
        
        # Market features
        spot_price = self.current_episode_data['spot_prices'].get(
            self.current_timestamp, 400
        )
        
        # Get ATM IV
        atm_iv = self._get_atm_iv()
        
        # Position features
        has_position = 1.0 if self.position else 0.0
        position_pnl = 0.0
        time_in_position = 0.0
        
        if self.position:
            position_pnl = self.position['current_pnl'] / 100  # Normalize
            time_in_position = self.position['time_held'] / 390
            
        # Risk score (normalized)
        risk_score = self._calculate_simple_risk_score()
        
        state = np.array([
            minutes_since_open / 390,
            spot_price / 500,
            atm_iv,
            has_position,
            position_pnl,
            time_in_position,
            risk_score,
            minutes_until_close / 390
        ], dtype=np.float32)
        
        return state
        
    def _get_info(self) -> Dict:
        """Get current environment info"""
        return {
            'timestamp': self.current_timestamp,
            'risk_level': self.risk_level,
            'risk_score': self._calculate_simple_risk_score(),
            'position': self.position.copy() if self.position else None,
            'cash': self.cash,
            'total_pnl': self._calculate_total_pnl(),
            'episode_date': self.current_episode_data['date']
        }
        
    def _execute_action(self, action: int) -> Dict:
        """
        Execute trading action with realistic mechanics
        """
        action_name = self.action_mapping[action]
        
        if action == 0:  # HOLD
            return {'action': 'HOLD', 'executed': False}
            
        elif action in [1, 2, 3]:  # SELL options
            if self.position:
                return {'action': action_name, 'rejected': True, 
                       'reason': 'Already have position'}
                       
            # Determine option type
            option_type = 'P' if action in [1, 2] else 'C'
            
            # Check if we already have a position on this side
            if option_type == 'C' and self.call_position:
                return {'action': action_name, 'rejected': True,
                       'reason': 'Already have call position'}
            elif option_type == 'P' and self.put_position:
                return {'action': action_name, 'rejected': True,
                       'reason': 'Already have put position'}
            
            # Check one-trade-per-side-per-day rule
            if option_type == 'C' and self.has_traded_calls_today:
                return {'action': action_name, 'rejected': True,
                       'reason': 'Already traded calls today - one trade per side per day'}
            elif option_type == 'P' and self.has_traded_puts_today:
                return {'action': action_name, 'rejected': True,
                       'reason': 'Already traded puts today - one trade per side per day'}
                       
            # Find target contract
            target_delta = {1: -0.15, 2: -0.10, 3: 0.15}[action]
            
            current_data = self.current_episode_data['by_time'][self.current_timestamp]
            contracts = self.data_loader.find_contracts_by_delta(
                current_data, target_delta, option_type
            )
            
            if contracts.empty:
                return {'action': action_name, 'rejected': True,
                       'reason': 'No contracts match criteria'}
                       
            # Select best contract (closest to target delta)
            contract = contracts.iloc[0]
            
            # Check delta constraint (|delta| must be <= 0.20)
            if abs(contract['delta']) > 0.20:
                return {'action': action_name, 'rejected': True,
                       'reason': f'Delta {contract["delta"]:.3f} exceeds 0.20 limit'}
            
            # Check volume
            if contract['volume'] < 10:
                return {'action': action_name, 'rejected': True,
                       'reason': 'Insufficient volume'}
                       
            # Execute at BID price (we're selling)
            fill_price = contract['bid']
            if fill_price <= 0:
                return {'action': action_name, 'rejected': True,
                       'reason': 'No bid available'}
                       
            # Calculate Kelly position size
            num_contracts = self.calculate_kelly_position_size()
            if num_contracts == 0:
                return {'action': action_name, 'rejected': True,
                       'reason': 'Kelly criterion suggests no trade',
                       'kelly_sized': True}
                       
            # Ensure we don't exceed per-side limit
            if num_contracts > self.max_contracts_per_side:
                num_contracts = self.max_contracts_per_side
                       
            # Create position
            premium_collected = fill_price * 100 * num_contracts  # Total for all contracts
            commission = TRADING_CONFIG['commission_per_contract'] * num_contracts
            net_credit = premium_collected - commission
            
            self.position = {
                'type': 'SHORT',
                'option_type': option_type,
                'strike': contract['strike'],
                'entry_price': fill_price,
                'current_price': fill_price,
                'delta': contract['delta'],
                'quantity': num_contracts,
                'entry_time': self.current_timestamp,
                'time_held': 0,
                'premium_collected': premium_collected,
                'net_credit': net_credit,
                'current_pnl': 0,
                'stop_loss': fill_price * self.risk_parameters['stop_multiple'],
                'contract_id': contract['contract_id']
            }
            
            self.cash += net_credit
            
            # Update daily trading tracking
            if option_type == 'C':
                self.call_contracts_sold = num_contracts
                self.has_traded_calls_today = True
                self.call_position = self.position  # Store reference
            else:
                self.put_contracts_sold = num_contracts
                self.has_traded_puts_today = True
                self.put_position = self.position  # Store reference
            
            return {
                'action': action_name,
                'executed': True,
                'strike': contract['strike'],
                'option_type': option_type,
                'fill_price': fill_price,
                'net_credit': net_credit,
                'num_contracts': num_contracts,
                'kelly_sized': True,
                'call_contracts_sold': self.call_contracts_sold,
                'put_contracts_sold': self.put_contracts_sold,
                'total_contracts': self.call_contracts_sold + self.put_contracts_sold
            }
            
        elif action == 4:  # CLOSE POSITION
            if not self.position:
                return {'action': 'CLOSE', 'rejected': True,
                       'reason': 'No position to close'}
                       
            return self._close_position()
            
    def _close_position(self) -> Dict:
        """Close current position"""
        if not self.position:
            return {'action': 'CLOSE', 'rejected': True, 'reason': 'No position'}
            
        # Get current contract data
        contract_data = self._get_current_contract_data()
        if contract_data.empty:
            return {'action': 'CLOSE', 'rejected': True, 'reason': 'No data'}
            
        # Buy back at ASK price
        ask_price = contract_data['ask'].iloc[0]
        if ask_price <= 0:
            # If no ask, use last + spread estimate
            ask_price = contract_data['close'].iloc[0] * 1.1
            
        # Calculate P&L
        num_contracts = self.position['quantity']
        buy_cost = ask_price * 100 * num_contracts
        commission = TRADING_CONFIG['commission_per_contract'] * num_contracts
        total_cost = buy_cost + commission
        
        # Net P&L = premium collected - buy back cost
        position_pnl = self.position['net_credit'] - total_cost
        
        self.cash -= total_cost
        self.episode_pnl += position_pnl
        
        # Track trade for Kelly calculation
        self.trade_history.append({
            'pnl': position_pnl,
            'entry_time': self.position['entry_time'],
            'exit_time': self.current_timestamp,
            'contracts': self.position['quantity']
        })
        
        result = {
            'action': 'CLOSE',
            'executed': True,
            'exit_price': ask_price,
            'position_pnl': position_pnl,
            'total_cost': total_cost
        }
        
        self.position = None
        
        return result
        
    def _update_position_value(self):
        """Update current position value and check stop loss"""
        if not self.position:
            return
            
        # Get current contract data
        contract_data = self._get_current_contract_data()
        if contract_data.empty:
            return
            
        # Update current price (use ask for short position)
        current_price = contract_data['ask'].iloc[0]
        if current_price <= 0:
            current_price = contract_data['close'].iloc[0]
            
        self.position['current_price'] = current_price
        self.position['time_held'] += 5  # Minutes
        
        # Calculate current P&L
        num_contracts = self.position['quantity']
        buy_cost = current_price * 100 * num_contracts + TRADING_CONFIG['commission_per_contract'] * num_contracts
        self.position['current_pnl'] = self.position['net_credit'] - buy_cost
        
        # Check stop loss
        if current_price >= self.position['stop_loss']:
            logger.info(f"Stop loss triggered at {current_price}")
            self._close_position()
            
    def _get_current_contract_data(self) -> pd.DataFrame:
        """Get current data for position contract"""
        if not self.position:
            return pd.DataFrame()
            
        current_data = self.current_episode_data['by_time'].get(
            self.current_timestamp, pd.DataFrame()
        )
        
        if current_data.empty:
            return pd.DataFrame()
            
        contract_data = current_data[
            current_data['contract_id'] == self.position['contract_id']
        ]
        
        return contract_data
        
    def _calculate_total_pnl(self) -> float:
        """Calculate total P&L including open position"""
        total_pnl = self.episode_pnl
        
        if self.position:
            total_pnl += self.position['current_pnl']
            
        return total_pnl
        
    def _get_valid_actions(self) -> list:
        """Get list of valid actions in current state"""
        valid = [0]  # Can always HOLD
        
        if not self.position:
            # Can sell puts if no put position AND haven't traded puts today
            if not self.put_position and not self.has_traded_puts_today:
                valid.extend([1, 2])  # SELL_PUT_15D, SELL_PUT_10D
            # Can sell calls if no call position AND haven't traded calls today
            if not self.call_position and not self.has_traded_calls_today:
                valid.append(3)  # SELL_CALL_15D
        else:
            # Can close if have position (closing is always allowed)
            valid.append(4)
            
        return valid
        
    def _find_time_index_after_wait(self, wait_minutes: int) -> int:
        """Find time index after market open + wait time"""
        market_open = datetime.combine(
            self.current_episode_data['date'],
            datetime.strptime('09:30', '%H:%M').time()
        )
        
        start_time = market_open + timedelta(minutes=wait_minutes)
        
        for i, ts in enumerate(self.current_episode_data['timestamps']):
            if ts >= start_time:
                return i
                
        return 0
        
    def _get_atm_iv(self) -> float:
        """Get ATM implied volatility"""
        current_data = self.current_episode_data['by_time'].get(
            self.current_timestamp, pd.DataFrame()
        )
        
        if current_data.empty:
            return 0.2  # Default 20%
            
        # Find ATM strike
        spot = self.current_episode_data['spot_prices'].get(
            self.current_timestamp, 400
        )
        
        strikes = current_data['strike'].unique()
        atm_strike = min(strikes, key=lambda x: abs(x - spot))
        
        # Get ATM options
        atm_options = current_data[current_data['strike'] == atm_strike]
        
        # Average IV of ATM call and put
        ivs = atm_options['implied_volatility'].dropna()
        if len(ivs) > 0:
            return ivs.mean()
        else:
            return 0.2
            
    def _calculate_simple_risk_score(self) -> float:
        """Calculate normalized risk score for state"""
        # For now, return fixed values based on risk level
        risk_mapping = {'LOW': 0.2, 'MEDIUM': 0.5, 'HIGH': 0.8}
        return risk_mapping.get(self.risk_level, 0.5)
        
    def _close_all_positions(self):
        """Close any open positions at end of day"""
        if self.position:
            self._close_position()
            
    def _log_decision(self, state, action, next_state, reward, info):
        """Log decision for future RLHF"""
        if self.episode_logger:
            self.episode_logger.log_decision(
                state, action, next_state, reward, info,
                self.current_timestamp, self._get_readable_state(state)
            )
            
    def _get_readable_state(self, state):
        """Convert state vector to human-readable format"""
        return {
            'minutes_since_open': int(state[0] * 390),
            'spy_price': f"${state[1] * 500:.2f}",
            'atm_iv': f"{state[2]:.1%}",
            'has_position': bool(state[3]),
            'position_pnl': f"${state[4] * 100:.2f}",
            'time_in_position': f"{int(state[5] * 390)} min",
            'risk_score': f"{state[6]:.2f}",
            'minutes_until_close': int(state[7] * 390)
        }
        
    def render(self):
        """Render current state (text only for now)"""
        if self.render_mode == 'human':
            print(f"\nTime: {self.current_timestamp}")
            print(f"Risk Level: {self.risk_level}")
            print(f"Cash: ${self.cash:.2f}")
            print(f"Total P&L: ${self._calculate_total_pnl():.2f}")
            if self.position:
                print(f"Position: {self.position['option_type']} "
                      f"{self.position['strike']} @ ${self.position['entry_price']:.2f}")
                print(f"Current P&L: ${self.position['current_pnl']:.2f}")
                
    def calculate_kelly_position_size(self) -> int:
        """
        Calculate position size using Kelly Criterion
        Returns: Number of contracts (30, 20, 10, or 0)
        Independent of risk level - purely based on Kelly percentage
        """
        # Need at least 20 trades for meaningful statistics
        if len(self.trade_history) < 20:
            logger.info("Kelly: Insufficient history, using default 20 contracts")
            return 20  # Default moderate size
            
        # Calculate win rate and average win/loss
        wins = [t['pnl'] for t in self.trade_history if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in self.trade_history if t['pnl'] < 0]
        
        if not wins or not losses:
            logger.info("Kelly: No mixed results yet, using default 20 contracts")
            return 20  # Default if no mixed results yet
            
        win_rate = len(wins) / len(self.trade_history)
        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)
        
        # Kelly formula: f = (p*b - q)/b
        # where p = win_rate, q = 1-p, b = avg_win/avg_loss
        b = avg_win / avg_loss
        q = 1 - win_rate
        
        # Full Kelly percentage
        full_kelly = (win_rate * b - q) / b
        
        # Apply safety factor (quarter Kelly for options trading)
        kelly_pct = full_kelly * self.kelly_confidence
        
        # Log the calculation
        logger.info(f"Kelly calc: Win rate={win_rate:.2%}, Avg win=${avg_win:.2f}, "
                   f"Avg loss=${avg_loss:.2f}, b={b:.2f}")
        logger.info(f"Kelly: Full={full_kelly:.2%}, Quarter={kelly_pct:.2%}")
        
        # Simple bucketing into position sizes
        if kelly_pct <= 0:
            logger.info("Kelly: Negative edge, no trade")
            return 0  # Don't trade
        elif kelly_pct < 0.33:
            logger.info(f"Kelly: {kelly_pct:.2%} -> 10 contracts")
            return 10  # Small position (33% of max)
        elif kelly_pct < 0.67:
            logger.info(f"Kelly: {kelly_pct:.2%} -> 20 contracts") 
            return 20  # Medium position (67% of max)
        else:
            logger.info(f"Kelly: {kelly_pct:.2%} -> 30 contracts")
            return 30  # Full position (100%)
                
    def close(self):
        """Clean up environment"""
        if self.data_loader:
            self.data_loader.close()