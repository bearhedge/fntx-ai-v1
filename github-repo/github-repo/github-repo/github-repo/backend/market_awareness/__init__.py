"""
Market Awareness Module
Real-time market analysis and pattern recognition.
"""

from .schemas import (
    MarketDataPoint,
    MarketSnapshot,
    TechnicalIndicators,
    MarketPattern,
    PatternType,
    MarketRegime,
    VolatilityRegime,
    TrendStrength,
    RegimeAnalysis,
    MarketEvent,
    EventType,
    EventPriority
)
from .market_data_collector import MarketDataCollector
from .pattern_recognition import PatternRecognitionEngine
from .regime_detector import MarketRegimeDetector
from .market_awareness_manager import MarketAwarenessManager, MarketAwarenessState

__all__ = [
    # Schemas
    'MarketDataPoint',
    'MarketSnapshot',
    'TechnicalIndicators',
    'MarketPattern',
    'PatternType',
    'MarketRegime',
    'VolatilityRegime',
    'TrendStrength',
    'RegimeAnalysis',
    'MarketEvent',
    'EventType',
    'EventPriority',
    
    # Components
    'MarketDataCollector',
    'PatternRecognitionEngine',
    'MarketRegimeDetector',
    
    # Manager
    'MarketAwarenessManager',
    'MarketAwarenessState'
]