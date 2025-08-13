#!/usr/bin/env python3
"""
Asset Liability Management API Endpoints
Provides comprehensive financial reporting and ALM functionality
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.data.data.trade_db import get_trade_db_connection
from backend.services.alm_integration_service import ALMIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alm", tags=["Asset Liability Management"])

# =====================================================
# PYDANTIC MODELS
# =====================================================

class BalanceSheetResponse(BaseModel):
    section: str
    line_item: str
    amount: float
    as_of_date: str

class IncomeStatementResponse(BaseModel):
    total_revenue: float
    total_expenses: float
    net_income: float
    net_margin_pct: float
    as_of_date: str

class CashFlowResponse(BaseModel):
    flow_type: str
    flow_category: str
    transaction_count: int
    total_inflows: float
    total_outflows: float
    net_cash_flow: float

class PositionResponse(BaseModel):
    instrument_type: str
    symbol: str
    position_count: int
    total_quantity: float
    total_cost_basis: float
    total_market_value: float
    total_unrealized_pnl: float
    weighted_avg_price: float

class RiskMetricsResponse(BaseModel):
    total_positions: int
    gross_exposure: float
    net_exposure: float
    total_cash: float
    net_asset_value: float
    total_unrealized_pnl: float
    unrealized_return_pct: float
    total_delta_exposure: float
    total_gamma_exposure: float
    total_theta_exposure: float
    total_vega_exposure: float

class JournalEntryRequest(BaseModel):
    description: str
    transaction_date: Optional[str] = None
    journal_lines: List[Dict[str, Any]]

class ReconciliationResponse(BaseModel):
    status: str
    trade_id: str
    expected_premium: float
    expected_commissions: float
    journal_debits: float
    journal_credits: float
    journal_entries_count: int
    balanced: bool
    reconciled: bool

# =====================================================
# BALANCE SHEET ENDPOINTS
# =====================================================

@router.get("/balance-sheet", response_model=List[BalanceSheetResponse])
async def get_balance_sheet():
    """Get current balance sheet in standard format"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.balance_sheet ORDER BY section, line_item")
                results = cur.fetchall()
                
                return [
                    BalanceSheetResponse(
                        section=row['section'],
                        line_item=row['line_item'],
                        amount=float(row['amount']) if row['amount'] else 0.0,
                        as_of_date=row['as_of_date'].isoformat()
                    )
                    for row in results
                ]
                
    except Exception as e:
        logger.error(f"Failed to get balance sheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/account-balances")
async def get_account_balances(
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    min_balance: Optional[float] = Query(None, description="Minimum balance filter")
):
    """Get detailed account balances with optional filtering"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM financial.account_balances WHERE 1=1"
                params = []
                
                if account_type:
                    query += " AND account_type = %s"
                    params.append(account_type)
                
                if min_balance is not None:
                    query += " AND ABS(balance) >= %s"
                    params.append(min_balance)
                
                query += " ORDER BY account_number"
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                return [dict(row) for row in results]
                
    except Exception as e:
        logger.error(f"Failed to get account balances: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# INCOME STATEMENT ENDPOINTS
# =====================================================

@router.get("/income-statement", response_model=IncomeStatementResponse)
async def get_income_statement():
    """Get income statement summary"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.income_statement_summary")
                result = cur.fetchone()
                
                if not result:
                    return IncomeStatementResponse(
                        total_revenue=0.0,
                        total_expenses=0.0,
                        net_income=0.0,
                        net_margin_pct=0.0,
                        as_of_date=datetime.now().isoformat()
                    )
                
                return IncomeStatementResponse(
                    total_revenue=float(result['total_revenue']) if result['total_revenue'] else 0.0,
                    total_expenses=float(result['total_expenses']) if result['total_expenses'] else 0.0,
                    net_income=float(result['net_income']) if result['net_income'] else 0.0,
                    net_margin_pct=float(result['net_margin_pct']) if result['net_margin_pct'] else 0.0,
                    as_of_date=result['as_of_date'].isoformat()
                )
                
    except Exception as e:
        logger.error(f"Failed to get income statement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/income-statement/detail")
async def get_income_statement_detail():
    """Get detailed income statement with account breakdown"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.income_statement_detail ORDER BY section DESC, account_number")
                results = cur.fetchall()
                
                return [dict(row) for row in results]
                
    except Exception as e:
        logger.error(f"Failed to get income statement detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# CASH FLOW ENDPOINTS
# =====================================================

@router.get("/cash-flows/summary", response_model=List[CashFlowResponse])
async def get_cash_flow_summary():
    """Get cash flow summary by type and category"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.cash_flow_summary ORDER BY flow_type, flow_category")
                results = cur.fetchall()
                
                return [
                    CashFlowResponse(
                        flow_type=row['flow_type'],
                        flow_category=row['flow_category'],
                        transaction_count=row['transaction_count'],
                        total_inflows=float(row['total_inflows']) if row['total_inflows'] else 0.0,
                        total_outflows=float(row['total_outflows']) if row['total_outflows'] else 0.0,
                        net_cash_flow=float(row['net_cash_flow']) if row['net_cash_flow'] else 0.0
                    )
                    for row in results
                ]
                
    except Exception as e:
        logger.error(f"Failed to get cash flow summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cash-positions")
