#!/usr/bin/env python3
"""
Monitor the progress of 5-minute data download
"""
import psycopg2
import sys
import time
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def monitor_progress():
    """Monitor download progress"""
    
    print("MONITORING 5-MINUTE DATA DOWNLOAD PROGRESS")
    print("="*80)
    
    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Check December 2022 data
            cursor.execute("""
            SELECT 
                COUNT(DISTINCT oc.contract_id) as contracts,
                COUNT(DISTINCT ohlc.datetime::date) as days,
                COUNT(ohlc.id) as ohlc_records,
                COUNT(g.id) as greeks_records,
                COUNT(iv.id) as iv_records,
                MIN(ohlc.datetime::date) as first_date,
                MAX(ohlc.datetime::date) as last_date
            FROM theta.options_contracts oc
            LEFT JOIN theta.options_ohlc ohlc ON oc.contract_id = ohlc.contract_id
            LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id 
                AND ohlc.datetime = g.datetime
            LEFT JOIN theta.options_iv iv ON oc.contract_id = iv.contract_id 
                AND ohlc.datetime = iv.datetime
            WHERE oc.symbol = 'SPY'
              AND oc.expiration >= '2022-12-01'
              AND oc.expiration <= '2022-12-31'
              AND oc.expiration = ohlc.datetime::date  -- 0DTE only
            """)
            
            result = cursor.fetchone()
            contracts, days, ohlc, greeks, iv, first_date, last_date = result
            
            print(f"\n{datetime.now().strftime('%H:%M:%S')} - Current Status:")
            print(f"  Days processed: {days or 0}")
            print(f"  Date range: {first_date} to {last_date}" if first_date else "  No data yet")
            print(f"  Contracts: {contracts or 0}")
            print(f"  OHLC records: {ohlc or 0:,}")
            print(f"  Greeks records: {greeks or 0:,}")
            print(f"  IV records: {iv or 0:,}")
            
            if ohlc and contracts:
                bars_per_contract = ohlc / contracts
                print(f"  Bars per contract: {bars_per_contract:.1f} (expecting ~78)")
                
            if ohlc and greeks:
                print(f"  Greeks coverage: {greeks/ohlc*100:.1f}%")
                
            if ohlc and iv:
                print(f"  IV coverage: {iv/ohlc*100:.1f}%")
            
            # Check latest log entries
            cursor.execute("""
            SELECT datetime::date, COUNT(*) as records
            FROM theta.options_ohlc
            WHERE datetime >= '2022-12-01'
            GROUP BY datetime::date
            ORDER BY datetime::date DESC
            LIMIT 3
            """)
            
            print("\n  Recent days:")
            for date, count in cursor.fetchall():
                print(f"    {date}: {count:,} records")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"\nError: {e}")
        
        # Wait 30 seconds before checking again
        time.sleep(30)

if __name__ == "__main__":
    try:
        monitor_progress()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")