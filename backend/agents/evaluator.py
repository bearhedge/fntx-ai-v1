#!/usr/bin/env python3
"""
FNTX AI EvaluatorAgent - Performance Monitoring and Analytics
Monitors all trade outcomes, generates weekly performance summaries, and provides insights
"""

import os
import json
import time
import logging
import statistics
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with dynamic path
from backend.core.utils.logging import get_agent_logger
from backend.core.utils.config import config
logger = get_agent_logger('EvaluatorAgent')

class EvaluatorAgent:
    """
    EvaluatorAgent monitors trade performance, identifies patterns, and generates insights
    for continuous improvement of the trading system.
    """
    
    def __init__(self):
        self.memory_file = config.get_memory_path("evaluator_memory.json")
        self.shared_context_file = config.get_memory_path("shared_context.json")
        self.executor_memory_file = config.get_memory_path("executor_memory.json")
        self.reward_memory_file = config.get_memory_path("reward_model_memory.json")
        
        # Performance tracking parameters
        self.performance_window = int(os.getenv("PERFORMANCE_WINDOW_DAYS", "7"))
        self.min_trades_for_analysis = int(os.getenv("MIN_TRADES_ANALYSIS", "5"))
        self.risk_alert_threshold = float(os.getenv("RISK_ALERT_THRESHOLD", "0.15"))
        
        logger.info("EvaluatorAgent initialized for performance monitoring")

    def load_memory(self) -> Dict[str, Any]:
        """Load evaluator memory from MCP-compatible JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
        
        # Default memory schema
        return {
            "agent_id": "EvaluatorAgent",
            "last_updated": datetime.now().isoformat(),
            "performance_summaries": [],
            "weekly_reports": [],
            "risk_alerts": [],
            "anomaly_detections": [],
            "improvement_suggestions": [],
            "metrics_history": {
                "total_profit": [],
                "win_rate": [],
                "sharpe_ratio": [],
                "max_drawdown": [],
                "avg_trade_duration": [],
                "volatility": []
            },
            "benchmarks": {
                "spy_return": 0.0,
                "risk_free_rate": 0.05,
                "target_win_rate": 0.70,
                "target_profit_factor": 1.5
            }
        }

    def save_memory(self, memory: Dict[str, Any]):
        """Save evaluator memory to MCP-compatible JSON file"""
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
        """Update shared context with performance insights"""
        try:
            context = self.load_shared_context()
            context.update(updates)
            context["last_updated"] = datetime.now().isoformat()
            
            with open(self.shared_context_file, 'w') as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating shared context: {e}")

    def load_executor_trades(self) -> List[Dict[str, Any]]:
        """Load executed trades from ExecutorAgent"""
        try:
            if os.path.exists(self.executor_memory_file):
                with open(self.executor_memory_file, 'r') as f:
                    executor_memory = json.load(f)
                    return executor_memory.get("executed_trades", [])
        except Exception as e:
            logger.error(f"Error loading executor trades: {e}")
        return []

    def load_reward_signals(self) -> List[Dict[str, Any]]:
        """Load reward signals from RewardModelAgent"""
        try:
            if os.path.exists(self.reward_memory_file):
                with open(self.reward_memory_file, 'r') as f:
                    reward_memory = json.load(f)
                    return reward_memory.get("reward_signals", [])
        except Exception as e:
            logger.error(f"Error loading reward signals: {e}")
        return []

    def calculate_performance_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        try:
            if not trades:
                return {}
            
            # Extract profit/loss values
            profits = []
            durations = []
            winning_trades = 0
            
            for trade in trades:
                try:
                    # Parse profit/loss
                    profit_str = str(trade.get("profit_loss", "0"))
                    profit = float(profit_str.replace("$", "").replace(",", ""))
                    profits.append(profit)
                    
                    if profit > 0:
                        winning_trades += 1
                    
                    # Parse trade duration (simplified - would need actual start/end times)
                    duration_str = trade.get("holding_period", "1h 0m")
                    if "h" in duration_str:
                        hours = int(duration_str.split("h")[0])
                        durations.append(hours)
                    
                except:
                    continue
            
            if not profits:
                return {}
            
            # Calculate metrics
            total_profit = sum(profits)
            win_rate = winning_trades / len(profits) if profits else 0
            avg_profit = statistics.mean(profits)
            profit_std = statistics.stdev(profits) if len(profits) > 1 else 0
            max_profit = max(profits)
            max_loss = min(profits)
            
            # Calculate Sharpe ratio (simplified)
            risk_free_rate = 0.05 / 252  # Daily risk-free rate
            sharpe_ratio = (avg_profit - risk_free_rate) / profit_std if profit_std > 0 else 0
            
            # Calculate max drawdown (simplified)
            cumulative = np.cumsum(profits)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = cumulative - running_max
            max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0
            
            # Profit factor
            winning_profits = sum(p for p in profits if p > 0)
            losing_profits = abs(sum(p for p in profits if p < 0))
            profit_factor = winning_profits / losing_profits if losing_profits > 0 else float('inf')
            
            metrics = {
                "total_profit": total_profit,
                "win_rate": win_rate,
                "avg_profit": avg_profit,
                "profit_std": profit_std,
                "max_profit": max_profit,
                "max_loss": max_loss,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "profit_factor": profit_factor,
                "total_trades": len(profits),
                "avg_duration": statistics.mean(durations) if durations else 0
            }
            
            logger.info(f"Performance metrics calculated: {len(profits)} trades, {win_rate:.2%} win rate")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}

    def detect_anomalies(self, trades: List[Dict[str, Any]], metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect anomalies in trading performance"""
        anomalies = []
        
        try:
            # Check for unusual loss streaks
            recent_trades = trades[-10:] if len(trades) >= 10 else trades
            consecutive_losses = 0
            max_consecutive_losses = 0
            
            for trade in recent_trades:
                profit = float(str(trade.get("profit_loss", "0")).replace("$", "").replace(",", ""))
                if profit < 0:
                    consecutive_losses += 1
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                else:
                    consecutive_losses = 0
            
            if max_consecutive_losses >= 5:
                anomalies.append({
                    "type": "consecutive_losses",
                    "severity": "high",
                    "description": f"Detected {max_consecutive_losses} consecutive losing trades",
                    "timestamp": datetime.now().isoformat(),
                    "action_required": "Review strategy parameters and market conditions"
                })
            
            # Check for unusual large losses
            if metrics.get("max_loss", 0) < -200:  # Loss greater than $200
                anomalies.append({
                    "type": "large_loss",
                    "severity": "medium",
                    "description": f"Large single trade loss: ${metrics['max_loss']:.2f}",
                    "timestamp": datetime.now().isoformat(),
                    "action_required": "Review position sizing and risk management"
                })
            
            # Check for declining win rate
            if metrics.get("win_rate", 0) < 0.5:
                anomalies.append({
                    "type": "low_win_rate",
                    "severity": "medium",
                    "description": f"Win rate below 50%: {metrics['win_rate']:.2%}",
                    "timestamp": datetime.now().isoformat(),
                    "action_required": "Analyze trade selection criteria and market conditions"
                })
            
            # Check for high drawdown
            if metrics.get("max_drawdown", 0) > self.risk_alert_threshold * 1000:  # Convert to dollar amount
                anomalies.append({
                    "type": "high_drawdown",
                    "severity": "high",
                    "description": f"Maximum drawdown exceeded: ${metrics['max_drawdown']:.2f}",
                    "timestamp": datetime.now().isoformat(),
                    "action_required": "Reduce position sizes and review risk parameters"
                })
            
            logger.info(f"Anomaly detection completed: {len(anomalies)} anomalies found")
            return anomalies
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return []

    def generate_improvement_suggestions(self, metrics: Dict[str, float], anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate actionable improvement suggestions"""
        suggestions = []
        
        try:
            # Win rate improvements
            if metrics.get("win_rate", 0) < 0.65:
                suggestions.append({
                    "category": "strategy",
                    "priority": "high",
                    "suggestion": "Consider tightening entry criteria for higher probability trades",
                    "rationale": f"Current win rate {metrics['win_rate']:.2%} below target 65%",
                    "implementation": "Increase minimum premium requirements or add technical filters"
                })
            
            # Risk management improvements
            if metrics.get("max_drawdown", 0) > 100:
                suggestions.append({
                    "category": "risk_management",
                    "priority": "high",
                    "suggestion": "Implement stricter position sizing rules",
                    "rationale": f"Maximum drawdown ${metrics['max_drawdown']:.2f} exceeds comfort zone",
                    "implementation": "Reduce position sizes by 25% until drawdown stabilizes"
                })
            
            # Profit optimization
            if metrics.get("profit_factor", 0) < 1.5:
                suggestions.append({
                    "category": "profit_optimization",
                    "priority": "medium",
                    "suggestion": "Review profit-taking strategies",
                    "rationale": f"Profit factor {metrics['profit_factor']:.2f} below target 1.5",
                    "implementation": "Consider taking profits earlier on winning trades"
                })
            
            # Trade frequency
            if metrics.get("total_trades", 0) < 10 and len(anomalies) == 0:
                suggestions.append({
                    "category": "opportunity",
                    "priority": "low",
                    "suggestion": "Consider increasing trade frequency",
                    "rationale": "Low trade count may limit profit potential",
                    "implementation": "Expand expiration date range or strike price criteria"
                })
            
            # Anomaly-based suggestions
            for anomaly in anomalies:
                if anomaly["type"] == "consecutive_losses":
                    suggestions.append({
                        "category": "strategy_adjustment",
                        "priority": "urgent",
                        "suggestion": "Temporarily reduce position sizes until performance improves",
                        "rationale": "Multiple consecutive losses indicate possible market regime change",
                        "implementation": "Halve position sizes for next 10 trades"
                    })
            
            logger.info(f"Generated {len(suggestions)} improvement suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {e}")
            return []

    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate comprehensive weekly performance report"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.performance_window)
            
            # Load trade data
            all_trades = self.load_executor_trades()
            reward_signals = self.load_reward_signals()
            
            # Filter trades for the reporting period
            weekly_trades = []
            for trade in all_trades:
                try:
                    trade_date = datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00"))
                    if start_date <= trade_date <= end_date:
                        weekly_trades.append(trade)
                except:
                    continue
            
            if len(weekly_trades) < self.min_trades_for_analysis:
                logger.warning(f"Insufficient trades for analysis: {len(weekly_trades)} < {self.min_trades_for_analysis}")
                return {}
            
            # Calculate performance metrics
            metrics = self.calculate_performance_metrics(weekly_trades)
            
            # Detect anomalies
            anomalies = self.detect_anomalies(weekly_trades, metrics)
            
            # Generate suggestions
            suggestions = self.generate_improvement_suggestions(metrics, anomalies)
            
            # Calculate reward model alignment
            reward_alignment = self._calculate_reward_alignment(weekly_trades, reward_signals)
            
            # Create weekly report
            weekly_report = {
                "report_id": f"week_{end_date.strftime('%Y%m%d')}",
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": self.performance_window
                },
                "performance_metrics": metrics,
                "trade_summary": {
                    "total_trades": len(weekly_trades),
                    "winning_trades": sum(1 for t in weekly_trades 
                                        if float(str(t.get("profit_loss", "0")).replace("$", "").replace(",", "")) > 0),
                    "losing_trades": sum(1 for t in weekly_trades 
                                       if float(str(t.get("profit_loss", "0")).replace("$", "").replace(",", "")) < 0),
                    "strategies_used": list(set(t.get("strategy", "unknown") for t in weekly_trades))
                },
                "anomalies": anomalies,
                "improvement_suggestions": suggestions,
                "reward_alignment": reward_alignment,
                "risk_assessment": self._assess_risk_levels(metrics),
                "next_week_recommendations": self._generate_next_week_recommendations(metrics, suggestions),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Weekly report generated: {len(weekly_trades)} trades analyzed")
            return weekly_report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return {}

    def _calculate_reward_alignment(self, trades: List[Dict[str, Any]], reward_signals: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate alignment between actual performance and reward model predictions"""
        try:
            if not trades or not reward_signals:
                return {"alignment_score": 0.0, "prediction_accuracy": 0.0}
            
            aligned_predictions = 0
            total_comparisons = 0
            
            for trade in trades:
                trade_id = trade.get("trade_id", "")
                actual_profit = float(str(trade.get("profit_loss", "0")).replace("$", "").replace(",", ""))
                
                # Find corresponding reward signal
                matching_signal = None
                for signal in reward_signals:
                    if signal.get("trade_id") == trade_id:
                        matching_signal = signal
                        break
                
                if matching_signal:
                    predicted_reward = matching_signal.get("reward_score", 0.5)
                    actual_success = 1.0 if actual_profit > 0 else 0.0
                    
                    # Check if prediction was directionally correct
                    if (predicted_reward > 0.5 and actual_success > 0.5) or \
                       (predicted_reward < 0.5 and actual_success < 0.5):
                        aligned_predictions += 1
                    
                    total_comparisons += 1
            
            alignment_score = aligned_predictions / total_comparisons if total_comparisons > 0 else 0.0
            
            return {
                "alignment_score": alignment_score,
                "prediction_accuracy": alignment_score,
                "total_comparisons": total_comparisons,
                "aligned_predictions": aligned_predictions
            }
            
        except Exception as e:
            logger.error(f"Error calculating reward alignment: {e}")
            return {"alignment_score": 0.0, "prediction_accuracy": 0.0}

    def _assess_risk_levels(self, metrics: Dict[str, float]) -> Dict[str, str]:
        """Assess current risk levels across different dimensions"""
        risk_assessment = {}
        
        try:
            # Drawdown risk
            max_drawdown = metrics.get("max_drawdown", 0)
            if max_drawdown > 200:
                risk_assessment["drawdown_risk"] = "high"
            elif max_drawdown > 100:
                risk_assessment["drawdown_risk"] = "medium"
            else:
                risk_assessment["drawdown_risk"] = "low"
            
            # Win rate risk
            win_rate = metrics.get("win_rate", 0)
            if win_rate < 0.5:
                risk_assessment["strategy_risk"] = "high"
            elif win_rate < 0.65:
                risk_assessment["strategy_risk"] = "medium"
            else:
                risk_assessment["strategy_risk"] = "low"
            
            # Volatility risk
            profit_std = metrics.get("profit_std", 0)
            if profit_std > 100:
                risk_assessment["volatility_risk"] = "high"
            elif profit_std > 50:
                risk_assessment["volatility_risk"] = "medium"
            else:
                risk_assessment["volatility_risk"] = "low"
            
            # Overall risk
            high_risks = sum(1 for risk in risk_assessment.values() if risk == "high")
            if high_risks >= 2:
                risk_assessment["overall_risk"] = "high"
            elif high_risks == 1:
                risk_assessment["overall_risk"] = "medium"
            else:
                risk_assessment["overall_risk"] = "low"
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error assessing risk levels: {e}")
            return {"overall_risk": "unknown"}

    def _generate_next_week_recommendations(self, metrics: Dict[str, float], suggestions: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommendations for the upcoming week"""
        recommendations = []
        
        try:
            # Priority-based recommendations
            urgent_suggestions = [s for s in suggestions if s.get("priority") == "urgent"]
            if urgent_suggestions:
                recommendations.append("URGENT: Address consecutive losses by reducing position sizes")
            
            high_priority = [s for s in suggestions if s.get("priority") == "high"]
            if high_priority:
                recommendations.append("Focus on improving strategy selection criteria")
                recommendations.append("Review and tighten risk management parameters")
            
            # Performance-based recommendations
            win_rate = metrics.get("win_rate", 0)
            if win_rate < 0.6:
                recommendations.append("Prioritize higher-probability trade setups this week")
            
            profit_factor = metrics.get("profit_factor", 0)
            if profit_factor < 1.5:
                recommendations.append("Consider earlier profit-taking on winning positions")
            
            # General recommendations
            recommendations.append("Continue monitoring VIX levels for optimal entry timing")
            recommendations.append("Maintain disciplined approach to 0DTE option selling")
            
            return recommendations[:5]  # Limit to top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error generating next week recommendations: {e}")
            return ["Continue current trading approach with increased monitoring"]

    def run_evaluation_cycle(self):
        """Run one complete evaluation cycle"""
        logger.info("Starting evaluator analysis cycle...")
        
        try:
            memory = self.load_memory()
            
            # Generate weekly report
            weekly_report = self.generate_weekly_report()
            
            if weekly_report:
                # Save report to memory
                memory["weekly_reports"].append(weekly_report)
                
                # Keep only last 8 weeks of reports
                if len(memory["weekly_reports"]) > 8:
                    memory["weekly_reports"] = memory["weekly_reports"][-8:]
                
                # Update metrics history
                if "performance_metrics" in weekly_report:
                    metrics = weekly_report["performance_metrics"]
                    for key, value in metrics.items():
                        if key in memory["metrics_history"]:
                            memory["metrics_history"][key].append({
                                "timestamp": datetime.now().isoformat(),
                                "value": value
                            })
                            # Keep last 30 entries
                            if len(memory["metrics_history"][key]) > 30:
                                memory["metrics_history"][key] = memory["metrics_history"][key][-30:]
                
                # Update shared context with insights
                self.update_shared_context({
                    "latest_evaluation": {
                        "timestamp": datetime.now().isoformat(),
                        "performance_summary": weekly_report.get("performance_metrics", {}),
                        "risk_level": weekly_report.get("risk_assessment", {}).get("overall_risk", "unknown"),
                        "recommendations": weekly_report.get("next_week_recommendations", []),
                        "anomalies_detected": len(weekly_report.get("anomalies", []))
                    }
                })
                
                logger.info(f"Evaluation cycle completed: {weekly_report.get('trade_summary', {}).get('total_trades', 0)} trades analyzed")
            
            self.save_memory(memory)
            
        except Exception as e:
            logger.error(f"Error in evaluation cycle: {e}")

    def run(self):
        """Main execution loop"""
        logger.info("EvaluatorAgent starting main loop...")
        
        try:
            while True:
                self.run_evaluation_cycle()
                
                # Sleep for 6 hours between evaluations
                time.sleep(6 * 3600)
                
        except KeyboardInterrupt:
            logger.info("EvaluatorAgent stopped by user")
        except Exception as e:
            logger.error(f"EvaluatorAgent crashed: {e}")

def main():
    """Main entry point"""
    agent = EvaluatorAgent()
    agent.run()

if __name__ == "__main__":
    main()