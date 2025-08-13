#!/usr/bin/env python3
"""
Unified ALM API - Combines Historical and Real-time Data
Provides endpoints for ALM track record with real-time current day data
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
import psycopg2
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any
import json
import logging
from dataclasses import dataclass, asdict
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'options_data',
    'user': 'postgres',
    'password': 'theta_data_2024'
}

# Pydantic models for API responses
class ALMDailySummary(BaseModel):
    summary_date: date
    opening_nav_hkd: float
    closing_nav_hkd: float
    total_pnl_hkd: float
    realized_pnl_hkd: float
    unrealized_pnl_hkd: float
    net_cash_flow_hkd: float
    broker_fees_hkd: float
    position_value_hkd: float
    cash_balance_hkd: float
    is_realtime: bool
    data_source: str
    last_updated: datetime

class ALMEvent(BaseModel):
    event_timestamp: datetime
    event_type: str
    symbol: Optional[str]
    instrument_type: Optional[str]
    strike_price: Optional[float]
    option_type: Optional[str]
    expiry_date: Optional[date]
    quantity: Optional[int]
    price: Optional[float]
    total_amount_hkd: float
    commission_hkd: float
    cash_impact_hkd: float
    description: str
    is_realtime: bool
    data_source: str

class ALMPosition(BaseModel):
    symbol: str
    instrument_type: str
    strike_price: Optional[float]
    option_type: Optional[str]
    expiry_date: Optional[date]
    quantity: int
    market_price: float
    market_value_hkd: float
    cost_basis_hkd: float
    unrealized_pnl_hkd: float
    is_realtime: bool
    as_of_timestamp: datetime

class ALMTrackRecord(BaseModel):
    summary: List[ALMDailySummary]
    events: List[ALMEvent]
    current_positions: List[ALMPosition]
    performance_metrics: Dict[str, float]
    data_as_of: datetime
    contains_realtime_data: bool

class SystemStatus(BaseModel):
    service_name: str
    status: str
    last_heartbeat: datetime
    connection_status: str
    data_lag_seconds: int
    error_message: Optional[str]

# Database connection helper
def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Decimal to float converter for JSON serialization
def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

class UnifiedALMService:
    """
    Service class for unified ALM data retrieval
    """
    
    @staticmethod
    def get_historical_summary(start_date: date, end_date: date) -> List[Dict]:
        """Get historical daily summary data"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        summary_date,
                        opening_nav_hkd,
                        closing_nav_hkd,
                        total_pnl_hkd,
                        COALESCE(realized_pnl_hkd, 0) as realized_pnl_hkd,
                        COALESCE(unrealized_pnl_hkd, 0) as unrealized_pnl_hkd,
                        net_cash_flow_hkd,
                        broker_fees_hkd,
                        COALESCE(position_value_hkd, 0) as position_value_hkd,
                        COALESCE(cash_balance_hkd, 0) as cash_balance_hkd,
                        false as is_realtime,
                        'FLEXQUERY' as data_source,
                        COALESCE(last_updated, created_at) as last_updated
                    FROM alm_reporting.daily_summary
                    WHERE summary_date >= %s AND summary_date < %s
                    ORDER BY summary_date
                """, (start_date, end_date))
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Convert Decimal to float
                    for key, value in row_dict.items():
                        row_dict[key] = decimal_to_float(value)
                    results.append(row_dict)
                
                return results
                
        finally:
            conn.close()
    
    @staticmethod
    def get_realtime_summary(target_date: date) -> Optional[Dict]:
        """Get real-time daily summary for current day"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        summary_date,
                        opening_nav_hkd,
                        current_nav_hkd as closing_nav_hkd,
                        total_pnl_hkd,
                        realized_pnl_hkd,
                        unrealized_pnl_hkd,
                        net_cash_flow_hkd,
                        broker_fees_hkd,
                        position_value_hkd,
                        cash_balance_hkd,
                        true as is_realtime,
                        data_source,
                        last_updated
                    FROM alm_realtime.daily_summary
                    WHERE summary_date = %s
                    ORDER BY last_updated DESC
                    LIMIT 1
                """, (target_date,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    row_dict = dict(zip(columns, row))
                    # Convert Decimal to float
                    for key, value in row_dict.items():
                        row_dict[key] = decimal_to_float(value)
                    return row_dict
                
                return None
                
        finally:
            conn.close()
    
    @staticmethod
    def get_historical_events(start_date: date, end_date: date) -> List[Dict]:
        """Get historical chronological events"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        event_timestamp,
                        event_type,
                        symbol,
                        instrument_type,
                        strike_price,
                        option_type,
                        expiry_date,
                        quantity,
                        price,
                        total_amount_hkd,
                        commission_hkd,
                        cash_impact_hkd,
                        description,
                        false as is_realtime,
                        COALESCE(data_source, 'FLEXQUERY') as data_source
                    FROM alm_reporting.chronological_events
                    WHERE DATE(event_timestamp) >= %s AND DATE(event_timestamp) < %s
                    ORDER BY event_timestamp
                """, (start_date, end_date))
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Convert Decimal to float
                    for key, value in row_dict.items():
                        row_dict[key] = decimal_to_float(value)
                    results.append(row_dict)
                
                return results
                
        finally:
            conn.close()
    
    @staticmethod
    def get_realtime_events(target_date: date) -> List[Dict]:
        """Get real-time events for current day"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        event_timestamp,
                        event_type,
                        symbol,
                        instrument_type,
                        strike_price,
                        option_type,
                        expiry_date,
                        quantity,
                        price,
                        total_amount_hkd,
                        commission_hkd,
                        cash_impact_hkd,
                        description,
                        true as is_realtime,
                        data_source
                    FROM alm_realtime.chronological_events
                    WHERE DATE(event_timestamp) = %s
                    ORDER BY event_timestamp
                """, (target_date,))
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Convert Decimal to float
                    for key, value in row_dict.items():
                        row_dict[key] = decimal_to_float(value)
                    results.append(row_dict)
                
                return results
                
        finally:
            conn.close()
    
    @staticmethod
    def get_current_positions() -> List[Dict]:
        """Get current real-time positions"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get latest positions for each unique instrument
                cursor.execute("""
                    WITH latest_positions AS (
                        SELECT 
                            symbol, instrument_type, strike_price, option_type, expiry_date,
                            quantity, market_price, market_value_hkd, cost_basis_hkd,
                            unrealized_pnl_hkd, as_of_timestamp,
                            ROW_NUMBER() OVER (
                                PARTITION BY symbol, instrument_type, strike_price, option_type, expiry_date 
                                ORDER BY as_of_timestamp DESC
                            ) as rn
                        FROM alm_realtime.positions
                        WHERE quantity != 0
                    )
                    SELECT 
                        symbol, instrument_type, strike_price, option_type, expiry_date,
                        quantity, market_price, market_value_hkd, cost_basis_hkd,
                        unrealized_pnl_hkd, as_of_timestamp,
                        true as is_realtime
                    FROM latest_positions
                    WHERE rn = 1
                    ORDER BY symbol, instrument_type, strike_price
                """)
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Convert Decimal to float
                    for key, value in row_dict.items():
                        row_dict[key] = decimal_to_float(value)
                    results.append(row_dict)
                
                return results
                
        finally:
            conn.close()
    
    @staticmethod
    def calculate_performance_metrics(summary_data: List[Dict]) -> Dict[str, float]:
        """Calculate performance metrics from summary data"""
        if not summary_data:
            return {}
        
        try:
            # Sort by date
            sorted_data = sorted(summary_data, key=lambda x: x['summary_date'])
            
            # Calculate metrics
            total_days = len(sorted_data)
            if total_days < 2:
                return {'total_days': total_days}
            
            # Get start and end NAV
            start_nav = sorted_data[0]['opening_nav_hkd']
            end_nav = sorted_data[-1]['closing_nav_hkd']
            
            # Total return
            total_return = ((end_nav - start_nav) / start_nav) if start_nav > 0 else 0.0
            
            # Daily returns
            daily_returns = []
            for i in range(1, len(sorted_data)):
                prev_nav = sorted_data[i-1]['closing_nav_hkd']
                curr_nav = sorted_data[i]['closing_nav_hkd']
                if prev_nav > 0:
                    daily_return = (curr_nav - prev_nav) / prev_nav
                    daily_returns.append(daily_return)
            
            # Average daily return
            avg_daily_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
            
            # Volatility (standard deviation)
            if len(daily_returns) > 1:
                mean_return = avg_daily_return
                variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
                volatility = variance ** 0.5
            else:
                volatility = 0.0
            
            # Sharpe ratio (assuming 0% risk-free rate)
            sharpe_ratio = avg_daily_return / volatility if volatility > 0 else 0.0
            
            # Maximum drawdown
            peak = start_nav
            max_drawdown = 0.0
            for data_point in sorted_data:
                nav = data_point['closing_nav_hkd']
                if nav > peak:
                    peak = nav
                drawdown = (peak - nav) / peak if peak > 0 else 0.0
                max_drawdown = max(max_drawdown, drawdown)
            
            # Win rate
            winning_days = sum(1 for r in daily_returns if r > 0)
            win_rate = winning_days / len(daily_returns) if daily_returns else 0.0
            
            # Total P&L
            total_pnl = sum(data_point['total_pnl_hkd'] for data_point in sorted_data)
            
            return {
                'total_days': total_days,
                'total_return': total_return,
                'avg_daily_return': avg_daily_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_pnl_hkd': total_pnl,
                'start_nav_hkd': start_nav,
                'end_nav_hkd': end_nav
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}

