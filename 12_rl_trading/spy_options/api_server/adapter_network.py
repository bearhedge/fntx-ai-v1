"""
Lightweight Adapter Network for CPU-based personalization
Learns user preferences on top of frozen base model
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID
import logging
from datetime import datetime


class AdapterNetwork(nn.Module):
    """
    Small neural network that adapts base model to user preferences
    Runs on CPU, updates quickly after each session
    """
    
    def __init__(self, input_dim: int = 20, hidden_dim: int = 64, output_dim: int = 3):
        super(AdapterNetwork, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # Lightweight architecture
        self.layers = nn.Sequential(
            nn.Linear(input_dim + output_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Softmax(dim=-1)
        )
        
        # Residual connection weight
        self.residual_weight = nn.Parameter(torch.tensor(0.8))
        
        # Training components
        self.optimizer = optim.Adam(self.parameters(), lr=0.001)
        self.criterion = nn.CrossEntropyLoss()
        
        # Memory buffer for online learning
        self.experience_buffer = []
        self.max_buffer_size = 1000
        
        self.logger = logging.getLogger(__name__)
        
    async def forward(self, 
                     features: np.ndarray,
                     base_probs: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Adjust base model probabilities based on learned preferences
        
        Args:
            features: 20-dim feature vector (8 base + 12 memory)
            base_probs: Base model's action probabilities
            
        Returns:
            Adjusted action probabilities
        """
        # Convert to tensor
        features_tensor = torch.FloatTensor(features)
        
        if base_probs is None:
            base_probs = np.array([0.33, 0.33, 0.34])  # Uniform default
        
        base_probs_tensor = torch.FloatTensor(base_probs)
        
        # Concatenate features and base probabilities
        combined_input = torch.cat([features_tensor, base_probs_tensor])
        
        # Forward pass
        with torch.no_grad():
            adapter_output = self.layers(combined_input.unsqueeze(0)).squeeze(0)
        
        # Residual connection: blend base and adapter
        # adjusted = residual_weight * base + (1 - residual_weight) * adapter
        residual_weight = torch.sigmoid(self.residual_weight).detach()
        adjusted_probs = residual_weight * base_probs_tensor + (1 - residual_weight) * adapter_output
        
        # Renormalize
        adjusted_probs = adjusted_probs / adjusted_probs.sum()
        
        return adjusted_probs.detach().numpy()
    
    async def learn_from_feedback(self, 
                                decision_id: UUID,
                                feedback) -> None:
        """
        Update adapter based on user feedback
        Fast online learning - runs in < 1 second on CPU
        """
        # Add to experience buffer
        experience = {
            'decision_id': decision_id,
            'feedback': feedback,
            'timestamp': datetime.now()
        }
        self.experience_buffer.append(experience)
        
        # Maintain buffer size
        if len(self.experience_buffer) > self.max_buffer_size:
            self.experience_buffer.pop(0)
        
        # Perform mini-batch update every 10 feedbacks
        if len(self.experience_buffer) % 10 == 0:
            await self._update_from_buffer()
    
    async def _update_from_buffer(self):
        """Perform batch update from experience buffer"""
        if len(self.experience_buffer) < 10:
            return
            
        # Get recent experiences
        recent_experiences = self.experience_buffer[-50:]
        
        # Prepare training batch
        features_batch = []
        base_probs_batch = []
        targets_batch = []
        
        for exp in recent_experiences:
            feedback = exp['feedback']
            
            # Skip if no decision data
            if not hasattr(feedback, 'decision_id'):
                continue
                
            # Create target based on feedback
            if feedback.accepted:
                # Reinforce the suggested action
                target = feedback.suggested_action
            else:
                # Discourage the suggested action
                # Could be more sophisticated based on rejection_reason
                if feedback.rejection_reason == 'wrong_direction':
                    # Flip to opposite action
                    target = 2 if feedback.suggested_action == 1 else 1
                else:
                    # Default to hold
                    target = 0
            
            # Would need to store features/probs with decision
            # For now, skip actual training
            
        # Perform gradient update
        if features_batch:
            self._train_step(features_batch, base_probs_batch, targets_batch)
            
        self.logger.info(f"Adapter updated with {len(features_batch)} examples")
    
    def _train_step(self, features, base_probs, targets):
        """Single training step"""
        # Convert to tensors
        features_tensor = torch.FloatTensor(features)
        base_probs_tensor = torch.FloatTensor(base_probs)
        targets_tensor = torch.LongTensor(targets)
        
        # Combine inputs
        combined_input = torch.cat([features_tensor, base_probs_tensor], dim=1)
        
        # Forward pass
        self.optimizer.zero_grad()
        output = self.layers(combined_input)
        
        # Calculate loss
        loss = self.criterion(output, targets_tensor)
        
        # Backward pass
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def adapt_to_preference(self, preference_type: str, strength: float = 0.1):
        """
        Directly adapt network for known preferences
        E.g., "avoid_morning_calls" or "prefer_tight_spreads"
        """
        with torch.no_grad():
            if preference_type == "avoid_morning_calls":
                # Reduce weight connecting morning time features to call action
                # This is simplified - real implementation would be more targeted
                self.layers[0].weight[0, :8] *= (1 - strength)
            
            elif preference_type == "conservative_risk":
                # Increase influence of risk features on hold action
                self.layers[0].weight[2, 6] *= (1 + strength)
                
            # Add more preference adaptations as discovered
    
    def save(self, path: Path):
        """Save adapter network to disk"""
        torch.save({
            'model_state_dict': self.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'experience_buffer': self.experience_buffer[-100:],  # Keep recent 100
            'timestamp': datetime.now().isoformat()
        }, path)
        
        self.logger.info(f"Adapter saved to {path}")
    
    def load(self, path: Path):
        """Load adapter network from disk"""
        if not path.exists():
            self.logger.warning(f"No adapter found at {path}")
            return
            
        checkpoint = torch.load(path, map_location='cpu')
        self.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.experience_buffer = checkpoint.get('experience_buffer', [])
        
        self.logger.info(f"Adapter loaded from {path}")
    
    def get_adaptation_summary(self) -> dict:
        """Get summary of current adaptations"""
        with torch.no_grad():
            # Analyze weights to understand adaptations
            first_layer_weights = self.layers[0].weight.numpy()
            
            # Feature importance (simplified)
            feature_importance = np.abs(first_layer_weights).mean(axis=0)
            
            # Action biases
            output_biases = self.layers[-2].bias.numpy()
            
            return {
                'residual_weight': float(torch.sigmoid(self.residual_weight)),
                'feature_importance': {
                    'time_features': float(feature_importance[:2].mean()),
                    'market_features': float(feature_importance[2:6].mean()),
                    'risk_features': float(feature_importance[6:8].mean()),
                    'memory_features': float(feature_importance[8:].mean())
                },
                'action_biases': {
                    'hold': float(output_biases[0]),
                    'call': float(output_biases[1]),
                    'put': float(output_biases[2])
                },
                'total_experiences': len(self.experience_buffer)
            }