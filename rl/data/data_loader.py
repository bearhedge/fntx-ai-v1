"""
Options Data Loader for TimescaleDB
Loads 5-minute bar data for SPY 0DTE options
"""
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class OptionsDataLoader:
    """Loads and manages options data from TimescaleDB"""
    
    def __init__(self, db_config: dict):
        """Initialize data loader with database configuration"""
        self.db_config = db_config
        self.conn = None
        self.trading_days = []
        self._connect()
        self._load_trading_days()
        
    def _connect(self):
        """Establish database connection"""
        try:
            # Create connection params, excluding password if empty
            conn_params = self.db_config.copy()
            if not conn_params.get('password'):
                conn_params.pop('password', None)
            
            # Debug print
            logger.info(f"Connecting with params: {conn_params}")
            
            self.conn = psycopg2.connect(**conn_params)
            logger.info("Connected to TimescaleDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    def _load_trading_days(self):
        """Load all available trading days from backend.data.database"""
        query = """
        SELECT DISTINCT expiration::date as trading_date
        FROM theta.options_contracts
        WHERE symbol = 'SPY'
        ORDER BY trading_date
        """
        
        df = pd.read_sql(query, self.conn)
        self.trading_days = df['trading_date'].tolist()
        logger.info(f"Loaded {len(self.trading_days)} trading days")
        
    def get_episode_data(self, date: datetime.date) -> Dict:
        """
        Load all data for a single trading day (episode)
        
        Returns:
            Dictionary with structured data for the environment
        """
        # Main query to get all options data for the day
        query = """
        SELECT 
            o.datetime,
            o.open, o.high, o.low, o.close, o.volume,
            g.delta, g.gamma, g.theta as greeks_theta, g.vega, g.rho,
            iv.implied_volatility,
            c.strike, c.option_type, c.contract_id
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id  
        LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        LEFT JOIN theta.options_iv iv ON o.contract_id = iv.contract_id 
            AND o.datetime = iv.datetime
        WHERE c.expiration = %s
            AND c.symbol = 'SPY'
        ORDER BY o.datetime, c.strike, c.option_type
        """
        
        df = pd.read_sql(query, self.conn, params=[date])
        
        if df.empty:
            logger.warning(f"No data found for {date}")
            return None
            
        # Add bid-ask spread estimates
        df = self._add_bid_ask_spreads(df)
        
        # Get SPY spot price (approximate from ATM options)
        spot_prices = self._calculate_spot_prices(df)
        
        # Structure data for fast lookup during episode
        return {
            'date': date,
            'dataframe': df,
            'by_time': dict(list(df.groupby('datetime'))),
            'strikes': sorted(df['strike'].unique()),
            'spot_prices': spot_prices,
            'timestamps': sorted(df['datetime'].unique()),
            'contract_map': self._create_contract_map(df)
        }
        
    def _add_bid_ask_spreads(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate bid-ask spreads from OHLC data
        
        For 0DTE options, spreads are wider than multi-day options
        Uses closing price with adjustments for:
        - Moneyness (OTM options have wider spreads)
        - Implied volatility (higher IV = wider spreads)
        - Volume (lower volume = wider spreads)
        - Time of day (spreads narrow near close)
        """
        # Calculate spot prices first for moneyness calculation
        spot_prices = self._calculate_spot_prices(df.copy())
        
        # Initialize bid/ask columns
        df['bid'] = 0.0
        df['ask'] = 0.0
        
        for idx, row in df.iterrows():
            close_price = row['close']
            
            # Skip if no price
            if close_price <= 0 or pd.isna(close_price):
                continue
                
            # Get spot price for this timestamp
            spot = spot_prices.get(row['datetime'], 400.0)
            
            # Calculate moneyness
            if row['option_type'] == 'C':
                moneyness = row['strike'] / spot
            else:  # Put
                moneyness = spot / row['strike']
                
            # Base spread as percentage of close
            # 0DTE options typically have 2-10% spreads
            if close_price < 0.50:
                base_spread_pct = 0.10  # 10% for very cheap options
            elif close_price < 1.00:
                base_spread_pct = 0.06  # 6% for cheap options  
            elif close_price < 5.00:
                base_spread_pct = 0.04  # 4% for medium options
            else:
                base_spread_pct = 0.02  # 2% for expensive options
                
            # Moneyness adjustment (OTM has wider spreads)
            if moneyness > 1.02:  # OTM
                moneyness_mult = 1.0 + (moneyness - 1.0) * 2  # Wider as more OTM
            elif moneyness < 0.98:  # ITM
                moneyness_mult = 1.0 + (1.0 - moneyness) * 1.5
            else:  # ATM
                moneyness_mult = 0.8  # Tightest spreads at ATM
                
            # IV adjustment (if available)
            iv = row.get('implied_volatility', 0.2)
            if not pd.isna(iv) and iv > 0:
                # Higher IV means wider spreads
                iv_mult = 1.0 + (iv - 0.2) * 0.5  # 0.2 is baseline IV
            else:
                iv_mult = 1.0
                
            # Volume adjustment
            volume = row.get('volume', 0)
            if volume < 10:
                volume_mult = 1.5  # Very wide for illiquid
            elif volume < 100:
                volume_mult = 1.2
            elif volume < 1000:
                volume_mult = 1.0
            else:
                volume_mult = 0.9  # Tighter for liquid options
                
            # Time of day adjustment
            hour = row['datetime'].hour
            minute = row['datetime'].minute
            minutes_from_open = (hour - 9) * 60 + (minute - 30)
            
            if minutes_from_open < 30:
                time_mult = 1.3  # Wider at open
            elif minutes_from_open > 360:  # Last 30 minutes
                time_mult = 0.8  # Tighter near close
            else:
                time_mult = 1.0
                
            # Calculate final spread
            spread_pct = base_spread_pct * moneyness_mult * iv_mult * volume_mult * time_mult
            
            # Cap spread at reasonable levels
            spread_pct = min(spread_pct, 0.25)  # Max 25% spread
            spread_pct = max(spread_pct, 0.01)  # Min 1% spread
            
            # Calculate bid/ask
            half_spread = close_price * spread_pct / 2
            
            # For 0DTE, use close as slightly above mid (market makers edge)
            # This reflects that close is usually slightly bid-favored
            mid_price = close_price * 0.99  # Close is ~1% above true mid
            
            df.at[idx, 'bid'] = max(0.01, mid_price - half_spread)  # Min 1 cent
            df.at[idx, 'ask'] = mid_price + half_spread
            
        # Log spread statistics
        avg_spread_pct = ((df['ask'] - df['bid']) / df['close']).mean() * 100
        logger.info(f"Added bid-ask spreads. Average spread: {avg_spread_pct:.1f}%")
        
        return df
        
    def _calculate_spot_prices(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate approximate spot price from ATM options
        Using put-call parity when possible
        """
        spot_prices = {}
        
        for timestamp in df['datetime'].unique():
            time_data = df[df['datetime'] == timestamp]
            
            # Find ATM strike (closest to previous spot or use midpoint)
            if spot_prices:
                prev_spot = list(spot_prices.values())[-1]
                atm_strike = min(time_data['strike'].unique(), 
                               key=lambda x: abs(x - prev_spot))
            else:
                # Initial guess: middle of strike range
                atm_strike = time_data['strike'].median()
                
            # Get ATM call and put prices
            atm_call = time_data[(time_data['strike'] == atm_strike) & 
                                (time_data['option_type'] == 'C')]
            atm_put = time_data[(time_data['strike'] == atm_strike) & 
                               (time_data['option_type'] == 'P')]
            
            if not atm_call.empty and not atm_put.empty:
                # Use put-call parity: S = K + C - P
                # Using close prices as a proxy for mid prices
                call_price = atm_call['close'].iloc[0]
                put_price = atm_put['close'].iloc[0]
                spot = atm_strike + call_price - put_price
            else:
                # Fallback: use strike as approximation
                spot = atm_strike
                
            spot_prices[timestamp] = spot
            
        return pd.Series(spot_prices)
        
    def _create_contract_map(self, df: pd.DataFrame) -> Dict:
        """Create mapping of (strike, option_type) to contract_id"""
        contract_map = {}
        for _, row in df[['strike', 'option_type', 'contract_id']].drop_duplicates().iterrows():
            key = (row['strike'], row['option_type'])
            contract_map[key] = row['contract_id']
        return contract_map
        
    def get_contract_data(self, date: datetime.date, strike: float, 
                         option_type: str) -> pd.DataFrame:
        """Get data for a specific contract"""
        query = """
        SELECT 
            o.datetime,
            o.open, o.high, o.low, o.close, o.volume,
            g.delta, g.gamma, g.theta as greeks_theta, g.vega,
            iv.implied_volatility
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id  
        JOIN theta.options_greeks g ON o.contract_id = g.contract_id 
            AND o.datetime = g.datetime
        LEFT JOIN theta.options_iv iv ON o.contract_id = iv.contract_id 
            AND o.datetime = iv.datetime
        WHERE c.expiration = %s
            AND c.symbol = 'SPY'
            AND c.strike = %s
            AND c.option_type = %s
        ORDER BY o.datetime
        """
        
        return pd.read_sql(query, self.conn, params=[date, strike, option_type])
        
    def find_contracts_by_delta(self, time_data: pd.DataFrame, 
                               target_delta: float, option_type: str) -> List[Dict]:
        """
        Find contracts closest to target delta
        
        Returns list of contracts sorted by proximity to target delta
        """
        # Filter by option type
        options = time_data[time_data['option_type'] == option_type].copy()
        
        if options.empty:
            return []
            
        # Apply delta constraint: |delta| <= 0.20
        options = options[abs(options['delta']) <= 0.20]
        
        if options.empty:
            logger.warning(f"No {option_type} options found with |delta| <= 0.20")
            return []
            
        # Calculate distance from target delta
        options['delta_distance'] = abs(options['delta'] - target_delta)
        
        # Sort by distance and return top candidates
        options = options.sort_values('delta_distance')
        
        contracts = []
        for _, row in options.head(5).iterrows():  # Top 5 candidates
            contracts.append({
                'strike': row['strike'],
                'delta': row['delta'],
                'bid': row['bid'],
                'ask': row['ask'],
                'volume': row['volume'],
                'iv': row['implied_volatility'],
                'contract_id': row['contract_id']
            })
            
        return contracts
        
    def get_market_indicators(self, date: datetime.date) -> Dict:
        """Calculate market indicators for the day"""
        # This would integrate with your existing market data
        # For now, returning placeholder
        return {
            'vix': 20.0,  # Would query actual VIX
            'put_call_ratio': 1.0,  # Would calculate from volume
            'spy_sma_10': 400.0,  # Would calculate from price data
            'spy_sma_30': 398.0,
            'atr': 2.5,
            'atr_20d_avg': 2.0
        }
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")