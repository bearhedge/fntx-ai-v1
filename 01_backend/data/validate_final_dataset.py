#!/usr/bin/env python3
"""
Validate the final December 2022 5-minute dataset for consistency
"""
import psycopg2
import pandas as pd
import sys
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def validate_dataset():
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("DECEMBER 2022 5-MINUTE DATA VALIDATION")
    print("="*100)
    
    # 1. Overall Data Integrity
    print("\n1. DATA INTEGRITY CHECK:")
    print("-"*80)
    
    query = """
    WITH data_counts AS (
        SELECT 
            oc.contract_id,
            oc.strike,
            oc.option_type,
            oc.expiration,
            COUNT(DISTINCT o.datetime) as ohlc_count,
            COUNT(DISTINCT g.datetime) as greeks_count,
            COUNT(DISTINCT i.datetime) as iv_count
        FROM theta.options_contracts oc
        LEFT JOIN theta.options_ohlc o ON oc.contract_id = o.contract_id
        LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id 
            AND o.datetime = i.datetime
        WHERE oc.symbol = 'SPY'
          AND oc.expiration >= '2022-12-01'
          AND oc.expiration <= '2022-12-31'
          AND oc.expiration = o.datetime::date  -- 0DTE only
        GROUP BY oc.contract_id, oc.strike, oc.option_type, oc.expiration
    )
    SELECT 
        COUNT(*) as total_contracts,
        SUM(CASE WHEN ohlc_count = 78 THEN 1 ELSE 0 END) as perfect_ohlc,
        SUM(CASE WHEN greeks_count = 78 THEN 1 ELSE 0 END) as perfect_greeks,
        SUM(CASE WHEN iv_count = 78 THEN 1 ELSE 0 END) as perfect_iv,
        SUM(CASE WHEN ohlc_count = 78 AND greeks_count = 78 AND iv_count = 78 THEN 1 ELSE 0 END) as perfect_all
    FROM data_counts
    """
    
    df = pd.read_sql_query(query, conn)
    stats = df.iloc[0]
    
    print(f"Total contracts: {stats['total_contracts']}")
    print(f"Contracts with exactly 78 OHLC bars: {stats['perfect_ohlc']} ({stats['perfect_ohlc']/stats['total_contracts']*100:.1f}%)")
    print(f"Contracts with exactly 78 Greeks bars: {stats['perfect_greeks']} ({stats['perfect_greeks']/stats['total_contracts']*100:.1f}%)")
    print(f"Contracts with exactly 78 IV bars: {stats['perfect_iv']} ({stats['perfect_iv']/stats['total_contracts']*100:.1f}%)")
    print(f"Contracts with perfect alignment (all 78): {stats['perfect_all']} ({stats['perfect_all']/stats['total_contracts']*100:.1f}%)")
    
    # 2. Identify Problem Contracts
    print("\n\n2. PROBLEM CONTRACTS:")
    print("-"*80)
    
    query = """
    SELECT 
        oc.expiration,
        oc.strike,
        oc.option_type,
        COUNT(DISTINCT o.datetime) as ohlc_count,
        COUNT(DISTINCT g.datetime) as greeks_count,
        COUNT(DISTINCT i.datetime) as iv_count
    FROM theta.options_contracts oc
    LEFT JOIN theta.options_ohlc o ON oc.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id 
        AND o.datetime = g.datetime
    LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id 
        AND o.datetime = i.datetime
    WHERE oc.symbol = 'SPY'
      AND oc.expiration >= '2022-12-01'
      AND oc.expiration <= '2022-12-31'
      AND oc.expiration = o.datetime::date
    GROUP BY oc.contract_id, oc.expiration, oc.strike, oc.option_type
    HAVING COUNT(DISTINCT o.datetime) != 78 
        OR COUNT(DISTINCT g.datetime) != 78 
        OR COUNT(DISTINCT i.datetime) != 78
    ORDER BY oc.expiration, oc.strike, oc.option_type
    LIMIT 20
    """
    
    df = pd.read_sql_query(query, conn)
    
    if len(df) > 0:
        print(f"Found {len(df)} contracts with issues (showing first 20):")
        print(f"{'Date':<12} {'Strike':<8} {'Type':<5} {'OHLC':>6} {'Greeks':>8} {'IV':>6}")
        print("-"*50)
        
        for _, row in df.iterrows():
            print(f"{row['expiration']} ${row['strike']:<6.0f} {row['option_type']:<5} "
                  f"{row['ohlc_count']:>6} {row['greeks_count']:>8} {row['iv_count']:>6}")
    else:
        print("✅ No problem contracts found!")
    
    # 3. Timestamp Alignment Check
    print("\n\n3. TIMESTAMP ALIGNMENT:")
    print("-"*80)
    
    query = """
    SELECT 
        COUNT(DISTINCT o.datetime) as unique_timestamps,
        MIN(o.datetime::time) as first_time,
        MAX(o.datetime::time) as last_time,
        COUNT(DISTINCT o.datetime::time) as unique_times
    FROM theta.options_ohlc o
    JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
    WHERE oc.symbol = 'SPY'
      AND oc.expiration = '2022-12-15'
      AND o.datetime::date = '2022-12-15'
    """
    
    df = pd.read_sql_query(query, conn)
    row = df.iloc[0]
    
    print(f"Sample day (Dec 15):")
    print(f"  Unique timestamps: {row['unique_timestamps']}")
    print(f"  Trading hours: {row['first_time']} to {row['last_time']}")
    print(f"  Unique times: {row['unique_times']} (should be 78)")
    
    # 4. Greeks Value Validation
    print("\n\n4. GREEKS VALUE VALIDATION:")
    print("-"*80)
    
    query = """
    SELECT 
        oc.option_type,
        COUNT(*) as total_records,
        SUM(CASE WHEN g.delta < -1 OR g.delta > 1 THEN 1 ELSE 0 END) as invalid_delta,
        SUM(CASE WHEN g.gamma < -10 OR g.gamma > 10 THEN 1 ELSE 0 END) as extreme_gamma,
        MIN(g.delta) as min_delta,
        MAX(g.delta) as max_delta
    FROM theta.options_greeks g
    JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
    WHERE oc.symbol = 'SPY'
      AND oc.expiration >= '2022-12-01'
      AND oc.expiration <= '2022-12-31'
      AND oc.expiration = g.datetime::date
    GROUP BY oc.option_type
    """
    
    df = pd.read_sql_query(query, conn)
    
    for _, row in df.iterrows():
        print(f"\n{row['option_type']} Options:")
        print(f"  Total records: {row['total_records']:,}")
        print(f"  Invalid delta (outside [-1,1]): {row['invalid_delta']}")
        print(f"  Extreme gamma (outside [-10,10]): {row['extreme_gamma']}")
        print(f"  Delta range: [{row['min_delta']:.4f}, {row['max_delta']:.4f}]")
    
    # 5. IV Coverage by Option Type
    print("\n\n5. IV COVERAGE BY OPTION TYPE:")
    print("-"*80)
    
    query = """
    SELECT 
        oc.option_type,
        COUNT(DISTINCT oc.contract_id) as contracts,
        COUNT(DISTINCT i.id) as iv_records,
        COUNT(DISTINCT i.id)::float / (COUNT(DISTINCT oc.contract_id) * 78) * 100 as coverage_pct
    FROM theta.options_contracts oc
    LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id
    WHERE oc.symbol = 'SPY'
      AND oc.expiration >= '2022-12-01'
      AND oc.expiration <= '2022-12-31'
    GROUP BY oc.option_type
    """
    
    df = pd.read_sql_query(query, conn)
    
    for _, row in df.iterrows():
        print(f"{row['option_type']} Options: {row['contracts']} contracts, "
              f"{row['iv_records']:,} IV records ({row['coverage_pct']:.1f}% coverage)")
    
    # 6. Final Summary
    print("\n\n6. FINAL DATASET SUMMARY:")
    print("-"*80)
    
    query = """
    SELECT 
        COUNT(DISTINCT oc.contract_id) as total_contracts,
        COUNT(DISTINCT o.id) as total_ohlc,
        COUNT(DISTINCT g.id) as total_greeks,
        COUNT(DISTINCT i.id) as total_iv,
        SUM(o.volume) as total_volume
    FROM theta.options_contracts oc
    LEFT JOIN theta.options_ohlc o ON oc.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id 
        AND o.datetime = g.datetime
    LEFT JOIN theta.options_iv i ON oc.contract_id = i.contract_id 
        AND o.datetime = i.datetime
    WHERE oc.symbol = 'SPY'
      AND oc.expiration >= '2022-12-01'
      AND oc.expiration <= '2022-12-31'
      AND oc.expiration = o.datetime::date
    """
    
    df = pd.read_sql_query(query, conn)
    row = df.iloc[0]
    
    print(f"Total contracts: {row['total_contracts']:,}")
    print(f"Total OHLC records: {row['total_ohlc']:,}")
    print(f"Total Greeks records: {row['total_greeks']:,}")
    print(f"Total IV records: {row['total_iv']:,}")
    print(f"Total volume traded: {row['total_volume']:,}")
    
    if row['total_ohlc'] > 0:
        print(f"\nAlignment rates:")
        print(f"  Greeks/OHLC: {row['total_greeks']/row['total_ohlc']*100:.1f}%")
        print(f"  IV/OHLC: {row['total_iv']/row['total_ohlc']*100:.1f}%")
    
    conn.close()

if __name__ == "__main__":
    validate_dataset()