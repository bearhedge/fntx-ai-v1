#!/usr/bin/env python3
"""
Trade Import API Endpoints
Handles Flex Query imports and CSV uploads for historical trade data
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel

from backend.services.ibkr_flex_query_enhanced import flex_query_enhanced as flex_query_service
from backend.database.trade_db import get_trade_db_connection
# from backend.scripts.import_flex_trades import import_matched_trades
# from backend.scripts.import_trades_csv import IBKRCSVImporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trades", tags=["Trade Import"])

class FlexQueryRequest(BaseModel):
    days_back: Optional[int] = 30
    include_open_positions: Optional[bool] = False

class FlexQueryResponse(BaseModel):
    status: str
    message: str
    import_id: Optional[str] = None
    trades_found: Optional[int] = None
    trades_imported: Optional[int] = None

class ImportStatusResponse(BaseModel):
    import_id: str
    status: str
    import_date: str
    trades_imported: int
    trades_skipped: int
    total_pnl: Optional[float] = None
    error_message: Optional[str] = None

@router.post("/import/flex", response_model=FlexQueryResponse)
async def trigger_flex_import(request: FlexQueryRequest, background_tasks: BackgroundTasks):
    """Trigger a Flex Query import for historical trades"""
    try:
        # Check if credentials are configured
        if not flex_query_service.token or not flex_query_service.query_id:
            raise HTTPException(
                status_code=400,
                detail="Flex Query credentials not configured. Please set IBKR_FLEX_TOKEN and IBKR_FLEX_QUERY_ID"
            )
        
        # Create import record
        import_id = None
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trading.flex_query_imports (
                        query_id, period_start, period_end, status
                    ) VALUES (%s, %s, %s, 'pending')
                    RETURNING import_id
                """, (
                    flex_query_service.query_id,
                    datetime.now() - timedelta(days=request.days_back),
                    datetime.now(),
                ))
                import_id = str(cur.fetchone()[0])
                conn.commit()
        
        # Start import in background
        background_tasks.add_task(
            run_flex_import,
            import_id,
            request.days_back,
            request.include_open_positions
        )
        
        return FlexQueryResponse(
            status="initiated",
            message=f"Flex Query import started for last {request.days_back} days",
            import_id=import_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger Flex import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_flex_import(import_id: str, days_back: int, include_open: bool):
    """Run Flex Query import in background"""
    try:
        logger.info(f"Starting Flex Query import {import_id}")
        
        # Get complete trade history
        matched_pairs = flex_query_service.get_complete_trade_history(days_back=days_back)
        
        if not matched_pairs:
            # Update import record
            with get_trade_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE trading.flex_query_imports
                        SET status = 'completed', trades_imported = 0, trades_skipped = 0
                        WHERE import_id = %s
                    """, (import_id,))
                    conn.commit()
            return
        
        # Import trades
        imported_count = import_matched_trades(matched_pairs)
        
        # Calculate total P&L
        total_pnl = sum(float(pair['net_pnl']) for pair in matched_pairs)
        
        # Update import record
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trading.flex_query_imports
                    SET status = 'completed', 
                        trades_imported = %s,
                        trades_skipped = %s,
                        total_pnl = %s
                    WHERE import_id = %s
                """, (
                    imported_count,
                    len(matched_pairs) - imported_count,
                    total_pnl,
                    import_id
                ))
                conn.commit()
        
        logger.info(f"Flex Query import {import_id} completed: {imported_count} trades imported")
        
    except Exception as e:
        logger.error(f"Flex Query import {import_id} failed: {e}")
        
        # Update import record with error
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trading.flex_query_imports
                    SET status = 'failed', error_message = %s
                    WHERE import_id = %s
                """, (str(e), import_id))
                conn.commit()

@router.post("/import/csv", response_model=FlexQueryResponse)
async def upload_csv_file(file: UploadFile = File(...)):
    """Upload and import trades from IBKR CSV file"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        contents = await file.read()
        
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        # Create import record
        import_id = None
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trading.csv_imports (filename, status)
                    VALUES (%s, 'pending')
                    RETURNING import_id
                """, (file.filename,))
                import_id = str(cur.fetchone()[0])
                conn.commit()
        
        # Process CSV
        importer = IBKRCSVImporter()
        
        if not importer.parse_csv_file(temp_path):
            raise HTTPException(status_code=400, detail="Failed to parse CSV file")
        
        # Match trades
        importer.match_trades()
        
        if not importer.matched_pairs:
            raise HTTPException(status_code=400, detail="No matched trade pairs found in CSV")
        
        # Import to database
        importer.import_to_database()
        
        # Update import record
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE trading.csv_imports
                    SET status = 'completed',
                        trades_imported = %s,
                        total_rows = %s
                    WHERE import_id = %s
                """, (len(importer.matched_pairs), len(importer.trades), import_id))
                conn.commit()
        
        # Clean up temp file
        os.remove(temp_path)
        
        return FlexQueryResponse(
            status="completed",
            message=f"Successfully imported {len(importer.matched_pairs)} trades from CSV",
            import_id=import_id,
            trades_found=len(importer.trades),
            trades_imported=len(importer.matched_pairs)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import/status/{import_id}", response_model=ImportStatusResponse)
async def get_import_status(import_id: str):
    """Get status of a specific import"""
    try:
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                # Check Flex Query imports
                cur.execute("""
                    SELECT import_date, status, trades_imported, trades_skipped, 
                           total_pnl, error_message
                    FROM trading.flex_query_imports
                    WHERE import_id = %s
                """, (import_id,))
                
                result = cur.fetchone()
                if result:
                    return ImportStatusResponse(
                        import_id=import_id,
                        status=result[1],
                        import_date=result[0].isoformat(),
                        trades_imported=result[2] or 0,
                        trades_skipped=result[3] or 0,
                        total_pnl=float(result[4]) if result[4] else None,
                        error_message=result[5]
                    )
                
                # Check CSV imports
                cur.execute("""
                    SELECT import_date, status, trades_imported, trades_skipped, error_message
                    FROM trading.csv_imports
                    WHERE import_id = %s
                """, (import_id,))
                
                result = cur.fetchone()
                if result:
                    return ImportStatusResponse(
                        import_id=import_id,
                        status=result[1],
                        import_date=result[0].isoformat(),
                        trades_imported=result[2] or 0,
                        trades_skipped=result[3] or 0,
                        error_message=result[4]
                    )
                
                raise HTTPException(status_code=404, detail="Import not found")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get import status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import/history")
async def get_import_history(limit: int = 10):
    """Get recent import history"""
    try:
        imports = []
        
        with get_trade_db_connection() as conn:
            with conn.cursor() as cur:
                # Get Flex Query imports
                cur.execute("""
                    SELECT import_id, import_date, status, trades_imported, 
                           trades_skipped, total_pnl, 'flex_query' as type
                    FROM trading.flex_query_imports
                    ORDER BY import_date DESC
                    LIMIT %s
                """, (limit,))
                
                for row in cur.fetchall():
                    imports.append({
                        "import_id": str(row[0]),
                        "import_date": row[1].isoformat(),
                        "status": row[2],
                        "trades_imported": row[3] or 0,
                        "trades_skipped": row[4] or 0,
                        "total_pnl": float(row[5]) if row[5] else None,
                        "type": row[6]
                    })
                
                # Get CSV imports
                cur.execute("""
                    SELECT import_id, import_date, status, trades_imported, 
                           trades_skipped, filename, 'csv' as type
                    FROM trading.csv_imports
                    ORDER BY import_date DESC
                    LIMIT %s
                """, (limit,))
                
                for row in cur.fetchall():
                    imports.append({
                        "import_id": str(row[0]),
                        "import_date": row[1].isoformat(),
                        "status": row[2],
                        "trades_imported": row[3] or 0,
                        "trades_skipped": row[4] or 0,
                        "filename": row[5],
                        "type": row[6]
                    })
        
        # Sort by date
        imports.sort(key=lambda x: x["import_date"], reverse=True)
        
        return imports[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get import history: {e}")
        raise HTTPException(status_code=500, detail=str(e))