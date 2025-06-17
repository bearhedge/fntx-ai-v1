"""
Session Management System
Provides stateful session management for trading operations.
"""

from .schemas import (
    # Enums
    SessionStatus,
    SessionType,
    
    # Core models
    AgentState,
    MarketState,
    TradingState,
    TradingSession,
    
    # Events and transitions
    SessionEvent,
    SessionTransition,
    
    # Recovery and persistence
    SessionCheckpoint,
    SessionRecoveryPlan,
    
    # Templates and metrics
    SessionTemplate,
    SessionMetrics
)

from .state_manager import SessionStateManager
from .lifecycle_manager import SessionLifecycleManager, TransitionError

__all__ = [
    # Enums
    'SessionStatus',
    'SessionType',
    
    # Core models
    'AgentState',
    'MarketState', 
    'TradingState',
    'TradingSession',
    
    # Events and transitions
    'SessionEvent',
    'SessionTransition',
    
    # Recovery and persistence
    'SessionCheckpoint',
    'SessionRecoveryPlan',
    
    # Templates and metrics
    'SessionTemplate',
    'SessionMetrics',
    
    # Managers
    'SessionStateManager',
    'SessionLifecycleManager',
    
    # Exceptions
    'TransitionError'
]