#!/usr/bin/env python3
"""
Portfolio Management API Endpoints
Handles NAV tracking, withdrawals, and reconciliation
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.database.trade_db import get_trade_db_connection
from backend.services.nav_reconciliation_service import nav_reconciliation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio Management"])

# =====================================================
# PYDANTIC MODELS
# =====================================================

class WithdrawalRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Withdrawal amount in USD")
    destination_type: str = Field(..., description="BANK, CRYPTO, WIRE, ACH")
    destination_details: str = Field(..., description="Account details")
    description: Optional[str] = None

class WithdrawalResponse(BaseModel):
    movement_id: str
    status: str
    message: str
    estimated_settlement: Optional[date] = None

class NAVSnapshot(BaseModel):
    snapshot_date: date
    opening_nav: float
    closing_nav: Optional[float]
    opening_cash: float
    closing_cash: Optional[float]
    trading_pnl: Optional[float]
    is_reconciled: bool

class CashMovement(BaseModel):
    movement_id: str
    movement_date: date
    movement_type: str
    amount: float
    status: str
    description: Optional[str]
    destination_details: Optional[str]

class ReconciliationStatus(BaseModel):
    date: date
    status: str
    opening_nav: float
    closing_nav: float
    discrepancy: Optional[float]
    is_balanced: bool

class PortfolioSummary(BaseModel):
    current_nav: float
    available_cash: float
    positions_value: float
    pending_withdrawals: float
    ytd_withdrawals: float
    last_updated: datetime

# =====================================================
# NAV ENDPOINTS
# =====================================================

@router.get("/nav/current", response_model=PortfolioSummary)
async def get_current_portfolio_status():
    """Get current portfolio status including NAV and available balance"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get latest NAV
                cur.execute("""
                    SELECT * FROM portfolio.current_nav_status
                """)
                nav_data = cur.fetchone()
                
                if not nav_data:
                    raise HTTPException(status_code=404, detail="No NAV data available")
                
                # Get pending withdrawals
                cur.execute("""
                    SELECT COALESCE(SUM(ABS(amount)), 0) as pending
                    FROM portfolio.cash_movements
                    WHERE movement_type = 'WITHDRAWAL' 
                        AND status = 'PENDING'
                """)
                pending = cur.fetchone()['pending']
                
                # Get YTD withdrawals
                cur.execute("""
                    SELECT COALESCE(SUM(ABS(amount)), 0) as ytd_total
                    FROM portfolio.cash_movements
                    WHERE movement_type = 'WITHDRAWAL' 
                        AND status = 'COMPLETED'
                        AND EXTRACT(YEAR FROM movement_date) = EXTRACT(YEAR FROM CURRENT_DATE)
                """)
                ytd = cur.fetchone()['ytd_total']
                
                # Calculate available cash (cash minus pending withdrawals)
                available_cash = float(nav_data['cash']) - float(pending)
                
                return PortfolioSummary(
                    current_nav=float(nav_data['nav']),
                    available_cash=available_cash,
                    positions_value=float(nav_data['positions_value']),
                    pending_withdrawals=float(pending),
                    ytd_withdrawals=float(ytd),
                    last_updated=datetime.now()
                )
                
    except Exception as e:
        logger.error(f"Error getting portfolio status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nav/history", response_model=List[NAVSnapshot])
