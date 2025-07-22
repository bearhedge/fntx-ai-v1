#!/usr/bin/env python3
"""
Extract only the clean 0DTE data from December 2022
"""
import psycopg2
import pandas as pd
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def extract_clean_data():
    conn = psycopg2.connect(**DB_CONFIG)
    
    print("EXTRACTING CLEAN 0DTE DATA")
    print("="*80)
    
    # Get clean 0DTE data statistics
    query = """
    WITH clean_contracts AS (
        SELECT DISTINCT oc.contract_id
        FROM theta.options_contracts oc
        WHERE oc.symbol = 'SPY'
          AND oc.expiration >= '2022-12-01'
          AND oc.expiration <= '2022-12-31'
          AND oc.contract_id BETWEEN 117799 AND 119374  -- Our download range
    )
    SELECT 
        COUNT(DISTINCT c.contract_id) as contracts,
        COUNT(DISTINCT o.id) as ohlc_records,
        COUNT(DISTINCT g.id) as greeks_records,
        COUNT(DISTINCT i.id) as iv_records,
        MIN(oc.expiration) as min_exp,
        MAX(oc.expiration) as max_exp
    FROM clean_contracts c
    JOIN theta.options_contracts oc ON c.contract_id = oc.contract_id
    LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
    LEFT JOIN theta.options_iv i ON c.contract_id = i.contract_id
    """
    
    df = pd.read_sql_query(query, conn)
    row = df.iloc[0]
    
    print(f"Clean 0DTE Dataset:")
    print(f"  Contracts: {row['contracts']:,}")
    print(f"  Date range: {row['min_exp']} to {row['max_exp']}")
    print(f"  OHLC records: {row['ohlc_records']:,}")
    print(f"  Greeks records: {row['greeks_records']:,}")
    print(f"  IV records: {row['iv_records']:,}")
    
    expected = row['contracts'] * 78
    print(f"\nExpected records: {expected:,}")
    print(f"OHLC completeness: {row['ohlc_records']/expected*100:.1f}%")
    print(f"Greeks completeness: {row['greeks_records']/expected*100:.1f}%")
    print(f"IV completeness: {row['iv_records']/expected*100:.1f}%")
    
    # Check alignment
    query = """
    WITH clean_contracts AS (
        SELECT DISTINCT oc.contract_id
        FROM theta.options_contracts oc
        WHERE oc.symbol = 'SPY'
          AND oc.expiration >= '2022-12-01'
          AND oc.expiration <= '2022-12-31'
          AND oc.contract_id BETWEEN 117799 AND 119374
    )
    SELECT 
        oc.option_type,
        COUNT(DISTINCT oc.contract_id) as contracts,
        COUNT(DISTINCT o.datetime) as unique_times,
        COUNT(o.id) as ohlc_count,
        COUNT(g.id) as greeks_count,
        COUNT(i.id) as iv_count
    FROM clean_contracts c
    JOIN theta.options_contracts oc ON c.contract_id = oc.contract_id
    LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id AND o.datetime = g.datetime
    LEFT JOIN theta.options_iv i ON c.contract_id = i.contract_id AND o.datetime = i.datetime
    GROUP BY oc.option_type
    """
    
    print("\n\nBreakdown by option type:")
    print(f"{'Type':<5} {'Contracts':>10} {'Times':>8} {'OHLC':>10} {'Greeks':>10} {'IV':>10}")
    print("-"*55)
    
    df = pd.read_sql_query(query, conn)
    for _, row in df.iterrows():
        print(f"{row['option_type']:<5} {row['contracts']:>10} {row['unique_times']:>8} "
              f"{row['ohlc_count']:>10,} {row['greeks_count']:>10,} {row['iv_count']:>10,}")
    
    # Check for 16:00 Greeks
    query = """
    WITH clean_contracts AS (
        SELECT DISTINCT oc.contract_id
        FROM theta.options_contracts oc
        WHERE oc.symbol = 'SPY'
          AND oc.expiration >= '2022-12-01'
          AND oc.expiration <= '2022-12-31'
          AND oc.contract_id BETWEEN 117799 AND 119374
    )
    SELECT COUNT(*) as extra_greeks
    FROM clean_contracts c
    JOIN theta.options_greeks g ON c.contract_id = g.contract_id
    WHERE g.datetime::time = '16:00:00'
    """
    
    df = pd.read_sql_query(query, conn)
    extra = df.iloc[0]['extra_greeks']
    print(f"\nExtra 16:00 Greeks records to remove: {extra:,}")
    
    conn.close()

if __name__ == "__main__":
    extract_clean_data()