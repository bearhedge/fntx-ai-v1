"""
SPY 0DTE Feature Engineering Engine
Performs advanced feature extraction for SPY options trading
Sends real-time computation updates to FNTX Computer display
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import asyncio
import json
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import psycopg2
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class ComputationStep:
    """Represents a computation step to display in FNTX Computer"""
    type: str
    message: str
    data: Optional[Dict] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")

class SPY0DTEFeatureEngine:
    """Advanced feature engineering for SPY 0DTE options trading"""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
        self.db_config = {
            'host': 'localhost',
            'database': 'theta_data',
            'user': 'postgres',
            'password': 'theta_data_2024'
        }
        self.computation_steps = []
        
    async def _broadcast_computation(self, step: ComputationStep):
        """Send computation step to FNTX Computer display"""
        self.computation_steps.append(step)
        
        if self.websocket_manager:
            await self.websocket_manager.broadcast({
                "type": step.type,
                "message": step.message,
                "data": step.data,
                "timestamp": step.timestamp
            })
        
        logger.info(f"Computation: {step.message}")
    
    def _connect_db(self):
        """Connect to PostgreSQL database"""
        return psycopg2.connect(**self.db_config)
    
    async def extract_features(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Extract advanced features from SPY options data"""
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="> Feature Extraction Pipeline Started"
        ))
        
        # Step 1: Load raw data
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="Loading SPY options data from database...",
            data={"start_date": start_date, "end_date": end_date}
        ))
        
        df = await self._load_options_data(start_date, end_date)
        
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message=f"Loaded {len(df):,} records spanning {df['datetime'].nunique()} time periods"
        ))
        
        # Step 2: Basic features
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="Computing basic features: moneyness, time decay, volume ratios..."
        ))
        
        df = await self._compute_basic_features(df)
        
        # Step 3: Microstructure features
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="Analyzing market microstructure: bid-ask spreads, price momentum..."
        ))
        
        df = await self._compute_microstructure_features(df)
        
        # Step 4: Volume profile analysis
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="Building volume profiles by strike and time..."
        ))
        
        df = await self._compute_volume_profiles(df)
        
        # Step 5: Statistical arbitrage features
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="Detecting statistical arbitrage opportunities..."
        ))
        
        df = await self._compute_stat_arb_features(df)
        
        # Step 6: Regime detection
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="Identifying market regimes: trending, mean-reverting, volatile..."
        ))
        
        df = await self._detect_market_regimes(df)
        
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message=f"> Feature extraction complete: {df.shape[1]} features generated"
        ))
        
        return df
    
    async def _load_options_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Load options data from PostgreSQL"""
        query = """
        SELECT 
            o.datetime,
            o.open,
            o.high,
            o.low,
            o.close,
            o.volume,
            o.trade_count,
            c.strike,
            c.expiration,
            c.option_type,
            s.close as spy_price
        FROM theta.options_ohlc o
        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
        LEFT JOIN theta.spy_prices s ON DATE(o.datetime) = s.date
        WHERE c.symbol = 'SPY'
        AND o.datetime BETWEEN %s AND %s
        AND o.volume > 0
        ORDER BY o.datetime, c.strike
        """
        
        with self._connect_db() as conn:
            df = pd.read_sql(query, conn, params=(start_date, end_date))
            
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['expiration'] = pd.to_datetime(df['expiration'])
        
        return df
    
    async def _compute_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute basic trading features"""
        # Moneyness
        df['moneyness'] = df['spy_price'] / df['strike']
        df['log_moneyness'] = np.log(df['moneyness'])
        
        # OTM/ITM flags
        df['is_otm'] = ((df['option_type'] == 'P') & (df['strike'] < df['spy_price'])) | \
                       ((df['option_type'] == 'C') & (df['strike'] > df['spy_price']))
        df['otm_distance'] = np.abs(df['spy_price'] - df['strike']) / df['spy_price']
        
        # Time to expiration
        df['dte'] = (df['expiration'] - df['datetime']).dt.total_seconds() / 86400
        df['is_0dte'] = df['dte'] < 1
        
        # Price features
        df['price_range'] = df['high'] - df['low']
        df['price_volatility'] = df['price_range'] / df['close'].clip(lower=0.01)
        
        # Volume features
        df['volume_per_trade'] = df['volume'] / df['trade_count'].clip(lower=1)
        df['log_volume'] = np.log1p(df['volume'])
        
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message=f"  ✓ Basic features computed: {df['is_0dte'].sum():,} 0DTE contracts identified"
        ))
        
        return df
    
    async def _compute_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute market microstructure features"""
        # Approximate bid-ask spread
        df['approx_spread'] = 2 * (df['high'] - df['low']) / (df['high'] + df['low']).clip(lower=0.01)
        
        # Price momentum
        df['price_momentum_5m'] = df.groupby(['strike', 'option_type'])['close'].pct_change(5)
        df['price_momentum_15m'] = df.groupby(['strike', 'option_type'])['close'].pct_change(15)
        
        # Volume momentum
        df['volume_momentum'] = df.groupby(['strike', 'option_type'])['volume'].pct_change(5)
        
        # Trade intensity
        df['trade_intensity'] = df['trade_count'] / df.groupby('datetime')['trade_count'].transform('sum')
        
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="  ✓ Microstructure features computed"
        ))
        
        return df
    
    async def _compute_volume_profiles(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute volume profile features"""
        # Volume profile by strike
        volume_by_strike = df.groupby(['datetime', 'strike'])['volume'].sum().reset_index()
        volume_by_strike['volume_rank'] = volume_by_strike.groupby('datetime')['volume'].rank(pct=True)
        
        df = df.merge(
            volume_by_strike[['datetime', 'strike', 'volume_rank']], 
            on=['datetime', 'strike'], 
            how='left'
        )
        
        # High volume node detection
        df['is_high_volume_strike'] = df['volume_rank'] > 0.8
        
        # Put/Call volume ratio
        pc_volume = df.groupby(['datetime', 'strike', 'option_type'])['volume'].sum().unstack(fill_value=0)
        pc_volume['pc_ratio'] = pc_volume.get('P', 0) / pc_volume.get('C', 1).clip(lower=1)
        
        df = df.merge(
            pc_volume['pc_ratio'].reset_index(),
            on=['datetime', 'strike'],
            how='left'
        )
        
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="  ✓ Volume profiles analyzed"
        ))
        
        return df
    
    async def _compute_stat_arb_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute statistical arbitrage features"""
        # Put-Call parity deviation
        calls = df[df['option_type'] == 'C'][['datetime', 'strike', 'close', 'spy_price']]
        puts = df[df['option_type'] == 'P'][['datetime', 'strike', 'close']]
        
        parity = calls.merge(
            puts, 
            on=['datetime', 'strike'], 
            suffixes=('_call', '_put')
        )
        
        # Theoretical put-call parity (simplified without interest rate)
        parity['theoretical_diff'] = parity['close_call'] - parity['close_put'] - (parity['spy_price'] - parity['strike'])
        parity['parity_deviation'] = parity['theoretical_diff'] / parity['spy_price']
        
        df = df.merge(
            parity[['datetime', 'strike', 'parity_deviation']], 
            on=['datetime', 'strike'], 
            how='left'
        )
        
        # Volatility smile features
        df['smile_moneyness'] = df.groupby(['datetime', 'option_type'])['moneyness'].transform(
            lambda x: (x - 1).abs()
        )
        
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message="  ✓ Statistical arbitrage features computed"
        ))
        
        return df
    
    async def _detect_market_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect market regimes using statistical methods"""
        # Calculate SPY returns
        spy_returns = df.groupby('datetime')['spy_price'].first().pct_change()
        
        # Rolling volatility (20 periods ~ 20 minutes)
        rolling_vol = spy_returns.rolling(20).std() * np.sqrt(252 * 390)  # Annualized
        
        # Regime classification
        regimes = pd.DataFrame(index=spy_returns.index)
        regimes['volatility'] = rolling_vol
        regimes['regime'] = 'normal'
        
        # High volatility regime
        regimes.loc[regimes['volatility'] > regimes['volatility'].quantile(0.8), 'regime'] = 'high_vol'
        
        # Low volatility regime  
        regimes.loc[regimes['volatility'] < regimes['volatility'].quantile(0.2), 'regime'] = 'low_vol'
        
        # Trend detection using returns
        regimes['trend'] = spy_returns.rolling(10).mean()
        regimes.loc[regimes['trend'] > 0.001, 'regime'] = regimes['regime'] + '_bullish'
        regimes.loc[regimes['trend'] < -0.001, 'regime'] = regimes['regime'] + '_bearish'
        
        df = df.merge(
            regimes[['regime', 'volatility']], 
            left_on='datetime', 
            right_index=True, 
            how='left'
        )
        
        await self._broadcast_computation(ComputationStep(
            type="computation_step",
            message=f"  ✓ Market regimes detected: {df['regime'].value_counts().to_dict()}"
        ))
        
        return df
    
    async def compute_real_time_features(self, current_data: Dict) -> Dict:
        """Compute features for real-time trading decisions"""
        await self._broadcast_computation(ComputationStep(
            type="market_analysis",
            message="Analyzing current market conditions",
            data={
                "spy_price": current_data.get('spy_price', 0),
                "market_state": "Pre-market" if datetime.now().hour < 9.5 else "Market hours",
                "volatility": "Calculating..."
            }
        ))
        
        features = {
            'moneyness': current_data['spy_price'] / current_data['strike'],
            'otm_distance': abs(current_data['spy_price'] - current_data['strike']) / current_data['spy_price'],
            'time_to_close': max(0, (16 - datetime.now().hour - datetime.now().minute/60)),
            'is_high_volume': current_data.get('volume', 0) > 1000,
            'spread_ratio': (current_data.get('ask', 0) - current_data.get('bid', 0)) / current_data.get('mid', 1)
        }
        
        await self._broadcast_computation(ComputationStep(
            type="strike_selection", 
            message="Evaluating strike selection",
            data={
                "range": f"${current_data['strike']-5} - ${current_data['strike']+5}",
                "volume_status": "High volume" if features['is_high_volume'] else "Normal volume",
                "selected_strike": f"${current_data['strike']} {'PUT' if current_data['option_type'] == 'P' else 'CALL'}"
            }
        ))
        
        return features