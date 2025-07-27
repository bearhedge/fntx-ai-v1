"""
Model Service integrating base PPO model with memory and adapter
"""
import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import numpy as np
from datetime import datetime


class ModelService:
    """Service layer for model predictions with memory integration"""
    
    def __init__(self, base_model, adapter_network, context_encoder):
        self.base_model = base_model
        self.adapter_network = adapter_network
        self.context_encoder = context_encoder
        self.logger = logging.getLogger(__name__)
        
        # Action mapping
        self.action_names = {
            0: "HOLD",
            1: "SELL CALL",
            2: "SELL PUT"
        }
        
    async def predict_with_memory(self,
                                base_features: np.ndarray,
                                market_data: Dict,
                                include_reasoning: bool = True) -> Dict:
        """
        Get prediction augmented with memory context
        
        Args:
            base_features: 8 original features
            market_data: Current market snapshot
            include_reasoning: Whether to generate reasoning
            
        Returns:
            Complete prediction with context
        """
        decision_id = uuid4()
        
        # 1. Augment features with memory
        augmented_features, memory_context = await self.context_encoder.encode_context(
            base_features, market_data
        )
        
        # 2. Get base model prediction (if available)
        if self.base_model:
            # Use base model with original 8 features
            base_action, _ = self.base_model.predict(base_features, deterministic=True)
            base_action = int(base_action)
            
            # Get action probabilities (mock for now)
            action_probs = self._get_action_probabilities(base_features)
        else:
            # Mock model for testing
            base_action, action_probs = self._mock_prediction(base_features)
        
        # 3. Apply adapter network adjustment
        if self.adapter_network:
            adjusted_probs = await self.adapter_network.forward(
                augmented_features, action_probs
            )
            final_action = int(np.argmax(adjusted_probs))
            final_probs = adjusted_probs
        else:
            final_action = base_action
            final_probs = action_probs
        
        # 4. Calculate confidence
        confidence = float(final_probs[final_action]) if final_probs is not None else 0.5
        
        # 5. Apply learned preferences
        adjusted_action, adjusted_confidence, applied_rules = \
            await self.context_encoder.apply_learned_preferences(
                final_action, confidence, augmented_features
            )
        
        # 6. Get similar historical contexts
        similar_historical = await self.context_encoder.get_similar_historical_decisions(
            market_data['spy_price'], 
            market_data.get('vix', 15)
        )
        
        # 7. Generate reasoning if requested
        reasoning = {}
        memory_impact = []
        constraints = {}
        
        if include_reasoning:
            reasoning = self._generate_reasoning(
                adjusted_action, augmented_features, market_data
            )
            memory_impact = self.context_encoder.explain_memory_impact(
                base_features, augmented_features[8:], base_action, adjusted_action
            )
            constraints = self._check_constraints(augmented_features, market_data)
        
        return {
            'decision_id': decision_id,
            'action': adjusted_action,
            'action_name': self.action_names[adjusted_action],
            'confidence': adjusted_confidence,
            'action_probabilities': final_probs.tolist() if final_probs is not None else None,
            'memory_context': memory_context,
            'similar_historical': similar_historical,
            'applied_preferences': applied_rules,
            'reasoning': reasoning,
            'memory_impact': memory_impact,
            'constraints': constraints
        }
    
    def _get_action_probabilities(self, features: np.ndarray) -> np.ndarray:
        """Get action probability distribution from model"""
        # PPO doesn't directly expose probabilities in SB3
        # This is a simplified approach
        
        # Use feature values to create mock probabilities
        time_factor = features[0]  # minutes_since_open
        
        if time_factor < 0.1:  # Early morning
            return np.array([0.7, 0.15, 0.15])  # Favor hold
        elif time_factor < 0.5:  # Morning
            return np.array([0.2, 0.5, 0.3])   # Favor calls
        else:  # Afternoon
            return np.array([0.2, 0.3, 0.5])   # Favor puts
    
    def _mock_prediction(self, features: np.ndarray) -> Tuple[int, np.ndarray]:
        """Mock prediction for testing without model"""
        time_progress = features[0]
        
        if time_progress < 0.1 or time_progress > 0.9:
            action = 0  # Hold near open/close
            probs = np.array([0.8, 0.1, 0.1])
        elif time_progress < 0.5:
            action = 1  # Morning calls
            probs = np.array([0.2, 0.6, 0.2])
        else:
            action = 2  # Afternoon puts
            probs = np.array([0.2, 0.2, 0.6])
            
        return action, probs
    
    def _generate_reasoning(self, 
                          action: int,
                          features: np.ndarray,
                          market_data: Dict) -> Dict:
        """Generate human-readable reasoning"""
        base_features = features[:8]
        memory_features = features[8:] if len(features) > 8 else None
        
        reasons = {
            'primary_factors': [],
            'market_conditions': [],
            'risk_assessment': "",
            'confidence_factors': []
        }
        
        # Time-based reasoning
        time_progress = base_features[0]
        if time_progress < 0.08:
            reasons['primary_factors'].append("Early session - limited data")
        elif time_progress > 0.92:
            reasons['primary_factors'].append("Near market close")
        
        # Volatility reasoning
        atm_iv = base_features[2]
        if atm_iv > 0.25:
            reasons['market_conditions'].append(f"Elevated volatility ({atm_iv:.1%})")
        elif atm_iv < 0.15:
            reasons['market_conditions'].append(f"Low volatility ({atm_iv:.1%})")
        
        # Risk assessment
        risk_score = base_features[6]
        if risk_score < 0.3:
            reasons['risk_assessment'] = "Low risk environment"
        elif risk_score < 0.6:
            reasons['risk_assessment'] = "Moderate risk"
        else:
            reasons['risk_assessment'] = "High risk - proceed with caution"
        
        # Memory-based reasoning
        if memory_features is not None:
            acceptance_rate = memory_features[5]
            if acceptance_rate > 0.7:
                reasons['confidence_factors'].append("High recent acceptance rate")
            elif acceptance_rate < 0.3:
                reasons['confidence_factors'].append("Low recent acceptance rate")
        
        # Action-specific reasoning
        if action == 0:
            reasons['primary_factors'].append("No clear edge identified")
        elif action == 1:
            reasons['primary_factors'].append("Call premium opportunity")
        else:
            reasons['primary_factors'].append("Put premium opportunity")
            
        return reasons
    
    def _check_constraints(self, features: np.ndarray, market_data: Dict) -> Dict:
        """Check trading constraints"""
        constraints = {
            'can_trade': True,
            'position_limit_ok': True,
            'risk_limit_ok': True,
            'time_constraint_ok': True,
            'market_hours_ok': True
        }
        
        # Check time constraints
        time_progress = features[0]
        if time_progress < 0.08:  # First 30 min
            constraints['time_constraint_ok'] = False
            constraints['can_trade'] = False
        elif time_progress > 0.92:  # Last 30 min
            constraints['time_constraint_ok'] = False
            constraints['can_trade'] = False
        
        # Check risk constraints
        risk_score = features[6]
        if risk_score > 0.8:
            constraints['risk_limit_ok'] = False
            constraints['can_trade'] = False
        
        # Check if has position (simplified)
        has_position = features[3]
        if has_position > 0:
            constraints['position_limit_ok'] = False
            
        return constraints