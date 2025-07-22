"""
Episode Logger for RLHF Preparation
Captures all trading decisions for future human review
"""
import json
import pickle
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class DecisionPoint:
    """Single decision point in an episode"""
    timestamp: datetime
    step_number: int
    
    # State information
    state_raw: np.ndarray
    state_readable: Dict[str, Any]
    
    # Action information
    action_taken: int
    action_readable: str
    valid_actions: List[int]
    
    # Outcome information  
    reward_received: float
    next_state_raw: np.ndarray
    next_state_readable: Dict[str, Any]
    
    # Context
    market_snapshot: Dict[str, Any]
    position_before: Optional[Dict] = None
    position_after: Optional[Dict] = None
    execution_result: Optional[Dict] = None
    
    # For RLHF
    human_rating: Optional[Dict] = None


@dataclass
class TradingEpisode:
    """Complete episode with all decisions"""
    episode_id: str
    date: datetime
    
    # Market conditions
    risk_level: str
    risk_parameters: Dict[str, Any]
    market_indicators: Dict[str, Any]
    
    # All decisions
    decisions: List[DecisionPoint]
    
    # Episode outcomes
    total_pnl: float
    max_drawdown: float
    trades_executed: int
    win_rate: Optional[float] = None
    
    # Metadata
    agent_version: str = "baseline_rl_v1"
    environment_version: str = "v1.0"
    
    # Human feedback
    overall_rating: Optional[Dict] = None
    feedback_timestamp: Optional[datetime] = None


