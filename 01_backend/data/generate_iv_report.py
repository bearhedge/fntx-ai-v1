#!/usr/bin/env python3
"""
Generate comprehensive IV coverage report for downloaded data
"""
import sys
import psycopg2
import pandas as pd
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def generate_iv_report(date: str = "2023-01-03"):
    """Generate comprehensive IV coverage report"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    print(f"\n📊 IV Coverage Report for {date}")
    print("=" * 80)
    
    # 1. Overall statistics
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT c.contract_id) as total_contracts,
            COUNT(o.datetime) as total_data_points,
            COUNT(iv.implied_volatility) as iv_data_points,
            COUNT(o.datetime) - COUNT(iv.implied_volatility) as null_iv_points,
            ROUND(COUNT(iv.implied_volatility)::numeric / COUNT(o.datetime) * 100, 1) as overall_coverage_pct
        FROM theta.options_contracts c
        JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id AND o.datetime = iv.datetime
        WHERE c.symbol = 'SPY' AND c.expiration = %s
    """, (date,))
    
    stats = cursor.fetchone()
    print(f"\n1. Overall Statistics:")
    print(f"   Total contracts: {stats[0]}")
    print(f"   Total data points: {stats[1]}")
    print(f"   IV data points: {stats[2]}")
    print(f"   NULL IV points: {stats[3]}")
    print(f"   Overall IV coverage: {stats[4]}%")
    
    # 2. Coverage by strike distance from ATM
    cursor.execute("""
        WITH contract_stats AS (
            SELECT 
                c.strike,
                c.option_type,
                COUNT(o.datetime) as total_points,
                COUNT(iv.implied_volatility) as iv_points,
                ROUND(COUNT(iv.implied_volatility)::numeric / COUNT(o.datetime) * 100, 1) as coverage_pct
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id AND o.datetime = iv.datetime
            WHERE c.symbol = 'SPY' AND c.expiration = %s
            GROUP BY c.contract_id, c.strike, c.option_type
        )
        SELECT 
            CASE 
                WHEN ABS(strike - 384) <= 2 THEN 'ATM (±$2)'
                WHEN ABS(strike - 384) <= 5 THEN 'Near ATM (±$5)'
                ELSE 'Far OTM (>$5)'
            END as distance_category,
            option_type,
            COUNT(*) as contracts,
            SUM(total_points) as total_points,
            SUM(iv_points) as iv_points,
            ROUND(SUM(iv_points)::numeric / SUM(total_points) * 100, 1) as coverage_pct
        FROM contract_stats
        GROUP BY 
            CASE 
                WHEN ABS(strike - 384) <= 2 THEN 'ATM (±$2)'
                WHEN ABS(strike - 384) <= 5 THEN 'Near ATM (±$5)'
                ELSE 'Far OTM (>$5)'
            END, option_type
        ORDER BY 
            CASE 
                WHEN MIN(ABS(strike - 384)) <= 2 THEN 1
                WHEN MIN(ABS(strike - 384)) <= 5 THEN 2
                ELSE 3
            END,
            option_type
    """, (date,))
    
    print(f"\n2. IV Coverage by Distance from ATM:")
    print(f"{'Category':<15} {'Type':<5} {'Contracts':<10} {'Coverage %':<12}")
    print("-" * 45)
    
    for row in cursor.fetchall():
        print(f"{row[0]:<15} {row[1]:<5} {row[2]:<10} {row[5]:<12}%")
    
    # 3. Problematic contracts (low IV coverage)
    cursor.execute("""
        SELECT 
            c.strike,
            c.option_type,
            COUNT(o.datetime) as total_bars,
            COUNT(iv.implied_volatility) as bars_with_iv,
            ROUND(COUNT(iv.implied_volatility)::numeric / COUNT(o.datetime) * 100, 1) as coverage_pct,
            SUM(o.volume) as total_volume
        FROM theta.options_contracts c
        JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id AND o.datetime = iv.datetime
        WHERE c.symbol = 'SPY' AND c.expiration = %s
        GROUP BY c.contract_id, c.strike, c.option_type
        HAVING COUNT(iv.implied_volatility)::numeric / COUNT(o.datetime) < 0.5
        ORDER BY coverage_pct, c.strike
    """, (date,))
    
    print(f"\n3. Contracts with Low IV Coverage (<50%):")
    print(f"{'Strike':<8} {'Type':<5} {'Bars':<8} {'IV Bars':<10} {'Coverage':<10} {'Volume':<12}")
    print("-" * 60)
    
    for row in cursor.fetchall():
        print(f"${row[0]:<7} {row[1]:<5} {row[2]:<8} {row[3]:<10} {row[4]:<9}% {row[5]:<12,}")
    
    # 4. Time-based IV availability
    cursor.execute("""
        SELECT 
            EXTRACT(HOUR FROM o.datetime) as hour,
            COUNT(o.datetime) as total_points,
            COUNT(iv.implied_volatility) as iv_points,
            ROUND(COUNT(iv.implied_volatility)::numeric / COUNT(o.datetime) * 100, 1) as coverage_pct
        FROM theta.options_contracts c
        JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id AND o.datetime = iv.datetime
        WHERE c.symbol = 'SPY' AND c.expiration = %s
        GROUP BY EXTRACT(HOUR FROM o.datetime)
        ORDER BY hour
    """, (date,))
    
    print(f"\n4. IV Coverage by Hour:")
    print(f"{'Hour':<6} {'Total':<8} {'With IV':<10} {'Coverage %':<12}")
    print("-" * 40)
    
    for row in cursor.fetchall():
        print(f"{int(row[0]):02d}:00  {row[1]:<8} {row[2]:<10} {row[3]:<12}%")
    
    # 5. LOCF effectiveness
    cursor.execute("""
        WITH locf_stats AS (
            SELECT 
                contract_id,
                COUNT(*) as total_bars,
                COUNT(CASE WHEN raw_iv IS NOT NULL THEN 1 END) as original_iv,
                COUNT(CASE WHEN raw_iv IS NULL AND iv_filled IS NOT NULL THEN 1 END) as interpolated_iv,
                COUNT(CASE WHEN iv_filled IS NULL THEN 1 END) as still_null
            FROM theta.options_data_filled
            WHERE symbol = 'SPY' AND expiration = %s
            GROUP BY contract_id
        )
        SELECT 
            SUM(total_bars) as total,
            SUM(original_iv) as original,
            SUM(interpolated_iv) as interpolated,
            SUM(still_null) as still_null,
            ROUND(SUM(interpolated_iv)::numeric / NULLIF(SUM(total_bars) - SUM(original_iv), 0) * 100, 1) as fill_rate
        FROM locf_stats
    """, (date,))
    
    stats = cursor.fetchone()
    if stats and stats[0]:
        print(f"\n5. LOCF Interpolation Effectiveness:")
        print(f"   Total data points: {stats[0]}")
        print(f"   Original IV values: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"   Interpolated values: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
        print(f"   Still NULL: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")
        if stats[4]:
            print(f"   Fill rate for gaps: {stats[4]}%")
    
    print("\n" + "=" * 80)
    print("✅ Report Complete")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_iv_report(sys.argv[1])
    else:
        generate_iv_report()