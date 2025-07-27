"""
Data Verifier - Ensures data integrity before blockchain submission

Multi-layer verification to prevent manipulation and ensure accuracy.
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio


@dataclass
class VerificationResult:
    """Result of data verification"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    verification_hash: str
    timestamp: datetime


class DataVerifier:
    """Comprehensive data verification system"""
    
    def __init__(self):
        self.verification_history: List[VerificationResult] = []
        self.mathematical_tolerance = Decimal('0.01')  # 1 cent tolerance
        
    async def verify_data_integrity(self,
                                  trading_data: Dict,
                                  market_data: Dict,
                                  account_data: Dict) -> VerificationResult:
        """
        Perform comprehensive data verification
        
        Checks:
        1. Mathematical consistency
        2. Logical constraints
        3. Cross-reference validation
        4. Historical consistency
        """
        
        errors = []
        warnings = []
        
        # 1. Mathematical Consistency Checks
        math_errors = await self._verify_mathematical_consistency(trading_data, account_data)
        errors.extend(math_errors)
        
        # 2. Logical Constraint Checks
        logic_errors = await self._verify_logical_constraints(trading_data, market_data)
        errors.extend(logic_errors)
        
        # 3. Cross-Reference Validation
        cross_ref_errors = await self._verify_cross_references(trading_data, account_data)
        errors.extend(cross_ref_errors)
        
        # 4. Historical Consistency
        historical_warnings = await self._verify_historical_consistency(trading_data, account_data)
        warnings.extend(historical_warnings)
        
        # Generate verification hash
        verification_hash = self._generate_verification_hash(
            trading_data, market_data, account_data, errors, warnings
        )
        
        result = VerificationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            verification_hash=verification_hash,
            timestamp=datetime.now()
        )
        
        # Store verification result
        self.verification_history.append(result)
        
        return result
    
    async def _verify_mathematical_consistency(self, 
                                             trading_data: Dict,
                                             account_data: Dict) -> List[str]:
        """Verify all mathematical relationships are consistent"""
        
        errors = []
        
        # 1. Verify balance equation
        opening = Decimal(str(account_data.get('opening_balance', 0)))
        closing = Decimal(str(account_data.get('closing_balance', 0)))
        deposits = Decimal(str(account_data.get('deposits', 0)))
        withdrawals = Decimal(str(account_data.get('withdrawals', 0)))
        net_pnl = Decimal(str(trading_data.get('net_pnl', 0)))
        
        calculated_closing = opening + deposits - withdrawals + net_pnl
        
        if abs(calculated_closing - closing) > self.mathematical_tolerance:
            errors.append(
                f"Balance mismatch: {opening} + {deposits} - {withdrawals} + {net_pnl} = "
                f"{calculated_closing}, but closing balance is {closing}"
            )
        
        # 2. Verify P&L components
        gross_pnl = Decimal(str(trading_data.get('gross_pnl', 0)))
        commissions = Decimal(str(trading_data.get('commissions', 0)))
        interest_expense = Decimal(str(trading_data.get('interest_expense', 0)))
        interest_accruals = Decimal(str(trading_data.get('interest_accruals', 0)))
        other_fees = Decimal(str(trading_data.get('other_fees', 0)))
        
        calculated_net_pnl = gross_pnl + commissions + interest_expense + interest_accruals + other_fees
        
        if abs(calculated_net_pnl - net_pnl) > self.mathematical_tolerance:
            errors.append(
                f"P&L component mismatch: components sum to {calculated_net_pnl}, "
                f"but net P&L is {net_pnl}"
            )
        
        # 3. Verify win rate calculation
        positions_expired = trading_data.get('positions_expired', 0)
        positions_assigned = trading_data.get('positions_assigned', 0)
        positions_stopped = trading_data.get('positions_stopped', 0)
        total_positions = positions_expired + positions_assigned + positions_stopped
        
        if total_positions > 0:
            calculated_win_rate = (positions_expired / total_positions) * 100
            reported_win_rate = trading_data.get('win_rate_30d', 0)
            
            if abs(calculated_win_rate - reported_win_rate) > 0.1:
                errors.append(
                    f"Win rate mismatch: calculated {calculated_win_rate:.1f}%, "
                    f"reported {reported_win_rate:.1f}%"
                )
        
        return errors
    
    async def _verify_logical_constraints(self,
                                        trading_data: Dict,
                                        market_data: Dict) -> List[str]:
        """Verify logical constraints and bounds"""
        
        errors = []
        
        # 1. Greeks bounds check
        delta = abs(Decimal(str(trading_data.get('delta_exposure', 0))))
        if delta > 1:
            errors.append(f"Invalid delta exposure: {delta} (must be <= 1)")
        
        # 2. Position size sanity check
        position_size_pct = trading_data.get('position_size_percentage', 0)
        if position_size_pct < 0:
            errors.append(f"Negative position size: {position_size_pct}%")
        elif position_size_pct > 500:  # More than 5x leverage warning
            errors.append(f"Excessive position size: {position_size_pct}%")
        
        # 3. Implied volatility bounds
        iv = trading_data.get('implied_volatility_avg', 0)
        if iv < 0:
            errors.append(f"Negative implied volatility: {iv}")
        elif iv > 500:  # 500% IV is extreme
            errors.append(f"Unrealistic implied volatility: {iv}%")
        
        # 4. Win rate bounds
        for timeframe in ['30d', 'mtd', 'ytd', 'all_time']:
            win_rate = trading_data.get(f'win_rate_{timeframe}', 0)
            if win_rate < 0 or win_rate > 100:
                errors.append(f"Invalid win rate for {timeframe}: {win_rate}%")
        
        # 5. Contracts traded sanity
        contracts = trading_data.get('contracts_traded', 0)
        if contracts < 0:
            errors.append(f"Negative contracts traded: {contracts}")
        
        # 6. Premium vs P&L logic check
        premium_collected = Decimal(str(trading_data.get('premium_collected', 0)))
        gross_pnl = Decimal(str(trading_data.get('gross_pnl', 0)))
        
        # For short options, P&L shouldn't exceed premium collected significantly
        if gross_pnl > premium_collected * Decimal('1.5') and premium_collected > 0:
            errors.append(
                f"P&L ({gross_pnl}) significantly exceeds premium collected ({premium_collected})"
            )
        
        return errors
    
    async def _verify_cross_references(self,
                                     trading_data: Dict,
                                     account_data: Dict) -> List[str]:
        """Cross-reference different data sources"""
        
        errors = []
        
        # 1. Verify implied turnover calculation
        contracts = trading_data.get('contracts_traded', 0)
        spy_price = Decimal(str(trading_data.get('spy_price', 450)))  # Assumed
        
        calculated_turnover = contracts * 100 * spy_price
        reported_turnover = Decimal(str(trading_data.get('implied_turnover', 0)))
        
        if abs(calculated_turnover - reported_turnover) > Decimal('1000'):  # $1000 tolerance
            errors.append(
                f"Turnover calculation mismatch: {contracts} * 100 * {spy_price} = "
                f"{calculated_turnover}, but reported {reported_turnover}"
            )
        
        # 2. Verify margin usage vs position size
        margin_used = Decimal(str(trading_data.get('margin_used', 0)))
        opening_balance = Decimal(str(account_data.get('opening_balance', 1)))
        position_size_pct = trading_data.get('position_size_percentage', 0)
        
        if margin_used > opening_balance:
            errors.append(
                f"Margin used ({margin_used}) exceeds account balance ({opening_balance})"
            )
        
        # 3. Verify interest calculations
        cash_balance = opening_balance - margin_used
        if cash_balance > 0:
            # Should have interest accruals
            interest_accruals = Decimal(str(trading_data.get('interest_accruals', 0)))
            if interest_accruals <= 0:
                errors.append(
                    f"No interest accruals despite cash balance of {cash_balance}"
                )
        
        return errors
    
    async def _verify_historical_consistency(self,
                                           trading_data: Dict,
                                           account_data: Dict) -> List[str]:
        """Verify consistency with historical patterns"""
        
        warnings = []
        
        # 1. Check for sudden balance changes
        opening = Decimal(str(account_data.get('opening_balance', 0)))
        closing = Decimal(str(account_data.get('closing_balance', 0)))
        
        daily_change_pct = abs((closing - opening) / opening * 100) if opening > 0 else 0
        
        if daily_change_pct > 10:  # More than 10% daily change
            warnings.append(
                f"Large daily balance change: {daily_change_pct:.1f}%"
            )
        
        # 2. Check for volatility spikes
        vol_30d = trading_data.get('volatility_30d', 0)
        vol_ytd = trading_data.get('volatility_ytd', 0)
        
        if vol_30d > vol_ytd * 2 and vol_ytd > 0:
            warnings.append(
                f"Recent volatility ({vol_30d}%) much higher than YTD ({vol_ytd}%)"
            )
        
        # 3. Check Sharpe ratio consistency
        sharpe_30d = trading_data.get('sharpe_ratio_30d', 0)
        sharpe_all_time = trading_data.get('sharpe_ratio_all_time', 0)
        
        if abs(sharpe_30d - sharpe_all_time) > 2:  # Significant deviation
            warnings.append(
                f"Recent Sharpe ({sharpe_30d}) deviates significantly from all-time ({sharpe_all_time})"
            )
        
        return warnings
    
    def _generate_verification_hash(self,
                                  trading_data: Dict,
                                  market_data: Dict,
                                  account_data: Dict,
                                  errors: List[str],
                                  warnings: List[str]) -> str:
        """Generate hash of verification process"""
        
        verification_data = {
            'timestamp': datetime.now().isoformat(),
            'data_hashes': {
                'trading': hashlib.sha256(
                    json.dumps(trading_data, sort_keys=True, default=str).encode()
                ).hexdigest(),
                'market': hashlib.sha256(
                    json.dumps(market_data, sort_keys=True, default=str).encode()
                ).hexdigest(),
                'account': hashlib.sha256(
                    json.dumps(account_data, sort_keys=True, default=str).encode()
                ).hexdigest()
            },
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }
        
        return hashlib.sha256(
            json.dumps(verification_data, sort_keys=True).encode()
        ).hexdigest()
    
    async def get_verification_history(self, limit: int = 100) -> List[VerificationResult]:
        """Get recent verification history"""
        return self.verification_history[-limit:]
    
    async def verify_signature_consistency(self, 
                                         signature_data: Dict,
                                         blockchain_data: Dict) -> bool:
        """Verify consistency between local signature and blockchain data"""
        
        # Compare key fields
        fields_to_check = [
            'date', 'net_pnl', 'closing_balance', 'contracts_traded',
            'implied_turnover', 'win_rate', 'sharpe_ratio_30d'
        ]
        
        for field in fields_to_check:
            sig_value = signature_data.get(field)
            chain_value = blockchain_data.get(field)
            
            if sig_value != chain_value:
                return False
        
        return True