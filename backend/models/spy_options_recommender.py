#!/usr/bin/env python3
"""
SPY Options Recommender
Analyzes historical patterns to recommend OTM options for selling
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.options_ml_dataloader import OptionsMLDataLoader


class SPYOptionsRecommender:
    """Recommend OTM SPY options for daily selling strategies"""
    
    def __init__(self):
        self.loader = OptionsMLDataLoader()
        self.analysis_cache = {}
    
    def analyze_historical_patterns(self, lookback_days: int = 90) -> Dict:
        """Analyze historical patterns for option selling"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Load historical data
        df = self.loader.load_ohlc_data(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if df.empty:
            return {}
        
        # Get SPY prices
        spy_prices = self.loader.get_spy_prices(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        # Engineer features
        df = self.loader.engineer_features(df, spy_prices)
        
        # Focus on OTM options only
        otm_df = df[df['is_otm'] == 1].copy()
        
        # Calculate win rate for different moneyness levels
        moneyness_buckets = [0.90, 0.92, 0.94, 0.96, 0.98, 1.00]
        win_rates = {}
        
        for i in range(len(moneyness_buckets) - 1):
            bucket_name = f"{moneyness_buckets[i]:.2f}-{moneyness_buckets[i+1]:.2f}"
            bucket_df = otm_df[
                (otm_df['moneyness'] >= moneyness_buckets[i]) & 
                (otm_df['moneyness'] < moneyness_buckets[i+1])
            ]
            
            if len(bucket_df) > 0:
                # An option "wins" if it expires OTM (seller keeps premium)
                win_rate = (bucket_df['expires_worthless'] == 1).mean()
                avg_premium = bucket_df['close'].mean()
                
                win_rates[bucket_name] = {
                    'win_rate': win_rate,
                    'avg_premium': avg_premium,
                    'sample_size': len(bucket_df)
                }
        
        # Analyze by DTE
        dte_analysis = {}
        for dte in [0, 1, 2, 3, 4, 5]:
            dte_df = otm_df[otm_df['dte'] == dte]
            if len(dte_df) > 0:
                dte_analysis[f"{dte}DTE"] = {
                    'avg_decay': dte_df['price_change_pct'].mean(),
                    'volatility': dte_df['price_change_pct'].std(),
                    'avg_volume': dte_df['volume'].mean()
                }
        
        # Best times to sell
        hourly_analysis = otm_df.groupby(otm_df['datetime'].dt.hour).agg({
            'close': 'mean',
            'volume': 'mean',
            'price_change_pct': 'mean'
        }).to_dict()
        
        return {
            'moneyness_win_rates': win_rates,
            'dte_analysis': dte_analysis,
            'hourly_patterns': hourly_analysis,
            'total_samples': len(otm_df)
        }
    
    def get_recommendations(self, 
                          current_spy_price: float,
                          target_dte: int = 0,
                          risk_level: str = 'conservative') -> List[Dict]:
        """Get specific option recommendations"""
        
        # Risk level determines how far OTM
        risk_params = {
            'conservative': {'put_delta': 0.95, 'call_delta': 1.05, 'min_premium': 0.20},
            'moderate': {'put_delta': 0.97, 'call_delta': 1.03, 'min_premium': 0.50},
            'aggressive': {'put_delta': 0.99, 'call_delta': 1.01, 'min_premium': 1.00}
        }
        
        params = risk_params.get(risk_level, risk_params['conservative'])
        
        recommendations = []
        
        # Recommend PUT strikes
        put_strike = int(current_spy_price * params['put_delta'])
        recommendations.append({
            'type': 'PUT',
            'strike': put_strike,
            'moneyness': put_strike / current_spy_price,
            'dte': target_dte,
            'risk_level': risk_level,
            'rationale': f"Selling {put_strike}P provides cushion of {(1-params['put_delta'])*100:.1f}%"
        })
        
        # Recommend CALL strikes
        call_strike = int(current_spy_price * params['call_delta'])
        recommendations.append({
            'type': 'CALL',
            'strike': call_strike,
            'moneyness': call_strike / current_spy_price,
            'dte': target_dte,
            'risk_level': risk_level,
            'rationale': f"Selling {call_strike}C captures upside above {(params['call_delta']-1)*100:.1f}%"
        })
        
        # Add historical context
        historical = self.analyze_historical_patterns()
        for rec in recommendations:
            moneyness = rec['moneyness']
            # Find closest bucket
            for bucket, stats in historical.get('moneyness_win_rates', {}).items():
                bucket_min, bucket_max = map(float, bucket.split('-'))
                if bucket_min <= moneyness < bucket_max:
                    rec['historical_win_rate'] = stats['win_rate']
                    rec['avg_premium'] = stats['avg_premium']
                    break
        
        return recommendations
    
    def backtest_strategy(self, 
                         strategy_params: Dict,
                         start_date: str,
                         end_date: str) -> pd.DataFrame:
        """Backtest a selling strategy"""
        # Load data
        df = self.loader.load_ohlc_data(start_date, end_date)
        spy_prices = self.loader.get_spy_prices(start_date, end_date)
        df = self.loader.engineer_features(df, spy_prices)
        
        # Simulate daily selling
        results = []
        
        for date in pd.date_range(start_date, end_date, freq='B'):  # Business days
            day_data = df[df['datetime'].dt.date == date.date()]
            
            if day_data.empty:
                continue
            
            # Get SPY price at open
            spy_open = day_data.iloc[0]['spy_price']
            
            # Get recommendations
            recs = self.get_recommendations(
                spy_open, 
                strategy_params.get('dte', 0),
                strategy_params.get('risk_level', 'conservative')
            )
            
            for rec in recs:
                # Find matching option
                option_data = day_data[
                    (day_data['strike'] == rec['strike']) & 
                    (day_data['option_type'] == rec['type'][0])
                ]
                
                if not option_data.empty:
                    # Simulate selling at 10 AM
                    entry_data = option_data[option_data['datetime'].dt.hour == 10]
                    if not entry_data.empty:
                        entry_price = entry_data.iloc[0]['close']
                        
                        # Check if expired ITM
                        final_price = option_data.iloc[-1]['close']
                        expired_otm = rec['moneyness'] < 1.0 if rec['type'] == 'PUT' else rec['moneyness'] > 1.0
                        
                        results.append({
                            'date': date,
                            'type': rec['type'],
                            'strike': rec['strike'],
                            'entry_price': entry_price,
                            'final_price': final_price,
                            'profit': entry_price if expired_otm else entry_price - final_price,
                            'win': expired_otm
                        })
        
        return pd.DataFrame(results)
    
    def close(self):
        """Clean up resources"""
        self.loader.close()


# Example usage
if __name__ == "__main__":
    recommender = SPYOptionsRecommender()
    
    try:
        # Analyze historical patterns
        print("Analyzing historical patterns...")
        patterns = recommender.analyze_historical_patterns(lookback_days=7)
        
        print("\nWin Rates by Moneyness:")
        for bucket, stats in patterns.get('moneyness_win_rates', {}).items():
            print(f"  {bucket}: {stats['win_rate']:.1%} win rate, "
                  f"${stats['avg_premium']:.2f} avg premium "
                  f"(n={stats['sample_size']})")
        
        # Get recommendations
        print("\nCurrent Recommendations (SPY at $520):")
        recs = recommender.get_recommendations(520, target_dte=0, risk_level='conservative')
        
        for rec in recs:
            print(f"\n{rec['type']} Recommendation:")
            print(f"  Strike: {rec['strike']}")
            print(f"  Rationale: {rec['rationale']}")
            if 'historical_win_rate' in rec:
                print(f"  Historical Win Rate: {rec['historical_win_rate']:.1%}")
        
        # Note about future enhancements
        print("\n" + "="*60)
        print("Note: When Standard subscription activates (July 18+):")
        print("- Greeks will be integrated for better strike selection")
        print("- IV analysis will improve premium estimates")
        print("- Delta-based recommendations will be more precise")
        print("="*60)
        
    finally:
        recommender.close()