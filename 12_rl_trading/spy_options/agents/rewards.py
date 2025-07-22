"""
Swappable Reward System for RLHF
Allows easy transition from simple P&L to human-aligned rewards
"""
from abc import ABC, abstractmethod
import numpy as np
import torch
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class RewardCalculator(ABC):
    """Abstract base class for reward calculation"""
    
    @abstractmethod
    def calculate(self, state: np.ndarray, action: int, 
                 next_state: np.ndarray, info: Dict[str, Any]) -> float:
        """
        Calculate reward for a state transition
        
        Args:
            state: Current state vector
            action: Action taken
            next_state: Resulting state
            info: Additional information (P&L, execution details, etc.)
            
        Returns:
            Reward value
        """
        pass


class SimplePnLReward(RewardCalculator):
    """
    Initial reward function based on P&L changes
    Used for baseline RL training
    """
    
    def __init__(self, scaling_factor: float = 0.01):
        """
        Args:
            scaling_factor: Scale P&L to reasonable reward range
        """
        self.scaling_factor = scaling_factor
        
    def calculate(self, state: np.ndarray, action: int,
                 next_state: np.ndarray, info: Dict[str, Any]) -> float:
        """Calculate reward based on P&L change"""
        
        # Base reward is scaled P&L change
        pnl_change = info.get('pnl_change', 0.0)
        reward = pnl_change * self.scaling_factor
        
        # Small penalty for holding to encourage action
        if action == 0 and info.get('has_position', False):
            reward -= 0.001
            
        # Penalty for rejected trades (no volume, etc.)
        if info.get('trade_rejected', False):
            reward -= 0.1
            
        # Bonus for successful trade execution
        if info.get('trade_executed', False):
            reward += 0.01
            
        return reward


class OptionsEpisodeReward(RewardCalculator):
    """
    Options-specific reward focusing on daily outcomes
    Minimal intra-day rewards, strong episode-end signal
    """
    
    def __init__(self):
        pass
        
    def calculate(self, state: np.ndarray, action: int,
                 next_state: np.ndarray, info: Dict[str, Any]) -> float:
        """Calculate reward with focus on episode outcomes"""
        
        reward = 0.0
        
        # Minimal 5-minute rewards (actions only, not P&L)
        if action != 0:  # Not HOLD
            if info.get('trade_executed', False):
                # Small nudge for taking action
                reward += 0.01
            elif info.get('trade_rejected', False):
                # Learn valid trades
                reward -= 0.05
        
        # Episode completion - this is where real learning happens
        if info.get('episode_ended', False):
            daily_pnl = info.get('episode_pnl', 0.0)
            
            # Scale daily P&L to meaningful reward
            if daily_pnl > 0:
                # Winning day
                reward += min(20.0, daily_pnl * 0.01)  # Cap at 20
            else:
                # Losing day - asymmetric to emphasize risk
                reward += max(-30.0, daily_pnl * 0.015)  # Losses hurt 1.5x more
            
            # Bonus for finishing without hitting stop loss
            if not info.get('stop_loss_triggered', False) and daily_pnl > 0:
                reward += 2.0
                
            # Small bonus for appropriate Kelly sizing
            if info.get('kelly_sized', False):
                reward += 1.0
                
            # Bonus for trading discipline (not forcing trades)
            if info.get('respected_one_trade_rule', True):
                reward += 0.5
        
        return reward


class RiskAdjustedReward(RewardCalculator):
    """
    Intermediate reward function with risk considerations
    """
    
    def __init__(self, scaling_factor: float = 0.01, risk_penalty: float = 0.5):
        self.scaling_factor = scaling_factor
        self.risk_penalty = risk_penalty
        
    def calculate(self, state: np.ndarray, action: int,
                 next_state: np.ndarray, info: Dict[str, Any]) -> float:
        """Calculate risk-adjusted reward"""
        
        # Start with P&L reward
        pnl_change = info.get('pnl_change', 0.0)
        reward = pnl_change * self.scaling_factor
        
        # Penalize trading in high risk conditions
        risk_level = info.get('risk_level', 'MEDIUM')
        if risk_level == 'HIGH' and action in [1, 2, 3]:  # Selling actions
            reward -= self.risk_penalty
            
        # Reward respecting wait times
        if info.get('respected_wait_time', True):
            reward += 0.05
        else:
            reward -= 0.5  # Heavy penalty for violating wait time
            
        # Reward appropriate position sizing
        if info.get('position_size_appropriate', True):
            reward += 0.02
            
        return reward


class HumanAlignedReward(RewardCalculator):
    """
    RLHF reward using learned preference model
    This will be implemented after collecting human feedback
    """
    
    def __init__(self, learned_model, feature_extractor=None):
        """
        Args:
            learned_model: Trained neural network predicting human preferences
            feature_extractor: Optional feature transformation
        """
        self.model = learned_model
        self.feature_extractor = feature_extractor
        
    def calculate(self, state: np.ndarray, action: int,
                 next_state: np.ndarray, info: Dict[str, Any]) -> float:
        """Calculate reward using learned human preferences"""
        
        # Extract features for the preference model
        if self.feature_extractor:
            features = self.feature_extractor(state, action, next_state, info)
        else:
            # Default: concatenate state, action, and key info
            features = np.concatenate([
                state,
                [action],
                [info.get('pnl_change', 0.0)],
                [info.get('risk_score', 0)],
                [1 if info.get('trade_executed', False) else 0]
            ])
            
        # Predict human preference score
        with torch.no_grad():
            preference_score = self.model(torch.FloatTensor(features)).item()
            
        # Add base P&L component to maintain profitability
        pnl_component = info.get('pnl_change', 0.0) * 0.005
        
        return preference_score + pnl_component


class CompositReward(RewardCalculator):
    """
    Combines multiple reward calculators with weights
    Useful for gradual transition to RLHF
    """
    
    def __init__(self, calculators: list, weights: list):
        """
        Args:
            calculators: List of RewardCalculator instances
            weights: List of weights (should sum to 1.0)
        """
        assert len(calculators) == len(weights)
        assert abs(sum(weights) - 1.0) < 1e-6
        
        self.calculators = calculators
        self.weights = weights
        
    def calculate(self, state: np.ndarray, action: int,
                 next_state: np.ndarray, info: Dict[str, Any]) -> float:
        """Calculate weighted combination of rewards"""
        
        total_reward = 0.0
        for calculator, weight in zip(self.calculators, self.weights):
            reward = calculator.calculate(state, action, next_state, info)
            total_reward += weight * reward
            
        return total_reward