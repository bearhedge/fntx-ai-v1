"""
Session State Manager
Manages session state persistence and recovery.
"""

import asyncio
import logging
import json
import pickle
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import aiofiles
import os

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from ..database.redis_client import RedisClient
from ..database.postgres_client import PostgresClient
from ..database.gcs_client import GCSClient
from .schemas import (
    TradingSession, SessionStatus, SessionCheckpoint, AgentState,
    MarketState, TradingState, SessionEvent, SessionRecoveryPlan
)

logger = logging.getLogger(__name__)


class SessionStateManager:
    """
    Manages session state across different storage tiers.
    """
    
    def __init__(self, mcp_manager: MCPContextManager,
                 redis_client: Optional[RedisClient] = None,
                 postgres_client: Optional[PostgresClient] = None,
                 gcs_client: Optional[GCSClient] = None):
        self.mcp = mcp_manager
        self.redis = redis_client
        self.postgres = postgres_client
        self.gcs = gcs_client
        
        # State caching
        self._session_cache: Dict[str, TradingSession] = {}
        self._checkpoint_cache: Dict[str, SessionCheckpoint] = {}
        
        # Configuration
        self.checkpoint_interval = timedelta(minutes=15)
        self.state_retention_days = 30
        self.max_checkpoints_per_session = 100
        
        # File storage paths
        self.local_backup_dir = "session_backups"
        os.makedirs(self.local_backup_dir, exist_ok=True)
        
    async def initialize(self) -> None:
        """Initialize the state manager."""
        # Register with MCP
        await self.mcp.register_agent(
            "SessionStateManager",
            ["session_persistence", "state_recovery", "checkpoint_management"]
        )
        
        # Initialize storage clients if not provided
        if not self.redis:
            self.redis = RedisClient()
            await self.redis.initialize()
            
        if not self.postgres:
            self.postgres = PostgresClient()
            await self.postgres.initialize()
            
        if not self.gcs:
            self.gcs = GCSClient()
            await self.gcs.initialize()
            
        logger.info("Session State Manager initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the state manager."""
        # Save all cached sessions
        for session_id, session in self._session_cache.items():
            await self.save_session_state(session)
            
        logger.info("Session State Manager shut down")
        
    # Session State Operations
    
    async def save_session_state(self, session: TradingSession,
                                create_checkpoint: bool = False) -> None:
        """
        Save session state to appropriate storage tier.
        
        Args:
            session: Session to save
            create_checkpoint: Whether to create a checkpoint
        """
        try:
            # Update cache
            self._session_cache[session.session_id] = session
            
            # Save to Redis for hot access
            await self._save_to_redis(session)
            
            # Create checkpoint if requested
            if create_checkpoint:
                checkpoint = await self.create_checkpoint(session)
                session.checkpoints.append(checkpoint.checkpoint_id)
                session.last_checkpoint_id = checkpoint.checkpoint_id
                
            # Save to PostgreSQL for persistence
            await self._save_to_postgres(session)
            
            # Archive old checkpoints to GCS
            if len(session.checkpoints) > self.max_checkpoints_per_session:
                await self._archive_old_checkpoints(session)
                
            # Store in MCP for agent access
            await self._save_to_mcp(session)
            
            logger.debug(f"Saved session state: {session.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            # Try local backup as fallback
            await self._save_local_backup(session)
            raise
            
    async def load_session_state(self, session_id: str) -> Optional[TradingSession]:
        """
        Load session state from storage.
        
        Args:
            session_id: ID of session to load
            
        Returns:
            Session if found
        """
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]
            
        # Try Redis
        session = await self._load_from_redis(session_id)
        if session:
            self._session_cache[session_id] = session
            return session
            
        # Try PostgreSQL
        session = await self._load_from_postgres(session_id)
        if session:
            self._session_cache[session_id] = session
            # Restore to Redis
            await self._save_to_redis(session)
            return session
            
        # Try local backup
        session = await self._load_local_backup(session_id)
        if session:
            self._session_cache[session_id] = session
            return session
            
        logger.warning(f"Session not found: {session_id}")
        return None
        
    async def delete_session_state(self, session_id: str) -> None:
        """Delete session state from all storage."""
        # Remove from cache
        self._session_cache.pop(session_id, None)
        
        # Remove from storage tiers
        await self._delete_from_redis(session_id)
        await self._delete_from_postgres(session_id)
        
        # Archive to GCS before deletion
        session = await self.load_session_state(session_id)
        if session:
            await self._archive_session(session)
            
    # Checkpoint Operations
    
    async def create_checkpoint(self, session: TradingSession) -> SessionCheckpoint:
        """
        Create a checkpoint of current session state.
        
        Args:
            session: Session to checkpoint
            
        Returns:
            Created checkpoint
        """
        checkpoint = SessionCheckpoint(
            session_id=session.session_id,
            agent_states=session.agent_states.copy(),
            market_state=session.market_state.copy() if session.market_state else MarketState(
                spy_price=0, vix_level=0, market_regime="unknown"
            ),
            trading_state=session.trading_state.copy() if session.trading_state else TradingState(
                max_daily_loss_remaining=10000,
                position_limit_remaining=3
            )
        )
        
        # Calculate checksum
        checkpoint.checksum = self._calculate_checksum(checkpoint)
        checkpoint.verified = True
        
        # Save checkpoint
        await self._save_checkpoint(checkpoint)
        
        # Update cache
        self._checkpoint_cache[checkpoint.checkpoint_id] = checkpoint
        
        logger.info(f"Created checkpoint {checkpoint.checkpoint_id} for session {session.session_id}")
        
        return checkpoint
        
    async def load_checkpoint(self, checkpoint_id: str) -> Optional[SessionCheckpoint]:
        """Load a specific checkpoint."""
        # Check cache
        if checkpoint_id in self._checkpoint_cache:
            return self._checkpoint_cache[checkpoint_id]
            
        # Load from storage
        checkpoint = await self._load_checkpoint(checkpoint_id)
        if checkpoint:
            # Verify integrity
            if self._verify_checkpoint(checkpoint):
                self._checkpoint_cache[checkpoint_id] = checkpoint
                return checkpoint
            else:
                logger.error(f"Checkpoint verification failed: {checkpoint_id}")
                
        return None
        
    async def restore_from_checkpoint(self, session: TradingSession,
                                    checkpoint_id: str) -> bool:
        """
        Restore session state from a checkpoint.
        
        Args:
            session: Session to restore
            checkpoint_id: Checkpoint to restore from
            
        Returns:
            Success status
        """
        checkpoint = await self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False
            
        try:
            # Restore state
            session.agent_states = checkpoint.agent_states.copy()
            session.market_state = checkpoint.market_state.copy()
            session.trading_state = checkpoint.trading_state.copy()
            
            # Add recovery event
            event = SessionEvent(
                session_id=session.session_id,
                event_type="checkpoint_restore",
                event_category="recovery",
                severity="info",
                description=f"Restored from checkpoint {checkpoint_id}",
                data={"checkpoint_id": checkpoint_id, "timestamp": checkpoint.timestamp.isoformat()}
            )
            session.events.append(event)
            
            # Save restored state
            await self.save_session_state(session)
            
            logger.info(f"Restored session {session.session_id} from checkpoint {checkpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from checkpoint: {e}")
            return False
            
    async def list_checkpoints(self, session_id: str,
                             limit: int = 10) -> List[SessionCheckpoint]:
        """List recent checkpoints for a session."""
        session = await self.load_session_state(session_id)
        if not session:
            return []
            
        checkpoints = []
        for checkpoint_id in reversed(session.checkpoints[-limit:]):
            checkpoint = await self.load_checkpoint(checkpoint_id)
            if checkpoint:
                checkpoints.append(checkpoint)
                
        return checkpoints
        
    # Recovery Operations
    
    async def create_recovery_plan(self, session_id: str) -> Optional[SessionRecoveryPlan]:
        """
        Create a recovery plan for a session.
        
        Args:
            session_id: Session to create plan for
            
        Returns:
            Recovery plan if possible
        """
        session = await self.load_session_state(session_id)
        if not session:
            logger.error(f"Cannot create recovery plan - session not found: {session_id}")
            return None
            
        # Find available checkpoints
        checkpoints = await self.list_checkpoints(session_id, limit=5)
        if not checkpoints:
            logger.error(f"No checkpoints available for recovery: {session_id}")
            return None
            
        # Create recovery plan
        plan = SessionRecoveryPlan(
            session_id=session_id,
            recovery_type="checkpoint_restore",
            checkpoint_id=checkpoints[0].checkpoint_id,
            fallback_checkpoint_ids=[c.checkpoint_id for c in checkpoints[1:]],
            steps=[
                {"step": "validate_checkpoint", "checkpoint_id": checkpoints[0].checkpoint_id},
                {"step": "restore_agent_states", "agents": list(session.agent_states.keys())},
                {"step": "restore_market_state", "verify_data": True},
                {"step": "restore_trading_state", "validate_positions": True},
                {"step": "reconnect_agents", "timeout": 30},
                {"step": "verify_recovery", "run_diagnostics": True}
            ],
            estimated_duration=timedelta(minutes=5),
            data_integrity_checks=[
                {"check": "checkpoint_checksum", "required": True},
                {"check": "agent_state_consistency", "required": True},
                {"check": "position_validation", "required": True}
            ],
            data_loss_risk="low" if len(checkpoints) > 1 else "medium",
            state_consistency_risk="low",
            recovery_confidence=0.9 if checkpoints[0].verified else 0.7
        )
        
        return plan
        
    async def execute_recovery_plan(self, plan: SessionRecoveryPlan) -> bool:
        """
        Execute a recovery plan.
        
        Args:
            plan: Recovery plan to execute
            
        Returns:
            Success status
        """
        logger.info(f"Executing recovery plan for session {plan.session_id}")
        
        session = await self.load_session_state(plan.session_id)
        if not session:
            logger.error("Session not found for recovery")
            return False
            
        # Try primary checkpoint
        if plan.checkpoint_id:
            success = await self.restore_from_checkpoint(session, plan.checkpoint_id)
            if success:
                return True
                
        # Try fallback checkpoints
        for checkpoint_id in plan.fallback_checkpoint_ids:
            logger.warning(f"Trying fallback checkpoint: {checkpoint_id}")
            success = await self.restore_from_checkpoint(session, checkpoint_id)
            if success:
                return True
                
        logger.error("All recovery attempts failed")
        return False
        
    # State Validation
    
    async def validate_session_state(self, session: TradingSession) -> Dict[str, Any]:
        """
        Validate session state integrity.
        
        Args:
            session: Session to validate
            
        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "checks_performed": []
        }
        
        # Check agent states
        for agent_id, agent_state in session.agent_states.items():
            if agent_state.errors_encountered > 10:
                results["warnings"].append(f"Agent {agent_id} has high error count: {agent_state.errors_encountered}")
                
            if agent_state.status == "error":
                results["errors"].append(f"Agent {agent_id} is in error state")
                results["valid"] = False
                
        results["checks_performed"].append("agent_states")
        
        # Check trading state
        if session.trading_state:
            if session.trading_state.max_daily_loss_remaining < 0:
                results["errors"].append("Daily loss limit exceeded")
                results["valid"] = False
                
            if session.trading_state.position_limit_remaining < 0:
                results["errors"].append("Position limit exceeded")
                results["valid"] = False
                
            if not session.trading_state.trading_enabled and session.status == SessionStatus.ACTIVE:
                results["warnings"].append("Trading disabled but session is active")
                
        results["checks_performed"].append("trading_state")
        
        # Check market state
        if session.market_state:
            if session.market_state.spy_price <= 0:
                results["warnings"].append("Invalid SPY price")
                
            if not session.market_state.market_open and session.status == SessionStatus.ACTIVE:
                results["warnings"].append("Market closed but session is active")
                
        results["checks_performed"].append("market_state")
        
        # Check checkpoint consistency
        if session.last_checkpoint_id:
            checkpoint = await self.load_checkpoint(session.last_checkpoint_id)
            if not checkpoint:
                results["errors"].append(f"Last checkpoint not found: {session.last_checkpoint_id}")
                results["valid"] = False
            elif not checkpoint.verified:
                results["warnings"].append("Last checkpoint not verified")
                
        results["checks_performed"].append("checkpoints")
        
        return results
        
    # Storage Operations
    
    async def _save_to_redis(self, session: TradingSession) -> None:
        """Save session to Redis."""
        if not self.redis:
            return
            
        key = f"session:{session.session_id}"
        data = session.json()
        
        # Set with expiration (7 days)
        await self.redis.set(key, data, ex=7 * 24 * 3600)
        
    async def _load_from_redis(self, session_id: str) -> Optional[TradingSession]:
        """Load session from Redis."""
        if not self.redis:
            return None
            
        key = f"session:{session_id}"
        data = await self.redis.get(key)
        
        if data:
            return TradingSession.parse_raw(data)
            
        return None
        
    async def _delete_from_redis(self, session_id: str) -> None:
        """Delete session from Redis."""
        if not self.redis:
            return
            
        key = f"session:{session_id}"
        await self.redis.delete(key)
        
    async def _save_to_postgres(self, session: TradingSession) -> None:
        """Save session to PostgreSQL."""
        if not self.postgres:
            return
            
        query = """
            INSERT INTO trading_sessions (session_id, data, created_at, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (session_id) DO UPDATE
            SET data = $2, updated_at = $4
        """
        
        await self.postgres.execute(
            query,
            session.session_id,
            session.json(),
            session.created_at,
            datetime.utcnow()
        )
        
    async def _load_from_postgres(self, session_id: str) -> Optional[TradingSession]:
        """Load session from PostgreSQL."""
        if not self.postgres:
            return None
            
        query = "SELECT data FROM trading_sessions WHERE session_id = $1"
        result = await self.postgres.fetchone(query, session_id)
        
        if result:
            return TradingSession.parse_raw(result['data'])
            
        return None
        
    async def _delete_from_postgres(self, session_id: str) -> None:
        """Delete session from PostgreSQL."""
        if not self.postgres:
            return
            
        query = "DELETE FROM trading_sessions WHERE session_id = $1"
        await self.postgres.execute(query, session_id)
        
    async def _save_checkpoint(self, checkpoint: SessionCheckpoint) -> None:
        """Save checkpoint to storage."""
        # Save to Redis with shorter expiration (1 day)
        if self.redis:
            key = f"checkpoint:{checkpoint.checkpoint_id}"
            await self.redis.set(key, checkpoint.json(), ex=24 * 3600)
            
        # Save to PostgreSQL
        if self.postgres:
            query = """
                INSERT INTO session_checkpoints (checkpoint_id, session_id, data, created_at)
                VALUES ($1, $2, $3, $4)
            """
            await self.postgres.execute(
                query,
                checkpoint.checkpoint_id,
                checkpoint.session_id,
                checkpoint.json(),
                checkpoint.timestamp
            )
            
    async def _load_checkpoint(self, checkpoint_id: str) -> Optional[SessionCheckpoint]:
        """Load checkpoint from storage."""
        # Try Redis first
        if self.redis:
            key = f"checkpoint:{checkpoint_id}"
            data = await self.redis.get(key)
            if data:
                return SessionCheckpoint.parse_raw(data)
                
        # Try PostgreSQL
        if self.postgres:
            query = "SELECT data FROM session_checkpoints WHERE checkpoint_id = $1"
            result = await self.postgres.fetchone(query, checkpoint_id)
            if result:
                return SessionCheckpoint.parse_raw(result['data'])
                
        return None
        
    async def _archive_old_checkpoints(self, session: TradingSession) -> None:
        """Archive old checkpoints to GCS."""
        if not self.gcs or len(session.checkpoints) <= self.max_checkpoints_per_session:
            return
            
        # Get checkpoints to archive (keep last N)
        to_archive = session.checkpoints[:-self.max_checkpoints_per_session]
        
        for checkpoint_id in to_archive:
            checkpoint = await self.load_checkpoint(checkpoint_id)
            if checkpoint:
                # Save to GCS
                blob_name = f"checkpoints/{session.session_id}/{checkpoint_id}.json"
                await self.gcs.upload_json(blob_name, checkpoint.dict())
                
                # Remove from hot storage
                if self.redis:
                    await self.redis.delete(f"checkpoint:{checkpoint_id}")
                    
        # Update session checkpoint list
        session.checkpoints = session.checkpoints[-self.max_checkpoints_per_session:]
        
    async def _archive_session(self, session: TradingSession) -> None:
        """Archive session to GCS."""
        if not self.gcs:
            return
            
        blob_name = f"sessions/{session.session_id}/final_state.json"
        await self.gcs.upload_json(blob_name, session.dict())
        
        # Archive checkpoints
        for checkpoint_id in session.checkpoints:
            checkpoint = await self.load_checkpoint(checkpoint_id)
            if checkpoint:
                checkpoint_blob = f"sessions/{session.session_id}/checkpoints/{checkpoint_id}.json"
                await self.gcs.upload_json(checkpoint_blob, checkpoint.dict())
                
    async def _save_local_backup(self, session: TradingSession) -> None:
        """Save local backup of session."""
        filepath = os.path.join(self.local_backup_dir, f"{session.session_id}.json")
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(session.json())
            
    async def _load_local_backup(self, session_id: str) -> Optional[TradingSession]:
        """Load session from local backup."""
        filepath = os.path.join(self.local_backup_dir, f"{session_id}.json")
        
        if os.path.exists(filepath):
            async with aiofiles.open(filepath, 'r') as f:
                data = await f.read()
                return TradingSession.parse_raw(data)
                
        return None
        
    async def _save_to_mcp(self, session: TradingSession) -> None:
        """Save session state to MCP."""
        await self.mcp.store_memory(
            "SessionStateManager",
            MemorySlice(
                memory_type=MemoryType.EXECUTION,
                content={
                    'session_state': {
                        'session_id': session.session_id,
                        'status': session.status.value,
                        'agent_states': {k: v.dict() for k, v in session.agent_states.items()},
                        'metrics': session.metrics.dict() if session.metrics else None
                    },
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )
        
    def _calculate_checksum(self, checkpoint: SessionCheckpoint) -> str:
        """Calculate checksum for checkpoint data."""
        data = json.dumps({
            'agent_states': {k: v.dict() for k, v in checkpoint.agent_states.items()},
            'market_state': checkpoint.market_state.dict(),
            'trading_state': checkpoint.trading_state.dict()
        }, sort_keys=True)
        
        return hashlib.sha256(data.encode()).hexdigest()
        
    def _verify_checkpoint(self, checkpoint: SessionCheckpoint) -> bool:
        """Verify checkpoint integrity."""
        if not checkpoint.checksum:
            return True  # No checksum to verify
            
        calculated = self._calculate_checksum(checkpoint)
        return calculated == checkpoint.checksum