async def get_cash_positions():
    """Get current cash positions by currency"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.cash_positions ORDER BY balance DESC")
                results = cur.fetchall()
                
                return [dict(row) for row in results]
                
    except Exception as e:
        logger.error(f"Failed to get cash positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# POSITIONS ENDPOINTS
# =====================================================

@router.get("/positions/current", response_model=List[PositionResponse])
async def get_current_positions():
    """Get current position summary"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.current_positions ORDER BY total_market_value DESC")
                results = cur.fetchall()
                
                return [
                    PositionResponse(
                        instrument_type=row['instrument_type'],
                        symbol=row['symbol'],
                        position_count=row['position_count'],
                        total_quantity=float(row['total_quantity']) if row['total_quantity'] else 0.0,
                        total_cost_basis=float(row['total_cost_basis']) if row['total_cost_basis'] else 0.0,
                        total_market_value=float(row['total_market_value']) if row['total_market_value'] else 0.0,
                        total_unrealized_pnl=float(row['total_unrealized_pnl']) if row['total_unrealized_pnl'] else 0.0,
                        weighted_avg_price=float(row['weighted_avg_price']) if row['weighted_avg_price'] else 0.0
                    )
                    for row in results
                ]
                
    except Exception as e:
        logger.error(f"Failed to get current positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/spy-options")
async def get_spy_options_positions():
    """Get detailed SPY options positions"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.spy_options_positions ORDER BY unrealized_pnl DESC")
                results = cur.fetchall()
                
                return [dict(row) for row in results]
                
    except Exception as e:
        logger.error(f"Failed to get SPY options positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# RISK METRICS ENDPOINTS
# =====================================================

@router.get("/risk-metrics", response_model=RiskMetricsResponse)
async def get_portfolio_risk_metrics():
    """Get portfolio-level risk metrics"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.portfolio_risk_metrics")
                result = cur.fetchone()
                
                if not result:
                    # Return zero metrics if no data
                    return RiskMetricsResponse(
                        total_positions=0,
                        gross_exposure=0.0,
                        net_exposure=0.0,
                        total_cash=0.0,
                        net_asset_value=0.0,
                        total_unrealized_pnl=0.0,
                        unrealized_return_pct=0.0,
                        total_delta_exposure=0.0,
                        total_gamma_exposure=0.0,
                        total_theta_exposure=0.0,
                        total_vega_exposure=0.0
                    )
                
                return RiskMetricsResponse(
                    total_positions=result['total_positions'] or 0,
                    gross_exposure=float(result['gross_exposure']) if result['gross_exposure'] else 0.0,
                    net_exposure=float(result['net_exposure']) if result['net_exposure'] else 0.0,
                    total_cash=float(result['total_cash']) if result['total_cash'] else 0.0,
                    net_asset_value=float(result['net_asset_value']) if result['net_asset_value'] else 0.0,
                    total_unrealized_pnl=float(result['total_unrealized_pnl']) if result['total_unrealized_pnl'] else 0.0,
                    unrealized_return_pct=float(result['unrealized_return_pct']) if result['unrealized_return_pct'] else 0.0,
                    total_delta_exposure=float(result['total_delta_exposure']) if result['total_delta_exposure'] else 0.0,
                    total_gamma_exposure=float(result['total_gamma_exposure']) if result['total_gamma_exposure'] else 0.0,
                    total_theta_exposure=float(result['total_theta_exposure']) if result['total_theta_exposure'] else 0.0,
                    total_vega_exposure=float(result['total_vega_exposure']) if result['total_vega_exposure'] else 0.0
                )
                
    except Exception as e:
        logger.error(f"Failed to get risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trading-performance")
async def get_trading_performance():
    """Get trading performance metrics"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.trading_performance")
                result = cur.fetchone()
                
                return dict(result) if result else {}
                
    except Exception as e:
        logger.error(f"Failed to get trading performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# JOURNAL ENTRY ENDPOINTS
# =====================================================

@router.post("/journal-entries")
async def create_journal_entry(request: JournalEntryRequest):
    """Create a manual journal entry"""
    try:
        # Get database config
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "fntx_trading"),
            "user": os.getenv("DB_USER", "info")
        }
        
        alm_service = ALMIntegrationService(db_config)
        
        # Create journal entry
        entry_id = alm_service._create_journal_entry(
            description=request.description,
            source_system='manual',
            source_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            journal_lines=request.journal_lines
        )
        
        if entry_id:
            return {"status": "success", "entry_id": entry_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create journal entry")
            
    except Exception as e:
        logger.error(f"Failed to create journal entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/journal-entries")
async def get_journal_entries(
    limit: int = Query(50, description="Number of entries to return"),
    offset: int = Query(0, description="Number of entries to skip"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """Get journal entries with pagination"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM financial.journal_audit_trail WHERE 1=1"
                params = []
                
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                query += " ORDER BY transaction_date DESC, entry_number DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                return [dict(row) for row in results]
                
    except Exception as e:
        logger.error(f"Failed to get journal entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# RECONCILIATION ENDPOINTS
# =====================================================

@router.get("/reconciliation/trade/{trade_id}", response_model=ReconciliationResponse)
async def reconcile_trade(trade_id: str):
    """Reconcile a specific trade against the general ledger"""
    try:
        # Get database config
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "fntx_trading"),
            "user": os.getenv("DB_USER", "info")
        }
        
        alm_service = ALMIntegrationService(db_config)
        result = alm_service.reconcile_trading_to_ledger(trade_id)
        
        if result['status'] == 'success':
            return ReconciliationResponse(**result)
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Reconciliation failed'))
            
    except Exception as e:
        logger.error(f"Failed to reconcile trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-quality")
