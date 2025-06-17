"""
PostgreSQL client for warm memory storage in MCP system.
Provides structured storage for trades, plans, and agent memories.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from contextlib import asynccontextmanager

import asyncpg
from asyncpg.pool import Pool

logger = logging.getLogger(__name__)


class PostgresClient:
    """
    Async PostgreSQL client wrapper for MCP warm memory storage.
    """
    
    def __init__(self, dsn: str, pool_size: int = 10):
        """
        Initialize PostgreSQL client.
        
        Args:
            dsn: Database connection string
            pool_size: Connection pool size
        """
        self.dsn = dsn
        self.pool_size = pool_size
        self._pool: Optional[Pool] = None
        
    async def connect(self) -> None:
        """Create connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=2,
                max_size=self.pool_size,
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Disable JIT for consistent performance
                }
            )
            
            # Test connection
            async with self._pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
                
            logger.info("Connected to PostgreSQL")
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
            
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL connection pool closed")
            
    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool."""
        if not self._pool:
            raise RuntimeError("PostgreSQL pool not initialized")
            
        async with self._pool.acquire() as conn:
            yield conn
            
    async def execute(self, query: str, *args) -> str:
        """
        Execute query without returning results.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Status string
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
            
    async def executemany(self, query: str, args: List[tuple]) -> None:
        """Execute query for multiple parameter sets."""
        async with self.acquire() as conn:
            await conn.executemany(query, args)
            
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """
        Fetch multiple rows.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            List of records
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
            
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Fetch single row.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Single record or None
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
            
    async def fetchval(self, query: str, *args) -> Any:
        """
        Fetch single value.
        
        Args:
            query: SQL query
            *args: Query parameters
            
        Returns:
            Single value
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)
            
    async def create_tables(self) -> None:
        """Create MCP schema tables."""
        create_tables_sql = """
        -- Enable pgvector extension for embeddings
        CREATE EXTENSION IF NOT EXISTS vector;
        
        -- Agent memories table
        CREATE TABLE IF NOT EXISTS agent_memories (
            id UUID PRIMARY KEY,
            agent_id VARCHAR(50) NOT NULL,
            session_id VARCHAR(100),
            user_id VARCHAR(100),
            memory_type VARCHAR(50) NOT NULL,
            content JSONB NOT NULL,
            embedding vector(1536),
            importance_score INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP,
            archived BOOLEAN DEFAULT FALSE,
            archived_at TIMESTAMP,
            CONSTRAINT valid_importance CHECK (importance_score >= 1 AND importance_score <= 10)
        );
        
        -- Execution plans table
        CREATE TABLE IF NOT EXISTS execution_plans (
            id UUID PRIMARY KEY,
            plan_id VARCHAR(50) UNIQUE NOT NULL,
            session_id VARCHAR(100) NOT NULL,
            user_id VARCHAR(100) NOT NULL,
            plan_status VARCHAR(50) NOT NULL,
            plan_content JSONB NOT NULL,
            user_confirmations JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP NOT NULL,
            executed_at TIMESTAMP,
            completed_at TIMESTAMP
        );
        
        -- Trade outcomes table
        CREATE TABLE IF NOT EXISTS trade_outcomes (
            id UUID PRIMARY KEY,
            trade_id VARCHAR(50) UNIQUE NOT NULL,
            plan_id VARCHAR(50),
            session_id VARCHAR(100) NOT NULL,
            user_id VARCHAR(100) NOT NULL,
            strategy JSONB NOT NULL,
            outcome JSONB NOT NULL,
            reflection JSONB DEFAULT '{}'::jsonb,
            profit_loss DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            entry_time TIMESTAMP NOT NULL,
            exit_time TIMESTAMP
        );
        
        -- Trading sessions table
        CREATE TABLE IF NOT EXISTS trading_sessions (
            id UUID PRIMARY KEY,
            session_id VARCHAR(100) UNIQUE NOT NULL,
            user_id VARCHAR(100) NOT NULL,
            session_date DATE NOT NULL,
            status VARCHAR(50) NOT NULL,
            market_snapshot JSONB NOT NULL,
            session_metrics JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP
        );
        
        -- User profiles table (for preferences)
        CREATE TABLE IF NOT EXISTS user_profiles (
            id UUID PRIMARY KEY,
            user_id VARCHAR(100) UNIQUE NOT NULL,
            preferences JSONB DEFAULT '{}'::jsonb,
            trading_personality JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP
        );
        
        -- Market intelligence table
        CREATE TABLE IF NOT EXISTS market_intelligence (
            id UUID PRIMARY KEY,
            scan_date DATE NOT NULL,
            intelligence_data JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_memories_user_agent ON agent_memories(user_id, agent_id);
        CREATE INDEX IF NOT EXISTS idx_memories_session ON agent_memories(session_id);
        CREATE INDEX IF NOT EXISTS idx_memories_type ON agent_memories(memory_type);
        CREATE INDEX IF NOT EXISTS idx_memories_created ON agent_memories(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON agent_memories(importance_score DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_archived ON agent_memories(archived);
        
        CREATE INDEX IF NOT EXISTS idx_plans_session ON execution_plans(session_id);
        CREATE INDEX IF NOT EXISTS idx_plans_user ON execution_plans(user_id);
        CREATE INDEX IF NOT EXISTS idx_plans_status ON execution_plans(plan_status);
        
        CREATE INDEX IF NOT EXISTS idx_trades_session ON trade_outcomes(session_id);
        CREATE INDEX IF NOT EXISTS idx_trades_user ON trade_outcomes(user_id);
        CREATE INDEX IF NOT EXISTS idx_trades_plan ON trade_outcomes(plan_id);
        CREATE INDEX IF NOT EXISTS idx_trades_created ON trade_outcomes(created_at DESC);
        
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON trading_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_date ON trading_sessions(session_date DESC);
        
        -- Vector similarity search index
        CREATE INDEX IF NOT EXISTS idx_memories_embedding ON agent_memories 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE embedding IS NOT NULL;
        """
        
        try:
            await self.execute(create_tables_sql)
            logger.info("MCP database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
            
    async def drop_tables(self) -> None:
        """Drop all MCP tables (use with caution)."""
        drop_tables_sql = """
        DROP TABLE IF EXISTS market_intelligence CASCADE;
        DROP TABLE IF EXISTS user_profiles CASCADE;
        DROP TABLE IF EXISTS trading_sessions CASCADE;
        DROP TABLE IF EXISTS trade_outcomes CASCADE;
        DROP TABLE IF EXISTS execution_plans CASCADE;
        DROP TABLE IF EXISTS agent_memories CASCADE;
        """
        
        try:
            await self.execute(drop_tables_sql)
            logger.info("MCP database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise