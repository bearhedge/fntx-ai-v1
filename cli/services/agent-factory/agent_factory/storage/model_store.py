"""
Model Store for saving and loading trained agents
"""
import os
import json
import pickle
import aioredis
from typing import Optional, Dict, Any
from datetime import datetime
import ray


class ModelStore:
    """
    Manages storage and retrieval of trained agents
    Uses Redis for metadata and filesystem for model weights
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.model_dir = os.getenv("MODEL_DIR", "/models")
        self.redis_client = None
        
        # Ensure model directory exists
        os.makedirs(self.model_dir, exist_ok=True)
    
    async def _get_redis(self):
        """Get Redis connection"""
        if not self.redis_client:
            self.redis_client = await aioredis.create_redis_pool(self.redis_url)
        return self.redis_client
    
    async def save_agent(self, agent) -> str:
        """Save agent to storage"""
        agent_id = agent.agent_id
        
        # Save model weights to filesystem
        model_path = os.path.join(self.model_dir, f"{agent_id}.pkl")
        
        # For Ray actors, we need to get the state
        if hasattr(agent, 'remote'):
            # Agent is a Ray actor
            agent_state = ray.get(agent.get_state.remote())
        else:
            agent_state = agent.__dict__
        
        with open(model_path, 'wb') as f:
            pickle.dump(agent_state, f)
        
        # Save metadata to Redis
        redis = await self._get_redis()
        metadata = {
            "agent_id": agent_id,
            "user_id": agent.user_id,
            "agent_type": agent.__class__.__name__,
            "created_at": str(agent.created_at),
            "model_path": model_path,
            "is_trained": agent.is_trained,
            "performance_metrics": agent.get_performance_metrics()
        }
        
        await redis.hset(
            f"agent:{agent_id}",
            mapping={k: json.dumps(v) if isinstance(v, dict) else str(v) 
                    for k, v in metadata.items()}
        )
        
        # Add to user's agent list
        await redis.sadd(f"user_agents:{agent.user_id}", agent_id)
        
        return agent_id
    
    async def load_agent(self, agent_id: str):
        """Load agent from storage"""
        redis = await self._get_redis()
        
        # Get metadata from Redis
        metadata = await redis.hgetall(f"agent:{agent_id}")
        if not metadata:
            return None
        
        # Decode metadata
        metadata = {k.decode(): v.decode() for k, v in metadata.items()}
        
        # Load model weights from filesystem
        model_path = metadata.get('model_path')
        if not model_path or not os.path.exists(model_path):
            return None
        
        with open(model_path, 'rb') as f:
            agent_state = pickle.load(f)
        
        # Reconstruct agent based on type
        agent_type = metadata.get('agent_type')
        
        if agent_type == 'EnsembleAgent':
            from agent_factory.models.ensemble_agent import EnsembleAgent
            agent = EnsembleAgent(
                user_id=metadata['user_id'],
                config=agent_state.get('config', {})
            )
            # Restore state
            agent.__dict__.update(agent_state)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return agent
    
    async def list_user_agents(self, user_id: str) -> list:
        """List all agents for a user"""
        redis = await self._get_redis()
        agent_ids = await redis.smembers(f"user_agents:{user_id}")
        
        agents = []
        for agent_id in agent_ids:
            agent_id = agent_id.decode()
            metadata = await redis.hgetall(f"agent:{agent_id}")
            if metadata:
                metadata = {k.decode(): v.decode() for k, v in metadata.items()}
                agents.append(metadata)
        
        return agents
    
    async def delete_agent(self, agent_id: str):
        """Delete an agent"""
        redis = await self._get_redis()
        
        # Get metadata
        metadata = await redis.hgetall(f"agent:{agent_id}")
        if not metadata:
            return
        
        metadata = {k.decode(): v.decode() for k, v in metadata.items()}
        
        # Delete model file
        model_path = metadata.get('model_path')
        if model_path and os.path.exists(model_path):
            os.remove(model_path)
        
        # Delete from Redis
        await redis.delete(f"agent:{agent_id}")
        
        # Remove from user's agent list
        user_id = metadata.get('user_id')
        if user_id:
            await redis.srem(f"user_agents:{user_id}", agent_id)
    
    async def update_metrics(self, agent_id: str, metrics: Dict[str, float]):
        """Update agent performance metrics"""
        redis = await self._get_redis()
        await redis.hset(
            f"agent:{agent_id}",
            "performance_metrics",
            json.dumps(metrics)
        )
        await redis.hset(
            f"agent:{agent_id}",
            "last_updated",
            str(datetime.now())
        )