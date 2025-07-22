#!/usr/bin/env python3
"""
Create extraction tables for December 2022 0DTE data
Creates three tables as requested:
1. Contracts data table
2. Historical options data table  
3. Underlying data table
"""
import sys
import psycopg2
import yfinance as yf
from datetime import datetime, timedelta

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def create_extraction_tables():
    """Create the three extraction tables"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("CREATING EXTRACTION TABLES FOR DECEMBER 2022 DATA")
        print("="*80)
        
        # 1. Create contracts data table
        print("\n1. Creating contracts data table...")
        
        cursor.execute("DROP TABLE IF EXISTS extract_contracts CASCADE")
        
        cursor.execute("""
            CREATE TABLE extract_contracts AS
            SELECT 
                oc.contract_id,
                oc.symbol,
                oc.expiration,
                oc.strike,
                oc.option_type,
                COUNT(DISTINCT o.datetime) as data_points,
                MIN(o.datetime) as first_bar,
                MAX(o.datetime) as last_bar,
                CASE 
                    WHEN COUNT(DISTINCT o.datetime) > 0 THEN 
                        (COUNT(DISTINCT o.datetime)::NUMERIC / 78) * 100 
                    ELSE 0 
                END as coverage_pct,
                COUNT(DISTINCT g.datetime) as greeks_points,
                COUNT(DISTINCT i.datetime) as iv_points
            FROM theta.options_contracts oc
            LEFT JOIN theta.options_ohlc o ON oc.contract_id = o.contract_id
            LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id
            LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id
            WHERE oc.symbol = 'SPY' 
            AND oc.expiration >= '2022-12-01' 
            AND oc.expiration <= '2022-12-31'
            GROUP BY oc.contract_id, oc.symbol, oc.expiration, oc.strike, oc.option_type
            ORDER BY oc.expiration, oc.strike, oc.option_type
        """)
        
        cursor.execute("SELECT COUNT(*) FROM extract_contracts")
        contract_count = cursor.fetchone()[0]
        print(f"   ✓ Created with {contract_count} contracts")
        
        # Add indexes
        cursor.execute("CREATE INDEX idx_extract_contracts_exp ON extract_contracts(expiration)")
        cursor.execute("CREATE INDEX idx_extract_contracts_strike ON extract_contracts(strike)")
        
        # 2. Create historical options data table (denormalized)
        print("\n2. Creating historical options data table...")
        
        cursor.execute("DROP TABLE IF EXISTS extract_options_data CASCADE")
        
        cursor.execute("""
            CREATE TABLE extract_options_data AS
            SELECT 
                o.datetime,
                o.contract_id,
                oc.symbol,
                oc.expiration,
                oc.strike,
                oc.option_type,
                o.open,
                o.high,
                o.low,
                o.close,
                o.volume,
                o.trade_count,
                g.delta,
                g.gamma,
                g.theta,
                g.vega,
                g.rho,
                i.implied_volatility,
                -- Calculate moneyness
                CASE 
                    WHEN oc.option_type = 'C' THEN 
                        GREATEST(o.close - oc.strike, 0)
                    ELSE 
                        GREATEST(oc.strike - o.close, 0)
                END as intrinsic_value,
                o.close - CASE 
                    WHEN oc.option_type = 'C' THEN 
                        GREATEST(o.close - oc.strike, 0)
                    ELSE 
                        GREATEST(oc.strike - o.close, 0)
                END as time_value
            FROM theta.options_ohlc o
            JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
            LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id 
                AND o.datetime = g.datetime
            LEFT JOIN theta.options_iv i ON o.contract_id = i.contract_id 
                AND o.datetime = i.datetime
            WHERE oc.symbol = 'SPY' 
            AND oc.expiration >= '2022-12-01' 
            AND oc.expiration <= '2022-12-31'
            ORDER BY o.datetime, oc.strike, oc.option_type
        """)
        
        cursor.execute("SELECT COUNT(*) FROM extract_options_data")
        data_count = cursor.fetchone()[0]
        print(f"   ✓ Created with {data_count} data points")
        
        # Add indexes
        cursor.execute("CREATE INDEX idx_extract_options_datetime ON extract_options_data(datetime)")
        cursor.execute("CREATE INDEX idx_extract_options_contract ON extract_options_data(contract_id)")
        cursor.execute("CREATE INDEX idx_extract_options_exp_strike ON extract_options_data(expiration, strike)")
        
        # 3. Create underlying SPY data table
        print("\n3. Creating underlying SPY data table...")
        
        cursor.execute("DROP TABLE IF EXISTS extract_spy_data CASCADE")
        
        cursor.execute("""
            CREATE TABLE extract_spy_data (
                date DATE PRIMARY KEY,
                open_price NUMERIC(10,4),
                high NUMERIC(10,4),
                low NUMERIC(10,4),
                close NUMERIC(10,4),
                volume BIGINT,
                strikes_available INTEGER,
                contracts_traded INTEGER,
                atm_strike NUMERIC(10,2),
                put_call_ratio NUMERIC(5,2)
            )
        """)
        
        # Get SPY data from yfinance
        print("   Fetching SPY data from yfinance...")
        spy = yf.Ticker('SPY')
        spy_data = spy.history(start='2022-12-01', end='2023-01-01')
        
        # Insert SPY data with options statistics
        for date, row in spy_data.iterrows():
            trade_date = date.date()
            
            # Get options statistics for this date
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT strike) as strikes,
                    COUNT(DISTINCT contract_id) as contracts,
                    COUNT(CASE WHEN option_type = 'P' THEN 1 END)::NUMERIC / 
                        NULLIF(COUNT(CASE WHEN option_type = 'C' THEN 1 END), 0) as pc_ratio
                FROM theta.options_contracts
                WHERE symbol = 'SPY' AND expiration = %s
            """, (trade_date,))
            
            stats = cursor.fetchone()
            strikes_count = stats[0] or 0
            contracts_count = stats[1] or 0
            pc_ratio = stats[2] or 0
            
            # Find ATM strike
            cursor.execute("""
                SELECT strike 
                FROM theta.options_contracts
                WHERE symbol = 'SPY' AND expiration = %s
                ORDER BY ABS(strike - %s)
                LIMIT 1
            """, (trade_date, float(row['Open'])))
            
            atm_result = cursor.fetchone()
            atm_strike = atm_result[0] if atm_result else None
            
            # Insert row
            cursor.execute("""
                INSERT INTO extract_spy_data 
                (date, open_price, high, low, close, volume, 
                 strikes_available, contracts_traded, atm_strike, put_call_ratio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO NOTHING
            """, (
                trade_date,
                float(row['Open']), float(row['High']), float(row['Low']), float(row['Close']),
                int(row['Volume']),
                strikes_count, contracts_count, atm_strike, float(pc_ratio) if pc_ratio else 0
            ))
        
        cursor.execute("SELECT COUNT(*) FROM extract_spy_data")
        spy_count = cursor.fetchone()[0]
        print(f"   ✓ Created with {spy_count} days of SPY data")
        
        conn.commit()
        
        # Print summary
        print("\n" + "="*80)
        print("EXTRACTION TABLES CREATED SUCCESSFULLY")
        print("="*80)
        
        print("\n📊 Table Summary:")
        print(f"1. extract_contracts: {contract_count} contracts")
        print(f"2. extract_options_data: {data_count} data points")
        print(f"3. extract_spy_data: {spy_count} trading days")
        
        # Sample queries
        print("\n📝 Sample Queries:")
        print("-- Get all contracts for a specific day:")
        print("SELECT * FROM extract_contracts WHERE expiration = '2022-12-01';")
        print("\n-- Get all data for ATM options:")
        print("SELECT * FROM extract_options_data WHERE ABS(strike - 400) < 5;")
        print("\n-- Get SPY daily statistics:")
        print("SELECT * FROM extract_spy_data ORDER BY date;")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error creating tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def verify_tables():
    """Verify the extraction tables were created correctly"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        print("\n\nVERIFYING EXTRACTION TABLES")
        print("="*80)
        
        # Check contracts table
        cursor.execute("""
            SELECT 
                COUNT(*) as total_contracts,
                COUNT(DISTINCT expiration) as trading_days,
                MIN(strike) as min_strike,
                MAX(strike) as max_strike,
                AVG(coverage_pct) as avg_coverage
            FROM extract_contracts
        """)
        
        stats = cursor.fetchone()
        print(f"\n✓ Contracts Table:")
        print(f"  Total contracts: {stats[0]}")
        print(f"  Trading days: {stats[1]}")
        print(f"  Strike range: ${stats[2]} - ${stats[3]}")
        print(f"  Average coverage: {stats[4]:.1f}%")
        
        # Check options data table
        cursor.execute("""
            SELECT 
                COUNT(*) as total_bars,
                COUNT(DISTINCT datetime::date) as days,
                COUNT(DISTINCT contract_id) as contracts,
                AVG(implied_volatility) as avg_iv
            FROM extract_options_data
            WHERE implied_volatility IS NOT NULL
        """)
        
        stats = cursor.fetchone()
        print(f"\n✓ Options Data Table:")
        print(f"  Total bars: {stats[0]:,}")
        print(f"  Days with data: {stats[1]}")
        print(f"  Unique contracts: {stats[2]}")
        print(f"  Average IV: {stats[3]:.4f}" if stats[3] else "  Average IV: N/A")
        
        # Check SPY data table
        cursor.execute("""
            SELECT 
                COUNT(*) as days,
                AVG(contracts_traded) as avg_contracts,
                AVG(strikes_available) as avg_strikes,
                AVG(put_call_ratio) as avg_pc_ratio
            FROM extract_spy_data
            WHERE contracts_traded > 0
        """)
        
        stats = cursor.fetchone()
        print(f"\n✓ SPY Data Table:")
        print(f"  Trading days: {stats[0]}")
        print(f"  Avg contracts/day: {stats[1]:.0f}" if stats[1] else "  Avg contracts/day: N/A")
        print(f"  Avg strikes/day: {stats[2]:.0f}" if stats[2] else "  Avg strikes/day: N/A")
        print(f"  Avg put/call ratio: {stats[3]:.2f}" if stats[3] else "  Avg put/call ratio: N/A")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_extraction_tables()
    verify_tables()