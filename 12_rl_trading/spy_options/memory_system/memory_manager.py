"""
Memory Manager for AI Trading System
Handles storage and retrieval of AI decisions, feedback, and learned patterns
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import numpy as np
import asyncpg
from dataclasses import dataclass, asdict


@dataclass
class Decision:
    """AI decision with full context"""
    decision_id: UUID
    timestamp: datetime
    features: np.ndarray
    suggested_action: int
    action_probabilities: Optional[np.ndarray]
    confidence_score: float
    spy_price: float
    vix_level: Optional[float]
    reasoning_factors: Dict
    constraints_active: Dict
    model_version: str
    session_id: UUID


@dataclass
class UserFeedback:
    """User's response to AI suggestion"""
    decision_id: UUID
    accepted: bool
    rejection_reason: Optional[str]
    user_comment: Optional[str]
    response_time_seconds: int
    executed_strike: Optional[float] = None
    executed_contracts: Optional[int] = None
    fill_price: Optional[float] = None


class MemoryManager:
    """Manages AI memory database operations"""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.pool = None
        self.logger = logging.getLogger(__name__)
        self.current_session_id = None
        
    async def initialize(self):
        """Create connection pool and setup session"""
        self.pool = await asyncpg.create_pool(
            host=self.db_config.get('host', 'localhost'),
            port=self.db_config.get('port', 5432),
            user=self.db_config.get('user', 'info'),
            password=self.db_config.get('password', ''),
            database=self.db_config.get('database', 'fntx_ai_memory'),
            min_size=2,
            max_size=10
        )
        
        # Start new session
        await self.start_new_session()
        
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            
    async def start_new_session(self) -> UUID:
        """Start a new trading session"""
        self.current_session_id = uuid4()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ai_memory.session_memory (session_id, session_date)
                VALUES ($1, $2)
            """, self.current_session_id, datetime.now().date())
            
        self.logger.info(f"Started new session: {self.current_session_id}")
        return self.current_session_id
    
    async def record_decision(self, 
                            features: np.ndarray,
                            action: int,
                            action_probs: Optional[np.ndarray],
                            confidence: float,
                            market_data: Dict,
                            reasoning: Dict,
                            constraints: Dict,
                            model_version: str = "ppo_2m_v1") -> UUID:
        """Record an AI decision"""
        decision_id = uuid4()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ai_memory.decisions (
                    decision_id, features, suggested_action, action_probabilities,
                    confidence_score, spy_price, vix_level, market_regime,
                    reasoning_factors, constraints_active, model_version, session_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, 
                decision_id,
                features.tolist(),
                action,
                action_probs.tolist() if action_probs is not None else None,
                confidence,
                market_data['spy_price'],
                market_data.get('vix'),
                self._detect_market_regime(market_data),
                json.dumps(reasoning),
                json.dumps(constraints),
                model_version,
                self.current_session_id
            )
            
        self.logger.info(f"Recorded decision {decision_id}: Action {action}")
        return decision_id
    
    async def record_feedback(self, feedback: UserFeedback):
        """Record user feedback on a decision"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ai_memory.user_feedback (
                    decision_id, accepted, rejection_reason, user_comment,
                    response_time_seconds, executed_strike, executed_contracts, fill_price
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                feedback.decision_id,
                feedback.accepted,
                feedback.rejection_reason,
                feedback.user_comment,
                feedback.response_time_seconds,
                feedback.executed_strike,
                feedback.executed_contracts,
                feedback.fill_price
            )
            
            # Update session stats
            if feedback.accepted:
                await self._increment_session_stat('suggestions_accepted')
            
        # Update learned preferences asynchronously
        asyncio.create_task(self._update_learned_preferences(feedback))
        
        self.logger.info(f"Recorded feedback for {feedback.decision_id}: "
                        f"{'Accepted' if feedback.accepted else f'Rejected ({feedback.rejection_reason})'}")
    
    async def get_memory_features(self) -> np.ndarray:
        """Get current memory features for model input"""
        async with self.pool.acquire() as conn:
            # Check cache first
            cached = await conn.fetchrow("""
                SELECT feature_vector FROM ai_memory.memory_features
                WHERE expires_at > NOW()
                ORDER BY compute_time DESC
                LIMIT 1
            """)
            
            if cached and cached['feature_vector']:
                return np.array(cached['feature_vector'])
            
            # Compute fresh features
            features = await self._compute_memory_features(conn)
            
            # Cache for 5 minutes
            await conn.execute("""
                INSERT INTO ai_memory.memory_features (
                    feature_vector, last_5_outcomes, recent_acceptance_rate,
                    recent_pnl_trend, same_hour_win_rate, current_regime,
                    expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW() + INTERVAL '5 minutes')
            """,
                features.tolist(),
                await self._get_recent_outcomes(conn),
                await self._get_recent_acceptance_rate(conn),
                await self._get_pnl_trend(conn),
                await self._get_same_hour_win_rate(conn),
                await self._get_current_regime(conn)
            )
            
            return features
    
    async def find_similar_contexts(self, 
                                  spy_price: float,
                                  vix: float,
                                  current_time: datetime) -> List[Dict]:
        """Find similar historical contexts"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM ai_memory.find_similar_contexts($1, $2, $3)
            """, spy_price, vix, current_time.time())
            
            return [dict(row) for row in rows]
    
    async def get_learned_preferences(self) -> List[Dict]:
        """Get active learned preferences"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT rule_type, condition, user_preference, confidence
                FROM ai_memory.learned_preferences
                WHERE is_active = TRUE AND confidence > 0.6
                ORDER BY confidence DESC
            """)
            
            return [dict(row) for row in rows]
    
    async def _compute_memory_features(self, conn) -> np.ndarray:
        """Compute 12 memory features"""
        features = []
        
        # 1-5: Recent trade outcomes (last 5)
        outcomes = await self._get_recent_outcomes(conn)
        features.extend(outcomes[:5] + [0] * (5 - len(outcomes)))
        
        # 6: Recent acceptance rate
        features.append(await self._get_recent_acceptance_rate(conn))
        
        # 7: Same hour historical win rate
        features.append(await self._get_same_hour_win_rate(conn))
        
        # 8: Recent P&L trend (-1 to 1)
        features.append(await self._get_pnl_trend(conn))
        
        # 9: Days since similar setup
        features.append(await self._get_days_since_similar(conn))
        
        # 10: Current session suggestion count
        features.append(await self._get_session_suggestion_count(conn))
        
        # 11: Risk tolerance score (0-1)
        features.append(await self._get_risk_tolerance_score(conn))
        
        # 12: Market regime encoding (0-3)
        regime_map = {'trending_up': 0, 'trending_down': 1, 'choppy': 2, 'unknown': 3}
        regime = await self._get_current_regime(conn)
        features.append(regime_map.get(regime, 3) / 3.0)
        
        return np.array(features, dtype=np.float32)
    
    async def _get_recent_outcomes(self, conn) -> List[int]:
        """Get recent trade outcomes: 1=win, -1=loss, 0=neutral"""
        # This would join with trade ledger for actual P&L
        # For now, use acceptance as proxy
        rows = await conn.fetch("""
            SELECT f.accepted
            FROM ai_memory.decisions d
            JOIN ai_memory.user_feedback f ON d.decision_id = f.decision_id
            WHERE d.session_id = $1
            ORDER BY d.timestamp DESC
            LIMIT 5
        """, self.current_session_id)
        
        return [1 if row['accepted'] else -1 for row in rows]
    
    async def _get_recent_acceptance_rate(self, conn) -> float:
        """Get acceptance rate for recent suggestions"""
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE f.accepted) as accepted,
                COUNT(*) as total
            FROM ai_memory.decisions d
            LEFT JOIN ai_memory.user_feedback f ON d.decision_id = f.decision_id
            WHERE d.timestamp > NOW() - INTERVAL '7 days'
        """)
        
        if result['total'] == 0:
            return 0.5  # Neutral default
        
        return result['accepted'] / result['total']
    
    async def _get_same_hour_win_rate(self, conn) -> float:
        """Get historical win rate for current hour"""
        current_hour = datetime.now().hour
        
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE f.accepted) as accepted,
                COUNT(*) as total
            FROM ai_memory.decisions d
            LEFT JOIN ai_memory.user_feedback f ON d.decision_id = f.decision_id
            WHERE EXTRACT(HOUR FROM d.timestamp) = $1
            AND d.timestamp > NOW() - INTERVAL '30 days'
        """, current_hour)
        
        if result['total'] < 5:
            return 0.5  # Not enough data
            
        return result['accepted'] / result['total']
    
    async def _get_pnl_trend(self, conn) -> float:
        """Get P&L trend (-1 to 1)"""
        # Simplified - would calculate from actual P&L
        recent_rate = await self._get_recent_acceptance_rate(conn)
        return (recent_rate - 0.5) * 2  # Convert to -1 to 1 scale
    
    async def _get_days_since_similar(self, conn) -> float:
        """Days since similar market setup"""
        # Simplified implementation
        result = await conn.fetchrow("""
            SELECT MIN(NOW() - timestamp) as time_diff
            FROM ai_memory.decisions
            WHERE spy_price BETWEEN $1 - 5 AND $1 + 5
            AND timestamp < NOW() - INTERVAL '1 day'
        """, 628.0)  # Would use current SPY price
        
        if not result['time_diff']:
            return 30.0  # Max value
            
        days = result['time_diff'].days
        return min(days, 30.0) / 30.0  # Normalize to 0-1
    
    async def _get_session_suggestion_count(self, conn) -> float:
        """Normalized count of suggestions this session"""
        result = await conn.fetchrow("""
            SELECT COUNT(*) as count
            FROM ai_memory.decisions
            WHERE session_id = $1
        """, self.current_session_id)
        
        # Normalize (assume max 20 per day)
        return min(result['count'], 20) / 20.0
    
    async def _get_risk_tolerance_score(self, conn) -> float:
        """Estimate risk tolerance from recent decisions"""
        # Look at rejection reasons
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE rejection_reason LIKE '%risk%') as risk_rejections,
                COUNT(*) as total
            FROM ai_memory.user_feedback
            WHERE created_at > NOW() - INTERVAL '14 days'
            AND rejection_reason IS NOT NULL
        """)
        
        if result['total'] == 0:
            return 0.5
            
        # More risk rejections = lower risk tolerance
        risk_aversion = result['risk_rejections'] / result['total']
        return 1.0 - risk_aversion
    
    async def _get_current_regime(self, conn) -> str:
        """Detect current market regime"""
        # Simplified - would use actual market analysis
        return "trending_up"
    
    def _detect_market_regime(self, market_data: Dict) -> str:
        """Simple market regime detection"""
        # Would implement actual regime detection
        return "trending_up"
    
    async def _increment_session_stat(self, stat: str):
        """Increment a session statistic"""
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE ai_memory.session_memory
                SET {stat} = {stat} + 1
                WHERE session_id = $1
            """, self.current_session_id)
    
    async def _update_learned_preferences(self, feedback: UserFeedback):
        """Update learned preferences based on feedback"""
        if not feedback.rejection_reason:
            return
            
        async with self.pool.acquire() as conn:
            # Get decision details
            decision = await conn.fetchrow("""
                SELECT * FROM ai_memory.decisions
                WHERE decision_id = $1
            """, feedback.decision_id)
            
            if not decision:
                return
            
            # Extract learning rules
            if 'morning' in feedback.rejection_reason and decision['suggested_action'] == 1:
                await self._update_preference(
                    conn, 
                    'timing',
                    {'time': 'before_10:30', 'action': 'call'},
                    'avoid',
                    feedback.decision_id
                )
            
            if 'high' in feedback.rejection_reason or 'far' in feedback.rejection_reason:
                await self._update_preference(
                    conn,
                    'strike_distance', 
                    {'direction': 'too_far_otm'},
                    'avoid',
                    feedback.decision_id
                )
    
    async def _update_preference(self, conn, rule_type: str, 
                               condition: Dict, preference: str, 
                               example_id: UUID):
        """Update or create a learned preference"""
        # Check if preference exists
        existing = await conn.fetchrow("""
            SELECT preference_id, sample_size, example_decisions
            FROM ai_memory.learned_preferences
            WHERE rule_type = $1 AND condition = $2
        """, rule_type, json.dumps(condition))
        
        if existing:
            # Update existing
            await conn.execute("""
                UPDATE ai_memory.learned_preferences
                SET sample_size = sample_size + 1,
                    confidence = LEAST(0.95, confidence + 0.05),
                    example_decisions = array_append(example_decisions, $1),
                    last_updated = NOW()
                WHERE preference_id = $2
            """, example_id, existing['preference_id'])
        else:
            # Create new
            await conn.execute("""
                INSERT INTO ai_memory.learned_preferences
                (rule_type, condition, user_preference, example_decisions)
                VALUES ($1, $2, $3, $4)
            """, rule_type, json.dumps(condition), preference, [example_id])