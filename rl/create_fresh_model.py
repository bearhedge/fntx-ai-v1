#!/usr/bin/env python3
"""
Create a fresh PPO model for the RL API server
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from stable_baselines3 import PPO
import logging

logging.basicConfig(level=logging.INFO)

class DummyEnv(gym.Env):
    """Minimal environment for model creation"""
    
    def __init__(self):
        super().__init__()
        # 8 features as expected by the API
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(8,), dtype=np.float32)
        # 3 actions: 0=hold, 1=call, 2=put
        self.action_space = spaces.Discrete(3)
    
    def step(self, action):
        observation = self.observation_space.sample()
        reward = np.random.randn()
        terminated = False
        truncated = False
        info = {}
        return observation, reward, terminated, truncated, info
    
    def reset(self, seed=None, options=None):
        if seed is not None:
            np.random.seed(seed)
        observation = self.observation_space.sample()
        info = {}
        return observation, info

def main():
    print("🏗️ Creating fresh PPO model...")
    
    # Create dummy environment
    env = DummyEnv()
    
    # Create PPO model
    model = PPO(
        'MlpPolicy',
        env,
        learning_rate=3e-4,
        n_steps=64,  # Small for quick creation
        batch_size=32,
        n_epochs=1,
        gamma=0.99,
        verbose=1
    )
    
    # Train for a few steps to initialize properly
    print("🏃 Quick training to initialize model...")
    model.learn(total_timesteps=100)
    
    # Save the model
    save_path = '/home/info/fntx-ai-v1/rl/models/gpu_trained/fresh_ppo_model.zip'
    model.save(save_path)
    print(f"✅ Fresh PPO model saved to: {save_path}")
    
    # Test loading
    test_model = PPO.load(save_path)
    print("✅ Model loads successfully!")
    
    # Test prediction
    obs = env.observation_space.sample()
    action, _states = test_model.predict(obs)
    print(f"✅ Model prediction test: action={action}")

if __name__ == "__main__":
    main()