async def get_data_quality_checks():
    """Get data quality validation results"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM financial.data_quality_checks")
                result = cur.fetchone()
                
                return dict(result) if result else {}
                
    except Exception as e:
        logger.error(f"Failed to get data quality checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# REPORTING ENDPOINTS
# =====================================================

@router.get("/reports/comprehensive")
async def get_comprehensive_report():
    """Get comprehensive financial report with all key metrics"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get multiple views in one call
                report = {}
                
                # Balance sheet summary
                cur.execute("SELECT * FROM financial.balance_sheet_summary ORDER BY account_type")
                report['balance_sheet_summary'] = [dict(row) for row in cur.fetchall()]
                
                # Income statement
                cur.execute("SELECT * FROM financial.income_statement_summary")
                income_result = cur.fetchone()
                report['income_statement'] = dict(income_result) if income_result else {}
                
                # Cash flows
                cur.execute("SELECT * FROM financial.cash_flow_summary")
                report['cash_flows'] = [dict(row) for row in cur.fetchall()]
                
                # Risk metrics
                cur.execute("SELECT * FROM financial.portfolio_risk_metrics")
                risk_result = cur.fetchone()
                report['risk_metrics'] = dict(risk_result) if risk_result else {}
                
                # Trading performance
                cur.execute("SELECT * FROM financial.trading_performance")
                trading_result = cur.fetchone()
                report['trading_performance'] = dict(trading_result) if trading_result else {}
                
                # Data quality
                cur.execute("SELECT * FROM financial.data_quality_checks")
                quality_result = cur.fetchone()
                report['data_quality'] = dict(quality_result) if quality_result else {}
                
                report['generated_at'] = datetime.now().isoformat()
                
                return report
                
    except Exception as e:
        logger.error(f"Failed to generate comprehensive report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/executive-summary")
async def get_executive_summary():
    """Get executive summary with key financial metrics"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Key metrics for executive view
                summary = {}
                
                # Net asset value and cash
                cur.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN account_type = 'asset' THEN balance ELSE 0 END), 0) as total_assets,
                        COALESCE(SUM(CASE WHEN account_type = 'liability' THEN balance ELSE 0 END), 0) as total_liabilities,
                        COALESCE(SUM(CASE WHEN account_type = 'equity' THEN balance ELSE 0 END), 0) as total_equity,
                        COALESCE(SUM(CASE WHEN account_subtype = 'cash_equivalents' THEN balance ELSE 0 END), 0) as cash_position
                    FROM financial.account_balances
                """)
                balance_result = cur.fetchone()
                
                # P&L metrics
                cur.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN account_type = 'revenue' THEN balance ELSE 0 END), 0) as total_revenue,
                        COALESCE(SUM(CASE WHEN account_type = 'expense' THEN balance ELSE 0 END), 0) as total_expenses
                    FROM financial.account_balances
                """)
                pnl_result = cur.fetchone()
                
                # Position count
                cur.execute("SELECT COUNT(*) as position_count FROM financial.positions WHERE quantity != 0")
                pos_result = cur.fetchone()
                
                summary.update({
                    'total_assets': float(balance_result['total_assets']) if balance_result['total_assets'] else 0.0,
                    'total_liabilities': float(balance_result['total_liabilities']) if balance_result['total_liabilities'] else 0.0,
                    'total_equity': float(balance_result['total_equity']) if balance_result['total_equity'] else 0.0,
                    'cash_position': float(balance_result['cash_position']) if balance_result['cash_position'] else 0.0,
                    'total_revenue': float(pnl_result['total_revenue']) if pnl_result['total_revenue'] else 0.0,
                    'total_expenses': float(pnl_result['total_expenses']) if pnl_result['total_expenses'] else 0.0,
                    'net_income': float(pnl_result['total_revenue'] - pnl_result['total_expenses']) if pnl_result['total_revenue'] and pnl_result['total_expenses'] else 0.0,
                    'active_positions': pos_result['position_count'] if pos_result else 0,
                    'generated_at': datetime.now().isoformat()
                })
                
                return summary
                
    except Exception as e:
        logger.error(f"Failed to generate executive summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))