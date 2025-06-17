#!/usr/bin/env python3
"""
SPY Straddle Endpoint Extension
Adds straddle-specific endpoint to main API
"""

from fastapi import APIRouter
from typing import List, Dict, Any
import logging

logger = logging.getLogger('StraddleAPI')

# This would be added to main.py
def create_straddle_endpoint(app, ibkr_service):
    """Add straddle endpoint to the main API"""
    
    @app.get("/api/spy-options/straddles")
    async def get_spy_straddles(num_strikes: int = 10):
        """Get SPY options formatted as straddles around ATM"""
        try:
            # Get current SPY price
            spy_data = ibkr_service.get_spy_price()
            spy_price = spy_data.get('price', 0)
            
            if spy_price == 0:
                return {"error": "Unable to get SPY price"}
            
            # Get options chain with enough strikes
            options_list = ibkr_service.get_spy_options_chain(max_strikes=num_strikes * 4)
            
            if not options_list:
                return {"error": "Unable to get options data"}
            
            # Group by strike
            strikes = {}
            for opt in options_list:
                strike = opt['strike']
                if strike not in strikes:
                    strikes[strike] = {
                        'strike': strike,
                        'distance': abs(strike - spy_price)
                    }
                
                if opt['right'] == 'P':
                    strikes[strike]['put'] = opt
                else:
                    strikes[strike]['call'] = opt
            
            # Get closest strikes to ATM
            sorted_strikes = sorted(strikes.values(), key=lambda x: x['distance'])[:num_strikes]
            sorted_strikes = sorted(sorted_strikes, key=lambda x: x['strike'])
            
            # Find ATM strike
            atm_strike = min(strikes.values(), key=lambda x: x['distance'])
            
            # Calculate straddle values for ATM
            straddle_info = {}
            if 'put' in atm_strike and 'call' in atm_strike:
                put_mid = (atm_strike['put']['bid'] + atm_strike['put']['ask']) / 2
                call_mid = (atm_strike['call']['bid'] + atm_strike['call']['ask']) / 2
                straddle_price = put_mid + call_mid
                
                straddle_info = {
                    'atm_strike': atm_strike['strike'],
                    'put_mid': put_mid,
                    'call_mid': call_mid,
                    'straddle_price': straddle_price,
                    'lower_breakeven': atm_strike['strike'] - straddle_price,
                    'upper_breakeven': atm_strike['strike'] + straddle_price,
                    'max_profit_range': straddle_price * 2
                }
            
            # Calculate market sentiment
            total_put_vol = sum(s.get('put', {}).get('volume', 0) for s in sorted_strikes)
            total_call_vol = sum(s.get('call', {}).get('volume', 0) for s in sorted_strikes)
            
            pc_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0
            
            sentiment = "neutral"
            if pc_ratio > 1.2:
                sentiment = "bearish"
            elif pc_ratio < 0.8:
                sentiment = "bullish"
            
            return {
                'spy_price': spy_price,
                'timestamp': spy_data.get('timestamp'),
                'expiration': options_list[0]['expiration'] if options_list else None,
                'straddles': sorted_strikes,
                'atm_analysis': straddle_info,
                'market_sentiment': {
                    'put_volume': total_put_vol,
                    'call_volume': total_call_vol,
                    'put_call_ratio': pc_ratio,
                    'sentiment': sentiment
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting straddles: {e}")
            return {"error": str(e)}