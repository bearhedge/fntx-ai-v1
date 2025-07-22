#!/usr/bin/env python3
"""
Pull 0DTE options data from the database
Various query options for different analysis needs
"""
import sys
import psycopg2
import pandas as pd
from datetime import datetime

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def get_all_data(date: str = "2023-01-03"):
    """Pull all data for a specific date"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            c.strike,
            c.option_type,
            o.datetime,
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
            iv.implied_volatility
        FROM theta.options_contracts c
        LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id AND o.datetime = g.datetime
        LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id AND o.datetime = iv.datetime
        WHERE c.symbol = 'SPY' 
        AND c.expiration = %s
        AND o.datetime IS NOT NULL
        ORDER BY c.strike, c.option_type, o.datetime
    """
    
    df = pd.read_sql(query, conn, params=[date])
    conn.close()
    
    return df

def get_ohlc_data(date: str = "2023-01-03"):
    """Pull just OHLC data"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            c.strike,
            c.option_type,
            o.datetime,
            o.open,
            o.high,
            o.low,
            o.close,
            o.volume,
            o.trade_count
        FROM theta.options_contracts c
        JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        WHERE c.symbol = 'SPY' 
        AND c.expiration = %s
        ORDER BY c.strike, c.option_type, o.datetime
    """
    
    df = pd.read_sql(query, conn, params=[date])
    conn.close()
    
    return df

def get_greeks_data(date: str = "2023-01-03"):
    """Pull just Greeks data"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            c.strike,
            c.option_type,
            g.datetime,
            g.delta,
            g.gamma,
            g.theta,
            g.vega,
            g.rho
        FROM theta.options_contracts c
        JOIN theta.options_greeks g ON c.contract_id = g.contract_id
        WHERE c.symbol = 'SPY' 
        AND c.expiration = %s
        ORDER BY c.strike, c.option_type, g.datetime
    """
    
    df = pd.read_sql(query, conn, params=[date])
    conn.close()
    
    return df

def get_iv_data(date: str = "2023-01-03"):
    """Pull just IV data"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            c.strike,
            c.option_type,
            iv.datetime,
            iv.implied_volatility
        FROM theta.options_contracts c
        JOIN theta.options_iv iv ON c.contract_id = iv.contract_id
        WHERE c.symbol = 'SPY' 
        AND c.expiration = %s
        ORDER BY c.strike, c.option_type, iv.datetime
    """
    
    df = pd.read_sql(query, conn, params=[date])
    conn.close()
    
    return df

def get_contract_summary(date: str = "2023-01-03"):
    """Get summary of available contracts"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            c.strike,
            c.option_type,
            COUNT(o.datetime) as ohlc_bars,
            COUNT(g.datetime) as greeks_bars,
            COUNT(iv.datetime) as iv_bars,
            MIN(o.datetime) as first_bar,
            MAX(o.datetime) as last_bar,
            SUM(o.volume) as total_volume
        FROM theta.options_contracts c
        LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
        LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id
        WHERE c.symbol = 'SPY' 
        AND c.expiration = %s
        GROUP BY c.contract_id, c.strike, c.option_type
        ORDER BY c.strike, c.option_type
    """
    
    df = pd.read_sql(query, conn, params=[date])
    conn.close()
    
    return df

def get_specific_strike(strike: float, option_type: str, date: str = "2023-01-03"):
    """Pull data for a specific strike and option type"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            o.datetime,
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
            iv.implied_volatility
        FROM theta.options_contracts c
        LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id AND o.datetime = g.datetime
        LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id AND o.datetime = iv.datetime
        WHERE c.symbol = 'SPY' 
        AND c.expiration = %s
        AND c.strike = %s
        AND c.option_type = %s
        AND o.datetime IS NOT NULL
        ORDER BY o.datetime
    """
    
    df = pd.read_sql(query, conn, params=[date, strike, option_type])
    conn.close()
    
    return df

def get_atm_data(date: str = "2023-01-03", atm_strike: float = 384):
    """Pull data for ATM strike (both calls and puts)"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
        SELECT 
            c.option_type,
            o.datetime,
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
            iv.implied_volatility
        FROM theta.options_contracts c
        LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
        LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id AND o.datetime = g.datetime
        LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id AND o.datetime = iv.datetime
        WHERE c.symbol = 'SPY' 
        AND c.expiration = %s
        AND c.strike = %s
        AND o.datetime IS NOT NULL
        ORDER BY c.option_type, o.datetime
    """
    
    df = pd.read_sql(query, conn, params=[date, atm_strike])
    conn.close()
    
    return df

def main():
    """Example usage"""
    print("Example queries for 0DTE options data:")
    print("="*50)
    
    # 1. Get contract summary
    print("\n1. Contract Summary:")
    summary = get_contract_summary()
    print(summary.head())
    
    # 2. Get specific strike data
    print("\n2. ATM Put ($384 Put):")
    atm_put = get_specific_strike(384, 'P')
    print(f"Shape: {atm_put.shape}")
    print(atm_put.head())
    
    # 3. Get OHLC data for all contracts
    print("\n3. All OHLC Data:")
    ohlc = get_ohlc_data()
    print(f"Shape: {ohlc.shape}")
    print(f"Date range: {ohlc['datetime'].min()} to {ohlc['datetime'].max()}")
    
    # 4. Get just the strikes available
    strikes = summary['strike'].unique()
    print(f"\n4. Available Strikes: {sorted(strikes)}")

if __name__ == "__main__":
    main()