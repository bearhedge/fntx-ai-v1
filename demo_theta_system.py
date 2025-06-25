#!/usr/bin/env python3
"""
Demo: ThetaTerminal Options Data System
Shows how to download data and use it for ML
"""
import sys
sys.path.append('backend')

from data.options_ml_dataloader import OptionsMLDataLoader
import pandas as pd

def demo():
    """Demonstrate the options data system"""
    print("=" * 60)
    print("ThetaTerminal Options Data System Demo")
    print("=" * 60)
    
    # Initialize dataloader
    loader = OptionsMLDataLoader()
    
    try:
        # 1. Check what data we have
        print("\n1. Checking downloaded data...")
        df = loader.load_ohlc_data('2024-06-03', '2024-06-07')
        print(f"   - Records in database: {len(df):,}")
        print(f"   - Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        print(f"   - Unique contracts: {df[['strike', 'option_type', 'expiration']].drop_duplicates().shape[0]}")
        
        # 2. Show sample data
        print("\n2. Sample OHLC data:")
        sample = df[df['volume'] > 0].head(5)
        print(sample[['strike', 'option_type', 'datetime', 'open', 'high', 'low', 'close', 'volume']].to_string())
        
        # 3. Get SPY price estimates
        print("\n3. SPY price estimates from options:")
        spy_prices = loader.get_spy_prices('2024-06-03', '2024-06-07')
        print(spy_prices.head())
        
        # 4. Show engineered features
        print("\n4. Feature engineering example:")
        df_features = loader.engineer_features(df.head(1000), spy_prices)
        feature_cols = ['moneyness', 'is_otm', 'dte', 'price_change_pct', 'volume_spike']
        print(df_features[feature_cols].describe())
        
        # 5. Get option chain snapshot
        print("\n5. Option chain snapshot (2024-06-03 10:00):")
        snapshot = loader.get_option_chain_snapshot('2024-06-03 10:00:00')
        if not snapshot.empty:
            pivot = snapshot.pivot_table(
                values='close',
                index='strike',
                columns='option_type',
                aggfunc='first'
            )
            print(pivot.head(10))
        
        print("\n" + "=" * 60)
        print("System Status:")
        print("- Database: ✓ Connected and operational")
        print("- OHLC Data: ✓ Available (Value subscription)")
        print("- Feature Engineering: ✓ Working")
        print("- ML Ready: ✓ Data prepared for training")
        print("\nGreeks/IV: ✗ Available July 18+ (Standard subscription)")
        print("=" * 60)
        
    finally:
        loader.close()


if __name__ == "__main__":
    demo()