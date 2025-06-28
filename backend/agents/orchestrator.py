#!/usr/bin/env python3
"""
FNTX AI Agent Orchestrator - Coordinates all 5 agents for end-to-end trade execution
Manages the complete trade lifecycle from user intent to execution and evaluation
"""

import os
import json
import time
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dotenv import load_dotenv

# Import all agents
from .strategic_planner import StrategicPlannerAgent
from .executor import ExecutorAgent
from .evaluator import EvaluatorAgent
from .environment_watcher import EnvironmentWatcherAgent
from .reward_model import RewardModelAgent

# Load environment variables
load_dotenv()

# Configure logging with dynamic path
from backend.utils.logging import get_agent_logger
logger = get_agent_logger('Orchestrator')

class TradePhase(Enum):
    """Trade execution phases"""
    INITIATED = "initiated"
    ENVIRONMENT_ANALYSIS = "environment_analysis"
    STRATEGIC_PLANNING = "strategic_planning"
    REWARD_OPTIMIZATION = "reward_optimization"
    TACTICAL_EXECUTION = "tactical_execution"
    EVALUATION = "evaluation"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentStatus(Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"

class FNTXOrchestrator:
    """
    Central orchestrator that coordinates all 5 agents for complete trade lifecycle management.
    Provides transparent logging and real-time status updates for UI consumption.
    """
    
    def __init__(self):
        # File paths
        self.trade_journey_file = "backend/agents/memory/trade_journey.json"
        self.shared_context_file = "backend/agents/memory/shared_context.json"
        self.orchestrator_memory_file = "backend/agents/memory/orchestrator_memory.json"
        
        # Initialize agents
        self.strategic_planner = StrategicPlannerAgent()
        self.executor = ExecutorAgent()
        self.evaluator = EvaluatorAgent()
        self.environment_watcher = EnvironmentWatcherAgent()
        self.reward_model = RewardModelAgent()
        
        # Trade execution state
        self.current_trade_id = None
        self.current_phase = TradePhase.INITIATED
        self.agent_statuses = {
            "environment_watcher": AgentStatus.PENDING,
            "strategic_planner": AgentStatus.PENDING,
            "reward_model": AgentStatus.PENDING,
            "executor": AgentStatus.PENDING,
            "evaluator": AgentStatus.PENDING
        }
        
        # Configuration
        self.max_execution_time = int(os.getenv("MAX_TRADE_EXECUTION_TIME", "300"))  # 5 minutes
        self.enable_live_trading = os.getenv("TRADING_MODE", "paper").lower() == "live"
        
        logger.info("FNTX Orchestrator initialized with all 5 agents")

    def load_orchestrator_memory(self) -> Dict[str, Any]:
        """Load orchestrator execution history"""
        try:
            if os.path.exists(self.orchestrator_memory_file):
                with open(self.orchestrator_memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading orchestrator memory: {e}")
        
        return {
            "orchestrator_id": "FNTXOrchestrator",
            "last_updated": datetime.now().isoformat(),
            "completed_trades": [],
            "failed_trades": [],
            "performance_stats": {
                "total_orchestrations": 0,
                "successful_trades": 0,
                "failed_trades": 0,
                "avg_execution_time": 0.0
            },
            "agent_performance": {
                "environment_watcher": {"success_rate": 1.0, "avg_time": 5.0},
                "strategic_planner": {"success_rate": 1.0, "avg_time": 10.0},
                "reward_model": {"success_rate": 1.0, "avg_time": 3.0},
                "executor": {"success_rate": 1.0, "avg_time": 15.0},
                "evaluator": {"success_rate": 1.0, "avg_time": 8.0}
            }
        }

    def save_orchestrator_memory(self, memory: Dict[str, Any]):
        """Save orchestrator execution history"""
        try:
            memory["last_updated"] = datetime.now().isoformat()
            os.makedirs(os.path.dirname(self.orchestrator_memory_file), exist_ok=True)
            with open(self.orchestrator_memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving orchestrator memory: {e}")

    def create_trade_journey_entry(self, user_request: str) -> str:
        """Create new trade journey and return trade ID"""
        trade_id = f"FNTX_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_trade_id = trade_id
        
        journey = {
            "trade_id": trade_id,
            "user_request": user_request,
            "initiated_at": datetime.now().isoformat(),
            "current_phase": TradePhase.INITIATED.value,
            "steps": [],
            "risk_assessment": {
                "overall_risk": "unknown",
                "confidence_level": 0.0,
                "max_exposure": 0.0,
                "stop_loss_level": 0.0
            },
            "final_outcome": None,
            "execution_time": 0.0,
            "errors": []
        }
        
        # Save initial journey
        self._save_trade_journey(journey)
        logger.info(f"Trade journey created: {trade_id}")
        return trade_id

    def _save_trade_journey(self, journey: Dict[str, Any]):
        """Save trade journey to file for UI consumption"""
        try:
            os.makedirs(os.path.dirname(self.trade_journey_file), exist_ok=True)
            with open(self.trade_journey_file, 'w') as f:
                json.dump(journey, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trade journey: {e}")

    def _load_trade_journey(self) -> Dict[str, Any]:
        """Load current trade journey"""
        try:
            if os.path.exists(self.trade_journey_file):
                with open(self.trade_journey_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading trade journey: {e}")
        return {}

    def _add_journey_step(self, agent_name: str, action: str, rationale: str, 
                         status: AgentStatus, confidence: float = 0.0, 
                         risk_info: Dict[str, Any] = None, error_msg: str = None):
        """Add a step to the trade journey log"""
        try:
            journey = self._load_trade_journey()
            
            step = {
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "action": action,
                "rationale": rationale,
                "status": status.value,
                "confidence_level": confidence,
                "risk_assessment": risk_info or {},
                "execution_time": 0.0,
                "error_message": error_msg
            }
            
            journey["steps"].append(step)
            journey["current_phase"] = self.current_phase.value
            
            # Update overall risk assessment
            if risk_info:
                journey["risk_assessment"].update(risk_info)
            
            self._save_trade_journey(journey)
            logger.info(f"Journey step added: {agent_name} - {action} ({status.value})")
            
        except Exception as e:
            logger.error(f"Error adding journey step: {e}")

    def _update_agent_status(self, agent_name: str, status: AgentStatus):
        """Update agent execution status"""
        self.agent_statuses[agent_name] = status
        logger.debug(f"Agent status updated: {agent_name} -> {status.value}")

    async def execute_environment_analysis(self) -> Tuple[bool, Dict[str, Any]]:
        """Execute environment analysis phase"""
        self.current_phase = TradePhase.ENVIRONMENT_ANALYSIS
        self._update_agent_status("environment_watcher", AgentStatus.RUNNING)
        
        try:
            self._add_journey_step(
                "EnvironmentWatcherAgent",
                "Analyzing market conditions and regime",
                "Gathering current market data, VIX levels, and regime indicators to assess trading environment",
                AgentStatus.RUNNING,
                confidence=0.9
            )
            
            # Run environment analysis
            start_time = time.time()
            self.environment_watcher.run_monitoring_cycle()
            execution_time = time.time() - start_time
            
            # Get results from shared context
            shared_context = self.environment_watcher.load_shared_context()
            market_regime = shared_context.get("market_regime", "unknown")
            vix_level = shared_context.get("vix_level", 0)
            spy_price = shared_context.get("spy_price", 0)
            alert_level = shared_context.get("environment_alert_level", "unknown")
            
            # Assess if conditions are favorable
            conditions_favorable = (
                market_regime in ["favorable_for_selling", "neutral"] and 
                vix_level < 25 and 
                alert_level in ["low", "medium"]
            )
            
            risk_info = {
                "market_regime": market_regime,
                "vix_level": vix_level,
                "alert_level": alert_level,
                "conditions_favorable": conditions_favorable
            }
            
            rationale = f"Market analysis complete: {market_regime} regime, VIX at {vix_level}, SPY at ${spy_price}. "
            rationale += "Favorable conditions for options selling." if conditions_favorable else "Suboptimal conditions detected."
            
            self._add_journey_step(
                "EnvironmentWatcherAgent",
                "Market analysis completed",
                rationale,
                AgentStatus.COMPLETED,
                confidence=0.85,
                risk_info=risk_info
            )
            
            self._update_agent_status("environment_watcher", AgentStatus.COMPLETED)
            logger.info(f"Environment analysis completed in {execution_time:.2f}s")
            
            return conditions_favorable, risk_info
            
        except Exception as e:
            error_msg = f"Environment analysis failed: {str(e)}"
            logger.error(error_msg)
            
            self._add_journey_step(
                "EnvironmentWatcherAgent",
                "Market analysis failed",
                "Failed to analyze market conditions",
                AgentStatus.ERROR,
                error_msg=error_msg
            )
            
            self._update_agent_status("environment_watcher", AgentStatus.ERROR)
            return False, {"error": error_msg}

    async def execute_strategic_planning(self, user_request: str, market_context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Execute strategic planning phase"""
        self.current_phase = TradePhase.STRATEGIC_PLANNING
        self._update_agent_status("strategic_planner", AgentStatus.RUNNING)
        
        try:
            self._add_journey_step(
                "StrategicPlannerAgent",
                "Generating trading strategy",
                f"Analyzing user request: '{user_request}' and current market conditions to formulate optimal strategy",
                AgentStatus.RUNNING,
                confidence=0.8
            )
            
            start_time = time.time()
            
            # Generate strategy based on user request and market context
            strategy_result = self.strategic_planner.generate_strategy({
                "user_request": user_request,
                "market_context": market_context,
                "timestamp": datetime.now().isoformat()
            })
            
            execution_time = time.time() - start_time
            
            if strategy_result and strategy_result.get("strategy"):
                strategy = strategy_result["strategy"]
                confidence = strategy_result.get("confidence", 0.7)
                
                risk_info = {
                    "strategy_type": strategy.get("type", "unknown"),
                    "max_risk": strategy.get("max_risk", 0),
                    "expected_return": strategy.get("expected_return", 0),
                    "win_probability": strategy.get("win_probability", 0)
                }
                
                rationale = f"Strategy formulated: {strategy.get('type', 'SPY options')} with "
                rationale += f"{confidence:.0%} confidence. Expected return: {strategy.get('expected_return', 0):.1%}, "
                rationale += f"Max risk: ${strategy.get('max_risk', 0):.0f}"
                
                self._add_journey_step(
                    "StrategicPlannerAgent",
                    "Strategy generated successfully",
                    rationale,
                    AgentStatus.COMPLETED,
                    confidence=confidence,
                    risk_info=risk_info
                )
                
                self._update_agent_status("strategic_planner", AgentStatus.COMPLETED)
                logger.info(f"Strategic planning completed in {execution_time:.2f}s")
                
                return True, strategy_result
            else:
                raise Exception("No valid strategy generated")
                
        except Exception as e:
            error_msg = f"Strategic planning failed: {str(e)}"
            logger.error(error_msg)
            
            self._add_journey_step(
                "StrategicPlannerAgent",
                "Strategy generation failed",
                "Unable to generate viable trading strategy",
                AgentStatus.ERROR,
                error_msg=error_msg
            )
            
            self._update_agent_status("strategic_planner", AgentStatus.ERROR)
            return False, {"error": error_msg}

    async def execute_reward_optimization(self, strategy: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Execute reward model optimization phase"""
        self.current_phase = TradePhase.REWARD_OPTIMIZATION
        self._update_agent_status("reward_model", AgentStatus.RUNNING)
        
        try:
            self._add_journey_step(
                "RewardModelAgent",
                "Optimizing strategy for user preferences",
                "Analyzing strategy against learned user preferences and historical performance patterns",
                AgentStatus.RUNNING,
                confidence=0.75
            )
            
            start_time = time.time()
            
            # Load user preferences and optimize strategy
            memory = self.reward_model.load_memory()
            preferences = memory.get("preferences", {})
            
            # Run learning cycle to get latest reward signals
            self.reward_model.run_learning_cycle()
            
            # Calculate strategy alignment with preferences
            alignment_score = self._calculate_strategy_alignment(strategy, preferences)
            
            execution_time = time.time() - start_time
            
            risk_info = {
                "preference_alignment": alignment_score,
                "risk_tolerance": preferences.get("risk_tolerance", "moderate"),
                "target_win_rate": preferences.get("win_rate_preference", 0.7)
            }
            
            if alignment_score > 0.6:
                rationale = f"Strategy well-aligned with user preferences (score: {alignment_score:.2f}). "
                rationale += f"Risk tolerance: {preferences.get('risk_tolerance', 'moderate')}, "
                rationale += f"Target win rate: {preferences.get('win_rate_preference', 0.7):.0%}"
                
                self._add_journey_step(
                    "RewardModelAgent",
                    "Strategy optimization completed",
                    rationale,
                    AgentStatus.COMPLETED,
                    confidence=alignment_score,
                    risk_info=risk_info
                )
                
                self._update_agent_status("reward_model", AgentStatus.COMPLETED)
                logger.info(f"Reward optimization completed in {execution_time:.2f}s")
                
                return True, {"alignment_score": alignment_score, "preferences": preferences}
            else:
                raise Exception(f"Strategy alignment too low: {alignment_score:.2f}")
                
        except Exception as e:
            error_msg = f"Reward optimization failed: {str(e)}"
            logger.error(error_msg)
            
            self._add_journey_step(
                "RewardModelAgent", 
                "Strategy optimization failed",
                "Unable to align strategy with user preferences",
                AgentStatus.ERROR,
                error_msg=error_msg
            )
            
            self._update_agent_status("reward_model", AgentStatus.ERROR)
            return False, {"error": error_msg}

    def _calculate_strategy_alignment(self, strategy: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate how well strategy aligns with user preferences"""
        try:
            alignment_score = 0.0
            
            # Risk tolerance alignment
            strategy_risk = strategy.get("max_risk", 100)
            risk_tolerance = preferences.get("risk_tolerance", "moderate")
            
            if risk_tolerance == "low" and strategy_risk < 150:
                alignment_score += 0.3
            elif risk_tolerance == "moderate" and strategy_risk < 300:
                alignment_score += 0.3
            elif risk_tolerance == "high":
                alignment_score += 0.3
            
            # Win rate alignment
            strategy_win_prob = strategy.get("win_probability", 0.7)
            target_win_rate = preferences.get("win_rate_preference", 0.7)
            
            if abs(strategy_win_prob - target_win_rate) < 0.1:
                alignment_score += 0.4
            elif abs(strategy_win_prob - target_win_rate) < 0.2:
                alignment_score += 0.2
            
            # Profit goal alignment
            strategy_return = strategy.get("expected_return", 0.02)
            profit_goal = preferences.get("profit_goal", 0.02)
            
            if abs(strategy_return - profit_goal) < 0.01:
                alignment_score += 0.3
            elif abs(strategy_return - profit_goal) < 0.02:
                alignment_score += 0.15
            
            return min(1.0, alignment_score)
            
        except Exception as e:
            logger.error(f"Error calculating strategy alignment: {e}")
            return 0.5

    async def execute_tactical_execution(self, strategy: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Execute tactical trade execution phase"""
        self.current_phase = TradePhase.TACTICAL_EXECUTION
        self._update_agent_status("executor", AgentStatus.RUNNING)
        
        try:
            self._add_journey_step(
                "ExecutorAgent",
                "Executing trade strategy",
                f"Placing {strategy.get('type', 'SPY options')} order with risk management controls",
                AgentStatus.RUNNING,
                confidence=0.8
            )
            
            start_time = time.time()
            
            # Execute the trade
            execution_result = self.executor.execute_trade_instruction({
                "strategy": strategy,
                "trade_id": self.current_trade_id,
                "timestamp": datetime.now().isoformat()
            })
            
            execution_time = time.time() - start_time
            
            if execution_result and execution_result.get("success"):
                trade_details = execution_result.get("trade_details", {})
                
                risk_info = {
                    "position_size": trade_details.get("quantity", 0),
                    "entry_price": trade_details.get("limit_price", 0),
                    "max_loss": trade_details.get("max_loss", 0),
                    "stop_loss": trade_details.get("stop_loss", 0),
                    "take_profit": trade_details.get("take_profit", 0)
                }
                
                rationale = f"Trade executed successfully: {trade_details.get('symbol', 'SPY')} "
                rationale += f"{trade_details.get('option_type', 'PUT')} {trade_details.get('strike', 0)} "
                rationale += f"@ ${trade_details.get('limit_price', 0):.2f}. "
                rationale += f"Position size: {trade_details.get('quantity', 1)} contract(s)"
                
                self._add_journey_step(
                    "ExecutorAgent",
                    "Trade executed successfully", 
                    rationale,
                    AgentStatus.COMPLETED,
                    confidence=0.9,
                    risk_info=risk_info
                )
                
                self._update_agent_status("executor", AgentStatus.COMPLETED)
                logger.info(f"Tactical execution completed in {execution_time:.2f}s")
                
                return True, execution_result
            else:
                raise Exception(execution_result.get("error", "Trade execution failed"))
                
        except Exception as e:
            error_msg = f"Tactical execution failed: {str(e)}"
            logger.error(error_msg)
            
            self._add_journey_step(
                "ExecutorAgent",
                "Trade execution failed",
                "Unable to execute trade order",
                AgentStatus.ERROR,
                error_msg=error_msg
            )
            
            self._update_agent_status("executor", AgentStatus.ERROR)
            return False, {"error": error_msg}

    async def execute_evaluation(self, execution_result: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Execute post-trade evaluation phase"""
        self.current_phase = TradePhase.EVALUATION
        self._update_agent_status("evaluator", AgentStatus.RUNNING)
        
        try:
            self._add_journey_step(
                "EvaluatorAgent",
                "Evaluating trade outcome",
                "Analyzing trade performance and generating insights for continuous improvement",
                AgentStatus.RUNNING,
                confidence=0.9
            )
            
            start_time = time.time()
            
            # Run evaluation cycle
            self.evaluator.run_evaluation_cycle()
            
            # Generate immediate trade assessment
            trade_assessment = self._generate_immediate_assessment(execution_result)
            
            execution_time = time.time() - start_time
            
            risk_info = {
                "trade_outcome": trade_assessment.get("outcome", "pending"),
                "performance_score": trade_assessment.get("score", 0.0),
                "risk_realization": trade_assessment.get("risk_realization", "unknown")
            }
            
            rationale = f"Trade evaluation completed. Outcome: {trade_assessment.get('outcome', 'pending')}. "
            rationale += f"Performance score: {trade_assessment.get('score', 0.0):.2f}/1.0. "
            rationale += f"Insights logged for future strategy optimization."
            
            self._add_journey_step(
                "EvaluatorAgent",
                "Trade evaluation completed",
                rationale,
                AgentStatus.COMPLETED,
                confidence=0.85,
                risk_info=risk_info
            )
            
            self._update_agent_status("evaluator", AgentStatus.COMPLETED)
            logger.info(f"Evaluation completed in {execution_time:.2f}s")
            
            return True, trade_assessment
            
        except Exception as e:
            error_msg = f"Evaluation failed: {str(e)}"
            logger.error(error_msg)
            
            self._add_journey_step(
                "EvaluatorAgent",
                "Trade evaluation failed", 
                "Unable to complete trade evaluation",
                AgentStatus.ERROR,
                error_msg=error_msg
            )
            
            self._update_agent_status("evaluator", AgentStatus.ERROR)
            return False, {"error": error_msg}

    def _generate_immediate_assessment(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate immediate trade assessment"""
        try:
            trade_details = execution_result.get("trade_details", {})
            
            # For immediate assessment, we evaluate the execution quality
            assessment = {
                "outcome": "executed_successfully",
                "score": 0.8,  # Base score for successful execution
                "risk_realization": "within_parameters",
                "execution_quality": "good",
                "timestamp": datetime.now().isoformat()
            }
            
            # Adjust score based on execution details
            if trade_details.get("execution_price"):
                # If we got a good fill price, increase score
                limit_price = trade_details.get("limit_price", 0)
                execution_price = trade_details.get("execution_price", 0)
                
                if execution_price >= limit_price * 0.95:  # Got 95%+ of target price
                    assessment["score"] = min(1.0, assessment["score"] + 0.1)
                    assessment["execution_quality"] = "excellent"
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error generating immediate assessment: {e}")
            return {"outcome": "assessment_pending", "score": 0.5}

    async def orchestrate_trade(self, user_request: str) -> Dict[str, Any]:
        """Main orchestration method - coordinates all agents for complete trade lifecycle"""
        logger.info(f"Starting trade orchestration for request: {user_request}")
        start_time = time.time()
        
        try:
            # Create trade journey
            trade_id = self.create_trade_journey_entry(user_request)
            
            # Phase 1: Environment Analysis
            env_success, env_result = await self.execute_environment_analysis()
            if not env_success:
                self.current_phase = TradePhase.FAILED
                return self._complete_trade_journey(False, "Environment analysis failed", start_time)
            
            # Phase 2: Strategic Planning
            strategy_success, strategy_result = await self.execute_strategic_planning(user_request, env_result)
            if not strategy_success:
                self.current_phase = TradePhase.FAILED
                return self._complete_trade_journey(False, "Strategic planning failed", start_time)
            
            # Phase 3: Reward Optimization
            reward_success, reward_result = await self.execute_reward_optimization(strategy_result)
            if not reward_success:
                self.current_phase = TradePhase.FAILED
                return self._complete_trade_journey(False, "Reward optimization failed", start_time)
            
            # Phase 4: Tactical Execution
            exec_success, exec_result = await self.execute_tactical_execution(strategy_result)
            if not exec_success:
                self.current_phase = TradePhase.FAILED
                return self._complete_trade_journey(False, "Tactical execution failed", start_time)
            
            # Phase 5: Evaluation
            eval_success, eval_result = await self.execute_evaluation(exec_result)
            if not eval_success:
                logger.warning("Evaluation failed, but trade was successful")
                # Don't fail the whole trade if just evaluation fails
            
            # Complete successfully
            self.current_phase = TradePhase.COMPLETED
            return self._complete_trade_journey(True, "Trade orchestration completed successfully", start_time)
            
        except Exception as e:
            error_msg = f"Orchestration failed: {str(e)}"
            logger.error(error_msg)
            self.current_phase = TradePhase.FAILED
            return self._complete_trade_journey(False, error_msg, start_time)

    def _complete_trade_journey(self, success: bool, message: str, start_time: float) -> Dict[str, Any]:
        """Complete the trade journey and save final results"""
        try:
            journey = self._load_trade_journey()
            execution_time = time.time() - start_time
            
            journey["current_phase"] = self.current_phase.value
            journey["execution_time"] = execution_time
            journey["final_outcome"] = {
                "success": success,
                "message": message,
                "completed_at": datetime.now().isoformat(),
                "total_steps": len(journey.get("steps", [])),
                "agent_statuses": {k: v.value for k, v in self.agent_statuses.items()}
            }
            
            self._save_trade_journey(journey)
            
            # Update orchestrator memory
            memory = self.load_orchestrator_memory()
            memory["performance_stats"]["total_orchestrations"] += 1
            
            if success:
                memory["performance_stats"]["successful_trades"] += 1
                memory["completed_trades"].append({
                    "trade_id": self.current_trade_id,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": execution_time
                })
            else:
                memory["performance_stats"]["failed_trades"] += 1
                memory["failed_trades"].append({
                    "trade_id": self.current_trade_id,
                    "timestamp": datetime.now().isoformat(),
                    "error": message
                })
            
            # Update average execution time
            total_trades = memory["performance_stats"]["total_orchestrations"]
            if total_trades > 0:
                current_avg = memory["performance_stats"]["avg_execution_time"]
                memory["performance_stats"]["avg_execution_time"] = (
                    (current_avg * (total_trades - 1) + execution_time) / total_trades
                )
            
            self.save_orchestrator_memory(memory)
            
            logger.info(f"Trade journey completed: {success} in {execution_time:.2f}s")
            return journey
            
        except Exception as e:
            logger.error(f"Error completing trade journey: {e}")
            return {"error": str(e)}

    def get_trade_status(self, trade_id: str = None) -> Dict[str, Any]:
        """Get current trade status for UI consumption"""
        try:
            journey = self._load_trade_journey()
            
            if trade_id and journey.get("trade_id") != trade_id:
                return {"error": "Trade ID not found"}
            
            return {
                "trade_id": journey.get("trade_id"),
                "current_phase": journey.get("current_phase"),
                "agent_statuses": {k: v.value for k, v in self.agent_statuses.items()},
                "steps_completed": len(journey.get("steps", [])),
                "execution_time": journey.get("execution_time", 0),
                "final_outcome": journey.get("final_outcome"),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting trade status: {e}")
            return {"error": str(e)}

    def start_background_monitoring(self):
        """Start background monitoring of environment and evaluation"""
        def background_monitor():
            while True:
                try:
                    # Run environment monitoring every 5 minutes
                    self.environment_watcher.run_monitoring_cycle()
                    
                    # Run evaluation every hour
                    if datetime.now().minute == 0:
                        self.evaluator.run_evaluation_cycle()
                    
                    time.sleep(300)  # 5 minutes
                    
                except Exception as e:
                    logger.error(f"Background monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()
        logger.info("Background monitoring started")