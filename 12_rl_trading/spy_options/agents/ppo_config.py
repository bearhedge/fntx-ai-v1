"""
PPO Configuration for SPY Options Trading
Tuned for financial time series and discrete option selling
"""
import torch
import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class OptionsFeatureExtractor(BaseFeaturesExtractor):
    """
    Custom feature extractor for options trading
    Processes the 8-feature state vector
    """
    
    def __init__(self, observation_space, features_dim: int = 64):
        super().__init__(observation_space, features_dim)
        
        n_input_features = observation_space.shape[0]  # 8
        
        # Network with skip connections for time features
        self.time_features = nn.Sequential(
            nn.Linear(3, 16),  # minutes_since_open, time_in_position, minutes_until_close
            nn.ReLU(),
            nn.Linear(16, 16),
            nn.ReLU()
        )
        
        # Market features processing
        self.market_features = nn.Sequential(
            nn.Linear(2, 16),  # spy_price, atm_iv
            nn.ReLU(),
            nn.Linear(16, 16),
            nn.ReLU()
        )
        
        # Position features processing
        self.position_features = nn.Sequential(
            nn.Linear(2, 16),  # has_position, position_pnl
            nn.ReLU(),
            nn.Linear(16, 16),
            nn.ReLU()
        )
        
        # Risk feature (single value)
        self.risk_features = nn.Sequential(
            nn.Linear(1, 8),
            nn.ReLU()
        )
        
        # Combine all features
        self.combine_features = nn.Sequential(
            nn.Linear(16 + 16 + 16 + 8, 128),
            nn.ReLU(),
            nn.Linear(128, features_dim),
            nn.ReLU()
        )
        
    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        # Split features
        time_feats = observations[:, [0, 5, 7]]  # time-related
        market_feats = observations[:, [1, 2]]   # market data
        position_feats = observations[:, [3, 4]] # position info
        risk_feats = observations[:, [6]]        # risk score
        
        # Process separately
        time_encoded = self.time_features(time_feats)
        market_encoded = self.market_features(market_feats)
        position_encoded = self.position_features(position_feats)
        risk_encoded = self.risk_features(risk_feats)
        
        # Combine
        combined = torch.cat([
            time_encoded, market_encoded, 
            position_encoded, risk_encoded
        ], dim=1)
        
        return self.combine_features(combined)


class PPOConfig:
    """PPO hyperparameters tuned for options trading"""
    
    # Model architecture
    policy_kwargs = dict(
        features_extractor_class=OptionsFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=64),
        net_arch=[dict(pi=[128, 128], vf=[128, 128])],  # Separate networks
        activation_fn=nn.Tanh,  # Smooth activation for financial data
    )
    
    # Learning parameters
    learning_rate = 3e-5          # Very conservative to prevent NaN
    n_steps = 390                 # One trading day (78 5-min bars)
    batch_size = 32               # Small batches for stability
    n_epochs = 10                 # PPO epochs per update
    
    # PPO specific
    gamma = 0.95                  # Discount factor (slight discount for intraday)
    gae_lambda = 0.95            # GAE parameter
    clip_range = 0.2             # PPO clip parameter
    clip_range_vf = None         # No value function clipping
    normalize_advantage = True    # Normalize advantages
    ent_coef = 0.01              # Entropy coefficient for exploration
    vf_coef = 0.5                # Value function coefficient
    max_grad_norm = 0.1          # Aggressive gradient clipping to prevent NaN
    
    # Training configuration
    use_sde = False              # Don't use stochastic policy
    sde_sample_freq = -1         # Not used
    target_kl = None             # No KL constraint
    
    # Logging
    tensorboard_log = "./logs/tensorboard/"
    verbose = 1
    
    # Environment specific
    seed = 42
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    @classmethod
    def get_config_dict(cls):
        """Get configuration as dictionary for stable-baselines3"""
        return {
            'policy_kwargs': cls.policy_kwargs,
            'learning_rate': cls.learning_rate,
            'n_steps': cls.n_steps,
            'batch_size': cls.batch_size,
            'n_epochs': cls.n_epochs,
            'gamma': cls.gamma,
            'gae_lambda': cls.gae_lambda,
            'clip_range': cls.clip_range,
            'clip_range_vf': cls.clip_range_vf,
            'normalize_advantage': cls.normalize_advantage,
            'ent_coef': cls.ent_coef,
            'vf_coef': cls.vf_coef,
            'max_grad_norm': cls.max_grad_norm,
            'use_sde': cls.use_sde,
            'sde_sample_freq': cls.sde_sample_freq,
            'target_kl': cls.target_kl,
            'tensorboard_log': cls.tensorboard_log,
            'verbose': cls.verbose,
            'seed': cls.seed,
            'device': cls.device
        }
        
    @classmethod
    def get_schedule_fn(cls, initial_value: float):
        """Create learning rate schedule function"""
        def schedule(progress_remaining: float) -> float:
            """
            Linear decay from initial_value to 0.1 * initial_value
            
            Args:
                progress_remaining: goes from 1 (start) to 0 (end)
            
            Returns:
                current learning rate
            """
            return initial_value * (0.1 + 0.9 * progress_remaining)
        
        return schedule