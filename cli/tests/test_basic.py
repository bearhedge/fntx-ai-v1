"""
Basic tests for FNTX Agent
"""
import pytest
from core.trading.engine import TradingEngine, TradingMode

def test_trading_engine_creation():
    """Test trading engine can be created"""
    engine = TradingEngine(mode=TradingMode.INDIVIDUAL)
    assert engine.mode == TradingMode.INDIVIDUAL
    assert not engine.is_running
    assert len(engine.active_positions) == 0

def test_enterprise_mode():
    """Test enterprise mode initialization"""
    engine = TradingEngine(mode=TradingMode.ENTERPRISE)
    assert engine.mode == TradingMode.ENTERPRISE

@pytest.mark.asyncio
async def test_market_analysis():
    """Test market analysis returns expected structure"""
    engine = TradingEngine()
    result = await engine.analyze_market("SPY")
    
    assert "symbol" in result
    assert "recommendation" in result
    assert result["symbol"] == "SPY"