class EpisodeLogger:
    """
    Logs episodes for RLHF preparation
    Stores in both JSON (human-readable) and pickle (efficient) formats
    """
    
    def __init__(self, log_dir: str = "logs/episodes"):
        """Initialize logger with storage directory"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current episode being logged
        self.current_episode = None
        self.decision_buffer = []
        
        # Performance tracking
        self.episode_stats = {
            'max_pnl': 0,
            'min_pnl': 0,
            'trades_executed': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
        
    def start_episode(self, episode_date: datetime, risk_level: str,
                     risk_parameters: Dict, market_indicators: Dict):
        """Start logging a new episode"""
        from uuid import uuid4
        
        episode_id = f"{episode_date.strftime('%Y%m%d')}_{uuid4().hex[:8]}"
        
        self.current_episode = TradingEpisode(
            episode_id=episode_id,
            date=episode_date,
            risk_level=risk_level,
            risk_parameters=risk_parameters,
            market_indicators=market_indicators,
            decisions=[],
            total_pnl=0,
            max_drawdown=0,
            trades_executed=0
        )
        
        self.decision_buffer = []
        self.episode_stats = {
            'max_pnl': 0,
            'min_pnl': 0,
            'trades_executed': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
        
        logger.info(f"Started episode {episode_id}")
        
    def log_decision(self, state: np.ndarray, action: int, next_state: np.ndarray,
                    reward: float, info: Dict, timestamp: datetime,
                    state_readable: Dict):
        """Log a single decision point"""
        
        if not self.current_episode:
            logger.warning("No active episode to log decision")
            return
            
        # Create readable action description
        action_readable = self._describe_action(action, info)
        
        # Extract market snapshot
        market_snapshot = {
            'spot_price': info.get('spot_price', 0),
            'risk_score': info.get('risk_score', 0),
            'minutes_into_day': state_readable.get('minutes_since_open', 0),
            'atm_iv': state_readable.get('atm_iv', '0%')
        }
        
        decision = DecisionPoint(
            timestamp=timestamp,
            step_number=len(self.current_episode.decisions),
            state_raw=state.copy(),
            state_readable=state_readable.copy(),
            action_taken=action,
            action_readable=action_readable,
            valid_actions=info.get('valid_actions', [0]),
            reward_received=reward,
            next_state_raw=next_state.copy(),
            next_state_readable=self._make_state_readable(next_state),
            market_snapshot=market_snapshot,
            position_before=info.get('position_before'),
            position_after=info.get('position_after'),
            execution_result=info.get('execution_result')
        )
        
        self.current_episode.decisions.append(decision)
        
        # Update episode stats
        self._update_stats(info)
        
    def end_episode(self, final_pnl: float):
        """Finalize and save the episode"""
        
        if not self.current_episode:
            logger.warning("No active episode to end")
            return
            
        # Calculate final metrics
        self.current_episode.total_pnl = final_pnl
        self.current_episode.max_drawdown = abs(self.episode_stats['min_pnl'])
        self.current_episode.trades_executed = self.episode_stats['trades_executed']
        
        if self.episode_stats['trades_executed'] > 0:
            self.current_episode.win_rate = (
                self.episode_stats['winning_trades'] / 
                self.episode_stats['trades_executed']
            )
            
        # Save episode
        self._save_episode()
        
        logger.info(f"Ended episode {self.current_episode.episode_id}: "
                   f"P&L=${final_pnl:.2f}, Trades={self.episode_stats['trades_executed']}")
        
        self.current_episode = None
        
    def _save_episode(self):
        """Save episode in multiple formats"""
        
        episode_id = self.current_episode.episode_id
        
        # Save as pickle (efficient for loading)
        pickle_path = self.log_dir / f"{episode_id}.pkl"
        with open(pickle_path, 'wb') as f:
            pickle.dump(self.current_episode, f)
            
        # Save as JSON (human-readable)
        json_path = self.log_dir / f"{episode_id}.json"
        episode_dict = self._episode_to_dict(self.current_episode)
        with open(json_path, 'w') as f:
            json.dump(episode_dict, f, indent=2, default=str)
            
        # Save summary CSV (for quick analysis)
        self._update_summary_csv()
        
    def _episode_to_dict(self, episode: TradingEpisode) -> Dict:
        """Convert episode to JSON-serializable dict"""
        
        # Convert numpy arrays to lists for JSON
        decisions_list = []
        for decision in episode.decisions:
            dec_dict = asdict(decision)
            dec_dict['state_raw'] = dec_dict['state_raw'].tolist()
            dec_dict['next_state_raw'] = dec_dict['next_state_raw'].tolist()
            decisions_list.append(dec_dict)
            
        episode_dict = asdict(episode)
        episode_dict['decisions'] = decisions_list
        
        return episode_dict
        
    def _update_summary_csv(self):
        """Update summary CSV with episode metrics"""
        
        summary_path = self.log_dir / "episode_summary.csv"
        
        summary_data = {
            'episode_id': self.current_episode.episode_id,
            'date': self.current_episode.date,
            'risk_level': self.current_episode.risk_level,
            'total_pnl': self.current_episode.total_pnl,
            'max_drawdown': self.current_episode.max_drawdown,
            'trades_executed': self.current_episode.trades_executed,
            'win_rate': self.current_episode.win_rate,
            'decisions_made': len(self.current_episode.decisions)
        }
        
        # Append to CSV
        df = pd.DataFrame([summary_data])
        if summary_path.exists():
            df.to_csv(summary_path, mode='a', header=False, index=False)
        else:
            df.to_csv(summary_path, index=False)
            
    def load_episode(self, episode_id: str) -> TradingEpisode:
        """Load a saved episode"""
        
        pickle_path = self.log_dir / f"{episode_id}.pkl"
        
        if not pickle_path.exists():
            raise FileNotFoundError(f"Episode {episode_id} not found")
            
        with open(pickle_path, 'rb') as f:
            return pickle.load(f)
            
    def load_episodes_for_date(self, date: datetime) -> List[TradingEpisode]:
        """Load all episodes for a specific date"""
        
        date_str = date.strftime('%Y%m%d')
        episodes = []
        
        for pickle_file in self.log_dir.glob(f"{date_str}_*.pkl"):
            with open(pickle_file, 'rb') as f:
                episodes.append(pickle.load(f))
                
        return episodes
        
    def get_episode_summary(self) -> pd.DataFrame:
        """Get summary of all logged episodes"""
        
        summary_path = self.log_dir / "episode_summary.csv"
        
        if summary_path.exists():
            return pd.read_csv(summary_path)
        else:
            return pd.DataFrame()
            
    def _describe_action(self, action: int, info: Dict) -> str:
        """Create human-readable action description"""
        
        action_map = {
            0: "HOLD",
            1: "SELL PUT (15 delta)",
            2: "SELL PUT (10 delta)", 
            3: "SELL CALL (15 delta)",
            4: "CLOSE POSITION"
        }
        
        base_description = action_map.get(action, f"Unknown ({action})")
        
        # Add execution details if available
        if info.get('execution_result', {}).get('executed'):
            exec_result = info['execution_result']
            if 'strike' in exec_result:
                base_description += f" - {exec_result['strike']} strike"
            if 'fill_price' in exec_result:
                base_description += f" @ ${exec_result['fill_price']:.2f}"
                
        elif info.get('execution_result', {}).get('rejected'):
            reason = info['execution_result'].get('reason', 'unknown')
            base_description += f" - REJECTED ({reason})"
            
        return base_description
        
    def _make_state_readable(self, state: np.ndarray) -> Dict:
        """Convert state vector to readable format"""
        
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
        
    def _update_stats(self, info: Dict):
        """Update episode statistics"""
        
        # Track P&L extremes
        current_pnl = info.get('total_pnl', 0)
        self.episode_stats['max_pnl'] = max(self.episode_stats['max_pnl'], current_pnl)
        self.episode_stats['min_pnl'] = min(self.episode_stats['min_pnl'], current_pnl)
        
        # Track trades
        if info.get('execution_result', {}).get('executed'):
            if 'SELL' in info['execution_result'].get('action', ''):
                self.episode_stats['trades_executed'] += 1
                
        # Track trade outcomes (when closing)
        if info.get('execution_result', {}).get('action') == 'CLOSE':
            if info['execution_result'].get('position_pnl', 0) > 0:
                self.episode_stats['winning_trades'] += 1
            else:
                self.episode_stats['losing_trades'] += 1