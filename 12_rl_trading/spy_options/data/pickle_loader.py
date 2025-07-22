"""
Pickle-based data loader for GPU training
Uses pre-exported episodes to avoid database connectivity issues
"""
import pickle
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time
import random


class PickleDataLoader:
    """Data loader that reads from pickle file instead of database"""
    
    def __init__(self, pickle_file: str = 'sample_episodes.pkl'):
        """Initialize with pickle file"""
        self.pickle_file = pickle_file
        self.episodes = None
        self.current_episode_idx = 0
        self.load_data()
        
    def load_data(self):
        """Load episodes from pickle file"""
        print(f"Loading data from {self.pickle_file}...")
        
        # Handle compressed files
        if self.pickle_file.endswith('.gz'):
            import gzip
            with gzip.open(self.pickle_file, 'rb') as f:
                self.episodes = pickle.load(f)
        else:
            with open(self.pickle_file, 'rb') as f:
                self.episodes = pickle.load(f)
                
        print(f"Loaded {len(self.episodes)} episodes")
        
        # Extract trading days
        self.trading_days = [ep['date'] for ep in self.episodes]
        
    def get_random_episode(self) -> Dict:
        """Get a random episode for training"""
        return random.choice(self.episodes)
        
    def get_next_episode(self) -> Dict:
        """Get next episode in sequence"""
        episode = self.episodes[self.current_episode_idx]
        self.current_episode_idx = (self.current_episode_idx + 1) % len(self.episodes)
        return episode
        
    def get_intraday_data(self, date: datetime) -> pd.DataFrame:
        """Get intraday data for a specific date"""
        # Find episode for this date
        for episode in self.episodes:
            if episode['date'] == date:
                return episode['intraday_data']
        return pd.DataFrame()
        
    def get_market_indicators(self, date: datetime) -> Dict:
        """Get market indicators for a date"""
        # Return empty dict for now - could be extended with VIX etc
        return {}
    
    def get_episode_data(self, date: datetime) -> Dict:
        """Get full episode data for a specific date"""
        for episode in self.episodes:
            if episode['date'] == date:
                return episode
        # If not found, return a random episode
        return self.get_random_episode()
    
    def get_options_data(self, date: datetime, time_str: str) -> pd.DataFrame:
        """Get options data for a specific date and time"""
        # Find episode for this date
        for episode in self.episodes:
            if episode['date'] == date:
                # Find the timestamp that matches the time_str
                for timestamp in episode['timestamps']:
                    if timestamp.strftime('%H:%M') == time_str:
                        return episode['by_time'][timestamp]
                # If no exact match, return empty
                return pd.DataFrame()
        return pd.DataFrame()
        
    def find_contracts_by_delta(self, current_data: Dict, target_delta: float,
                               option_type: str, delta_range: float = 0.05) -> pd.DataFrame:
        """Find option contracts by target delta"""
        # Extract date and time from current_data
        if 'date' in current_data:
            date = current_data['date']
        else:
            # Find from current episode
            date = self.trading_days[self.current_episode_idx % len(self.trading_days)]
            
        time_str = current_data.get('time_str', '09:30')
        
        options_df = self.get_options_data(date, time_str)
        
        if options_df.empty:
            return pd.DataFrame()
            
        # Filter by option type
        mask = options_df['option_type'] == option_type
        options_df = options_df[mask]
        
        # Apply delta constraint (|delta| <= 0.20)
        if option_type == 'C':
            mask = (options_df['delta'] >= 0) & (options_df['delta'] <= 0.20)
        else:  # Put
            mask = (options_df['delta'] <= 0) & (options_df['delta'] >= -0.20)
        options_df = options_df[mask]
        
        if options_df.empty:
            return pd.DataFrame()
            
        # Calculate distance from target delta
        options_df['delta_distance'] = np.abs(options_df['delta'] - target_delta)
        
        # Sort by delta distance and return top candidates
        return options_df.nsmallest(5, 'delta_distance')
        
    def close(self):
        """Cleanup (no database connection to close)"""
        pass