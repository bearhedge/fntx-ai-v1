#!/usr/bin/env python3
"""
FNTX.ai EnvironmentWatcherAgent - Market Monitoring and Regime Detection
Monitors market conditions, volatility, and regime changes for optimal trading decisions
"""

import os
import json
import time
import logging
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with dynamic path
from backend.utils.logging import get_agent_logger
logger = get_agent_logger('EnvironmentWatcherAgent')

class EnvironmentWatcherAgent:
    """
    EnvironmentWatcherAgent monitors market conditions, regime changes, and environmental factors
    that impact trading decisions and strategy optimization.
    """
    
    def __init__(self):
        self.memory_file = "backend/agents/memory/environment_watcher_memory.json"
        self.shared_context_file = "backend/agents/memory/shared_context.json"
        
        # Market monitoring parameters
        self.vix_low_threshold = float(os.getenv("VIX_LOW_THRESHOLD", "15.0"))
        self.vix_high_threshold = float(os.getenv("VIX_HIGH_THRESHOLD", "25.0"))
        self.spy_support_threshold = float(os.getenv("SPY_SUPPORT_THRESHOLD", "0.02"))
        self.volume_spike_threshold = float(os.getenv("VOLUME_SPIKE_THRESHOLD", "1.5"))
        
        # Use unified IBKR service
        from backend.services.ibkr_unified_service import ibkr_unified_service
        self.ibkr_service = ibkr_unified_service
        
        logger.info("EnvironmentWatcherAgent initialized for market monitoring")

    def load_memory(self) -> Dict[str, Any]:
        """Load environment watcher memory from MCP-compatible JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
        
        # Default memory schema
        return {
            "agent_id": "EnvironmentWatcherAgent",
            "last_updated": datetime.now().isoformat(),
            "current_market_regime": "unknown",
            "market_conditions": {
                "spy_price": 0.0,
                "vix_level": 0.0,
                "volume_profile": "normal",
                "trend_direction": "neutral",
                "support_levels": [],
                "resistance_levels": []
            },
            "regime_history": [],
            "volatility_alerts": [],
            "market_alerts": [],
            "economic_calendar": [],
            "regime_indicators": {
                "vix_regime": "normal",
                "trend_regime": "neutral",
                "volume_regime": "normal",
                "volatility_regime": "normal"
            },
            "trading_recommendations": {
                "overall_signal": "neutral",
                "strategy_preference": "defensive",
                "position_sizing": "normal",
                "timing_preference": "patient"
            }
        }

    def save_memory(self, memory: Dict[str, Any]):
        """Save environment watcher memory to MCP-compatible JSON file"""
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
        """Update shared context with market insights"""
        try:
            context = self.load_shared_context()
            context.update(updates)
            context["last_updated"] = datetime.now().isoformat()
            
            with open(self.shared_context_file, 'w') as f:
                json.dump(context, f, indent=2)
        except Exception as e:
            logger.error(f"Error updating shared context: {e}")

    def get_market_data(self) -> Dict[str, Any]:
        """Fetch current market data from IBKR live feed"""
        try:
            current_time = datetime.now()
            market_data = {
                "timestamp": current_time.isoformat(),
                "market_hours": self._is_market_hours(current_time),
                "trading_day": self._is_trading_day(current_time)
            }
            
            # Ensure IBKR is connected
            if not self.ibkr_service.connect():
                logger.error("Failed to connect to IBKR for market data")
                return market_data
            
            # Fetch SPY data from IBKR
            spy_data = self.ibkr_service.get_spy_price()
            if spy_data and spy_data.get('price', 0) > 0:
                market_data["spy"] = spy_data
            else:
                market_data["spy"] = {"price": 0, "source": "unavailable"}
            
            # For now, use estimated VIX (would get from IBKR in production)
            market_data["vix"] = {"level": 15.0, "source": "estimated"}
            
            # Get SPY options chain data for additional analysis
            options_data = self._fetch_spy_options_data()
            if options_data:
                market_data["options"] = options_data
            
            if "spy" in market_data and "vix" in market_data:
                logger.info(f"IBKR live data: SPY ${market_data['spy']['price']}, VIX {market_data['vix']['level']}")
            else:
                logger.warning("Incomplete market data received from IBKR")
                
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching IBKR market data: {e}")
            return {}

    def _is_market_hours(self, timestamp: datetime) -> bool:
        """Check if market is currently open"""
        # Simplified - assumes EST timezone
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
        return weekday < 5 and 9 <= hour < 16

    def _is_trading_day(self, timestamp: datetime) -> bool:
        """Check if today is a trading day"""
        # Simplified - excludes weekends, would check holidays in production
        return timestamp.weekday() < 5

    def _ensure_ibkr_connection(self) -> bool:
        """Ensure IBKR connection is established"""
        try:
            import asyncio
            from ib_insync import IB, Stock
            
            # Check if we're in an event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, can't use sync connect
                    logger.warning("Cannot connect to IBKR from running event loop context")
                    return False
            except RuntimeError:
                # No event loop, we can proceed
                pass
            
            if self.ib_connection is None or not self.ib_connection.isConnected():
                logger.info(f"Connecting to IBKR at {self.ibkr_host}:{self.ibkr_port}")
                self.ib_connection = IB()
                self.ib_connection.connect(self.ibkr_host, self.ibkr_port, clientId=self.ibkr_client_id)
                logger.info("IBKR connection established for market data")
            
            return self.ib_connection.isConnected()
            
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            return False

    def _fetch_spy_data_ibkr(self) -> Dict[str, Any]:
        """Fetch live SPY data from IBKR"""
        try:
            from ib_insync import Stock
            
            if not self.ib_connection or not self.ib_connection.isConnected():
                logger.error("IBKR not connected for SPY data")
                return {}
            
            # Create SPY contract
            spy_contract = Stock('SPY', 'SMART', 'USD')
            self.ib_connection.qualifyContracts(spy_contract)
            
            # Get market data
            ticker = self.ib_connection.reqMktData(spy_contract, '', False, False)
            self.ib_connection.sleep(2)  # Wait for data
            
            if ticker.last and ticker.last > 0:
                # Calculate change from previous close
                prev_close = ticker.close if ticker.close else ticker.last
                change = ticker.last - prev_close
                
                return {
                    "price": float(ticker.last),
                    "change": float(change),
                    "volume": int(ticker.volume) if ticker.volume else 0,
                    "high": float(ticker.high) if ticker.high else float(ticker.last),
                    "low": float(ticker.low) if ticker.low else float(ticker.last),
                    "bid": float(ticker.bid) if ticker.bid else 0,
                    "ask": float(ticker.ask) if ticker.ask else 0
                }
            else:
                logger.warning("No SPY price data received from IBKR")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching SPY data from IBKR: {e}")
            return {}

    def _fetch_vix_data_ibkr(self) -> Dict[str, Any]:
        """Fetch live VIX data from IBKR"""
        try:
            from ib_insync import Index
            
            if not self.ib_connection or not self.ib_connection.isConnected():
                logger.error("IBKR not connected for VIX data")
                return {}
            
            # Create VIX contract
            vix_contract = Index('VIX', 'CBOE', 'USD')
            self.ib_connection.qualifyContracts(vix_contract)
            
            # Get market data
            ticker = self.ib_connection.reqMktData(vix_contract, '', False, False)
            self.ib_connection.sleep(2)  # Wait for data
            
            if ticker.last and ticker.last > 0:
                # Calculate change from previous close
                prev_close = ticker.close if ticker.close else ticker.last
                change = ticker.last - prev_close
                
                return {
                    "level": float(ticker.last),
                    "change": float(change),
                    "high": float(ticker.high) if ticker.high else float(ticker.last),
                    "low": float(ticker.low) if ticker.low else float(ticker.last)
                }
            else:
                logger.warning("No VIX data received from IBKR")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching VIX data from IBKR: {e}")
            return {}

    def _fetch_spy_options_data(self) -> Dict[str, Any]:
        """Fetch SPY options chain data for additional market analysis"""
        try:
            from ib_insync import Stock, Option
            from datetime import datetime, timedelta
            
            if not self.ib_connection or not self.ib_connection.isConnected():
                logger.warning("IBKR not connected for options data")
                return {}
            
            # Create SPY contract for options chain
            spy_contract = Stock('SPY', 'SMART', 'USD')
            self.ib_connection.qualifyContracts(spy_contract)
            
            # Get chains for 0DTE and 1DTE options
            chains = self.ib_connection.reqSecDefOptParams('SPY', '', 'STK', 8314)
            
            if not chains:
                logger.warning("No options chains received for SPY")
                return {}
            
            # Focus on nearest expiration dates (0DTE, 1DTE)
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            options_data = {
                "chains_available": len(chains),
                "expirations": [],
                "iv_summary": {},
                "put_call_ratio": 0.0
            }
            
            # Get available expirations
            for chain in chains[:3]:  # Limit to first 3 chains
                expirations = [exp for exp in chain.expirations if exp <= str(tomorrow.strftime('%Y%m%d'))]
                options_data["expirations"].extend(expirations)
            
            options_data["expirations"] = list(set(options_data["expirations"]))
            logger.info(f"SPY options data: {len(options_data['expirations'])} near-term expirations")
            
            return options_data
            
        except Exception as e:
            logger.error(f"Error fetching SPY options data: {e}")
            return {}

    def analyze_market_regime(self, market_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze current market regime based on multiple indicators"""
        try:
            regime_indicators = {}
            
            if not market_data:
                return {"overall_regime": "unknown"}
            
            spy_data = market_data.get("spy", {})
            vix_data = market_data.get("vix", {})
            options_data = market_data.get("options", {})
            
            spy_price = spy_data.get("price", 0)
            spy_change = spy_data.get("change", 0)
            vix_level = vix_data.get("level", 0)
            volume = spy_data.get("volume", 0)
            bid_ask_spread = spy_data.get("ask", 0) - spy_data.get("bid", 0)
            
            # VIX-based regime analysis
            if vix_level < self.vix_low_threshold:
                regime_indicators["vix_regime"] = "low_volatility"
            elif vix_level > self.vix_high_threshold:
                regime_indicators["vix_regime"] = "high_volatility"
            else:
                regime_indicators["vix_regime"] = "normal_volatility"
            
            # Trend-based regime analysis
            if spy_change > 1.0:
                regime_indicators["trend_regime"] = "bullish"
            elif spy_change < -1.0:
                regime_indicators["trend_regime"] = "bearish"
            else:
                regime_indicators["trend_regime"] = "neutral"
            
            # Volume-based regime analysis
            avg_volume = 85000000  # Typical SPY volume
            if volume > avg_volume * self.volume_spike_threshold:
                regime_indicators["volume_regime"] = "high_volume"
            elif volume < avg_volume * 0.7:
                regime_indicators["volume_regime"] = "low_volume"
            else:
                regime_indicators["volume_regime"] = "normal_volume"
            
            # Options-based regime indicators
            if options_data:
                chains_available = options_data.get("chains_available", 0)
                expirations = options_data.get("expirations", [])
                
                if chains_available > 0 and expirations:
                    regime_indicators["options_regime"] = "active_chains"
                    if len(expirations) >= 2:  # 0DTE and 1DTE available
                        regime_indicators["intraday_opportunities"] = "available"
                    else:
                        regime_indicators["intraday_opportunities"] = "limited"
                else:
                    regime_indicators["options_regime"] = "limited_chains"
                    regime_indicators["intraday_opportunities"] = "unavailable"
            
            # Liquidity regime based on bid-ask spread
            if bid_ask_spread <= 0.01:
                regime_indicators["liquidity_regime"] = "excellent"
            elif bid_ask_spread <= 0.03:
                regime_indicators["liquidity_regime"] = "good"
            elif bid_ask_spread <= 0.05:
                regime_indicators["liquidity_regime"] = "fair"
            else:
                regime_indicators["liquidity_regime"] = "poor"
            
            # Combined volatility regime
            if vix_level < 12 and abs(spy_change) < 0.5:
                regime_indicators["volatility_regime"] = "very_low"
            elif vix_level > 20 or abs(spy_change) > 2.0:
                regime_indicators["volatility_regime"] = "elevated"
            else:
                regime_indicators["volatility_regime"] = "normal"
            
            # Overall regime determination (enhanced with options and liquidity)
            liquidity_good = regime_indicators.get("liquidity_regime") in ["excellent", "good"]
            options_active = regime_indicators.get("options_regime") == "active_chains"
            intraday_available = regime_indicators.get("intraday_opportunities") == "available"
            
            if (regime_indicators["vix_regime"] == "low_volatility" and 
                regime_indicators["trend_regime"] in ["bullish", "neutral"] and
                liquidity_good and options_active):
                overall_regime = "favorable_for_selling"
            elif regime_indicators["vix_regime"] == "high_volatility":
                overall_regime = "unfavorable_high_vol"
            elif regime_indicators["volume_regime"] == "high_volume" and regime_indicators["trend_regime"] == "bearish":
                overall_regime = "risk_off"
            elif not liquidity_good or not options_active:
                overall_regime = "illiquid_conditions"
            else:
                overall_regime = "neutral"
            
            regime_indicators["overall_regime"] = overall_regime
            
            logger.info(f"Market regime analyzed: {overall_regime} (VIX: {vix_level}, SPY: ${spy_price})")
            return regime_indicators
            
        except Exception as e:
            logger.error(f"Error analyzing market regime: {e}")
            return {"overall_regime": "unknown"}

    def detect_regime_changes(self, current_regime: Dict[str, str], memory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect significant regime changes"""
        changes = []
        
        try:
            previous_regime = memory.get("current_market_regime", "unknown")
            current_overall = current_regime.get("overall_regime", "unknown")
            
            # Check for significant regime change
            if previous_regime != current_overall and previous_regime != "unknown":
                change_event = {
                    "timestamp": datetime.now().isoformat(),
                    "change_type": "market_regime",
                    "from_regime": previous_regime,
                    "to_regime": current_overall,
                    "significance": self._assess_regime_change_significance(previous_regime, current_overall),
                    "trading_impact": self._assess_trading_impact(previous_regime, current_overall),
                    "recommended_actions": self._get_regime_change_actions(current_overall)
                }
                changes.append(change_event)
                
                logger.info(f"Regime change detected: {previous_regime} -> {current_overall}")
            
            # Check for VIX spikes
            current_vix = memory.get("market_conditions", {}).get("vix_level", 0)
            if current_vix > self.vix_high_threshold:
                vix_alert = {
                    "timestamp": datetime.now().isoformat(),
                    "change_type": "vix_spike",
                    "vix_level": current_vix,
                    "significance": "high" if current_vix > 30 else "medium",
                    "trading_impact": "reduce_position_sizes",
                    "recommended_actions": ["Pause new positions", "Consider defensive strategies"]
                }
                changes.append(vix_alert)
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting regime changes: {e}")
            return []

    def _assess_regime_change_significance(self, from_regime: str, to_regime: str) -> str:
        """Assess the significance of a regime change"""
        high_impact_changes = [
            ("favorable_for_selling", "unfavorable_high_vol"),
            ("favorable_for_selling", "risk_off"),
            ("neutral", "unfavorable_high_vol"),
            ("neutral", "risk_off")
        ]
        
        if (from_regime, to_regime) in high_impact_changes:
            return "high"
        elif from_regime == "unknown" or to_regime == "unknown":
            return "low"
        else:
            return "medium"

    def _assess_trading_impact(self, from_regime: str, to_regime: str) -> str:
        """Assess the impact on trading strategy"""
        if to_regime == "favorable_for_selling":
            return "increase_activity"
        elif to_regime in ["unfavorable_high_vol", "risk_off"]:
            return "reduce_activity"
        else:
            return "maintain_current"

    def _get_regime_change_actions(self, new_regime: str) -> List[str]:
        """Get recommended actions for new regime"""
        actions = {
            "favorable_for_selling": [
                "Consider increasing position sizes",
                "Focus on premium collection strategies",
                "Look for shorter-duration trades"
            ],
            "unfavorable_high_vol": [
                "Reduce position sizes significantly",
                "Avoid new positions until volatility subsides",
                "Consider defensive strategies only"
            ],
            "risk_off": [
                "Halt new position opening",
                "Consider closing existing positions",
                "Wait for market stabilization"
            ],
            "neutral": [
                "Maintain current approach",
                "Monitor for clearer signals",
                "Use normal position sizing"
            ]
        }
        
        return actions.get(new_regime, ["Monitor market conditions closely"])

    def generate_trading_recommendations(self, regime_indicators: Dict[str, str], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific trading recommendations based on environment"""
        try:
            recommendations = {
                "timestamp": datetime.now().isoformat(),
                "overall_signal": "neutral",
                "strategy_preference": "conservative",
                "position_sizing": "normal",
                "timing_preference": "patient",
                "specific_actions": [],
                "risk_adjustments": []
            }
            
            overall_regime = regime_indicators.get("overall_regime", "neutral")
            vix_level = market_data.get("vix", {}).get("level", 15)
            spy_change = market_data.get("spy", {}).get("change", 0)
            
            # Overall signal determination
            if overall_regime == "favorable_for_selling":
                recommendations["overall_signal"] = "bullish"
                recommendations["strategy_preference"] = "aggressive_selling"
                recommendations["position_sizing"] = "increased"
                recommendations["timing_preference"] = "opportunistic"
                recommendations["specific_actions"].extend([
                    "Focus on SPY PUT selling strategies",
                    "Consider 0DTE and 1DTE options",
                    "Target strikes with good premium/probability ratio"
                ])
            
            elif overall_regime in ["unfavorable_high_vol", "risk_off"]:
                recommendations["overall_signal"] = "bearish"
                recommendations["strategy_preference"] = "defensive"
                recommendations["position_sizing"] = "reduced"
                recommendations["timing_preference"] = "very_patient"
                recommendations["specific_actions"].extend([
                    "Halt new position opening",
                    "Consider closing existing positions early",
                    "Wait for volatility to normalize"
                ])
            
            # VIX-specific recommendations
            if vix_level < 12:
                recommendations["specific_actions"].append("Excellent conditions for premium selling")
                recommendations["risk_adjustments"].append("Can use normal position sizes")
            elif vix_level > 25:
                recommendations["specific_actions"].append("High volatility - avoid new positions")
                recommendations["risk_adjustments"].append("Reduce all position sizes by 50%")
            
            # Trend-specific recommendations
            if spy_change > 2.0:
                recommendations["specific_actions"].append("Strong uptrend - consider PUT selling")
            elif spy_change < -2.0:
                recommendations["specific_actions"].append("Downtrend - avoid PUT selling")
            
            # Market hours recommendations
            if not market_data.get("market_hours", False):
                recommendations["timing_preference"] = "wait_for_open"
                recommendations["specific_actions"].append("Wait for market open for better liquidity")
            
            logger.info(f"Trading recommendations generated: {recommendations['overall_signal']} signal")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating trading recommendations: {e}")
            return {"overall_signal": "neutral", "strategy_preference": "conservative"}

    def monitor_economic_calendar(self) -> List[Dict[str, Any]]:
        """Monitor upcoming economic events from real data sources"""
        try:
            # TODO: Integrate with real economic calendar API (e.g., Trading Economics, FRED API)
            # For now, return empty list until real API is integrated
            logger.info("Economic calendar monitoring: Real API integration pending")
            return []
            
        except Exception as e:
            logger.error(f"Error monitoring economic calendar: {e}")
            return []

    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        logger.info("Starting environment monitoring cycle...")
        
        try:
            memory = self.load_memory()
            
            # Get current market data
            market_data = self.get_market_data()
            
            if market_data:
                # Update current market conditions
                memory["market_conditions"].update({
                    "spy_price": market_data.get("spy", {}).get("price", 0),
                    "vix_level": market_data.get("vix", {}).get("level", 0),
                    "last_updated": datetime.now().isoformat()
                })
                
                # Analyze market regime
                regime_indicators = self.analyze_market_regime(market_data)
                memory["regime_indicators"] = regime_indicators
                
                # Detect regime changes
                regime_changes = self.detect_regime_changes(regime_indicators, memory)
                if regime_changes:
                    memory["regime_history"].extend(regime_changes)
                    # Keep last 50 regime changes
                    if len(memory["regime_history"]) > 50:
                        memory["regime_history"] = memory["regime_history"][-50:]
                
                # Update current regime
                memory["current_market_regime"] = regime_indicators.get("overall_regime", "unknown")
                
                # Generate trading recommendations
                trading_recommendations = self.generate_trading_recommendations(regime_indicators, market_data)
                memory["trading_recommendations"] = trading_recommendations
                
                # Monitor economic calendar
                economic_events = self.monitor_economic_calendar()
                memory["economic_calendar"] = economic_events
                
                # Update shared context
                self.update_shared_context({
                    "market_regime": regime_indicators.get("overall_regime", "unknown"),
                    "vix_level": market_data.get("vix", {}).get("level", 0),
                    "spy_price": market_data.get("spy", {}).get("price", 0),
                    "trading_recommendations": trading_recommendations,
                    "regime_changes": regime_changes,
                    "market_hours": market_data.get("market_hours", False),
                    "environment_alert_level": self._calculate_alert_level(regime_indicators, market_data)
                })
                
                logger.info(f"Monitoring cycle completed: {regime_indicators.get('overall_regime', 'unknown')} regime detected")
            
            self.save_memory(memory)
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")

    def _calculate_alert_level(self, regime_indicators: Dict[str, str], market_data: Dict[str, Any]) -> str:
        """Calculate overall alert level for the system"""
        try:
            vix_level = market_data.get("vix", {}).get("level", 15)
            overall_regime = regime_indicators.get("overall_regime", "neutral")
            
            if vix_level > 30 or overall_regime == "risk_off":
                return "high"
            elif vix_level > 20 or overall_regime == "unfavorable_high_vol":
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"Error calculating alert level: {e}")
            return "unknown"

    def run(self):
        """Main execution loop"""
        logger.info("EnvironmentWatcherAgent starting main loop...")
        
        try:
            while True:
                self.run_monitoring_cycle()
                
                # Sleep for 5 minutes between monitoring cycles
                time.sleep(5 * 60)
                
        except KeyboardInterrupt:
            logger.info("EnvironmentWatcherAgent stopped by user")
        except Exception as e:
            logger.error(f"EnvironmentWatcherAgent crashed: {e}")
    
    def cleanup(self):
        """Clean up IBKR connection"""
        try:
            if self.ib_connection and self.ib_connection.isConnected():
                logger.info("Disconnecting from IBKR")
                self.ib_connection.disconnect()
                self.ib_connection = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main entry point"""
    agent = EnvironmentWatcherAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down EnvironmentWatcher...")
        agent.cleanup()
    except Exception as e:
        logger.error(f"EnvironmentWatcher error: {e}")
        agent.cleanup()

if __name__ == "__main__":
    main()