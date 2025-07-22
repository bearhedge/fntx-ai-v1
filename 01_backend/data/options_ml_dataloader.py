#!/usr/bin/env python3
"""
ML DataLoader for Options Data
Provides efficient data loading and feature engineering for ML models
"""
import os
import sys
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.theta_config import DB_CONFIG


class OptionsMLDataLoader:
    """Load and prepare options data for ML training"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.scaler = StandardScaler()
    
    def load_ohlc_data(self, 
                      start_date: str, 
                      end_date: str,
                      min_volume: int = 0) -> pd.DataFrame:
        """Load OHLC data for date range"""
        query = """
        SELECT 
            c.symbol,
            c.expiration,
            c.strike,
            c.option_type,
            o.datetime,
            o.open,
            o.high,
            o.low,
            o.close,
            o.volume,
            o.trade_count
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        WHERE o.datetime >= %s AND o.datetime <= %s
        AND o.volume >= %s
        ORDER BY o.datetime, c.strike, c.option_type
        """
        
        df = pd.read_sql(query, self.conn, params=(start_date, end_date, min_volume))
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['expiration'] = pd.to_datetime(df['expiration'])
        return df
    
    def engineer_features(self, df: pd.DataFrame, spy_prices: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for ML training"""
        # Merge with SPY prices
        df = df.merge(spy_prices[['datetime', 'spy_price']], on='datetime', how='left')
        df['spy_price'].fillna(method='ffill', inplace=True)
        
        # Moneyness features
        df['moneyness'] = df['spy_price'] / df['strike']
        df['log_moneyness'] = np.log(df['moneyness'])
        df['is_otm'] = ((df['option_type'] == 'P') & (df['strike'] < df['spy_price'])) | \
                       ((df['option_type'] == 'C') & (df['strike'] > df['spy_price']))
        
        # Time features
        df['dte'] = (df['expiration'].dt.date - df['datetime'].dt.date).apply(lambda x: x.days)
        df['time_to_close'] = (16 - df['datetime'].dt.hour) - (df['datetime'].dt.minute / 60)
        df['day_of_week'] = df['datetime'].dt.dayofweek
        df['is_friday'] = (df['day_of_week'] == 4).astype(int)
        
        # Price features
        df['price_range'] = df['high'] - df['low']
        df['price_change'] = df['close'] - df['open']
        df['price_change_pct'] = df['price_change'] / (df['open'] + 0.0001)
        
        # Volume features
        df['volume_ma_5'] = df.groupby(['strike', 'option_type'])['volume'].transform(
            lambda x: x.rolling(5, min_periods=1).mean()
        )
        df['volume_spike'] = df['volume'] / (df['volume_ma_5'] + 1)
        
        # Volatility proxy (using price range)
        df['realized_vol'] = df.groupby(['strike', 'option_type'])['price_change_pct'].transform(
            lambda x: x.rolling(20, min_periods=1).std()
        )
        
        # Technical indicators
        df['rsi'] = df.groupby(['strike', 'option_type'])['close'].transform(
            lambda x: self._calculate_rsi(x, 14)
        )
        
        # Target variables for different ML tasks
        df['next_price'] = df.groupby(['strike', 'option_type'])['close'].shift(-1)
        df['next_return'] = (df['next_price'] - df['close']) / (df['close'] + 0.0001)
        df['expires_worthless'] = ((df['dte'] == 0) & (df['is_otm'] == 1)).astype(int)
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def get_spy_prices(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get SPY underlying prices"""
        # For now, estimate from ATM options since we don't have stock data
        query = """
        SELECT 
            o.datetime,
            c.strike,
            AVG(o.close) as option_price
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        WHERE c.symbol = 'SPY'
        AND o.datetime >= %s AND o.datetime <= %s
        AND c.option_type = 'C'
        AND c.strike BETWEEN 
            (SELECT AVG(strike) - 5 FROM theta.options_contracts WHERE symbol = 'SPY')
            AND 
            (SELECT AVG(strike) + 5 FROM theta.options_contracts WHERE symbol = 'SPY')
        GROUP BY o.datetime, c.strike
        """
        
        df = pd.read_sql(query, self.conn, params=(start_date, end_date))
        
        # Estimate SPY price from ATM options
        spy_prices = df.groupby('datetime').apply(
            lambda x: x.loc[x['option_price'].idxmax(), 'strike']
        ).reset_index()
        spy_prices.columns = ['datetime', 'spy_price']
        
        return spy_prices
    
    def prepare_training_data(self, 
                            start_date: str, 
                            end_date: str,
                            target: str = 'next_return',
                            feature_cols: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare data for ML training"""
        # Load data
        df = self.load_ohlc_data(start_date, end_date)
        spy_prices = self.get_spy_prices(start_date, end_date)
        
        # Engineer features
        df = self.engineer_features(df, spy_prices)
        
        # Default features if not specified
        if feature_cols is None:
            feature_cols = [
                'moneyness', 'log_moneyness', 'is_otm', 'dte', 'time_to_close',
                'day_of_week', 'price_range', 'price_change_pct', 'volume_spike',
                'realized_vol', 'rsi'
            ]
        
        # Remove NaN values
        df = df.dropna(subset=feature_cols + [target])
        
        # Prepare features and target
        X = df[feature_cols]
        y = df[target]
        
        # Scale features
        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X),
            columns=X.columns,
            index=X.index
        )
        
        return X_scaled, y
    
    def get_option_chain_snapshot(self, datetime_str: str, dte_max: int = 7) -> pd.DataFrame:
        """Get option chain snapshot at specific datetime"""
        query = """
        SELECT 
            c.strike,
            c.option_type,
            c.expiration,
            o.open,
            o.high,
            o.low,
            o.close,
            o.volume
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        WHERE c.symbol = 'SPY'
        AND o.datetime = %s
        AND c.expiration - DATE(%s) <= %s
        ORDER BY c.expiration, c.strike, c.option_type
        """
        
        datetime_obj = pd.to_datetime(datetime_str)
        df = pd.read_sql(query, self.conn, params=(datetime_str, datetime_obj.date(), dte_max))
        
        return df
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Example usage
if __name__ == "__main__":
    loader = OptionsMLDataLoader()
    
    # Load some test data
    print("Loading test data...")
    df = loader.load_ohlc_data('2024-06-03', '2024-06-07')
    print(f"Loaded {len(df)} records")
    
    # Get SPY prices
    spy_prices = loader.get_spy_prices('2024-06-03', '2024-06-07')
    print(f"\nSPY price estimates:")
    print(spy_prices.head())
    
    # Engineer features
    df_features = loader.engineer_features(df, spy_prices)
    print(f"\nEngineered features:")
    print(df_features.columns.tolist())
    
    # Prepare training data
    X, y = loader.prepare_training_data('2024-06-03', '2024-06-07')
    print(f"\nTraining data shape: X={X.shape}, y={y.shape}")
    
    loader.close()