# FastAPI app
app = FastAPI(title="Unified ALM API", version="1.0.0")

@app.get("/alm/track-record", response_model=ALMTrackRecord)
async def get_alm_track_record(
    start_date: date = Query(..., description="Start date for historical data"),
    end_date: date = Query(default=None, description="End date (default: today)"),
    include_realtime: bool = Query(default=True, description="Include real-time current day data")
):
    """
    Get unified ALM track record combining historical and real-time data
    """
    try:
        if end_date is None:
            end_date = date.today()
        
        today = date.today()
        
        # Get historical data (excluding today)
        historical_end = today if include_realtime else end_date + timedelta(days=1)
        historical_summary = UnifiedALMService.get_historical_summary(start_date, historical_end)
        historical_events = UnifiedALMService.get_historical_events(start_date, historical_end)
        
        # Initialize combined data
        combined_summary = historical_summary.copy()
        combined_events = historical_events.copy()
        contains_realtime = False
        
        # Add real-time data for today if requested and within date range
        if include_realtime and start_date <= today <= end_date:
            realtime_summary = UnifiedALMService.get_realtime_summary(today)
            if realtime_summary:
                combined_summary.append(realtime_summary)
                contains_realtime = True
            
            realtime_events = UnifiedALMService.get_realtime_events(today)
            combined_events.extend(realtime_events)
            if realtime_events:
                contains_realtime = True
        
        # Get current positions
        current_positions = UnifiedALMService.get_current_positions() if include_realtime else []
        
        # Calculate performance metrics
        performance_metrics = UnifiedALMService.calculate_performance_metrics(combined_summary)
        
        # Sort data
        combined_summary.sort(key=lambda x: x['summary_date'])
        combined_events.sort(key=lambda x: x['event_timestamp'])
        
        return ALMTrackRecord(
            summary=[ALMDailySummary(**item) for item in combined_summary],
            events=[ALMEvent(**item) for item in combined_events],
            current_positions=[ALMPosition(**item) for item in current_positions],
            performance_metrics=performance_metrics,
            data_as_of=datetime.now(timezone.utc),
            contains_realtime_data=contains_realtime
        )
        
    except Exception as e:
        logger.error(f"Error getting ALM track record: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alm/current-nav")