async def get_nav_history(
    days: int = Query(30, description="Number of days of history")
):
    """Get NAV history for the specified number of days"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        snapshot_date,
                        opening_nav,
                        closing_nav,
                        opening_cash,
                        closing_cash,
                        trading_pnl,
                        is_reconciled
                    FROM portfolio.daily_nav_snapshots
                    WHERE snapshot_date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY snapshot_date DESC
                """, (days,))
                
                results = cur.fetchall()
                
                return [NAVSnapshot(**row) for row in results]
                
    except Exception as e:
        logger.error(f"Error getting NAV history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# WITHDRAWAL ENDPOINTS
# =====================================================

@router.post("/withdrawals", response_model=WithdrawalResponse)
async def create_withdrawal(request: WithdrawalRequest):
    """Create a new withdrawal request"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check available balance
                cur.execute("SELECT * FROM portfolio.current_nav_status")
                nav_data = cur.fetchone()
                
                if not nav_data or float(nav_data['cash']) < request.amount:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Insufficient funds. Available: ${nav_data['cash'] if nav_data else 0}"
                    )
                
                # Create withdrawal record
                cur.execute("""
                    INSERT INTO portfolio.cash_movements (
                        movement_date,
                        movement_time,
                        movement_type,
                        amount,
                        destination_type,
                        destination_details,
                        description,
                        status,
                        settlement_date
                    ) VALUES (
                        CURRENT_DATE,
                        CURRENT_TIMESTAMP,
                        'WITHDRAWAL',
                        %s,
                        %s,
                        %s,
                        %s,
                        'PENDING',
                        CURRENT_DATE + INTERVAL '1 day'
                    ) RETURNING movement_id, settlement_date
                """, (
                    -abs(request.amount),  # Negative for withdrawals
                    request.destination_type,
                    request.destination_details,
                    request.description
                ))
                
                result = cur.fetchone()
                conn.commit()
                
                return WithdrawalResponse(
                    movement_id=str(result['movement_id']),
                    status="PENDING",
                    message="Withdrawal request created successfully",
                    estimated_settlement=result['settlement_date']
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating withdrawal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/withdrawals", response_model=List[CashMovement])
async def get_withdrawal_history(
    status: Optional[str] = Query(None, description="Filter by status"),
    days: int = Query(90, description="Number of days of history")
):
    """Get withdrawal history"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT 
                        movement_id::text,
                        movement_date,
                        movement_type,
                        amount,
                        status,
                        description,
                        destination_details
                    FROM portfolio.cash_movements
                    WHERE movement_date >= CURRENT_DATE - INTERVAL '%s days'
                """
                params = [days]
                
                if status:
                    query += " AND status = %s"
                    params.append(status)
                
                query += " ORDER BY movement_date DESC, movement_time DESC"
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                return [CashMovement(**row) for row in results]
                
    except Exception as e:
        logger.error(f"Error getting withdrawal history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# RECONCILIATION ENDPOINTS
# =====================================================

@router.get("/reconciliation/status", response_model=List[ReconciliationStatus])
async def get_reconciliation_status(days: int = Query(7, description="Number of days")):
    """Get reconciliation status for recent days"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        reconciliation_date as date,
                        CASE 
                            WHEN is_balanced THEN 'balanced'
                            WHEN actual_closing_nav IS NULL THEN 'pending'
                            ELSE 'discrepancy'
                        END as status,
                        opening_nav,
                        actual_closing_nav as closing_nav,
                        discrepancy,
                        is_balanced
                    FROM portfolio.nav_reconciliation
                    WHERE reconciliation_date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY reconciliation_date DESC
                """, (days,))
                
                results = cur.fetchall()
                return [ReconciliationStatus(**row) for row in results]
                
    except Exception as e:
        logger.error(f"Error getting reconciliation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reconciliation/run")
async def run_reconciliation(
    date_str: Optional[str] = Query(None, description="Date to reconcile (YYYY-MM-DD)")
):
    """Run reconciliation for a specific date or today"""
    try:
        # Parse date or use today
        if date_str:
            reconcile_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            reconcile_date = date.today()
        
        # Run reconciliation
        result = nav_reconciliation_service.reconcile_date(reconcile_date)
        
        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['message'])
        
        return {
            "status": "success",
            "date": reconcile_date,
            "reconciliation_status": result['status'],
            "discrepancy": result.get('discrepancy', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running reconciliation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reconciliation/summary")
async def get_reconciliation_summary():
    """Get reconciliation summary for the past 30 days"""
    try:
        summary = nav_reconciliation_service.get_reconciliation_summary(days_back=30)
        return summary
    except Exception as e:
        logger.error(f"Error getting reconciliation summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# REPORTING ENDPOINTS
# =====================================================

@router.get("/reports/monthly-summary")
async def get_monthly_summary():
    """Get monthly NAV and withdrawal summary"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        TO_CHAR(snapshot_date, 'YYYY-MM') as month,
                        MIN(opening_nav) as month_start_nav,
                        MAX(closing_nav) as month_end_nav,
                        MAX(closing_nav) - MIN(opening_nav) as nav_change,
                        SUM(trading_pnl) as total_trading_pnl,
                        COUNT(DISTINCT snapshot_date) as trading_days
                    FROM portfolio.daily_nav_snapshots
                    WHERE snapshot_date >= DATE_TRUNC('year', CURRENT_DATE)
                    GROUP BY TO_CHAR(snapshot_date, 'YYYY-MM')
                    ORDER BY month DESC
                """)
                
                nav_summary = cur.fetchall()
                
                # Get withdrawal summary
                cur.execute("""
                    SELECT 
                        TO_CHAR(movement_date, 'YYYY-MM') as month,
                        COUNT(*) FILTER (WHERE movement_type = 'WITHDRAWAL') as withdrawal_count,
                        COALESCE(SUM(ABS(amount)) FILTER (WHERE movement_type = 'WITHDRAWAL'), 0) as total_withdrawn,
                        COUNT(*) FILTER (WHERE movement_type = 'DEPOSIT') as deposit_count,
                        COALESCE(SUM(amount) FILTER (WHERE movement_type = 'DEPOSIT'), 0) as total_deposited
                    FROM portfolio.cash_movements
                    WHERE status = 'COMPLETED'
                        AND movement_date >= DATE_TRUNC('year', CURRENT_DATE)
                    GROUP BY TO_CHAR(movement_date, 'YYYY-MM')
                    ORDER BY month DESC
                """)
                
                cash_summary = cur.fetchall()
                
                # Combine summaries
                summary_dict = {}
                for nav in nav_summary:
                    month = nav['month']
                    summary_dict[month] = {
                        "month": month,
                        "nav_start": float(nav['month_start_nav']),
                        "nav_end": float(nav['month_end_nav']),
                        "nav_change": float(nav['nav_change']),
                        "trading_pnl": float(nav['total_trading_pnl']),
                        "trading_days": nav['trading_days'],
                        "withdrawals": 0,
                        "deposits": 0
                    }
                
                for cash in cash_summary:
                    month = cash['month']
                    if month in summary_dict:
                        summary_dict[month]['withdrawals'] = float(cash['total_withdrawn'])
                        summary_dict[month]['deposits'] = float(cash['total_deposited'])
                
                return list(summary_dict.values())
                
    except Exception as e:
        logger.error(f"Error getting monthly summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))