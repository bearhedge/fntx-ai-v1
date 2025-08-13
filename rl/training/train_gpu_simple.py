"""
Simplified GPU training script for SPY Options RL Agent
Minimal setup to test GPU training functionality
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

from config import RL_CONFIG
from data.pickle_loader import PickleDataLoader
from environments import SPY0DTEEnvironment
from environments.normalized_env import NormalizedTradingEnv
from agents.rewards import OptionsEpisodeReward
from agents.ppo_config import PPOConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_training_env(data_loader: PickleDataLoader) -> SPY0DTEEnvironment:
    """Create training environment"""
    
    env = SPY0DTEEnvironment(
        data_loader=data_loader,
        reward_calculator=OptionsEpisodeReward(),
        episode_logger=None,
        initial_capital=125000
    )
    
    # Wrap with normalization to prevent NaN
    env = NormalizedTradingEnv(env)
    
    # Wrap with Monitor for basic logging
    env = Monitor(env)
    
    return env


def train_simple(
    pickle_file: str = 'full_training_episodes.pkl.gz',
    total_timesteps: int = 2000000
):
    """Simple training function for testing"""
    
    logger.info(f"Starting simplified GPU training with {pickle_file}")
    
    # Check if we need to use compressed file
    if not os.path.exists(pickle_file) and os.path.exists(f"{pickle_file}.gz"):
        logger.info(f"Using compressed file {pickle_file}.gz")
        pickle_file = f"{pickle_file}.gz"
    
    # Initialize data loader
    data_loader = PickleDataLoader(pickle_file)
    logger.info(f"Loaded {len(data_loader.episodes)} episodes from pickle file")
    
    # Create environment
    train_env = create_training_env(data_loader)
    
    # Create PPO model with GPU support
    device = 'cuda' if os.environ.get('CUDA_VISIBLE_DEVICES') is not None else 'auto'
    
    # Get config and update device
    ppo_config = PPOConfig.get_config_dict()
    ppo_config['device'] = device
    ppo_config['verbose'] = 1  # Set verbose in config
    
    model = PPO(
        policy="MlpPolicy",
        env=train_env,
        **ppo_config
    )
    
    logger.info("Created PPO model with configuration:")
    logger.info(f"  Device: {device}")
    logger.info(f"  Learning rate: {PPOConfig.learning_rate}")
    logger.info(f"  Batch size: {PPOConfig.batch_size}")
    logger.info(f"  N steps: {PPOConfig.n_steps}")
    
    # Train the model
    logger.info(f"Starting training for {total_timesteps} timesteps...")
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            progress_bar=True
        )
        
        # Save final model
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_path = f"ppo_gpu_test_{timestamp}"
        model.save(final_path)
        logger.info(f"Saved model to {final_path}")
        
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        
    finally:
        # Clean up
        train_env.close()
        data_loader.close()
        
    logger.info("Training complete!")


if __name__ == "__main__":
    # Create necessary directories
    for dir_path in ['logs']:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Run simple training
    train_simple()