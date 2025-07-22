"""
Federated Learning Coordinator Service

Enables privacy-preserving collective intelligence by:
- Aggregating model updates from individual agents
- Computing global model improvements without accessing user data
- Distributing improved models back to agents
- Ensuring differential privacy in aggregation
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import numpy as np
import asyncio
import ray
from datetime import datetime
import uuid
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FNTX Federated Learning Coordinator", version="1.0.0")


class ModelUpdate(BaseModel):
    """Individual model update from an agent"""
    agent_id: str
    user_id: str
    model_type: str
    weights_delta: Dict[str, List[float]]  # Layer name -> weight deltas
    performance_metrics: Dict[str, float]
    training_samples: int
    timestamp: datetime = datetime.now()


class AggregationRequest(BaseModel):
    """Request to aggregate model updates"""
    round_id: Optional[str] = None
    min_participants: int = 10
    aggregation_method: str = "fedavg"  # fedavg, weighted_avg, secure_agg
    differential_privacy: bool = True
    epsilon: float = 1.0  # Privacy budget


class GlobalModel(BaseModel):
    """Global model after aggregation"""
    round_id: str
    model_type: str
    weights: Dict[str, List[float]]
    participants: int
    avg_performance: Dict[str, float]
    timestamp: datetime


@ray.remote
class FederatedAggregator:
    """
    Ray actor for performing federated aggregation
    Runs on GPU for efficient computation
    """
    
    def __init__(self):
        self.pending_updates: Dict[str, List[ModelUpdate]] = {}
        self.global_models: Dict[str, GlobalModel] = {}
        self.round_counter = 0
    
    async def add_update(self, update: ModelUpdate) -> str:
        """Add a model update to pending aggregation"""
        round_id = f"round_{self.round_counter}"
        
        if round_id not in self.pending_updates:
            self.pending_updates[round_id] = []
        
        self.pending_updates[round_id].append(update)
        logger.info(f"Added update from agent {update.agent_id} to round {round_id}")
        
        return round_id
    
    async def aggregate_updates(self, request: AggregationRequest) -> GlobalModel:
        """Perform federated aggregation on pending updates"""
        round_id = request.round_id or f"round_{self.round_counter}"
        
        if round_id not in self.pending_updates:
            raise ValueError(f"No updates pending for round {round_id}")
        
        updates = self.pending_updates[round_id]
        
        if len(updates) < request.min_participants:
            raise ValueError(
                f"Insufficient participants: {len(updates)} < {request.min_participants}"
            )
        
        logger.info(f"Aggregating {len(updates)} updates for round {round_id}")
        
        # Perform aggregation based on method
        if request.aggregation_method == "fedavg":
            global_weights = self._federated_averaging(updates)
        elif request.aggregation_method == "weighted_avg":
            global_weights = self._weighted_averaging(updates)
        elif request.aggregation_method == "secure_agg":
            global_weights = self._secure_aggregation(updates)
        else:
            raise ValueError(f"Unknown aggregation method: {request.aggregation_method}")
        
        # Apply differential privacy if requested
        if request.differential_privacy:
            global_weights = self._apply_differential_privacy(
                global_weights, request.epsilon
            )
        
        # Compute average performance metrics
        avg_metrics = self._compute_average_metrics(updates)
        
        # Create global model
        global_model = GlobalModel(
            round_id=round_id,
            model_type=updates[0].model_type,
            weights=global_weights,
            participants=len(updates),
            avg_performance=avg_metrics,
            timestamp=datetime.now()
        )
        
        # Store global model
        self.global_models[round_id] = global_model
        
        # Clear pending updates for this round
        del self.pending_updates[round_id]
        self.round_counter += 1
        
        logger.info(f"Aggregation complete for round {round_id}")
        
        return global_model
    
    def _federated_averaging(self, updates: List[ModelUpdate]) -> Dict[str, List[float]]:
        """Standard FederatedAveraging algorithm"""
        # Initialize aggregated weights
        aggregated = {}
        
        # Get total training samples for normalization
        total_samples = sum(u.training_samples for u in updates)
        
        for update in updates:
            weight = update.training_samples / total_samples
            
            for layer_name, deltas in update.weights_delta.items():
                if layer_name not in aggregated:
                    aggregated[layer_name] = np.zeros_like(deltas)
                
                aggregated[layer_name] += np.array(deltas) * weight
        
        # Convert back to lists
        return {k: v.tolist() for k, v in aggregated.items()}
    
    def _weighted_averaging(self, updates: List[ModelUpdate]) -> Dict[str, List[float]]:
        """Weighted averaging based on performance metrics"""
        # Use Sharpe ratio as weight
        sharpe_ratios = [u.performance_metrics.get('sharpe_ratio', 0) for u in updates]
        
        # Normalize weights (softmax to ensure positive weights)
        weights = np.exp(sharpe_ratios) / np.sum(np.exp(sharpe_ratios))
        
        aggregated = {}
        
        for i, update in enumerate(updates):
            for layer_name, deltas in update.weights_delta.items():
                if layer_name not in aggregated:
                    aggregated[layer_name] = np.zeros_like(deltas)
                
                aggregated[layer_name] += np.array(deltas) * weights[i]
        
        return {k: v.tolist() for k, v in aggregated.items()}
    
    def _secure_aggregation(self, updates: List[ModelUpdate]) -> Dict[str, List[float]]:
        """Secure aggregation with privacy guarantees"""
        # Simplified secure aggregation
        # In production, use cryptographic techniques like SecAgg
        
        aggregated = {}
        n = len(updates)
        
        for update in updates:
            for layer_name, deltas in update.weights_delta.items():
                if layer_name not in aggregated:
                    aggregated[layer_name] = np.zeros_like(deltas)
                
                # Add noise for privacy during aggregation
                noise = np.random.laplace(0, 0.01, size=len(deltas))
                aggregated[layer_name] += (np.array(deltas) + noise) / n
        
        return {k: v.tolist() for k, v in aggregated.items()}
    
    def _apply_differential_privacy(
        self, weights: Dict[str, List[float]], epsilon: float
    ) -> Dict[str, List[float]]:
        """Apply differential privacy to aggregated weights"""
        private_weights = {}
        
        for layer_name, layer_weights in weights.items():
            # Calculate sensitivity (L2 norm clipping)
            sensitivity = 1.0  # Assuming weights are already clipped
            
            # Add Laplacian noise
            scale = sensitivity / epsilon
            noise = np.random.laplace(0, scale, size=len(layer_weights))
            
            private_weights[layer_name] = (np.array(layer_weights) + noise).tolist()
        
        return private_weights
    
    def _compute_average_metrics(self, updates: List[ModelUpdate]) -> Dict[str, float]:
        """Compute average performance metrics across updates"""
        metrics_sum = {}
        
        for update in updates:
            for metric, value in update.performance_metrics.items():
                if metric not in metrics_sum:
                    metrics_sum[metric] = 0
                metrics_sum[metric] += value
        
        # Average metrics
        n = len(updates)
        return {k: v / n for k, v in metrics_sum.items()}
    
    async def get_global_model(self, round_id: str) -> Optional[GlobalModel]:
        """Retrieve a global model by round ID"""
        return self.global_models.get(round_id)
    
    async def get_latest_model(self, model_type: str) -> Optional[GlobalModel]:
        """Get the latest global model for a specific type"""
        for round_id in sorted(self.global_models.keys(), reverse=True):
            model = self.global_models[round_id]
            if model.model_type == model_type:
                return model
        return None


# Initialize Ray and create aggregator actor
aggregator = None


@app.on_event("startup")
async def startup_event():
    """Initialize Ray and create aggregator actor"""
    global aggregator
    
    if not ray.is_initialized():
        ray.init(address=os.getenv("RAY_ADDRESS", "auto"))
    
    aggregator = FederatedAggregator.remote()
    logger.info("Federated Learning Coordinator started")


@app.post("/updates/submit", response_model=Dict[str, str])
async def submit_update(update: ModelUpdate):
    """Submit a model update for aggregation"""
    if not aggregator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        round_id = await aggregator.add_update.remote(update)
        return {
            "status": "accepted",
            "round_id": round_id,
            "message": f"Update from agent {update.agent_id} added to aggregation round"
        }
    except Exception as e:
        logger.error(f"Failed to submit update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/aggregate", response_model=GlobalModel)
async def trigger_aggregation(
    request: AggregationRequest,
    background_tasks: BackgroundTasks
):
    """Trigger aggregation of pending updates"""
    if not aggregator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        global_model = await aggregator.aggregate_updates.remote(request)
        
        # Schedule distribution of global model
        background_tasks.add_task(distribute_global_model, global_model)
        
        return global_model
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{round_id}", response_model=GlobalModel)
async def get_global_model(round_id: str):
    """Retrieve a specific global model"""
    if not aggregator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    model = await aggregator.get_global_model.remote(round_id)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model for round {round_id} not found")
    
    return model


@app.get("/models/latest/{model_type}", response_model=GlobalModel)
async def get_latest_model(model_type: str):
    """Get the latest global model for a specific type"""
    if not aggregator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    model = await aggregator.get_latest_model.remote(model_type)
    
    if not model:
        raise HTTPException(
            status_code=404, 
            detail=f"No global model found for type {model_type}"
        )
    
    return model


async def distribute_global_model(model: GlobalModel):
    """Distribute global model to participating agents"""
    # In production, this would publish to Pulsar
    # For now, just log the distribution
    logger.info(
        f"Distributing global model {model.round_id} to {model.participants} participants"
    )
    
    # TODO: Implement actual distribution via Pulsar
    # - Publish to agent-specific topics
    # - Include model weights and metadata
    # - Track distribution confirmations


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "federated-learning",
        "ray_initialized": ray.is_initialized() if ray else False
    }


if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("FL_SERVICE_PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)