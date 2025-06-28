#!/usr/bin/env python3
"""
FNTX AI StrategicPlannerAgent - Strategy Formulation and Planning
Generates optimal trading strategies based on market conditions and user preferences
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
from backend.utils.logging import get_agent_logger
logger = get_agent_logger('StrategicPlannerAgent')

class StrategicPlannerAgent:
    """
    StrategicPlannerAgent formulates optimal trading strategies based on market analysis,
    user preferences, and risk parameters.
    """
    
    def __init__(self):
        self.memory_file = "backend/agents/memory/strategic_planner_memory.json"
        self.shared_context_file = "backend/agents/memory/shared_context.json"
        
        # Strategy parameters
        self.default_strategies = {
            "SPY_0DTE_Put_Selling": {
                "type": "SPY_0DTE_Put_Selling",
                "description": "Sell SPY PUT options expiring same day",
                "risk_level": "medium",
                "win_probability": 0.75,
                "expected_return": 0.02,
                "max_risk": 200,
                "optimal_conditions": ["low_volatility", "bullish_trend"]
            },
            "SPY_1DTE_Put_Selling": {
                "type": "SPY_1DTE_Put_Selling", 
                "description": "Sell SPY PUT options expiring next day",
                "risk_level": "low",
                "win_probability": 0.80,
                "expected_return": 0.015,
                "max_risk": 150,
                "optimal_conditions": ["low_volatility", "neutral_trend"]
            },
            "SPY_Weekly_Put_Selling": {
                "type": "SPY_Weekly_Put_Selling",
                "description": "Sell SPY PUT options expiring within a week",
                "risk_level": "low",
                "win_probability": 0.85,
                "expected_return": 0.025,
                "max_risk": 300,
                "optimal_conditions": ["stable_market", "low_volatility"]
            }
        }
        
        logger.info("StrategicPlannerAgent initialized")

    def load_memory(self) -> Dict[str, Any]:
        """Load strategic planner memory from MCP-compatible JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
        
        # Default memory schema
        return {
            "agent_id": "StrategicPlannerAgent",
            "last_updated": datetime.now().isoformat(),
            "strategies_generated": [],
            "successful_strategies": [],
            "failed_strategies": [],
            "strategy_performance": {},
            "market_adaptations": [],
            "user_preference_adjustments": []
        }

    def save_memory(self, memory: Dict[str, Any]):
        """Save strategic planner memory to MCP-compatible JSON file"""
        try:
            memory["last_updated"] = datetime.now().isoformat()
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def load_shared_context(self) -> Dict[str, Any]:
        """Load shared context for market data and inter-agent communication"""
        try:
            if os.path.exists(self.shared_context_file):
                with open(self.shared_context_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading shared context: {e}")
        return {}

    def update_shared_context(self, updates: Dict[str, Any]):
        """Update shared context with strategy recommendations"""
        try:
            context = self.load_shared_context()
            context.update(updates)
            context["last_updated"] = datetime.now().isoformat()
            
            with open(self.shared_context_file, 'w') as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating shared context: {e}")

    def analyze_market_conditions(self, shared_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current market conditions for strategy formulation"""
        try:
            market_analysis = {
                "vix_level": shared_context.get("vix_level", 15.0),
                "spy_price": shared_context.get("spy_price", 450.0),
                "market_regime": shared_context.get("market_regime", "neutral"),
                "trend_direction": "bullish",  # Would be calculated from price data
                "volatility_environment": "low",
                "support_levels": [445.0, 442.0, 440.0],
                "resistance_levels": [455.0, 458.0, 460.0],
                "optimal_strike_range": (435.0, 445.0),
                "recommended_dte": 0  # 0DTE preferred in low vol
            }
            
            # Adjust analysis based on VIX
            if market_analysis["vix_level"] < 12:
                market_analysis["volatility_environment"] = "very_low"
                market_analysis["recommended_dte"] = 0
            elif market_analysis["vix_level"] > 20:
                market_analysis["volatility_environment"] = "elevated"
                market_analysis["recommended_dte"] = 1
            
            # Determine trend from market regime
            regime = market_analysis["market_regime"]
            if regime in ["favorable_for_selling", "bullish"]:
                market_analysis["trend_direction"] = "bullish"
            elif regime in ["risk_off", "bearish"]:
                market_analysis["trend_direction"] = "bearish"
            else:
                market_analysis["trend_direction"] = "neutral"
            
            logger.info(f"Market analysis: {regime} regime, VIX {market_analysis['vix_level']}")
            return market_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return {}

    def evaluate_strategy_suitability(self, strategy: Dict[str, Any], market_conditions: Dict[str, Any]) -> float:
        """Evaluate how suitable a strategy is for current market conditions"""
        try:
            suitability_score = 0.0
            
            # Check optimal conditions
            optimal_conditions = strategy.get("optimal_conditions", [])
            market_regime = market_conditions.get("market_regime", "neutral")
            volatility_env = market_conditions.get("volatility_environment", "normal")
            trend = market_conditions.get("trend_direction", "neutral")
            
            # Volatility matching
            if "low_volatility" in optimal_conditions and volatility_env in ["low", "very_low"]:
                suitability_score += 0.4
            elif "high_volatility" in optimal_conditions and volatility_env == "elevated":
                suitability_score += 0.4
            
            # Trend matching
            if "bullish_trend" in optimal_conditions and trend == "bullish":
                suitability_score += 0.3
            elif "neutral_trend" in optimal_conditions and trend == "neutral":
                suitability_score += 0.3
            elif "bearish_trend" in optimal_conditions and trend == "bearish":
                suitability_score += 0.3
            
            # Market regime matching
            if "stable_market" in optimal_conditions and market_regime == "favorable_for_selling":
                suitability_score += 0.3
            
            return min(1.0, suitability_score)
            
        except Exception as e:
            logger.error(f"Error evaluating strategy suitability: {e}")
            return 0.5

    def generate_strategy(self, request_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimal trading strategy based on request and market conditions"""
        try:
            user_request = request_context.get("user_request", "")
            shared_context = self.load_shared_context()
            
            # Analyze market conditions
            market_conditions = self.analyze_market_conditions(shared_context)
            
            # Determine strategy type based on user request
            strategy_type = self._determine_strategy_type(user_request, market_conditions)
            
            # Get base strategy
            base_strategy = self.default_strategies.get(strategy_type, self.default_strategies["SPY_1DTE_Put_Selling"])
            
            # Customize strategy for current conditions
            customized_strategy = self._customize_strategy(base_strategy, market_conditions, user_request)
            
            # Calculate confidence and risk metrics
            confidence = self._calculate_strategy_confidence(customized_strategy, market_conditions)
            
            # Generate complete strategy recommendation
            strategy_recommendation = {
                "strategy": customized_strategy,
                "confidence": confidence,
                "market_analysis": market_conditions,
                "rationale": self._generate_strategy_rationale(customized_strategy, market_conditions),
                "risk_assessment": self._assess_strategy_risk(customized_strategy, market_conditions),
                "execution_parameters": self._generate_execution_parameters(customized_strategy, market_conditions),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save to memory
            self._record_strategy_generation(strategy_recommendation)
            
            # Update shared context
            self.update_shared_context({
                "strategy_recommendation": strategy_recommendation,
                "planner_status": "strategy_generated",
                "strategy_confidence": confidence
            })
            
            logger.info(f"Strategy generated: {strategy_type} with {confidence:.0%} confidence")
            return strategy_recommendation
            
        except Exception as e:
            logger.error(f"Error generating strategy: {e}")
            return {"error": str(e)}

    def _determine_strategy_type(self, user_request: str, market_conditions: Dict[str, Any]) -> str:
        """Determine the most appropriate strategy type based on user request and market"""
        request_lower = user_request.lower()
        vix_level = market_conditions.get("vix_level", 15)
        volatility_env = market_conditions.get("volatility_environment", "normal")
        
        # Check for specific requests
        if "0dte" in request_lower or "same day" in request_lower:
            return "SPY_0DTE_Put_Selling"
        elif "1dte" in request_lower or "next day" in request_lower:
            return "SPY_1DTE_Put_Selling"
        elif "weekly" in request_lower or "week" in request_lower:
            return "SPY_Weekly_Put_Selling"
        elif "safe" in request_lower or "conservative" in request_lower:
            return "SPY_1DTE_Put_Selling"  # Most conservative
        elif "aggressive" in request_lower or "high return" in request_lower:
            return "SPY_0DTE_Put_Selling"  # More aggressive
        
        # Default based on market conditions
        if volatility_env == "very_low" and vix_level < 12:
            return "SPY_0DTE_Put_Selling"  # Optimal for very low vol
        elif volatility_env == "low":
            return "SPY_1DTE_Put_Selling"   # Safe choice for low vol
        else:
            return "SPY_Weekly_Put_Selling"  # Conservative for higher vol
    
    def _customize_strategy(self, base_strategy: Dict[str, Any], market_conditions: Dict[str, Any], user_request: str) -> Dict[str, Any]:
        """Customize base strategy for current market conditions"""
        try:
            strategy = base_strategy.copy()
            
            spy_price = market_conditions.get("spy_price", 450.0)
            vix_level = market_conditions.get("vix_level", 15.0)
            optimal_strikes = market_conditions.get("optimal_strike_range", (435.0, 445.0))
            
            # Adjust strike price based on SPY price and support levels
            support_levels = market_conditions.get("support_levels", [440.0])
            nearest_support = min(support_levels, key=lambda x: abs(x - spy_price))
            
            # Calculate optimal strike (typically 5-10 points below SPY for PUT selling)
            if "safe" in user_request.lower():
                strike_distance = 10  # Further OTM for safety
            elif "aggressive" in user_request.lower():
                strike_distance = 5   # Closer to money for higher premium
            else:
                strike_distance = 7   # Balanced approach
            
            optimal_strike = spy_price - strike_distance
            
            # Round to nearest $0.50
            optimal_strike = round(optimal_strike * 2) / 2
            
            # Ensure strike is within reasonable bounds
            optimal_strike = max(optimal_strikes[0], min(optimal_strikes[1], optimal_strike))
            
            # Update strategy parameters
            strategy.update({
                "symbol": "SPY",
                "option_type": "P",  # PUT
                "strike": optimal_strike,
                "expiration": self._calculate_expiration(strategy["type"]),
                "action": "SELL",
                "quantity": self._calculate_position_size(strategy, market_conditions, user_request),
                "target_premium": self._estimate_premium(optimal_strike, spy_price, vix_level),
                "stop_loss": optimal_strike - (strategy["max_risk"] / 100),  # Convert to price
                "take_profit_pct": 0.5,  # Take 50% profit
                "current_spy_price": spy_price,
                "days_to_expiration": self._get_dte(strategy["type"])
            })
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error customizing strategy: {e}")
            return base_strategy

    def _calculate_expiration(self, strategy_type: str) -> str:
        """Calculate expiration date based on strategy type"""
        today = datetime.now()
        
        if "0DTE" in strategy_type:
            return today.strftime("%Y%m%d")
        elif "1DTE" in strategy_type:
            tomorrow = today + timedelta(days=1)
            # Skip weekends
            while tomorrow.weekday() >= 5:
                tomorrow += timedelta(days=1)
            return tomorrow.strftime("%Y%m%d")
        elif "Weekly" in strategy_type:
            # Next Friday
            days_ahead = 4 - today.weekday()  # Friday is 4
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            target_date = today + timedelta(days_ahead)
            return target_date.strftime("%Y%m%d")
        else:
            return today.strftime("%Y%m%d")

    def _get_dte(self, strategy_type: str) -> int:
        """Get days to expiration for strategy type"""
        if "0DTE" in strategy_type:
            return 0
        elif "1DTE" in strategy_type:
            return 1
        elif "Weekly" in strategy_type:
            today = datetime.now()
            days_to_friday = 4 - today.weekday()
            return max(1, days_to_friday)
        return 1

    def _calculate_position_size(self, strategy: Dict[str, Any], market_conditions: Dict[str, Any], user_request: str) -> int:
        """Calculate appropriate position size"""
        base_size = 1
        
        # Adjust based on user request
        if "large" in user_request.lower() or "aggressive" in user_request.lower():
            base_size = 2
        elif "small" in user_request.lower() or "conservative" in user_request.lower():
            base_size = 1
        
        # Adjust based on market conditions
        vix_level = market_conditions.get("vix_level", 15)
        if vix_level > 20:  # High volatility
            base_size = max(1, base_size - 1)
        
        return base_size

    def _estimate_premium(self, strike: float, spy_price: float, vix_level: float) -> float:
        """Estimate option premium (simplified Black-Scholes approximation)"""
        try:
            # Simplified premium estimation based on moneyness and volatility
            moneyness = (spy_price - strike) / spy_price
            vol_factor = vix_level / 100
            
            # Basic premium estimate for 0-1 DTE options
            if moneyness > 0.02:  # Far OTM
                premium = vol_factor * 0.3 * 100  # $30-50 typical for far OTM
            elif moneyness > 0.01:  # Moderately OTM  
                premium = vol_factor * 0.5 * 100  # $50-75
            else:  # Close to money
                premium = vol_factor * 0.8 * 100  # $80-120
            
            return round(max(0.05, premium), 2)
            
        except Exception as e:
            logger.error(f"Error estimating premium: {e}")
            return 0.50  # Default premium

    def _calculate_strategy_confidence(self, strategy: Dict[str, Any], market_conditions: Dict[str, Any]) -> float:
        """Calculate confidence level for the strategy"""
        try:
            base_confidence = strategy.get("win_probability", 0.7)
            
            # Adjust based on market conditions
            market_regime = market_conditions.get("market_regime", "neutral")
            vix_level = market_conditions.get("vix_level", 15)
            
            # Positive adjustments
            if market_regime == "favorable_for_selling":
                base_confidence += 0.1
            if vix_level < 12:  # Very low volatility
                base_confidence += 0.05
            
            # Negative adjustments  
            if market_regime in ["risk_off", "unfavorable_high_vol"]:
                base_confidence -= 0.15
            if vix_level > 25:  # High volatility
                base_confidence -= 0.1
            
            return min(0.95, max(0.3, base_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.7

    def _generate_strategy_rationale(self, strategy: Dict[str, Any], market_conditions: Dict[str, Any]) -> str:
        """Generate human-readable rationale for the strategy"""
        try:
            strategy_type = strategy.get("type", "Unknown")
            strike = strategy.get("strike", 0)
            spy_price = market_conditions.get("spy_price", 0)
            vix_level = market_conditions.get("vix_level", 0)
            market_regime = market_conditions.get("market_regime", "neutral")
            
            rationale = f"Recommending {strategy_type} strategy: "
            rationale += f"SELL SPY {strike}P expiring {strategy.get('expiration', 'today')}. "
            rationale += f"Current SPY at ${spy_price}, strike ${strike} away (${spy_price - strike:.2f} cushion). "
            rationale += f"VIX at {vix_level} indicates {market_conditions.get('volatility_environment', 'normal')} volatility. "
            rationale += f"Market regime: {market_regime}. "
            rationale += f"Expected premium: ~${strategy.get('target_premium', 0):.2f}. "
            rationale += f"Win probability: {strategy.get('win_probability', 0.7):.0%}."
            
            return rationale
            
        except Exception as e:
            logger.error(f"Error generating rationale: {e}")
            return "Strategy recommendation based on current market analysis."

    def _assess_strategy_risk(self, strategy: Dict[str, Any], market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk factors for the strategy"""
        try:
            max_loss = strategy.get("max_risk", 200)
            win_probability = strategy.get("win_probability", 0.7)
            strike = strategy.get("strike", 440)
            spy_price = market_conditions.get("spy_price", 450)
            
            risk_assessment = {
                "max_loss": max_loss,
                "probability_of_loss": 1 - win_probability,
                "breakeven_price": strike - (strategy.get("target_premium", 50) / 100),
                "distance_to_breakeven": spy_price - (strike - (strategy.get("target_premium", 50) / 100)),
                "risk_reward_ratio": strategy.get("target_premium", 50) / max_loss,
                "time_decay_advantage": strategy.get("days_to_expiration", 1) <= 1,
                "support_levels": market_conditions.get("support_levels", []),
                "overall_risk_level": strategy.get("risk_level", "medium")
            }
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error assessing strategy risk: {e}")
            return {"overall_risk_level": "unknown"}

    def _generate_execution_parameters(self, strategy: Dict[str, Any], market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific execution parameters for the trade"""
        try:
            target_premium = strategy.get("target_premium", 0.50)
            
            execution_params = {
                "order_type": "LIMIT",
                "limit_price": target_premium,
                "time_in_force": "DAY",
                "stop_loss_price": strategy.get("stop_loss", 0),
                "take_profit_percentage": strategy.get("take_profit_pct", 0.5),
                "max_fill_time": 300,  # 5 minutes
                "partial_fills_allowed": False,
                "market_hours_only": True,
                "minimum_premium": target_premium * 0.8,  # Accept 80% of target
                "maximum_slippage": 0.05,  # $5 max slippage
                "risk_management": {
                    "stop_loss_multiplier": 3.0,
                    "take_profit_multiplier": 0.5,
                    "position_monitoring": True
                }
            }
            
            return execution_params
            
        except Exception as e:
            logger.error(f"Error generating execution parameters: {e}")
            return {"order_type": "LIMIT"}

    def _record_strategy_generation(self, strategy_recommendation: Dict[str, Any]):
        """Record the strategy generation in memory"""
        try:
            memory = self.load_memory()
            
            strategy_record = {
                "timestamp": datetime.now().isoformat(),
                "strategy_type": strategy_recommendation["strategy"].get("type", "unknown"),
                "confidence": strategy_recommendation["confidence"],
                "market_conditions": strategy_recommendation["market_analysis"],
                "strategy_id": f"STRAT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            memory["strategies_generated"].append(strategy_record)
            
            # Keep only last 50 strategies
            if len(memory["strategies_generated"]) > 50:
                memory["strategies_generated"] = memory["strategies_generated"][-50:]
            
            self.save_memory(memory)
            
        except Exception as e:
            logger.error(f"Error recording strategy generation: {e}")

