"""
Memory store abstraction layer for MCP system.
Provides unified interface for memory operations across hot, warm, and cold storage tiers.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
import asyncio
from uuid import uuid4

from ..database.redis_client import RedisClient
from ..database.postgres_client import PostgreSQLClient
from ..database.gcs_client import GCSClient
from .vector_store import VectorStore
from ..utils.embeddings import EmbeddingGenerator
from .schemas import (
    MemorySlice, MemoryQuery, MemoryType, MemoryImportance,
    TradingSession, MarketIntelligence, ExecutionPlan, TradeOutcome
)

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Unified memory store handling hot, warm, and cold storage tiers.
    """
    
    def __init__(self, redis_client: RedisClient, postgres_client: PostgreSQLClient,
                 gcs_client: GCSClient, vector_store: VectorStore, 
                 embedding_generator: EmbeddingGenerator):
        """
        Initialize memory store with all storage backends.
        
        Args:
            redis_client: Redis client for hot storage
            postgres_client: PostgreSQL client for warm storage
            gcs_client: GCS client for cold storage
            vector_store: Vector store for semantic search
            embedding_generator: Embedding generator for semantic search
        """
        self.redis = redis_client
        self.postgres = postgres_client
        self.gcs = gcs_client
        self.vector_store = vector_store
        self.embeddings = embedding_generator
        
        # Memory tier thresholds
        self.hot_threshold = timedelta(hours=24)  # Keep in Redis for 24 hours
        self.warm_threshold = timedelta(days=7)   # Keep in PostgreSQL for 7 days
        
    async def initialize(self) -> None:
        """Initialize all storage backends."""
        await asyncio.gather(
            self.redis.connect(),
            self.postgres.connect(),
            self.gcs.connect(),
            self.vector_store.initialize()
        )
        logger.info("Memory store initialized with all backends")
        
    async def close(self) -> None:
        """Close all storage backends."""
        await asyncio.gather(
            self.redis.close(),
            self.postgres.close(),
            self.gcs.close(),
            self.vector_store.close()
        )
        logger.info("Memory store closed")
        
    async def store_memory(self, memory: MemorySlice) -> str:
        """
        Store a memory slice across appropriate tiers.
        
        Args:
            memory: Memory slice to store
            
        Returns:
            Memory ID
        """
        try:
            # Generate ID if not present
            if not memory.id:
                memory.id = str(uuid4())
                
            # Generate embedding for semantic search
            content_text = json.dumps(memory.content)
            embedding = await self.embeddings.generate(content_text)
            
            # Store in hot tier (Redis) for immediate access
            redis_key = f"memory:{memory.agent_id}:{memory.id}"
            await self.redis.set_json(
                redis_key,
                memory.dict(),
                ttl=int(self.hot_threshold.total_seconds())
            )
            
            # Store in warm tier (PostgreSQL) for persistence
            await self.postgres.execute_query(
                """
                INSERT INTO agent_memories 
                (id, agent_id, session_id, user_id, memory_type, content, 
                 embedding, importance_score, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    importance_score = EXCLUDED.importance_score,
                    updated_at = EXCLUDED.updated_at
                """,
                memory.id,
                memory.agent_id,
                memory.session_id,
                memory.user_id,
                memory.memory_type.value,
                json.dumps(memory.content),
                embedding.tolist(),
                memory.importance.value,
                memory.created_at,
                memory.updated_at
            )
            
            # Index in vector store for semantic search
            await self.vector_store.upsert([{
                'id': memory.id,
                'values': embedding.tolist(),
                'metadata': {
                    'agent_id': memory.agent_id,
                    'session_id': memory.session_id,
                    'user_id': memory.user_id,
                    'memory_type': memory.memory_type.value,
                    'importance': memory.importance.value,
                    'created_at': memory.created_at.isoformat()
                }
            }])
            
            # Add to agent's memory index
            await self._update_memory_index(memory.agent_id, memory.id)
            
            logger.info(f"Stored memory {memory.id} for agent {memory.agent_id}")
            
            return memory.id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
            
    async def retrieve_memory(self, memory_id: str, agent_id: Optional[str] = None) -> Optional[MemorySlice]:
        """
        Retrieve a memory by ID, checking tiers in order.
        
        Args:
            memory_id: Memory ID to retrieve
            agent_id: Optional agent ID for faster lookup
            
        Returns:
            Memory slice if found, None otherwise
        """
        try:
            # Check hot tier first
            redis_key = f"memory:{agent_id}:{memory_id}" if agent_id else f"memory:*:{memory_id}"
            
            if agent_id:
                data = await self.redis.get_json(redis_key)
                if data:
                    return MemorySlice(**data)
            else:
                # Search across all agents
                keys = await self.redis.scan_match(redis_key)
                for key in keys:
                    data = await self.redis.get_json(key)
                    if data:
                        return MemorySlice(**data)
                        
            # Check warm tier
            result = await self.postgres.fetch_one(
                """
                SELECT * FROM agent_memories WHERE id = $1
                """,
                memory_id
            )
            
            if result:
                memory = MemorySlice(
                    id=result['id'],
                    agent_id=result['agent_id'],
                    session_id=result['session_id'],
                    user_id=result['user_id'],
                    memory_type=MemoryType(result['memory_type']),
                    content=json.loads(result['content']),
                    importance=MemoryImportance(result['importance_score']),
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                )
                
                # Promote to hot tier for faster access
                await self._promote_to_hot_tier(memory)
                
                return memory
                
            # Check cold tier
            # Memory IDs in cold storage follow pattern: archives/{agent_id}/{date}/memories.json
            # This would require searching through archived memory collections
            # For now, we'll skip cold tier search for individual memories
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None
            
    async def query_memories(self, query: MemoryQuery) -> List[MemorySlice]:
        """
        Query memories based on various criteria.
        
        Args:
            query: Memory query parameters
            
        Returns:
            List of matching memories
        """
        try:
            memories = []
            
            # Build PostgreSQL query
            conditions = []
            params = []
            param_count = 0
            
            if query.agent_id:
                param_count += 1
                conditions.append(f"agent_id = ${param_count}")
                params.append(query.agent_id)
                
            if query.session_id:
                param_count += 1
                conditions.append(f"session_id = ${param_count}")
                params.append(query.session_id)
                
            if query.user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(query.user_id)
                
            if query.memory_types:
                param_count += 1
                types = [t.value for t in query.memory_types]
                conditions.append(f"memory_type = ANY(${param_count})")
                params.append(types)
                
            if query.min_importance:
                param_count += 1
                conditions.append(f"importance_score >= ${param_count}")
                params.append(query.min_importance.value)
                
            if query.start_time:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(query.start_time)
                
            if query.end_time:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(query.end_time)
                
            # Construct query
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
                SELECT * FROM agent_memories 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {query.limit}
            """
            
            # Execute query
            results = await self.postgres.fetch_all(sql, *params)
            
            # Convert to memory slices
            for row in results:
                memory = MemorySlice(
                    id=row['id'],
                    agent_id=row['agent_id'],
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    memory_type=MemoryType(row['memory_type']),
                    content=json.loads(row['content']),
                    importance=MemoryImportance(row['importance_score']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                memories.append(memory)
                
            logger.info(f"Found {len(memories)} memories matching query")
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to query memories: {e}")
            return []
            
    async def semantic_search(self, query_text: str, agent_id: Optional[str] = None,
                            top_k: int = 10, threshold: float = 0.7) -> List[MemorySlice]:
        """
        Search memories using semantic similarity.
        
        Args:
            query_text: Text to search for
            agent_id: Optional agent ID filter
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of semantically similar memories
        """
        try:
            # Generate query embedding
            query_embedding = await self.embeddings.generate(query_text)
            
            # Build filter
            filter_dict = {}
            if agent_id:
                filter_dict['agent_id'] = agent_id
                
            # Search vector store
            results = await self.vector_store.search(
                embedding=query_embedding.tolist(),
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True
            )
            
            # Filter by threshold and retrieve full memories
            memories = []
            for result in results:
                if result['score'] >= threshold:
                    memory = await self.retrieve_memory(
                        result['id'],
                        result.get('metadata', {}).get('agent_id')
                    )
                    if memory:
                        memories.append(memory)
                        
            logger.info(f"Found {len(memories)} semantically similar memories")
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to perform semantic search: {e}")
            return []
            
    async def archive_old_memories(self, days_old: int = 7) -> int:
        """
        Archive old memories to cold storage.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of memories archived
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Get memories to archive
            results = await self.postgres.fetch_all(
                """
                SELECT DISTINCT agent_id, DATE(created_at) as memory_date
                FROM agent_memories
                WHERE created_at < $1
                ORDER BY agent_id, memory_date
                """,
                cutoff_date
            )
            
            archived_count = 0
            
            for row in results:
                agent_id = row['agent_id']
                date_str = row['memory_date'].strftime('%Y%m%d')
                
                # Get all memories for this agent and date
                memories = await self.postgres.fetch_all(
                    """
                    SELECT * FROM agent_memories
                    WHERE agent_id = $1 AND DATE(created_at) = $2
                    """,
                    agent_id,
                    row['memory_date']
                )
                
                if not memories:
                    continue
                    
                # Prepare archive data
                archive_data = {
                    'agent_id': agent_id,
                    'date': date_str,
                    'memory_count': len(memories),
                    'memories': []
                }
                
                for mem in memories:
                    archive_data['memories'].append({
                        'id': mem['id'],
                        'session_id': mem['session_id'],
                        'user_id': mem['user_id'],
                        'memory_type': mem['memory_type'],
                        'content': json.loads(mem['content']),
                        'importance_score': mem['importance_score'],
                        'created_at': mem['created_at'].isoformat(),
                        'updated_at': mem['updated_at'].isoformat()
                    })
                    
                # Upload to cold storage
                archive_path = f"archives/{agent_id}/{date_str}/memories.json"
                await self.gcs.upload_json(archive_path, archive_data, compress=True)
                
                # Delete from warm storage
                memory_ids = [mem['id'] for mem in memories]
                await self.postgres.execute_query(
                    """
                    DELETE FROM agent_memories WHERE id = ANY($1)
                    """,
                    memory_ids
                )
                
                # Remove from vector store
                await self.vector_store.delete(memory_ids)
                
                archived_count += len(memories)
                
            logger.info(f"Archived {archived_count} memories to cold storage")
            
            return archived_count
            
        except Exception as e:
            logger.error(f"Failed to archive memories: {e}")
            return 0
            
    async def consolidate_session_memories(self, session_id: str) -> Dict[str, Any]:
        """
        Consolidate all memories from a trading session.
        
        Args:
            session_id: Trading session ID
            
        Returns:
            Consolidated session data
        """
        try:
            # Get all memories for session
            memories = await self.query_memories(MemoryQuery(
                session_id=session_id,
                limit=1000
            ))
            
            # Group by type
            grouped = {
                'strategic_planning': [],
                'execution_plans': [],
                'trade_outcomes': [],
                'market_observations': [],
                'evaluations': [],
                'other': []
            }
            
            for memory in memories:
                if memory.memory_type == MemoryType.STRATEGIC_PLANNING:
                    grouped['strategic_planning'].append(memory)
                elif memory.memory_type == MemoryType.EXECUTION_PLAN:
                    grouped['execution_plans'].append(memory)
                elif memory.memory_type == MemoryType.TRADE_OUTCOME:
                    grouped['trade_outcomes'].append(memory)
                elif memory.memory_type == MemoryType.MARKET_OBSERVATION:
                    grouped['market_observations'].append(memory)
                elif memory.memory_type == MemoryType.EVALUATION:
                    grouped['evaluations'].append(memory)
                else:
                    grouped['other'].append(memory)
                    
            # Create consolidated summary
            consolidated = {
                'session_id': session_id,
                'total_memories': len(memories),
                'memory_breakdown': {
                    key: len(value) for key, value in grouped.items()
                },
                'strategic_plans': [m.content for m in grouped['strategic_planning']],
                'executed_trades': [m.content for m in grouped['execution_plans']],
                'trade_results': [m.content for m in grouped['trade_outcomes']],
                'market_insights': [m.content for m in grouped['market_observations']],
                'performance_evaluations': [m.content for m in grouped['evaluations']]
            }
            
            # Save consolidated session
            session_date = datetime.utcnow().strftime('%Y%m%d')
            path = f"sessions/{session_date}/{session_id}/consolidated.json"
            await self.gcs.upload_json(path, consolidated, compress=True)
            
            logger.info(f"Consolidated {len(memories)} memories for session {session_id}")
            
            return consolidated
            
        except Exception as e:
            logger.error(f"Failed to consolidate session memories: {e}")
            return {}
            
    async def _promote_to_hot_tier(self, memory: MemorySlice) -> None:
        """Promote a memory to hot tier for faster access."""
        redis_key = f"memory:{memory.agent_id}:{memory.id}"
        await self.redis.set_json(
            redis_key,
            memory.dict(),
            ttl=int(self.hot_threshold.total_seconds())
        )
        
    async def _update_memory_index(self, agent_id: str, memory_id: str) -> None:
        """Update agent's memory index."""
        index_key = f"agent_memories:{agent_id}"
        await self.redis.sadd(index_key, memory_id)
        
    async def get_agent_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for an agent."""
        try:
            # Get memory counts by type
            results = await self.postgres.fetch_all(
                """
                SELECT memory_type, COUNT(*) as count
                FROM agent_memories
                WHERE agent_id = $1
                GROUP BY memory_type
                """,
                agent_id
            )
            
            type_counts = {row['memory_type']: row['count'] for row in results}
            
            # Get importance distribution
            importance_results = await self.postgres.fetch_all(
                """
                SELECT importance_score, COUNT(*) as count
                FROM agent_memories
                WHERE agent_id = $1
                GROUP BY importance_score
                """,
                agent_id
            )
            
            importance_dist = {
                row['importance_score']: row['count'] 
                for row in importance_results
            }
            
            # Get recent memory activity
            recent_count = await self.postgres.fetch_val(
                """
                SELECT COUNT(*) FROM agent_memories
                WHERE agent_id = $1 AND created_at > $2
                """,
                agent_id,
                datetime.utcnow() - timedelta(hours=24)
            )
            
            return {
                'total_memories': sum(type_counts.values()),
                'memory_types': type_counts,
                'importance_distribution': importance_dist,
                'recent_24h': recent_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent memory stats: {e}")
            return {}