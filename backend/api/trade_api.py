#!/usr/bin/env python3
"""
Standalone Trade API for automated trade logging
Runs 24/7 to capture all IBKR trades automatically
"""

import os
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="FNTX Trade Logger API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "fntx_trading"),
    "user": os.getenv("DB_USER", "info"),
    "password": os.getenv("DB_PASSWORD", "")
}

def get_db_connection():
    """Get database connection"""
    # Remove password for local trust authentication
    config = DB_CONFIG.copy()
    if config.get("password") == "trust" or config.get("password") == "":
        config.pop("password", None)
    return psycopg2.connect(**config)

@app.get("/")
async def root():
    return {"service": "FNTX Trade Logger API", "status": "running"}

@app.get("/api/trades/history")
async def get_trade_history(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get automated trade history from IBKR"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query based on filters
                query = """
                SELECT 
                    trade_id,
                    symbol,
                    strike_price,
                    option_type,
                    expiration,
                    quantity,
                    entry_time,
                    entry_price,
                    entry_commission,
                    exit_time,
                    exit_price,
                    exit_commission,
                    exit_reason,
                    realized_pnl,
                    status,
                    stop_loss_price,
                    take_profit_price,
                    market_snapshot
                FROM trading.trades
                """
                
                conditions = []
                params = []
                
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY entry_time DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                trades = cur.fetchall()
                
                # Convert decimal and date types for JSON serialization
                for trade in trades:
                    for key, value in trade.items():
                        if hasattr(value, 'isoformat'):
                            trade[key] = value.isoformat()
                        elif hasattr(value, '__float__'):
                            trade[key] = float(value)
                
                return {
                    "trades": trades,
                    "count": len(trades),
                    "offset": offset,
                    "limit": limit
                }
                
    except Exception as e:
        logger.error(f"Failed to fetch trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades/performance")
async def get_performance_metrics():
    """Get overall trading performance metrics"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get performance metrics from view
                cur.execute("SELECT * FROM trading.performance_metrics")
                metrics = cur.fetchone()
                
                # Get daily P&L chart data
                cur.execute("""
                    SELECT * FROM trading.daily_performance
                    WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'
                    ORDER BY trade_date DESC
                """)
                daily_performance = cur.fetchall()
                
                # Convert types
                if metrics:
                    for key, value in metrics.items():
                        if hasattr(value, '__float__'):
                            metrics[key] = float(value)
                
                for record in daily_performance:
                    if 'trade_date' in record:
                        record['trade_date'] = record['trade_date'].isoformat()
                    for key, value in record.items():
                        if hasattr(value, '__float__'):
                            record[key] = float(value)
                
                return {
                    "metrics": metrics,
                    "daily_performance": daily_performance,
                    "timestamp": datetime.now().isoformat()
                }
                
    except Exception as e:
        logger.error(f"Failed to fetch performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades/active")
async def get_active_trades():
    """Get currently active/open trades"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        trade_id,
                        symbol,
                        strike_price,
                        option_type,
                        expiration,
                        quantity,
                        entry_time,
                        entry_price,
                        stop_loss_price,
                        take_profit_price,
                        market_snapshot,
                        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - entry_time)) as seconds_active
                    FROM trading.trades
                    WHERE status = 'open'
                    ORDER BY entry_time DESC
                """)
                active_trades = cur.fetchall()
                
                # Convert types and calculate unrealized P&L
                for trade in active_trades:
                    for key, value in trade.items():
                        if hasattr(value, 'isoformat'):
                            trade[key] = value.isoformat()
                        elif hasattr(value, '__float__'):
                            trade[key] = float(value)
                    
                    # Calculate time active
                    if trade.get('seconds_active'):
                        seconds = int(trade['seconds_active'])
                        hours = seconds // 3600
                        minutes = (seconds % 3600) // 60
                        trade['time_active'] = f"{hours}h {minutes}m"
                
                return {
                    "active_trades": active_trades,
                    "count": len(active_trades),
                    "timestamp": datetime.now().isoformat()
                }
                
    except Exception as e:
        logger.error(f"Failed to fetch active trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades/analytics")
async def get_trade_analytics():
    """Get trade analytics for optimization"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Strike analysis
                cur.execute("SELECT * FROM trading.strike_analysis LIMIT 20")
                strike_analysis = cur.fetchall()
                
                # Time analysis
                cur.execute("SELECT * FROM trading.time_analysis ORDER BY entry_hour")
                time_analysis = cur.fetchall()
                
                # Risk analysis
                cur.execute("SELECT * FROM trading.risk_analysis")
                risk_analysis = cur.fetchall()
                
                # Convert types
                for analysis_list in [strike_analysis, time_analysis, risk_analysis]:
                    for record in analysis_list:
                        for key, value in record.items():
                            if hasattr(value, '__float__'):
                                record[key] = float(value)
                
                return {
                    "strike_analysis": strike_analysis,
                    "time_analysis": time_analysis,
                    "risk_analysis": risk_analysis,
                    "timestamp": datetime.now().isoformat()
                }
                
    except Exception as e:
        logger.error(f"Failed to fetch trade analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)