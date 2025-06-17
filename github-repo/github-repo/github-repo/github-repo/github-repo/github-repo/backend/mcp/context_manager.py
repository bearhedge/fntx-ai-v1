"""
MCP Context Manager - Core orchestrator for the Model Context Protocol system.
Manages agent memory persistence, retrieval, and cross-agent knowledge sharing.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

from ..database.redis_client import RedisClient
from ..database.postgres_client import PostgreSQLClient
from ..database.gcs_client import GCSClient
from .vector_store import VectorStore
from .memory_store import MemoryStore
from ..utils.embeddings import EmbeddingGenerator
from .schemas import (
    MemorySlice, MemoryQuery, MemoryType, MemoryImportance,
    TradingSession, ExecutionPlan, TradeOutcome, MarketIntelligence,
    AgentMemory
)

logger = logging.getLogger(__name__)


class MCPContextManager:
    """
    Central context manager for MCP system.
    Coordinates memory operations across all agents and storage tiers.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MCP context manager.
        
        Args:
            config: Configuration dictionary with connection details
        """
        self.config = config
        
        # Initialize storage clients
        self.redis = RedisClient(
            host=config.get('redis_host', 'localhost'),
            port=config.get('redis_port', 6379),
            password=config.get('redis_password'),
            db=config.get('redis_db', 0)
        )
        
        self.postgres = PostgreSQLClient(
            host=config.get('postgres_host', 'localhost'),
            port=config.get('postgres_port', 5432),
            database=config.get('postgres_database', 'fntx_mcp'),
            user=config.get('postgres_user', 'postgres'),
            password=config.get('postgres_password')
        )
        
        self.gcs = GCSClient(
            bucket_name=config.get('gcs_bucket', 'fntx-mcp-storage'),
            credentials_path=config.get('gcs_credentials_path')
        )
        
        self.vector_store = VectorStore(
            api_key=config.get('pinecone_api_key'),
            environment=config.get('pinecone_environment', 'us-east-1'),
            index_name=config.get('pinecone_index', 'fntx-agent-memories')
        )
        
        self.embeddings = EmbeddingGenerator(
            model_name=config.get('embedding_model', 'text-embedding-ada-002'),
            api_key=config.get('openai_api_key')
        )
        
        # Initialize memory store
        self.memory_store = MemoryStore(
            self.redis, self.postgres, self.gcs, 
            self.vector_store, self.embeddings
        )
        
        # Active sessions tracking
        self._active_sessions: Dict[str, TradingSession] = {}
        
        # Agent registry
        self._registered_agents: Set[str] = set()
        
        # Context sharing channels
        self._context_channels: Dict[str, List[str]] = {}
        
    async def initialize(self) -> None:
        """Initialize all components and load active sessions."""
        try:
            # Initialize memory store
            await self.memory_store.initialize()
            
            # Load active sessions from Redis
            session_keys = await self.redis.scan_match("session:*")
            for key in session_keys:
                session_data = await self.redis.get_json(key)
                if session_data:
                    session = TradingSession(**session_data)
                    self._active_sessions[session.session_id] = session
                    
            # Load registered agents
            agents = await self.redis.smembers("registered_agents")
            self._registered_agents = set(agents)
            
            logger.info(f"MCP Context Manager initialized with {len(self._active_sessions)} "
                       f"active sessions and {len(self._registered_agents)} registered agents")
                       
        except Exception as e:
            logger.error(f"Failed to initialize MCP Context Manager: {e}")
            raise
            
    async def shutdown(self) -> None:
        """Shutdown all components gracefully."""
        try:
            # Save active sessions
            for session_id, session in self._active_sessions.items():
                await self.redis.set_json(
                    f"session:{session_id}",
                    session.dict(),
                    ttl=86400  # Keep for 24 hours
                )
                
            # Close memory store
            await self.memory_store.close()
            
            logger.info("MCP Context Manager shut down")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    # Agent Registration
    
    async def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """
        Register an agent with the MCP system.
        
        Args:
            agent_id: Unique agent identifier
            capabilities: List of agent capabilities
        """
        try:
            # Add to registry
            self._registered_agents.add(agent_id)
            await self.redis.sadd("registered_agents", agent_id)
            
            # Store capabilities
            await self.redis.set_json(
                f"agent_capabilities:{agent_id}",
                capabilities,
                ttl=None  # Permanent
            )
            
            logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            raise
            
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the MCP system."""
        try:
            self._registered_agents.discard(agent_id)
            await self.redis.srem("registered_agents", agent_id)
            await self.redis.delete(f"agent_capabilities:{agent_id}")
            
            logger.info(f"Unregistered agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            
    # Session Management
    
    async def create_session(self, user_id: str) -> TradingSession:
        """
        Create a new trading session.
        
        Args:
            user_id: User ID for the session
            
        Returns:
            New trading session
        """
        try:
            session = TradingSession(
                user_id=user_id,
                start_time=datetime.utcnow(),
                status="active"
            )
            
            # Store in active sessions
            self._active_sessions[session.session_id] = session
            
            # Persist to Redis
            await self.redis.set_json(
                f"session:{session.session_id}",
                session.dict(),
                ttl=86400  # 24 hours
            )
            
            # Notify agents of new session
            await self._broadcast_context_update({
                'event': 'session_created',
                'session_id': session.session_id,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Created session {session.session_id} for user {user_id}")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
            
    async def end_session(self, session_id: str) -> None:
        """End a trading session and consolidate memories."""
        try:
            session = self._active_sessions.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return
                
            # Update session status
            session.end_time = datetime.utcnow()
            session.status = "completed"
            
            # Consolidate session memories
            consolidated = await self.memory_store.consolidate_session_memories(session_id)
            
            # Archive session
            await self.gcs.upload_json(
                f"sessions/completed/{session_id}/session.json",
                {
                    'session': session.dict(),
                    'consolidated_memories': consolidated
                },
                compress=True
            )
            
            # Remove from active sessions
            del self._active_sessions[session_id]
            await self.redis.delete(f"session:{session_id}")
            
            # Notify agents
            await self._broadcast_context_update({
                'event': 'session_ended',
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Ended session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            
    # Memory Operations
    
    async def store_memory(self, agent_id: str, memory: MemorySlice) -> str:
        """
        Store a memory for an agent.
        
        Args:
            agent_id: Agent storing the memory
            memory: Memory slice to store
            
        Returns:
            Memory ID
        """
        try:
            # Ensure agent is registered
            if agent_id not in self._registered_agents:
                raise ValueError(f"Agent {agent_id} not registered")
                
            # Set agent ID
            memory.agent_id = agent_id
            
            # Store memory
            memory_id = await self.memory_store.store_memory(memory)
            
            # Update agent's last activity
            await self.redis.set(
                f"agent_last_activity:{agent_id}",
                datetime.utcnow().isoformat()
            )
            
            # Notify interested agents if high importance
            if memory.importance == MemoryImportance.CRITICAL:
                await self._notify_critical_memory(memory)
                
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory for agent {agent_id}: {e}")
            raise
            
    async def retrieve_memories(self, agent_id: str, query: MemoryQuery) -> List[MemorySlice]:
        """
        Retrieve memories for an agent.
        
        Args:
            agent_id: Agent requesting memories
            query: Memory query parameters
            
        Returns:
            List of matching memories
        """
        try:
            # Set agent ID in query if not specified
            if not query.agent_id:
                query.agent_id = agent_id
                
            # Retrieve memories
            memories = await self.memory_store.query_memories(query)
            
            # Log access for learning
            await self._log_memory_access(agent_id, [m.id for m in memories])
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories for agent {agent_id}: {e}")
            return []
            
    async def semantic_search(self, agent_id: str, query_text: str, 
                            scope: str = "own") -> List[MemorySlice]:
        """
        Perform semantic search across memories.
        
        Args:
            agent_id: Agent performing search
            query_text: Search query
            scope: Search scope - "own", "session", or "global"
            
        Returns:
            List of semantically similar memories
        """
        try:
            # Determine search scope
            filter_agent_id = None
            if scope == "own":
                filter_agent_id = agent_id
            elif scope == "session":
                # Get current session for agent
                session_id = await self._get_agent_session(agent_id)
                if session_id:
                    # Search will be filtered by session in memory store
                    pass
                    
            # Perform semantic search
            memories = await self.memory_store.semantic_search(
                query_text=query_text,
                agent_id=filter_agent_id,
                top_k=20,
                threshold=0.7
            )
            
            # Filter by access permissions
            filtered = []
            for memory in memories:
                if await self._can_access_memory(agent_id, memory):
                    filtered.append(memory)
                    
            return filtered
            
        except Exception as e:
            logger.error(f"Semantic search failed for agent {agent_id}: {e}")
            return []
            
    # Context Sharing
    
    async def share_context(self, from_agent: str, to_agents: List[str], 
                          context: Dict[str, Any]) -> None:
        """
        Share context between agents.
        
        Args:
            from_agent: Agent sharing context
            to_agents: Target agents
            context: Context data to share
        """
        try:
            # Create context message
            message = {
                'from_agent': from_agent,
                'timestamp': datetime.utcnow().isoformat(),
                'context': context
            }
            
            # Send to each target agent
            for agent_id in to_agents:
                if agent_id in self._registered_agents:
                    channel = f"agent_context:{agent_id}"
                    await self.redis.publish(channel, json.dumps(message))
                    
            logger.info(f"Shared context from {from_agent} to {len(to_agents)} agents")
            
        except Exception as e:
            logger.error(f"Failed to share context: {e}")
            
    async def subscribe_to_context(self, agent_id: str) -> asyncio.Queue:
        """
        Subscribe an agent to context updates.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Queue for receiving context updates
        """
        try:
            # Create queue for agent
            queue = asyncio.Queue()
            
            # Subscribe to agent's channel
            channel = f"agent_context:{agent_id}"
            
            async def message_handler(message):
                await queue.put(json.loads(message))
                
            await self.redis.subscribe(channel, message_handler)
            
            logger.info(f"Agent {agent_id} subscribed to context updates")
            
            return queue
            
        except Exception as e:
            logger.error(f"Failed to subscribe agent {agent_id}: {e}")
            raise
            
    # Reflection & Learning
    
    async def submit_reflection(self, agent_id: str, reflection: Dict[str, Any]) -> None:
        """
        Submit a reflection for learning.
        
        Args:
            agent_id: Agent submitting reflection
            reflection: Reflection data
        """
        try:
            # Store as high-importance memory
            memory = MemorySlice(
                agent_id=agent_id,
                memory_type=MemoryType.REFLECTION,
                content=reflection,
                importance=MemoryImportance.HIGH
            )
            
            await self.store_memory(agent_id, memory)
            
            # Trigger learning update
            await self._trigger_learning_update(agent_id, reflection)
            
            logger.info(f"Stored reflection from agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to submit reflection: {e}")
            
    async def get_learning_insights(self, agent_id: str, 
                                  timeframe: timedelta = timedelta(days=7)) -> Dict[str, Any]:
        """
        Get learning insights for an agent.
        
        Args:
            agent_id: Agent ID
            timeframe: Time period to analyze
            
        Returns:
            Learning insights and patterns
        """
        try:
            # Query reflections and evaluations
            query = MemoryQuery(
                agent_id=agent_id,
                memory_types=[MemoryType.REFLECTION, MemoryType.EVALUATION],
                start_time=datetime.utcnow() - timeframe,
                limit=100
            )
            
            memories = await self.memory_store.query_memories(query)
            
            # Analyze patterns
            insights = {
                'total_reflections': len([m for m in memories if m.memory_type == MemoryType.REFLECTION]),
                'total_evaluations': len([m for m in memories if m.memory_type == MemoryType.EVALUATION]),
                'patterns': [],
                'improvements': [],
                'success_factors': []
            }
            
            # Extract patterns from memory content
            for memory in memories:
                content = memory.content
                if 'patterns' in content:
                    insights['patterns'].extend(content['patterns'])
                if 'improvements' in content:
                    insights['improvements'].extend(content['improvements'])
                if 'success_factors' in content:
                    insights['success_factors'].extend(content['success_factors'])
                    
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get learning insights: {e}")
            return {}
            
    # Utility Methods
    
    async def _broadcast_context_update(self, update: Dict[str, Any]) -> None:
        """Broadcast context update to all agents."""
        message = json.dumps(update)
        await self.redis.publish("global_context_updates", message)
        
    async def _notify_critical_memory(self, memory: MemorySlice) -> None:
        """Notify relevant agents of critical memory."""
        # Determine which agents should be notified
        if memory.memory_type == MemoryType.RISK_ALERT:
            target_agents = ["RiskManagerAgent", "ExecutorAgent", "StrategicPlannerAgent"]
        elif memory.memory_type == MemoryType.TRADE_OUTCOME:
            target_agents = ["EvaluatorAgent", "RewardModelAgent"]
        else:
            target_agents = []
            
        await self.share_context(
            memory.agent_id,
            target_agents,
            {
                'critical_memory': memory.dict(),
                'action_required': True
            }
        )
        
    async def _can_access_memory(self, agent_id: str, memory: MemorySlice) -> bool:
        """Check if agent can access a memory."""
        # Agent can always access own memories
        if memory.agent_id == agent_id:
            return True
            
        # Check if memory is shared
        if memory.content.get('shared', False):
            return True
            
        # Check if agents are in same session
        agent_session = await self._get_agent_session(agent_id)
        if agent_session and memory.session_id == agent_session:
            return True
            
        return False
        
    async def _get_agent_session(self, agent_id: str) -> Optional[str]:
        """Get current session for an agent."""
        return await self.redis.get(f"agent_session:{agent_id}")
        
    async def _log_memory_access(self, agent_id: str, memory_ids: List[str]) -> None:
        """Log memory access for learning."""
        access_log = {
            'agent_id': agent_id,
            'memory_ids': memory_ids,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.redis.lpush(
            f"memory_access_log:{agent_id}",
            json.dumps(access_log)
        )
        
        # Trim to last 1000 accesses
        await self.redis.ltrim(f"memory_access_log:{agent_id}", 0, 999)
        
    async def _trigger_learning_update(self, agent_id: str, reflection: Dict[str, Any]) -> None:
        """Trigger learning update based on reflection."""
        # This would integrate with the reward model and learning system
        update = {
            'agent_id': agent_id,
            'reflection': reflection,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.redis.publish("learning_updates", json.dumps(update))
        
    # Context Manager Protocol
    
    @asynccontextmanager
    async def agent_context(self, agent_id: str, session_id: Optional[str] = None):
        """
        Context manager for agent operations.
        
        Usage:
            async with mcp.agent_context("StrategicPlannerAgent") as ctx:
                # Agent operations with automatic context tracking
                memory = await ctx.store_memory(...)
        """
        try:
            # Set agent session if provided
            if session_id:
                await self.redis.set(f"agent_session:{agent_id}", session_id)
                
            # Create context wrapper
            class AgentContext:
                def __init__(self, mcp, agent_id):
                    self.mcp = mcp
                    self.agent_id = agent_id
                    
                async def store_memory(self, memory: MemorySlice) -> str:
                    return await self.mcp.store_memory(self.agent_id, memory)
                    
                async def retrieve_memories(self, query: MemoryQuery) -> List[MemorySlice]:
                    return await self.mcp.retrieve_memories(self.agent_id, query)
                    
                async def semantic_search(self, query_text: str, scope: str = "own") -> List[MemorySlice]:
                    return await self.mcp.semantic_search(self.agent_id, query_text, scope)
                    
                async def share_context(self, to_agents: List[str], context: Dict[str, Any]) -> None:
                    return await self.mcp.share_context(self.agent_id, to_agents, context)
                    
            yield AgentContext(self, agent_id)
            
        finally:
            # Clean up session binding if temporary
            if session_id:
                await self.redis.delete(f"agent_session:{agent_id}")