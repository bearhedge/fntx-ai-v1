"""
Normalized environment wrapper to prevent NaN issues
"""
import numpy as np
import gymnasium as gym
from typing import Dict, Tuple, Any


class NormalizedTradingEnv(gym.Wrapper):
    """
    Normalizes observations to prevent NaN issues in neural networks
    """
    
    def __init__(self, env: gym.Env):
        super().__init__(env)
        
        # The observation space is already normalized to [0,1] with 8 features!
        # Features from _get_state():
        # 0: minutes_since_open / 390 (normalized time)
        # 1: spot_price / 1000 (normalized price)
        # 2: atm_iv (already 0-1)
        # 3: has_position (0 or 1)
        # 4: position_pnl / 1000 (normalized P&L)
        # 5: time_in_position / 390 (normalized time)
        # 6: risk_score (0-1)
        # 7: minutes_until_close / 390 (normalized time)
        
        # Since observations are already normalized, we don't need to do much
        self.obs_mean = np.zeros(env.observation_space.shape[0])
        self.obs_std = np.ones(env.observation_space.shape[0])
        
        # Prevent division by zero
        self.obs_std = np.maximum(self.obs_std, 1e-8)
        
        # Clip range to prevent extreme values
        self.clip_range = 10.0
        
    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        return self._normalize_obs(obs), info
        
    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        
        # Normalize observation
        obs = self._normalize_obs(obs)
        
        # Clip reward to prevent explosion
        reward = np.clip(reward, -10, 10)
        
        return obs, reward, terminated, truncated, info
        
    def _normalize_obs(self, obs: np.ndarray) -> np.ndarray:
        """Ensure observations are valid"""
        # Replace any inf/nan with safe values
        obs = np.nan_to_num(obs, nan=0.5, posinf=1.0, neginf=0.0)
        
        # Clip to valid range [0, 1] since that's what the env promises
        obs = np.clip(obs, 0.0, 1.0)
        
        # Final safety check
        if np.any(np.isnan(obs)) or np.any(np.isinf(obs)):
            print(f"WARNING: Invalid observation detected: {obs}")
            obs = np.ones_like(obs) * 0.5  # Safe middle values
        
        return obs.astype(np.float32)