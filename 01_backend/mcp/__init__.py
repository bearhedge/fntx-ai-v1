"""
Model Context Protocol (MCP) implementation for FNTX AI
Provides persistent memory, context management, and cross-agent communication.
"""

from .context_manager import MCPContextManager
from .memory_store import MemoryStore
from .schemas import (
    MemorySlice,
    ExecutionPlan,
    TradeOutcome,
    AgentMemory,
    MemoryQuery,
    MemoryType,
    MemoryImportance,
    TradingSession,
    MarketIntelligence
)

__all__ = [
    'MCPContextManager',
    'MemoryStore',
    'MemorySlice',
    'ExecutionPlan',
    'TradeOutcome',
    'AgentMemory',
    'MemoryQuery',
    'MemoryType',
    'MemoryImportance',
    'TradingSession',
    'MarketIntelligence'
]