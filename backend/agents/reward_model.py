#!/usr/bin/env python3
"""
FNTX AI RewardModelAgent - Reinforcement Learning from Human Feedback (RLHF)
Learns user preferences and generates reward signals for strategy optimization
"""

import os
import json
import time
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with dynamic path
from backend.core.utils.logging import get_agent_logger
from backend.core.utils.config import config
logger = get_agent_logger('RewardModelAgent')

class RewardModelAgent:
    """
    RewardModelAgent learns user preferences through RLHF and generates reward signals
    to optimize trading strategies based on user feedback and performance outcomes.
    """
    
    def __init__(self):
        self.memory_file = config.get_memory_path("reward_model_memory.json")
        self.shared_context_file = config.get_memory_path("shared_context.json")
        self.executor_memory_file = config.get_memory_path("executor_memory.json")
        
        # Reward model parameters
        self.learning_rate = float(os.getenv("REWARD_LEARNING_RATE", "0.01"))
        self.preference_decay = float(os.getenv("PREFERENCE_DECAY", "0.99"))
        self.min_feedback_threshold = int(os.getenv("MIN_FEEDBACK_THRESHOLD", "5"))
        
        logger.info("RewardModelAgent initialized with RLHF capabilities")

    def load_memory(self) -> Dict[str, Any]:
        """Load reward model memory from MCP-compatible JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
        
        # Default memory schema
        return {
            "agent_id": "RewardModelAgent",
            "last_updated": datetime.now().isoformat(),
            "preferences": {
                "risk_tolerance": "moderate",
                "profit_goal": 0.02,
                "trade_style": "conservative",
                "max_drawdown": 0.15,
                "win_rate_preference": 0.70,
                "volatility_preference": "low"
            },
            "reward_signals": [],
            "learning_signals": [],
            "user_feedback_history": [],
            "preference_weights": {
                "profit_factor": 0.4,
                "risk_factor": 0.3,
                "consistency_factor": 0.2,
                "user_satisfaction_factor": 0.1
            },
            "model_performance": {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0
            }
        }

    def save_memory(self, memory: Dict[str, Any]):
        """Save reward model memory to MCP-compatible JSON file"""
        try:
            memory["last_updated"] = datetime.now().isoformat()
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def load_shared_context(self) -> Dict[str, Any]:
        """Load shared context for inter-agent communication"""
        try:
            if os.path.exists(self.shared_context_file):
                with open(self.shared_context_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading shared context: {e}")
        return {}

    def update_shared_context(self, updates: Dict[str, Any]):
        """Update shared context with reward signals and preferences"""
        try:
            context = self.load_shared_context()
            context.update(updates)
            context["last_updated"] = datetime.now().isoformat()
            
            with open(self.shared_context_file, 'w') as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating shared context: {e}")

    def load_executor_trades(self) -> List[Dict[str, Any]]:
        """Load executed trades from ExecutorAgent for reward calculation"""
        try:
            if os.path.exists(self.executor_memory_file):
                with open(self.executor_memory_file, 'r') as f:
                    executor_memory = json.load(f)
                    return executor_memory.get("executed_trades", [])
        except Exception as e:
            logger.error(f"Error loading executor trades: {e}")
        return []

    def calculate_trade_reward(self, trade: Dict[str, Any], user_preferences: Dict[str, Any]) -> float:
        """Calculate reward score for a trade based on outcome and user preferences"""
        try:
            # Extract trade metrics
            profit_loss = trade.get("profit_loss", 0)
            trade_duration = trade.get("holding_period", "0h 0m")
            status = trade.get("status", "unknown")
            
            # Parse profit/loss
            if isinstance(profit_loss, str):
                profit_loss = float(profit_loss.replace("$", "").replace(",", ""))
            
            # Base reward from profit/loss
            profit_reward = profit_loss / 100.0  # Normalize to reasonable scale
            
            # Risk-adjusted reward based on user preferences
            risk_tolerance = user_preferences.get("risk_tolerance", "moderate")
            risk_multiplier = {"low": 0.5, "moderate": 1.0, "high": 1.5}.get(risk_tolerance, 1.0)
            
            # Status-based rewards
            status_rewards = {
                "CLOSED_PROFIT": 1.0,
                "TAKE_PROFIT": 1.2,  # Bonus for hitting take profit
                "EXPIRED_WORTHLESS": 1.1,  # Good for option selling
                "STOP_LOSS": -0.5,  # Penalty for stop loss
                "CLOSED_LOSS": -0.3
            }
            
            status_reward = status_rewards.get(status, 0.0)
            
            # Duration reward (prefer shorter holds for options selling)
            duration_reward = 0.1 if "h" in trade_duration and int(trade_duration.split("h")[0]) < 6 else 0.0
            
            # Combined reward score
            total_reward = (profit_reward * risk_multiplier + status_reward + duration_reward)
            
            # Normalize to [0, 1] range
            reward_score = max(0.0, min(1.0, (total_reward + 1.0) / 2.0))
            
            logger.info(f"Trade reward calculated: {reward_score:.3f} for trade {trade.get('trade_id', 'unknown')}")
            return reward_score
            
        except Exception as e:
            logger.error(f"Error calculating trade reward: {e}")
            return 0.5  # Neutral reward on error

    def process_user_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Process explicit user feedback and update preferences"""
        try:
            memory = self.load_memory()
            
            # Add feedback to history
            feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "trade_id": feedback.get("trade_id"),
                "rating": feedback.get("rating", 3),  # 1-5 scale
                "comment": feedback.get("comment", ""),
                "preference_updates": feedback.get("preference_updates", {})
            }
            
            memory["user_feedback_history"].append(feedback_entry)
            
            # Update preferences based on feedback
            if "preference_updates" in feedback:
                for key, value in feedback["preference_updates"].items():
                    if key in memory["preferences"]:
                        # Gradual preference update with learning rate
                        current_val = memory["preferences"][key]
                        if isinstance(current_val, (int, float)):
                            memory["preferences"][key] = current_val + self.learning_rate * (value - current_val)
                        else:
                            memory["preferences"][key] = value
            
            # Generate learning signal
            learning_signal = {
                "timestamp": datetime.now().isoformat(),
                "type": "user_feedback",
                "insight": f"User provided {feedback.get('rating', 3)}/5 rating",
                "preference_impact": feedback.get("preference_updates", {}),
                "action_recommended": self._generate_action_recommendation(feedback)
            }
            
            memory["learning_signals"].append(learning_signal)
            
            # Keep only recent feedback (last 100 entries)
            if len(memory["user_feedback_history"]) > 100:
                memory["user_feedback_history"] = memory["user_feedback_history"][-100:]
            
            self.save_memory(memory)
            logger.info(f"User feedback processed: {feedback_entry}")
            
            return learning_signal
            
        except Exception as e:
            logger.error(f"Error processing user feedback: {e}")
            return {}

    def _generate_action_recommendation(self, feedback: Dict[str, Any]) -> str:
        """Generate action recommendation based on feedback"""
        rating = feedback.get("rating", 3)
        comment = feedback.get("comment", "").lower()
        
        if rating >= 4:
            return "Continue current strategy, user satisfaction high"
        elif rating <= 2:
            if "risk" in comment:
                return "Reduce position sizes and increase safety margins"
            elif "slow" in comment or "conservative" in comment:
                return "Consider slightly more aggressive strategies if risk tolerance allows"
            else:
                return "Review and adjust strategy based on user concerns"
        else:
            return "Monitor performance closely, minor adjustments may be needed"

    def update_strategy_preferences(self, performance_data: Dict[str, Any]):
        """Update strategy preferences based on performance patterns"""
        try:
            memory = self.load_memory()
            
            # Analyze performance patterns
            win_rate = performance_data.get("win_rate", 0.0)
            avg_return = performance_data.get("avg_return", 0.0)
            max_drawdown = performance_data.get("max_drawdown", 0.0)
            volatility = performance_data.get("volatility", 0.0)
            
            # Update preferences based on performance
            preferences = memory["preferences"]
            
            # Adjust risk tolerance based on drawdown
            if max_drawdown > preferences["max_drawdown"]:
                if preferences["risk_tolerance"] == "high":
                    preferences["risk_tolerance"] = "moderate"
                elif preferences["risk_tolerance"] == "moderate":
                    preferences["risk_tolerance"] = "low"
            
            # Adjust profit goals based on achieved returns
            if avg_return > preferences["profit_goal"] * 1.5:
                preferences["profit_goal"] = min(0.05, preferences["profit_goal"] * 1.1)
            elif avg_return < preferences["profit_goal"] * 0.5:
                preferences["profit_goal"] = max(0.01, preferences["profit_goal"] * 0.9)
            
            # Generate learning signal
            learning_signal = {
                "timestamp": datetime.now().isoformat(),
                "type": "performance_adaptation",
                "insight": f"Adjusted preferences based on performance: win_rate={win_rate:.2f}, drawdown={max_drawdown:.2f}",
                "preference_changes": {
                    "risk_tolerance": preferences["risk_tolerance"],
                    "profit_goal": preferences["profit_goal"]
                }
            }
            
            memory["learning_signals"].append(learning_signal)
            self.save_memory(memory)
            
            logger.info(f"Strategy preferences updated: {learning_signal}")
            
        except Exception as e:
            logger.error(f"Error updating strategy preferences: {e}")

    def generate_reward_signals(self) -> List[Dict[str, Any]]:
        """Generate reward signals for recent trades"""
        try:
            memory = self.load_memory()
            trades = self.load_executor_trades()
            reward_signals = []
            
            # Get recent trades (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_trades = []
            
            for trade in trades:
                try:
                    trade_time = datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00"))
                    if trade_time > cutoff_time:
                        recent_trades.append(trade)
                except:
                    continue
            
            # Generate reward signals for recent trades
            for trade in recent_trades:
                reward_score = self.calculate_trade_reward(trade, memory["preferences"])
                
                # Determine user feedback type based on reward score
                feedback_type = "positive" if reward_score > 0.7 else "negative" if reward_score < 0.3 else "neutral"
                
                reward_signal = {
                    "timestamp": datetime.now().isoformat(),
                    "trade_id": trade.get("trade_id", "unknown"),
                    "reward_score": reward_score,
                    "user_feedback": feedback_type,
                    "rationale": self._generate_reward_rationale(trade, reward_score),
                    "strategy": trade.get("strategy", "SPY_options_selling"),
                    "profit_loss": trade.get("profit_loss", 0),
                    "preference_alignment": self._calculate_preference_alignment(trade, memory["preferences"])
                }
                
                reward_signals.append(reward_signal)
                memory["reward_signals"].append(reward_signal)
            
            # Keep only recent reward signals (last 100)
            if len(memory["reward_signals"]) > 100:
                memory["reward_signals"] = memory["reward_signals"][-100:]
            
            self.save_memory(memory)
            
            # Share reward signals with other agents
            if reward_signals:
                self.update_shared_context({
                    "latest_reward_signals": reward_signals,
                    "current_preferences": memory["preferences"]
                })
            
            logger.info(f"Generated {len(reward_signals)} reward signals")
            return reward_signals
            
        except Exception as e:
            logger.error(f"Error generating reward signals: {e}")
            return []

    def _generate_reward_rationale(self, trade: Dict[str, Any], reward_score: float) -> str:
        """Generate human-readable rationale for reward score"""
        profit_loss = trade.get("profit_loss", 0)
        status = trade.get("status", "unknown")
        
        if reward_score > 0.7:
            return f"Excellent trade: ${profit_loss} profit with {status}. Aligns well with user preferences."
        elif reward_score > 0.5:
            return f"Good trade: ${profit_loss} outcome with {status}. Meets user expectations."
        elif reward_score > 0.3:
            return f"Neutral trade: ${profit_loss} outcome. Could be improved to better match preferences."
        else:
            return f"Poor trade: ${profit_loss} outcome with {status}. Does not align with user preferences."

    def _calculate_preference_alignment(self, trade: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate how well a trade aligns with user preferences"""
        try:
            alignment_score = 0.0
            
            # Check profit alignment
            profit_loss = float(str(trade.get("profit_loss", 0)).replace("$", "").replace(",", ""))
            if profit_loss > 0:
                alignment_score += 0.3
            
            # Check risk alignment
            risk_tolerance = preferences.get("risk_tolerance", "moderate")
            if risk_tolerance == "low" and trade.get("status") in ["TAKE_PROFIT", "EXPIRED_WORTHLESS"]:
                alignment_score += 0.3
            elif risk_tolerance == "high" and profit_loss > 50:
                alignment_score += 0.3
            
            # Check style alignment
            trade_style = preferences.get("trade_style", "conservative")
            if trade_style == "conservative" and trade.get("strategy", "").lower().find("sell") >= 0:
                alignment_score += 0.4
            
            return min(1.0, alignment_score)
            
        except Exception as e:
            logger.error(f"Error calculating preference alignment: {e}")
            return 0.5

    def run_learning_cycle(self):
        """Run one complete learning cycle"""
        logger.info("Starting reward model learning cycle...")
        
        try:
            # Generate reward signals for recent trades
            reward_signals = self.generate_reward_signals()
            
            # Load executor performance data for strategy adjustment
            trades = self.load_executor_trades()
            if len(trades) >= self.min_feedback_threshold:
                # Calculate aggregate performance metrics
                total_profit = sum(float(str(trade.get("profit_loss", 0)).replace("$", "").replace(",", "")) 
                                 for trade in trades[-20:])  # Last 20 trades
                win_rate = sum(1 for trade in trades[-20:] 
                             if float(str(trade.get("profit_loss", 0)).replace("$", "").replace(",", "")) > 0) / len(trades[-20:])
                
                performance_data = {
                    "total_profit": total_profit,
                    "win_rate": win_rate,
                    "avg_return": total_profit / len(trades[-20:]),
                    "max_drawdown": 0.1,  # Placeholder - would calculate from trade series
                    "volatility": 0.15    # Placeholder - would calculate from returns
                }
                
                # Update preferences based on performance
                self.update_strategy_preferences(performance_data)
            
            # Update model performance metrics
            self._update_model_performance(reward_signals)
            
        except Exception as e:
            logger.error(f"Error in learning cycle: {e}")

    def _update_model_performance(self, reward_signals: List[Dict[str, Any]]):
        """Update model performance metrics based on recent predictions"""
        try:
            if not reward_signals:
                return
            
            memory = self.load_memory()
            
            # Simple performance calculation based on reward accuracy
            high_reward_count = sum(1 for signal in reward_signals if signal["reward_score"] > 0.7)
            total_signals = len(reward_signals)
            
            if total_signals > 0:
                accuracy = high_reward_count / total_signals
                memory["model_performance"]["accuracy"] = accuracy
                memory["model_performance"]["precision"] = accuracy  # Simplified
                memory["model_performance"]["recall"] = accuracy     # Simplified
                memory["model_performance"]["f1_score"] = accuracy   # Simplified
            
            self.save_memory(memory)
            
        except Exception as e:
            logger.error(f"Error updating model performance: {e}")

    def run(self):
        """Main execution loop"""
        logger.info("RewardModelAgent starting main loop...")
        
        try:
            while True:
                self.run_learning_cycle()
                
                # Sleep for 30 seconds between cycles
                time.sleep(30)
                
        except KeyboardInterrupt:
            logger.info("RewardModelAgent stopped by user")
        except Exception as e:
            logger.error(f"RewardModelAgent crashed: {e}")

def main():
    """Main entry point"""
    agent = RewardModelAgent()
    agent.run()

if __name__ == "__main__":
    main()