async def get_current_nav():
    """Get current real-time NAV"""
    try:
        today = date.today()
        nav_data = UnifiedALMService.get_realtime_summary(today)
        
        if not nav_data:
            raise HTTPException(status_code=404, detail="No current NAV data available")
        
        return {
            "current_nav_hkd": nav_data["closing_nav_hkd"],
            "opening_nav_hkd": nav_data["opening_nav_hkd"],
            "total_pnl_hkd": nav_data["total_pnl_hkd"],
            "unrealized_pnl_hkd": nav_data["unrealized_pnl_hkd"],
            "realized_pnl_hkd": nav_data["realized_pnl_hkd"],
            "cash_balance_hkd": nav_data["cash_balance_hkd"],
            "position_value_hkd": nav_data["position_value_hkd"],
            "as_of_timestamp": nav_data["last_updated"],
            "is_realtime": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current NAV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alm/todays-trades")
async def get_todays_trades():
    """Get today's trade executions"""
    try:
        today = date.today()
        trades = UnifiedALMService.get_realtime_events(today)
        
        # Filter for trade executions only
        trade_executions = [
            trade for trade in trades 
            if trade['event_type'] == 'TRADE_EXECUTION'
        ]
        
        return {
            "trade_date": today,
            "trades_count": len(trade_executions),
            "trades": trade_executions,
            "total_volume_hkd": sum(abs(trade["total_amount_hkd"]) for trade in trade_executions),
            "total_commissions_hkd": sum(trade["commission_hkd"] for trade in trade_executions)
        }
        
    except Exception as e:
        logger.error(f"Error getting today's trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alm/positions")
async def get_current_positions():
    """Get current positions"""
    try:
        positions = UnifiedALMService.get_current_positions()
        
        # Calculate summary statistics
        total_market_value = sum(pos["market_value_hkd"] for pos in positions)
        total_unrealized_pnl = sum(pos["unrealized_pnl_hkd"] for pos in positions)
        
        return {
            "positions_count": len(positions),
            "total_market_value_hkd": total_market_value,
            "total_unrealized_pnl_hkd": total_unrealized_pnl,
            "positions": positions,
            "as_of_timestamp": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Error getting current positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alm/system-status")
async def get_system_status():
    """Get real-time system status"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    service_name, status, last_heartbeat, connection_status,
                    data_lag_seconds, error_message, updated_at
                FROM alm_realtime.system_status
                ORDER BY service_name
            """)
            
            columns = [desc[0] for desc in cursor.description]
            services = []
            
            for row in cursor.fetchall():
                service_dict = dict(zip(columns, row))
                services.append(SystemStatus(**service_dict))
            
            # Overall system health
            all_running = all(service.status == 'RUNNING' for service in services)
            any_errors = any(service.status == 'ERROR' for service in services)
            
            return {
                "overall_status": "HEALTHY" if all_running else "DEGRADED" if not any_errors else "ERROR",
                "services": services,
                "checked_at": datetime.now(timezone.utc)
            }
            
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/alm/performance-metrics")
async def get_performance_metrics(
    start_date: date = Query(..., description="Start date for performance calculation"),
    end_date: date = Query(default=None, description="End date (default: today)")
):
    """Get performance metrics for specified period"""
    try:
        if end_date is None:
            end_date = date.today()
        
        # Get summary data
        historical_summary = UnifiedALMService.get_historical_summary(start_date, end_date + timedelta(days=1))
        
        # Add today's real-time data if within range
        today = date.today()
        if start_date <= today <= end_date:
            realtime_summary = UnifiedALMService.get_realtime_summary(today)
            if realtime_summary:
                historical_summary.append(realtime_summary)
        
        # Calculate metrics
        metrics = UnifiedALMService.calculate_performance_metrics(historical_summary)
        
        return {
            "period_start": start_date,
            "period_end": end_date,
            "metrics": metrics,
            "calculated_at": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)