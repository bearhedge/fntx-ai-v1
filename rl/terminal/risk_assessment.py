"""
Risk Assessment Module
Provides risk management functionality for trading operations
"""
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskMetrics:
    """Risk metrics for trading positions"""
    portfolio_risk: float
    position_risk: float
    market_risk: float
    liquidity_risk: float
    overall_risk: RiskLevel

class RiskAssessment:
    """Risk assessment and management system"""
    
    def __init__(self, max_portfolio_risk: float = 0.05):
        self.max_portfolio_risk = max_portfolio_risk
        self.risk_thresholds = {
            RiskLevel.LOW: 0.02,
            RiskLevel.MEDIUM: 0.04,
            RiskLevel.HIGH: 0.06,
            RiskLevel.CRITICAL: 0.10
        }
    
    def assess_trade_risk(self, 
                         position_value: float,
                         portfolio_value: float,
                         volatility: float = 0.2,
                         liquidity_score: float = 1.0) -> RiskMetrics:
        """Assess risk for a potential trade"""
        
        # Calculate position risk as percentage of portfolio
        position_risk = abs(position_value) / portfolio_value if portfolio_value > 0 else 1.0
        
        # Portfolio risk based on current exposure
        portfolio_risk = min(position_risk, self.max_portfolio_risk)
        
        # Market risk based on volatility
        market_risk = volatility * position_risk
        
        # Liquidity risk (lower liquidity_score = higher risk)
        liquidity_risk = (1.0 - liquidity_score) * position_risk
        
        # Overall risk assessment
        total_risk = (portfolio_risk + market_risk + liquidity_risk) / 3.0
        
        # Determine risk level
        overall_risk = RiskLevel.LOW
        for level, threshold in self.risk_thresholds.items():
            if total_risk >= threshold:
                overall_risk = level
        
        return RiskMetrics(
            portfolio_risk=portfolio_risk,
            position_risk=position_risk,
            market_risk=market_risk,
            liquidity_risk=liquidity_risk,
            overall_risk=overall_risk
        )
    
    def is_trade_allowed(self, risk_metrics: RiskMetrics) -> bool:
        """Check if trade is allowed based on risk assessment"""
        return risk_metrics.overall_risk != RiskLevel.CRITICAL
    
    def get_position_size_limit(self, 
                              portfolio_value: float,
                              volatility: float = 0.2) -> float:
        """Calculate maximum position size based on risk limits"""
        base_limit = portfolio_value * self.max_portfolio_risk
        volatility_adjustment = max(0.1, 1.0 - volatility)
        return base_limit * volatility_adjustment