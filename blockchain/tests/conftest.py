"""
Pytest configuration and shared fixtures for blockchain tests
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from decimal import Decimal
from datetime import datetime
from typing import Dict


@pytest.fixture
def sample_trading_data() -> Dict:
    """Sample trading data for testing"""
    return {
        'net_pnl': Decimal('1250.50'),
        'gross_pnl': Decimal('1450.00'),
        'commissions': Decimal('-150.00'),
        'interest_expense': Decimal('-50.00'),
        'win_rate_30d': 67.5,
        'sharpe_ratio_30d': 2.1,
        'contracts_traded': 45,
        'implied_turnover': Decimal('2025000'),
        'trading_day_num': 156,
        'delta_exposure': Decimal('-0.15'),
        'gamma_exposure': Decimal('0.02'),
        'theta_decay': Decimal('125'),
        'vega_exposure': Decimal('-50'),
        'positions_expired': 30,
        'positions_assigned': 10,
        'positions_stopped': 5,
    }


@pytest.fixture
def sample_account_data() -> Dict:
    """Sample account data for testing"""
    return {
        'opening_balance': Decimal('215000'),
        'closing_balance': Decimal('216250.50'),
        'deposits': Decimal('0'),
        'withdrawals': Decimal('0'),
        'initial_capital': Decimal('200000'),
        'total_distributions': Decimal('15000'),
    }


@pytest.fixture
def sample_market_data() -> Dict:
    """Sample market data for testing"""
    return {
        'spy_price': Decimal('450.25'),
        'vix': 15.2,
        'market_open': True,
    }


@pytest.fixture
def mock_blockchain():
    """Mock blockchain for testing"""
    blockchain = Mock()
    blockchain.post_daily_record = AsyncMock(return_value="0x123abc...")
    blockchain.get_record = AsyncMock()
    blockchain.account = Mock()
    blockchain.account.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f82f3d"
    return blockchain


@pytest.fixture
def mock_verifier():
    """Mock data verifier"""
    verifier = Mock()
    verifier.verify_data_integrity = AsyncMock()
    # Default to valid verification
    verifier.verify_data_integrity.return_value = Mock(
        is_valid=True,
        errors=[],
        warnings=[],
        verification_hash="0xabc123...",
        timestamp=datetime.now()
    )
    return verifier


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Edge case fixtures
@pytest.fixture
def edge_case_zero_balance():
    """Edge case: zero opening balance"""
    return {
        'opening_balance': Decimal('0'),
        'closing_balance': Decimal('1000'),
        'deposits': Decimal('1000'),
        'withdrawals': Decimal('0'),
    }


@pytest.fixture
def edge_case_negative_pnl():
    """Edge case: negative P&L"""
    return {
        'net_pnl': Decimal('-5000'),
        'gross_pnl': Decimal('-4500'),
        'commissions': Decimal('-300'),
        'interest_expense': Decimal('-200'),
    }


@pytest.fixture
def edge_case_high_volatility():
    """Edge case: extremely high volatility"""
    return {
        'volatility_30d': 150.0,
        'volatility_ytd': 25.0,
        'max_drawdown_30d': -45.0,
    }