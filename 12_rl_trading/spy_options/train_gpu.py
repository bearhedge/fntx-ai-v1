"""
GPU training script for SPY Options RL Agent
Uses pickle data loader to avoid database connectivity issues
"""
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import logging
import gzip
import pickle

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import (
    BaseCallback, EvalCallback, CheckpointCallback
)
from stable_baselines3.common.monitor import Monitor

from config import RL_CONFIG
from data.pickle_loader import PickleDataLoader
from environments import SPY0DTEEnvironment
from agents.rewards import OptionsEpisodeReward
from agents.ppo_config import PPOConfig
from rlhf import EpisodeLogger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EpisodeLoggerCallback(BaseCallback):
    """Custom callback to integrate EpisodeLogger with training"""
    
    def __init__(self, episode_logger: EpisodeLogger, verbose=0):
        super().__init__(verbose)
        self.episode_logger = episode_logger
        self.episode_started = False
        
    def _on_rollout_start(self) -> None:
        """Called at the start of a rollout"""
        if not self.episode_started:
            # Get environment info
            env_info = self.training_env.get_attr('_get_info')[0]
            
            # Start episode logging
            self.episode_logger.start_episode(
                episode_date=env_info['episode_date'],
                risk_level=env_info['risk_level'],
                risk_parameters=self.training_env.get_attr('risk_parameters')[0],
                market_indicators={}  # Would get from data loader
            )
            self.episode_started = True
            
    def _on_step(self) -> bool:
        """Called after each step"""
        # Episode logger is called directly from environment
        return True
        
    def _on_rollout_end(self) -> None:
        """Called at the end of a rollout"""
        if self.episode_started:
            # Get final P&L
            final_pnl = self.training_env.get_attr('_calculate_total_pnl')[0]
            self.episode_logger.end_episode(final_pnl)
            self.episode_started = False
            
        return True


def create_training_env(data_loader: PickleDataLoader, 
                       episode_logger: EpisodeLogger) -> SPY0DTEEnvironment:
    """Create training environment with monitoring"""
    
    # Create base environment
    env = SPY0DTEEnvironment(
        data_loader=data_loader,
        reward_calculator=OptionsEpisodeReward(),
        episode_logger=episode_logger,
        initial_capital=125000
    )
    
    # Wrap with Monitor for additional logging
    env = Monitor(env, filename="logs/monitor/train")
    
    return env


def create_eval_env(data_loader: PickleDataLoader) -> SPY0DTEEnvironment:
    """Create evaluation environment"""
    
    env = SPY0DTEEnvironment(
        data_loader=data_loader,
        reward_calculator=OptionsEpisodeReward(),
        episode_logger=None,  # No logging during eval
        initial_capital=125000
    )
    
    env = Monitor(env, filename="logs/monitor/eval")
    
    return env


def train_baseline_agent_gpu(
    pickle_file: str = 'sample_episodes.pkl',
    total_timesteps: int = 500_000,
    eval_freq: int = 10_000,
    save_freq: int = 25_000
):
    """
    Train baseline PPO agent on GPU
    
    Args:
        pickle_file: Path to pickle file with episodes
        total_timesteps: Total training steps
        eval_freq: Evaluation frequency
        save_freq: Model checkpoint frequency
    """
    
    logger.info(f"Starting GPU training with {pickle_file}")
    
    # Check if we need to use compressed file
    if not os.path.exists(pickle_file) and os.path.exists(f"{pickle_file}.gz"):
        logger.info(f"Using compressed file {pickle_file}.gz")
        pickle_file = f"{pickle_file}.gz"
    
    # Initialize data loader
    data_loader = PickleDataLoader(pickle_file)
    logger.info(f"Loaded {len(data_loader.episodes)} episodes from pickle file")
    
    # Initialize episode logger
    episode_logger = EpisodeLogger(log_dir="logs/episodes/train")
    
    # Create environments
    train_env = create_training_env(data_loader, episode_logger)
    eval_env = create_eval_env(data_loader)
    
    # Create PPO model with GPU support
    device = 'cuda' if os.environ.get('CUDA_VISIBLE_DEVICES') is not None else 'auto'
    
    # Get config and update device
    ppo_config = PPOConfig.get_config_dict()
    ppo_config['device'] = device
    
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
    
    # Create callbacks
    callbacks = []
    
    # Episode logger callback
    episode_callback = EpisodeLoggerCallback(episode_logger)
    callbacks.append(episode_callback)
    
    # Evaluation callback
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path="./models/best/",
        log_path="./logs/eval/",
        eval_freq=eval_freq,
        deterministic=True,
        render=False,
        n_eval_episodes=5  # Reduced for faster eval with limited data
    )
    callbacks.append(eval_callback)
    
    # Checkpoint callback
    checkpoint_callback = CheckpointCallback(
        save_freq=save_freq,
        save_path="./models/checkpoints/",
        name_prefix="ppo_spy_options_gpu"
    )
    callbacks.append(checkpoint_callback)
    
    # Train the model
    logger.info(f"Starting training for {total_timesteps} timesteps...")
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            progress_bar=True
        )
        
        # Save final model
        final_path = f"./models/final/ppo_baseline_gpu_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        model.save(final_path)
        logger.info(f"Saved final model to {final_path}")
        
        # Print episode summary
        summary = episode_logger.get_episode_summary()
        if not summary.empty:
            logger.info("\nTraining Summary:")
            logger.info(f"  Episodes: {len(summary)}")
            logger.info(f"  Avg P&L: ${summary['total_pnl'].mean():.2f}")
            logger.info(f"  Win Rate: {summary['win_rate'].mean():.2%}")
            logger.info(f"  Avg Trades: {summary['trades_executed'].mean():.1f}")
            
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        
    finally:
        # Clean up
        train_env.close()
        eval_env.close()
        data_loader.close()
        
    logger.info("Training complete!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Train PPO agent for SPY options trading on GPU"
    )
    
    parser.add_argument(
        '--pickle-file',
        type=str,
        default='sample_episodes.pkl',
        help='Path to pickle file with episodes'
    )
    
    parser.add_argument(
        '--timesteps',
        type=int,
        default=500_000,
        help='Total training timesteps (default: 500k)'
    )
    
    parser.add_argument(
        '--eval-freq',
        type=int,
        default=10_000,
        help='Evaluation frequency (default: 10k)'
    )
    
    parser.add_argument(
        '--save-freq',
        type=int,
        default=25_000,
        help='Model save frequency (default: 25k)'
    )
    
    args = parser.parse_args()
    
    # Create necessary directories
    for dir_path in ['logs/episodes', 'logs/monitor', 'logs/eval', 
                     'logs/tensorboard', 'models/best', 'models/checkpoints',
                     'models/final']:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        
    # Run training
    train_baseline_agent_gpu(
        pickle_file=args.pickle_file,
        total_timesteps=args.timesteps,
        eval_freq=args.eval_freq,
        save_freq=args.save_freq
    )


if __name__ == "__main__":
    main()