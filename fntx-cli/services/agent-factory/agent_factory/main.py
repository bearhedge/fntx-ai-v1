"""
Agent Factory Service - Main entry point
"""
import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import ray
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pulsar

from agent_factory.models.ensemble_agent import EnsembleAgent
from agent_factory.storage.model_store import ModelStore
from agent_factory.config import settings

# Initialize FastAPI app
app = FastAPI(title="FNTX Agent Factory", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Ray
ray.init(address=os.getenv("RAY_ADDRESS", "auto"))

# Initialize Pulsar client
pulsar_client = pulsar.Client(
    os.getenv("PULSAR_URL", "pulsar://localhost:6650")
)

# Initialize model store
model_store = ModelStore()

# Request models
class CreateAgentRequest(BaseModel):
    user_id: str
    agent_type: str = "ensemble"  # ensemble, ppo, a2c, ddpg
    config: Optional[Dict[str, Any]] = None

class TrainAgentRequest(BaseModel):
    agent_id: str
    training_data: Optional[Dict[str, Any]] = None
    epochs: int = 10

class AgentResponse(BaseModel):
    agent_id: str
    status: str
    performance_metrics: Optional[Dict[str, float]] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "agent-factory"}

@app.post("/agents/create", response_model=AgentResponse)
async def create_agent(request: CreateAgentRequest):
    """Create a new personalized trading agent"""
    try:
        # Create agent based on type
        if request.agent_type == "ensemble":
            agent = EnsembleAgent(
                user_id=request.user_id,
                config=request.config or {}
            )
        else:
            raise ValueError(f"Unsupported agent type: {request.agent_type}")
        
        # Save agent to model store
        agent_id = await model_store.save_agent(agent)
        
        # Publish agent creation event
        producer = pulsar_client.create_producer("agent-events")
        producer.send(
            f"agent_created:{agent_id}:{request.user_id}".encode("utf-8")
        )
        producer.close()
        
        return AgentResponse(
            agent_id=agent_id,
            status="created",
            performance_metrics=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_id}/train", response_model=AgentResponse)
async def train_agent(agent_id: str, request: TrainAgentRequest):
    """Train an existing agent with new data"""
    try:
        # Load agent from model store
        agent = await model_store.load_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Train agent (this would be done asynchronously in production)
        metrics = await agent.train(
            training_data=request.training_data,
            epochs=request.epochs
        )
        
        # Save updated agent
        await model_store.save_agent(agent)
        
        # Publish training completion event
        producer = pulsar_client.create_producer("agent-events")
        producer.send(
            f"agent_trained:{agent_id}:{metrics}".encode("utf-8")
        )
        producer.close()
        
        return AgentResponse(
            agent_id=agent_id,
            status="trained",
            performance_metrics=metrics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent details and performance metrics"""
    try:
        agent = await model_store.load_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        metrics = agent.get_performance_metrics()
        
        return AgentResponse(
            agent_id=agent_id,
            status="active",
            performance_metrics=metrics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_id}/predict")
async def predict(agent_id: str, market_data: Dict[str, Any]):
    """Get trading predictions from agent"""
    try:
        agent = await model_store.load_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        prediction = await agent.predict(market_data)
        
        return {"agent_id": agent_id, "prediction": prediction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)