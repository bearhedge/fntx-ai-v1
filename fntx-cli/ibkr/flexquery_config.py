#!/usr/bin/env python3
"""
IBKR FlexQuery Configuration
Contains all 11 FlexQuery IDs and configuration for the ALM system
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FlexQueryConfig:
    """Configuration for a single FlexQuery"""
    query_id: str
    name: str
    query_type: str  # NAV, TRADES, EXERCISES_EXPIRIES, OPEN_POSITIONS, CASH_TRANSACTIONS, INTEREST_ACCRUALS
    period: str  # MTD, LBD
    description: str
    
    @property
    def import_type(self) -> str:
        """Generate import type identifier"""
        return f"{self.query_type}_{self.period}"


class FlexQueryManager:
    """Manages all FlexQuery configurations for the ALM system"""
    
    def __init__(self):
        # Load token from environment
        self.token = os.getenv("IBKR_FLEX_TOKEN")
        if not self.token:
            raise ValueError("IBKR_FLEX_TOKEN environment variable not set")
        
        # Define all 11 FlexQuery configurations
        self.queries = {
            # NAV Tracking
            "NAV_MTD": FlexQueryConfig(
                query_id="1244257",
                name="NAV (1244257) - MTD",
                query_type="NAV",
                period="MTD",
                description="Daily equity summaries, cash, options, interest accruals (Month to Date)"
            ),
            "NAV_LBD": FlexQueryConfig(
                query_id="1257542",
                name="NAV (1257542) - LBD",
                query_type="NAV",
                period="LBD",
                description="Daily NAV snapshot (Last Business Day)"
            ),
            
            # Trading Activity
            "TRADES_MTD": FlexQueryConfig(
                query_id="1257686",
                name="Trades (1257686) - MTD",
                query_type="TRADES",
                period="MTD",
                description="All trades with proceeds, commissions, P&L (Month to Date)"
            ),
            "TRADES_LBD": FlexQueryConfig(
                query_id="1257690",
                name="Trades (1257690) - LBD",
                query_type="TRADES",
                period="LBD",
                description="Daily trades with commission details (Last Business Day)"
            ),
            
            # Options Activity
            "EXERCISES_EXPIRIES_MTD": FlexQueryConfig(
                query_id="1257675",
                name="Exercises and Expiries (1257675) - MTD",
                query_type="EXERCISES_EXPIRIES",
                period="MTD",
                description="Option expirations and exercises (Month to Date)"
            ),
            "EXERCISES_EXPIRIES_LBD": FlexQueryConfig(
                query_id="1257679",
                name="Exercises and Expiries (1257679) - LBD",
                query_type="EXERCISES_EXPIRIES",
                period="LBD",
                description="Daily option activity (Last Business Day)"
            ),
            
            # Position Tracking
            "OPEN_POSITIONS_LBD": FlexQueryConfig(
                query_id="1257695",
                name="Open Positions (1257695) - LBD",
                query_type="OPEN_POSITIONS",
                period="LBD",
                description="All open positions snapshot (Last Business Day)"
            ),
            
            # Cash Movements
            "CASH_TRANSACTIONS_MTD": FlexQueryConfig(
                query_id="1257703",
                name="Cash Transactions (1257703) - MTD",
                query_type="CASH_TRANSACTIONS",
                period="MTD",
                description="Deposits, withdrawals, fees, adjustments (Month to Date)"
            ),
            "CASH_TRANSACTIONS_LBD": FlexQueryConfig(
                query_id="1257704",
                name="Cash Transactions (1257704) - LBD",
                query_type="CASH_TRANSACTIONS",
                period="LBD",
                description="Daily cash transaction details (Last Business Day)"
            ),
            
            # Interest Tracking
            "INTEREST_ACCRUALS_MTD": FlexQueryConfig(
                query_id="1257707",
                name="Interest Accruals (1257707) - MTD",
                query_type="INTEREST_ACCRUALS",
                period="MTD",
                description="Interest accrued, tier details, balances (Month to Date)"
            ),
            "INTEREST_ACCRUALS_LBD": FlexQueryConfig(
                query_id="1257708",
                name="Interest Accruals (1257708) - LBD",
                query_type="INTEREST_ACCRUALS",
                period="LBD",
                description="Daily interest accrual details (Last Business Day)"
            )
        }
        
        # Create lookup by query ID
        self.queries_by_id = {q.query_id: q for q in self.queries.values()}
        
    def get_query(self, import_type: str) -> Optional[FlexQueryConfig]:
        """Get query configuration by import type"""
        return self.queries.get(import_type)
    
    def get_query_by_id(self, query_id: str) -> Optional[FlexQueryConfig]:
        """Get query configuration by query ID"""
        return self.queries_by_id.get(query_id)
    
    def get_daily_queries(self) -> List[FlexQueryConfig]:
        """Get all LBD (Last Business Day) queries for daily import"""
        return [q for q in self.queries.values() if q.period == "LBD"]
    
    def get_monthly_queries(self) -> List[FlexQueryConfig]:
        """Get all MTD (Month to Date) queries for monthly reconciliation"""
        return [q for q in self.queries.values() if q.period == "MTD"]
    
    def get_queries_by_type(self, query_type: str) -> List[FlexQueryConfig]:
        """Get all queries of a specific type"""
        return [q for q in self.queries.values() if q.query_type == query_type]
    
    def validate_environment(self) -> Dict[str, bool]:
        """Validate that all required environment variables are set"""
        validation = {
            "IBKR_FLEX_TOKEN": bool(self.token),
            "All Query IDs Configured": len(self.queries) == 11
        }
        
        # Check if we have at least one query for each type
        required_types = ["NAV", "TRADES", "EXERCISES_EXPIRIES", "OPEN_POSITIONS", 
                         "CASH_TRANSACTIONS", "INTEREST_ACCRUALS"]
        for req_type in required_types:
            validation[f"{req_type} queries"] = any(q.query_type == req_type for q in self.queries.values())
        
        return validation
    
    def get_alm_formula_queries(self) -> Dict[str, FlexQueryConfig]:
        """Get queries needed for ALM reconciliation formula"""
        # For ALM: Opening NAV + Deposits - Withdrawals + Trading P&L - Commissions - Fees + Interest = Closing NAV
        return {
            "nav": self.get_query("NAV_LBD"),
            "cash": self.get_query("CASH_TRANSACTIONS_LBD"),
            "interest": self.get_query("INTEREST_ACCRUALS_LBD"),
            "positions": self.get_query("OPEN_POSITIONS_LBD")
        }


# Singleton instance
flexquery_manager = FlexQueryManager()


if __name__ == "__main__":
    # Test configuration
    print("IBKR FlexQuery Configuration")
    print("=" * 50)
    
    # Validate environment
    validation = flexquery_manager.validate_environment()
    print("\nEnvironment Validation:")
    for check, passed in validation.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    # List all queries
    print(f"\nTotal Queries Configured: {len(flexquery_manager.queries)}")
    print("\nDaily Import Queries (LBD):")
    for query in flexquery_manager.get_daily_queries():
        print(f"  - {query.name}: {query.description}")
    
    print("\nMonthly Reconciliation Queries (MTD):")
    for query in flexquery_manager.get_monthly_queries():
        print(f"  - {query.name}: {query.description}")
    
    # ALM formula queries
    print("\nALM Formula Required Queries:")
    for key, query in flexquery_manager.get_alm_formula_queries().items():
        if query:
            print(f"  - {key}: {query.name}")