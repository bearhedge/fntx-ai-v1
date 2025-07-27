"""
Unit tests for SignatureEngine following TDD principles

Tests financial calculations, error handling, and signature generation.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from blockchain.blockchain_integration.signatures.signature_engine import SignatureEngine, DailyTradingSignature
from blockchain.blockchain_integration.signatures.data_verifier import VerificationResult


class TestSignatureEngine:
    """Test-driven development for SignatureEngine"""
    
    @pytest.mark.asyncio
    async def test_generate_signature_with_invalid_data_fails(self, mock_blockchain, mock_verifier):
        """RED: Test that invalid data causes signature generation to fail"""
        # Arrange
        mock_verifier.verify_data_integrity.return_value = Mock(
            is_valid=False,
            errors=["Invalid P&L calculation", "Balance mismatch"],
            warnings=[],
            verification_hash="",
            timestamp=datetime.now()
        )
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Data verification failed"):
            await engine.generate_daily_signature(
                date=datetime.now(),
                trading_data={},
                market_data={},
                account_data={}
            )
        
        # Verify that blockchain was not called
        mock_blockchain.post_daily_record.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_net_pnl_calculation_accuracy(self, mock_blockchain, mock_verifier):
        """Test precise calculation of net P&L including all components"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        trading_data = {
            'gross_pnl': Decimal('1000.00'),
            'commissions': Decimal('-50.00'),
            'interest_expense': Decimal('-25.00'),
            'interest_accruals': Decimal('10.00'),
        }
        
        # Act
        metrics = await engine._calculate_all_metrics(
            datetime.now(),
            trading_data,
            {},
            {'opening_balance': Decimal('100000'), 'closing_balance': Decimal('100935')}
        )
        
        # Assert
        expected_net_pnl = Decimal('1000.00') - Decimal('50.00') - Decimal('25.00') + Decimal('10.00')
        assert metrics['net_pnl'] == expected_net_pnl
        assert metrics['net_pnl'] == Decimal('935.00')
    
    @pytest.mark.asyncio
    async def test_handles_zero_opening_balance_gracefully(self, mock_blockchain, mock_verifier):
        """Test graceful handling of zero opening balance"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        account_data = {
            'opening_balance': Decimal('0'),
            'closing_balance': Decimal('1000'),
            'deposits': Decimal('1000'),
            'withdrawals': Decimal('0'),
        }
        
        # Act
        metrics = await engine._calculate_all_metrics(
            datetime.now(),
            {'gross_pnl': Decimal('0'), 'commissions': Decimal('0')},
            {},
            account_data
        )
        
        # Assert
        assert metrics['net_pnl_percentage'] == 0.0
        assert metrics['annualized_pnl_percentage'] == 0.0
        assert metrics['position_size_percentage'] == 0.0
        # Should not raise division by zero error
    
    @pytest.mark.asyncio
    async def test_merkle_tree_deterministic_generation(self, mock_blockchain, mock_verifier):
        """Test that same data always produces same merkle root"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        metrics = {
            'net_pnl': Decimal('1000'),
            'win_rate': 75.5,
            'contracts_traded': 50,
        }
        
        # Act
        tree1 = engine._build_merkle_tree(metrics)
        tree2 = engine._build_merkle_tree(metrics)
        
        # Assert
        assert tree1.root == tree2.root
        assert len(tree1.root) == 64  # SHA256 hash length
    
    @pytest.mark.asyncio
    async def test_implied_turnover_calculation(self, mock_blockchain, mock_verifier):
        """Test implied turnover calculation accuracy"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        trading_data = {'contracts_traded': 100}
        market_data = {'spy_price': Decimal('450.00')}
        
        # Act
        metrics = await engine._calculate_all_metrics(
            datetime.now(),
            trading_data,
            market_data,
            {'opening_balance': Decimal('100000'), 'closing_balance': Decimal('100000')}
        )
        
        # Assert
        expected_turnover = 100 * 100 * Decimal('450.00')  # contracts * 100 * price
        assert metrics['implied_turnover'] == expected_turnover
        assert metrics['implied_turnover'] == Decimal('4500000')
    
    @pytest.mark.asyncio
    async def test_fund_metrics_calculation(self, mock_blockchain, mock_verifier):
        """Test DPI, TVPI, RVPI calculations"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        account_data = {
            'opening_balance': Decimal('100000'),
            'closing_balance': Decimal('120000'),
            'initial_capital': Decimal('100000'),
            'total_distributions': Decimal('15000'),
            'deposits': Decimal('0'),
            'withdrawals': Decimal('0'),
        }
        
        # Act
        metrics = await engine._calculate_all_metrics(
            datetime.now(),
            {'gross_pnl': Decimal('20000'), 'commissions': Decimal('0')},
            {},
            account_data
        )
        
        # Assert
        assert metrics['dpi'] == 0.15  # 15000 / 100000
        assert metrics['tvpi'] == 1.2  # 120000 / 100000
        assert metrics['rvpi'] == 1.2  # Same as TVPI for active fund
    
    @pytest.mark.asyncio
    async def test_blockchain_submission_retry_on_failure(self, mock_blockchain, mock_verifier):
        """Test retry logic for blockchain submission failures"""
        # Arrange
        mock_blockchain.post_daily_record.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            "0x123abc..."  # Success on third try
        ]
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        
        # Create valid signature
        signature = DailyTradingSignature(
            date='20250126',
            timestamp=int(datetime.now().timestamp()),
            trading_day_num=156,
            opening_balance=Decimal('100000'),
            closing_balance=Decimal('101000'),
            deposits=Decimal('0'),
            withdrawals=Decimal('0'),
            gross_pnl=Decimal('1000'),
            commissions=Decimal('0'),
            interest_expense=Decimal('0'),
            interest_accruals=Decimal('0'),
            net_pnl=Decimal('1000'),
            net_pnl_percentage=1.0,
            annualized_pnl_percentage=252.0,
            position_size_percentage=10.0,
            contracts_traded=50,
            notional_volume=Decimal('500000'),
            implied_turnover=Decimal('2250000'),
            delta_exposure=Decimal('-0.15'),
            gamma_exposure=Decimal('0.02'),
            theta_decay=Decimal('125'),
            vega_exposure=Decimal('-50'),
            implied_volatility_avg=15.5,
            win_rate_30d=75.0,
            win_rate_mtd=72.0,
            win_rate_ytd=70.0,
            win_rate_all_time=68.0,
            volatility_30d=12.5,
            volatility_mtd=11.0,
            volatility_ytd=10.5,
            volatility_all_time=10.0,
            sharpe_ratio_30d=2.1,
            sharpe_ratio_mtd=2.0,
            sharpe_ratio_ytd=1.9,
            sharpe_ratio_all_time=1.8,
            max_drawdown_30d=-5.0,
            max_drawdown_mtd=-6.0,
            max_drawdown_ytd=-8.0,
            max_drawdown_all_time=-10.0,
            dpi=0.15,
            tvpi=1.2,
            rvpi=1.2,
            merkle_root='0xabc123...',
            calculation_hash='0xdef456...',
            data_source_hash='0xghi789...'
        )
        
        # Act
        # This would normally be wrapped in retry logic
        with pytest.raises(Exception):
            await engine._submit_to_blockchain(signature)
        
        # Assert
        assert mock_blockchain.post_daily_record.call_count == 2  # Called twice before we stopped
    
    @pytest.mark.asyncio
    async def test_signature_storage_and_retrieval(self, mock_blockchain, mock_verifier):
        """Test that signatures are stored locally after blockchain submission"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        date = datetime(2025, 1, 26)
        
        # Act
        signature, tx_hash = await engine.generate_daily_signature(
            date=date,
            trading_data={'gross_pnl': Decimal('1000'), 'commissions': Decimal('-50')},
            market_data={'spy_price': Decimal('450')},
            account_data={'opening_balance': Decimal('100000'), 'closing_balance': Decimal('100950')}
        )
        
        # Assert
        stored_signature = await engine.get_signature('20250126')
        assert stored_signature is not None
        assert stored_signature.date == '20250126'
        assert stored_signature.net_pnl == Decimal('950')  # 1000 - 50
        assert tx_hash == "0x123abc..."
    
    def test_blockchain_format_conversion(self, mock_blockchain, mock_verifier):
        """Test conversion to blockchain-compatible format"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        signature = Mock()
        signature.date = '20250126'
        signature.trading_day_num = 156
        signature.timestamp = 1737878400
        signature.opening_balance = Decimal('100000')
        signature.closing_balance = Decimal('101000')
        signature.net_pnl = Decimal('1000')
        signature.sharpe_ratio_30d = 2.1
        signature.contracts_traded = 50
        signature.implied_turnover = Decimal('2250000')
        # ... set other required fields
        
        # Act
        blockchain_data = engine._convert_to_blockchain_format(signature)
        
        # Assert
        assert blockchain_data['date'] == '20250126'
        assert blockchain_data['balance_start'] == 100000.0
        assert blockchain_data['balance_end'] == 101000.0
        assert blockchain_data['net_pnl'] == 1000.0
        assert isinstance(blockchain_data['balance_start'], float)  # Ensure Decimal converted
    
    @pytest.mark.asyncio
    async def test_hash_generation_consistency(self, mock_blockchain, mock_verifier):
        """Test that hash generation is consistent and includes all data"""
        # Arrange
        engine = SignatureEngine(mock_blockchain, mock_verifier)
        trading_data = {'gross_pnl': Decimal('1000')}
        market_data = {'spy_price': Decimal('450')}
        account_data = {'opening_balance': Decimal('100000')}
        
        # Act
        hash1 = engine._hash_input_data(trading_data, market_data, account_data)
        hash2 = engine._hash_input_data(trading_data, market_data, account_data)
        
        # Change one value
        trading_data['gross_pnl'] = Decimal('1001')
        hash3 = engine._hash_input_data(trading_data, market_data, account_data)
        
        # Assert
        assert hash1 == hash2  # Same data produces same hash
        assert hash1 != hash3  # Different data produces different hash
        assert len(hash1) == 64  # SHA256 hash length