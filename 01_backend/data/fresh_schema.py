#!/usr/bin/env python3
"""
Create fresh schema with only clean data
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("CREATING FRESH SCHEMA WITH CLEAN DATA")
print("="*50)

try:
    # Drop and recreate theta schema
    print("1. Dropping old theta schema...")
    cursor.execute("DROP SCHEMA IF EXISTS theta CASCADE")
    cursor.execute("CREATE SCHEMA theta")
    conn.commit()
    print("   ✓ Created fresh theta schema")
    
    # Create contracts table
    print("2. Creating contracts table...")
    cursor.execute("""
    CREATE TABLE theta.options_contracts (
        contract_id BIGINT PRIMARY KEY,
        symbol VARCHAR(10),
        strike DECIMAL(10,2),
        expiration DATE,
        option_type CHAR(1),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create OHLC table
    cursor.execute("""
    CREATE TABLE theta.options_ohlc (
        id BIGSERIAL PRIMARY KEY,
        contract_id BIGINT,
        datetime TIMESTAMP,
        open DECIMAL(10,4),
        high DECIMAL(10,4),
        low DECIMAL(10,4),
        close DECIMAL(10,4),
        volume INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create Greeks table
    cursor.execute("""
    CREATE TABLE theta.options_greeks (
        id BIGSERIAL PRIMARY KEY,
        contract_id BIGINT,
        datetime TIMESTAMP,
        delta DECIMAL(10,6),
        gamma DECIMAL(10,6),
        theta DECIMAL(10,6),
        vega DECIMAL(10,6),
        rho DECIMAL(10,6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create IV table
    cursor.execute("""
    CREATE TABLE theta.options_iv (
        id BIGSERIAL PRIMARY KEY,
        contract_id BIGINT,
        datetime TIMESTAMP,
        implied_volatility DECIMAL(10,6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    print("   ✓ Created all tables")
    
    print("\n✓ Fresh schema ready - database is now clean!")
    print("Run your downloader again to populate with December 2022 0DTE data.")
    
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
finally:
    cursor.close()
    conn.close()