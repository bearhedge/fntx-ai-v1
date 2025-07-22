#!/usr/bin/env python3
"""
FastAPI server for SPY Options AI with Memory
Provides predictions with context and continuous learning
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from stable_baselines3 import PPO

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from memory_system import MemoryManager, ContextEncoder
from data_pipeline import FeatureEngine, PositionTracker
from api_server import ModelService, AdapterNetwork


# Request/Response models
class PredictionRequest(BaseModel):
    """Request for AI prediction"""
    features: List[float]  # 8 base features
    market_data: Dict
    include_memory: bool = True
    include_reasoning: bool = True


class FeedbackRequest(BaseModel):
    """User feedback on AI suggestion"""
    decision_id: str
    accepted: bool
    rejection_reason: Optional[str] = None
    user_comment: Optional[str] = None
    response_time_seconds: int
    executed_strike: Optional[float] = None
    executed_contracts: Optional[int] = None
    fill_price: Optional[float] = None


class PredictionResponse(BaseModel):
    """AI prediction with context"""
    decision_id: str
    action: int  # 0=hold, 1=call, 2=put
    action_name: str
    confidence: float
    action_probabilities: Optional[List[float]]
    
    # Memory context
    memory_context: Optional[Dict]
    similar_historical: Optional[List[Dict]]
    applied_preferences: Optional[List[str]]
    
    # Reasoning
    reasoning: Optional[Dict]
    memory_impact: Optional[List[str]]


class StatusResponse(BaseModel):
    """API status and statistics"""
    status: str
    model_version: str
    memory_enabled: bool
    adapter_enabled: bool
    session_stats: Dict
    uptime_seconds: int


# Initialize FastAPI app
app = FastAPI(
    title="SPY Options AI API",
    description="AI predictions with persistent memory and learning",
    version="2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
model_service: Optional[ModelService] = None
memory_manager: Optional[MemoryManager] = None
context_encoder: Optional[ContextEncoder] = None
adapter_network: Optional[AdapterNetwork] = None
startup_time: datetime = None

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup"""
    global model_service, memory_manager, context_encoder, adapter_network, startup_time
    
    startup_time = datetime.now()
    logger.info("Starting SPY Options AI API Server...")
    
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'info'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'fntx_trading')
    }
    
    # Initialize memory manager
    memory_manager = MemoryManager(db_config)
    await memory_manager.initialize()
    logger.info("Memory manager initialized")
    
    # Initialize context encoder
    context_encoder = ContextEncoder(memory_manager)
    logger.info("Context encoder initialized")
    
    # Load base model
    model_path = os.getenv('MODEL_PATH', 'models/gpu_trained/ppo_gpu_test_20250706_074954.zip')
    if Path(model_path).exists():
        base_model = PPO.load(model_path)
        logger.info(f"Loaded model from {model_path}")
    else:
        logger.warning(f"Model not found at {model_path}, using mock model")
        base_model = None
    
    # Initialize adapter network
    adapter_network = AdapterNetwork(input_dim=20, hidden_dim=64, output_dim=3)
    adapter_path = Path("models/adapter_network.pt")
    if adapter_path.exists():
        adapter_network.load(adapter_path)
        logger.info("Loaded adapter network")
    
    # Initialize model service
    model_service = ModelService(
        base_model=base_model,
        adapter_network=adapter_network,
        context_encoder=context_encoder
    )
    
    logger.info("API server initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if memory_manager:
        await memory_manager.close()
    logger.info("API server shutdown complete")


@app.get("/", response_model=StatusResponse)
async def get_status():
    """Get API status and statistics"""
    uptime = (datetime.now() - startup_time).total_seconds() if startup_time else 0
    
    # Get session stats
    session_stats = {}
    if memory_manager and memory_manager.current_session_id:
        # Would query database for stats
        session_stats = {
            "session_id": str(memory_manager.current_session_id),
            "suggestions_today": 0,  # Would query
            "acceptance_rate": 0.0   # Would calculate
        }
    
    return StatusResponse(
        status="healthy",
        model_version="ppo_2m_v1",
        memory_enabled=memory_manager is not None,
        adapter_enabled=adapter_network is not None,
        session_stats=session_stats,
        uptime_seconds=int(uptime)
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Get AI prediction with memory context"""
    try:
        # Convert to numpy array
        base_features = np.array(request.features, dtype=np.float32)
        
        if len(base_features) != 8:
            raise HTTPException(400, "Expected 8 features")
        
        # Get prediction with memory
        result = await model_service.predict_with_memory(
            base_features,
            request.market_data,
            include_reasoning=request.include_reasoning
        )
        
        # Record decision in background
        background_tasks.add_task(
            record_decision,
            result['decision_id'],
            base_features,
            result['action'],
            result.get('action_probabilities'),
            result['confidence'],
            request.market_data,
            result.get('reasoning', {}),
            result.get('constraints', {})
        )
        
        return PredictionResponse(
            decision_id=str(result['decision_id']),
            action=result['action'],
            action_name=result['action_name'],
            confidence=result['confidence'],
            action_probabilities=result.get('action_probabilities'),
            memory_context=result.get('memory_context'),
            similar_historical=result.get('similar_historical'),
            applied_preferences=result.get('applied_preferences'),
            reasoning=result.get('reasoning'),
            memory_impact=result.get('memory_impact')
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(500, str(e))


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback on AI suggestion"""
    try:
        # Create feedback object
        from memory_system.memory_manager import UserFeedback
        
        feedback = UserFeedback(
            decision_id=UUID(request.decision_id),
            accepted=request.accepted,
            rejection_reason=request.rejection_reason,
            user_comment=request.user_comment,
            response_time_seconds=request.response_time_seconds,
            executed_strike=request.executed_strike,
            executed_contracts=request.executed_contracts,
            fill_price=request.fill_price
        )
        
        # Record feedback
        await memory_manager.record_feedback(feedback)
        
        # Update adapter network if rejected
        if not request.accepted and adapter_network:
            await adapter_network.learn_from_feedback(
                UUID(request.decision_id),
                feedback
            )
        
        return {"status": "success", "message": "Feedback recorded"}
        
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        raise HTTPException(500, str(e))


@app.get("/memory/similar")
async def get_similar_contexts(spy_price: float, vix: float):
    """Find similar historical contexts"""
    try:
        similar = await memory_manager.find_similar_contexts(
            spy_price, vix, datetime.now()
        )
        return {"similar_contexts": similar}
    except Exception as e:
        logger.error(f"Similar context error: {e}")
        raise HTTPException(500, str(e))


@app.get("/memory/preferences")
async def get_preferences():
    """Get learned user preferences"""
    try:
        preferences = await memory_manager.get_learned_preferences()
        return {"preferences": preferences}
    except Exception as e:
        logger.error(f"Preferences error: {e}")
        raise HTTPException(500, str(e))


@app.post("/session/new")
async def start_new_session():
    """Start a new trading session"""
    try:
        session_id = await memory_manager.start_new_session()
        return {"session_id": str(session_id)}
    except Exception as e:
        logger.error(f"Session error: {e}")
        raise HTTPException(500, str(e))


@app.post("/adapter/save")
async def save_adapter():
    """Save adapter network to disk"""
    try:
        if adapter_network:
            adapter_network.save(Path("models/adapter_network.pt"))
            return {"status": "success", "message": "Adapter saved"}
        else:
            raise HTTPException(400, "No adapter network loaded")
    except Exception as e:
        logger.error(f"Adapter save error: {e}")
        raise HTTPException(500, str(e))


# Background task functions
async def record_decision(decision_id: UUID, features: np.ndarray, 
                         action: int, action_probs: Optional[np.ndarray],
                         confidence: float, market_data: Dict,
                         reasoning: Dict, constraints: Dict):
    """Record decision in memory database"""
    try:
        await memory_manager.record_decision(
            features, action, action_probs, confidence,
            market_data, reasoning, constraints
        )
    except Exception as e:
        logger.error(f"Failed to record decision: {e}")


def main():
    """Run the API server"""
    port = int(os.getenv('API_PORT', 8100))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()