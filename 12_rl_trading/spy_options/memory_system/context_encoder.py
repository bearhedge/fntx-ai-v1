"""
Context Encoder for Memory Features
Converts historical memory into additional features for the model
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging


class ContextEncoder:
    """Encodes memory and context into additional model features"""
    
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(__name__)
        
        # Feature names for debugging
        self.memory_feature_names = [
            "last_trade_outcome_1",
            "last_trade_outcome_2", 
            "last_trade_outcome_3",
            "last_trade_outcome_4",
            "last_trade_outcome_5",
            "recent_acceptance_rate",
            "same_hour_win_rate",
            "pnl_trend",
            "days_since_similar",
            "session_suggestion_count",
            "risk_tolerance_score",
            "market_regime_encoded"
        ]
        
    async def encode_context(self, 
                           base_features: np.ndarray,
                           market_data: Dict) -> Tuple[np.ndarray, Dict]:
        """
        Augment base features with memory context
        
        Args:
            base_features: Original 8 features from market
            market_data: Current market snapshot
            
        Returns:
            augmented_features: 20 features (8 base + 12 memory)
            context_info: Dict with human-readable context
        """
        # Get memory features from database
        memory_features = await self.memory_manager.get_memory_features()
        
        # Combine base + memory
        augmented_features = np.concatenate([base_features, memory_features])
        
        # Create context info for transparency
        context_info = self._create_context_info(memory_features, market_data)
        
        return augmented_features, context_info
    
    def _create_context_info(self, 
                           memory_features: np.ndarray,
                           market_data: Dict) -> Dict:
        """Create human-readable context information"""
        
        # Recent outcomes
        outcomes = memory_features[:5]
        outcome_str = []
        for i, outcome in enumerate(outcomes):
            if outcome == 1:
                outcome_str.append(f"T-{i+1}: ✓")
            elif outcome == -1:
                outcome_str.append(f"T-{i+1}: ✗")
            else:
                outcome_str.append(f"T-{i+1}: -")
        
        # Acceptance rate
        acceptance_rate = memory_features[5]
        acceptance_desc = "High" if acceptance_rate > 0.7 else "Medium" if acceptance_rate > 0.4 else "Low"
        
        # Same hour performance
        hour_rate = memory_features[6]
        current_hour = datetime.now().hour
        hour_desc = f"{hour_rate:.1%} success at {current_hour}:00"
        
        # P&L trend
        pnl_trend = memory_features[7]
        trend_desc = "Improving" if pnl_trend > 0.2 else "Declining" if pnl_trend < -0.2 else "Stable"
        
        # Market regime
        regime_val = memory_features[11]
        regime_map = {0: "Trending Up", 0.33: "Trending Down", 0.67: "Choppy", 1.0: "Unknown"}
        regime = min(regime_map.keys(), key=lambda x: abs(x - regime_val))
        
        return {
            "recent_trades": " ".join(outcome_str),
            "acceptance_rate": f"{acceptance_rate:.1%} ({acceptance_desc})",
            "hour_performance": hour_desc,
            "pnl_trend": trend_desc,
            "suggestions_today": int(memory_features[9] * 20),
            "risk_tolerance": f"{memory_features[10]:.1%}",
            "market_regime": regime_map[regime],
            "days_since_similar": int(memory_features[8] * 30)
        }
    
    async def apply_learned_preferences(self,
                                      base_action: int,
                                      confidence: float,
                                      features: np.ndarray) -> Tuple[int, float, List[str]]:
        """
        Apply learned user preferences to modify suggestions
        
        Args:
            base_action: Model's suggested action (0/1/2)
            confidence: Model's confidence
            features: Current features
            
        Returns:
            adjusted_action: Potentially modified action
            adjusted_confidence: Modified confidence
            applied_rules: List of rules that were applied
        """
        preferences = await self.memory_manager.get_learned_preferences()
        
        adjusted_action = base_action
        adjusted_confidence = confidence
        applied_rules = []
        
        for pref in preferences:
            if self._should_apply_preference(pref, base_action, features):
                # Apply the preference
                if pref['user_preference'] == 'avoid':
                    adjusted_confidence *= (1 - pref['confidence'])
                    applied_rules.append(f"Avoiding {pref['rule_type']}: {pref['condition']}")
                    
                    # If confidence drops too low, suggest hold instead
                    if adjusted_confidence < 0.3 and base_action != 0:
                        adjusted_action = 0
                        applied_rules.append("Changed to HOLD due to low confidence")
                        
                elif pref['user_preference'] == 'prefer':
                    adjusted_confidence *= (1 + pref['confidence'] * 0.5)
                    applied_rules.append(f"Preferring {pref['rule_type']}: {pref['condition']}")
        
        return adjusted_action, adjusted_confidence, applied_rules
    
    def _should_apply_preference(self, 
                               preference: Dict,
                               action: int,
                               features: np.ndarray) -> bool:
        """Check if a preference rule applies to current context"""
        condition = preference['condition']
        
        # Time-based rules
        if preference['rule_type'] == 'timing':
            current_hour = datetime.now().hour
            if 'before_10:30' in str(condition) and current_hour < 10.5:
                if 'call' in str(condition) and action == 1:
                    return True
                    
        # Add more rule types as learned
        
        return False
    
    async def get_similar_historical_decisions(self,
                                             spy_price: float,
                                             vix: float) -> List[Dict]:
        """Get similar historical contexts for reference"""
        similar = await self.memory_manager.find_similar_contexts(
            spy_price, vix, datetime.now()
        )
        
        # Format for display
        formatted = []
        for ctx in similar[:5]:  # Top 5
            formatted.append({
                'similarity': f"{ctx['similarity_score']:.1%}",
                'accepted': '✓' if ctx['was_accepted'] else '✗',
                'outcome': f"${ctx['outcome_pnl']:+.0f}" if ctx['outcome_pnl'] else "N/A"
            })
            
        return formatted
    
    def explain_memory_impact(self, 
                            base_features: np.ndarray,
                            memory_features: np.ndarray,
                            original_action: int,
                            final_action: int) -> List[str]:
        """Explain how memory affected the decision"""
        explanations = []
        
        # Check recent performance
        recent_rate = memory_features[5]
        if recent_rate < 0.3:
            explanations.append("⚠️ Low recent acceptance rate - being more cautious")
        elif recent_rate > 0.7:
            explanations.append("✓ High recent acceptance rate - confident in suggestions")
        
        # Check time-based performance
        hour_rate = memory_features[6]
        if hour_rate < 0.4:
            explanations.append(f"📊 Poor historical performance at this hour ({hour_rate:.1%})")
        elif hour_rate > 0.6:
            explanations.append(f"📈 Strong historical performance at this hour ({hour_rate:.1%})")
        
        # Check P&L trend
        pnl_trend = memory_features[7]
        if pnl_trend < -0.3:
            explanations.append("📉 Recent P&L declining - adjusting strategy")
        elif pnl_trend > 0.3:
            explanations.append("📈 Recent P&L improving - maintaining approach")
        
        # Check if action was changed
        if original_action != final_action:
            explanations.append(f"🔄 Changed recommendation from {self._action_name(original_action)} "
                              f"to {self._action_name(final_action)} based on your preferences")
        
        return explanations
    
    def _action_name(self, action: int) -> str:
        """Convert action number to name"""
        return {0: "HOLD", 1: "SELL CALL", 2: "SELL PUT"}.get(action, "UNKNOWN")
    
    def get_memory_feature_summary(self, memory_features: np.ndarray) -> Dict[str, str]:
        """Create summary of memory features for display"""
        summary = {}
        
        for i, (feature_name, value) in enumerate(zip(self.memory_feature_names, memory_features)):
            if i < 5:  # Recent outcomes
                summary[feature_name] = "Win" if value > 0 else "Loss" if value < 0 else "N/A"
            elif feature_name.endswith("_rate") or feature_name.endswith("_score"):
                summary[feature_name] = f"{value:.1%}"
            elif feature_name == "pnl_trend":
                summary[feature_name] = f"{value:+.2f}"
            elif feature_name == "days_since_similar":
                summary[feature_name] = f"{int(value * 30)} days"
            elif feature_name == "session_suggestion_count":
                summary[feature_name] = str(int(value * 20))
            elif feature_name == "market_regime_encoded":
                regimes = ["Trend Up", "Trend Down", "Choppy", "Unknown"]
                idx = int(value * 3)
                summary[feature_name] = regimes[min(idx, 3)]
            else:
                summary[feature_name] = f"{value:.3f}"
                
        return summary