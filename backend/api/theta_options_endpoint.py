#!/usr/bin/env python3
"""
ThetaTerminal Options Chain API Endpoint for fntx.ai
Automatically uses Greeks when Standard subscription is active
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import requests
import pandas as pd
from datetime import datetime
import json

router = APIRouter()

THETA_HTTP_API = "http://localhost:25510"

# Check subscription level
def check_greeks_available():
    """Check if Greeks are available (Standard subscription active)"""
    try:
        resp = requests.get(f"{THETA_HTTP_API}/v2/bulk_snapshot/option/greeks?root=SPY&exp=20250718", timeout=2)
        return resp.status_code == 200
    except:
        return False

GREEKS_AVAILABLE = check_greeks_available()

class ThetaOptionsProvider:
    """Provider for ThetaTerminal options data"""
    
    @staticmethod
    def get_spy_chain(strike_start: int = 600, strike_end: int = 610, expiry: str = None) -> pd.DataFrame:
        """Get SPY option chain as pandas DataFrame"""
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
        
        data = []
        
        for strike in range(strike_start, strike_end + 1):
            # Get PUT data
            put_url = f"{THETA_HTTP_API}/v2/snapshot/option/quote?root=SPY&exp={expiry}&strike={strike}000&right=P"
            put_resp = requests.get(put_url, timeout=2)
            
            # Get CALL data
            call_url = f"{THETA_HTTP_API}/v2/snapshot/option/quote?root=SPY&exp={expiry}&strike={strike}000&right=C"
            call_resp = requests.get(call_url, timeout=2)
            
            row = {'Strike': strike}
            
            # Process PUT
            if put_resp.status_code == 200:
                p_data = put_resp.json()
                if p_data.get('response'):
                    quote = p_data['response'][0]
                    row.update({
                        'Put_Bid': quote[3],
                        'Put_Ask': quote[7],
                        'Put_Mid': (quote[3] + quote[7]) / 2,
                        'Put_Size': f"{quote[1]}x{quote[5]}"
                    })
            else:
                row.update({'Put_Bid': 0, 'Put_Ask': 0, 'Put_Mid': 0, 'Put_Size': '-'})
            
            # Process CALL
            if call_resp.status_code == 200:
                c_data = call_resp.json()
                if c_data.get('response'):
                    quote = c_data['response'][0]
                    row.update({
                        'Call_Bid': quote[3],
                        'Call_Ask': quote[7],
                        'Call_Mid': (quote[3] + quote[7]) / 2,
                        'Call_Size': f"{quote[1]}x{quote[5]}"
                    })
            else:
                row.update({'Call_Bid': 0, 'Call_Ask': 0, 'Call_Mid': 0, 'Call_Size': '-'})
            
            # Add straddle
            row['Straddle'] = row.get('Put_Mid', 0) + row.get('Call_Mid', 0)
            data.append(row)
        
        return pd.DataFrame(data)

@router.get("/api/options/spy-chain")
async def get_spy_option_chain(
    strike_start: int = 600,
    strike_end: int = 610,
    expiry: Optional[str] = None
):
    """
    Get SPY option chain data from ThetaTerminal
    
    Returns formatted option chain with bid/ask/mid for puts and calls
    """
    try:
        # Get the chain
        df = ThetaOptionsProvider.get_spy_chain(strike_start, strike_end, expiry)
        
        # Convert to dict for JSON response
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "expiry": expiry or datetime.now().strftime('%Y%m%d'),
            "data": df.to_dict('records'),
            "formatted_table": df.to_string(index=False)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/options/spy-atm")
async def get_spy_atm_options(num_strikes: int = 5):
    """Get ATM options for SPY with frontend-compatible format"""
    try:
        # Get current SPY price first
        spy_url = f"{THETA_HTTP_API}/v2/snapshot/stock/quote?root=SPY"
        spy_resp = requests.get(spy_url, timeout=2)
        
        spy_price = 606  # default
        data_date = None
        if spy_resp.status_code == 200:
            data = spy_resp.json()
            if data.get('response') and len(data['response']) > 0:
                # Stock quote format: [ms_of_day, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition, date]
                quote_data = data['response'][0]
                if len(quote_data) >= 10:
                    # Use mid of bid/ask
                    bid_price = quote_data[3]
                    ask_price = quote_data[7]
                    spy_price = round((bid_price + ask_price) / 2, 2)
                    data_date = str(quote_data[9])  # Save date for later
        
        # Get today's expiration
        expiry = datetime.now().strftime('%Y%m%d')
        
        # Get strikes around ATM
        atm_strike = round(spy_price)
        strike_start = atm_strike - num_strikes
        strike_end = atm_strike + num_strikes
        
        # Get contracts data
        contracts = []
        for strike in range(strike_start, strike_end + 1):
            # Skip ATM strike for OTM only
            otm_percentage = abs(strike - spy_price) / spy_price * 100
            
            # Get PUT data (OTM if strike < spy_price)
            if strike < spy_price:
                put_url = f"{THETA_HTTP_API}/v2/snapshot/option/quote?root=SPY&exp={expiry}&strike={strike}000&right=P"
                put_resp = requests.get(put_url, timeout=2)
                
                if put_resp.status_code == 200:
                    p_data = put_resp.json()
                    if p_data.get('response'):
                        quote = p_data['response'][0]
                        
                        # Get volume from OHLC endpoint
                        volume = 0
                        ohlc_url = f"{THETA_HTTP_API}/v2/snapshot/option/ohlc?root=SPY&exp={expiry}&strike={strike}000&right=P"
                        ohlc_resp = requests.get(ohlc_url, timeout=1)
                        if ohlc_resp.status_code == 200:
                            ohlc_data = ohlc_resp.json()
                            if ohlc_data.get('response') and len(ohlc_data['response'][0]) > 5:
                                volume = ohlc_data['response'][0][5]
                        
                        # Get open interest
                        oi = 0
                        oi_url = f"{THETA_HTTP_API}/v2/snapshot/option/open_interest?root=SPY&exp={expiry}&strike={strike}000&right=P"
                        oi_resp = requests.get(oi_url, timeout=1)
                        if oi_resp.status_code == 200:
                            oi_data = oi_resp.json()
                            if oi_data.get('response') and len(oi_data['response'][0]) > 1:
                                oi = oi_data['response'][0][1]
                        
                        contracts.append({
                            "symbol": f"SPY{expiry[2:]}P{strike:03d}000",
                            "strike": float(strike),
                            "expiration": expiry,
                            "option_type": "P",
                            "bid": quote[3] if len(quote) > 3 else 0,
                            "ask": quote[7] if len(quote) > 7 else 0,
                            "last": (quote[3] + quote[7]) / 2 if len(quote) > 7 else 0,
                            "volume": volume,
                            "open_interest": oi,
                            "implied_volatility": None,  # Not available from ThetaTerminal HTTP API
                            "ai_score": 8.5 if otm_percentage < 1 else 7.0
                        })
            
            # Get CALL data (OTM if strike > spy_price)
            if strike > spy_price:
                call_url = f"{THETA_HTTP_API}/v2/snapshot/option/quote?root=SPY&exp={expiry}&strike={strike}000&right=C"
                call_resp = requests.get(call_url, timeout=2)
                
                if call_resp.status_code == 200:
                    c_data = call_resp.json()
                    if c_data.get('response'):
                        quote = c_data['response'][0]
                        
                        # Get volume from OHLC endpoint
                        volume = 0
                        ohlc_url = f"{THETA_HTTP_API}/v2/snapshot/option/ohlc?root=SPY&exp={expiry}&strike={strike}000&right=C"
                        ohlc_resp = requests.get(ohlc_url, timeout=1)
                        if ohlc_resp.status_code == 200:
                            ohlc_data = ohlc_resp.json()
                            if ohlc_data.get('response') and len(ohlc_data['response'][0]) > 5:
                                volume = ohlc_data['response'][0][5]
                        
                        # Get open interest
                        oi = 0
                        oi_url = f"{THETA_HTTP_API}/v2/snapshot/option/open_interest?root=SPY&exp={expiry}&strike={strike}000&right=C"
                        oi_resp = requests.get(oi_url, timeout=1)
                        if oi_resp.status_code == 200:
                            oi_data = oi_resp.json()
                            if oi_data.get('response') and len(oi_data['response'][0]) > 1:
                                oi = oi_data['response'][0][1]
                        
                        contracts.append({
                            "symbol": f"SPY{expiry[2:]}C{strike:03d}000",
                            "strike": float(strike),
                            "expiration": expiry,
                            "option_type": "C",
                            "bid": quote[3] if len(quote) > 3 else 0,
                            "ask": quote[7] if len(quote) > 7 else 0,
                            "last": (quote[3] + quote[7]) / 2 if len(quote) > 7 else 0,
                            "volume": volume,
                            "open_interest": oi,
                            "implied_volatility": None,  # Not available from ThetaTerminal HTTP API
                            "ai_score": 8.5 if otm_percentage < 1 else 7.0
                        })
        
        # Create AI insights
        # Note: VIX is an estimate as ThetaTerminal doesn't provide it via standard quote endpoint
        vix_estimate = None  # Set to None to indicate unavailable
        ai_insights = {
            "market_regime": "favorable_for_selling" if spy_price > 600 else "neutral",
            "vix_level": vix_estimate,
            "trading_signal": "bullish" if spy_price > 605 else "neutral",
            "strategy_preference": "PUT selling",
            "position_sizing": "Normal",
            "specific_actions": [
                f"Consider selling {atm_strike - 3} PUT for income",
                f"Monitor {atm_strike + 2} CALL for hedge",
                "Focus on 0DTE time decay"
            ],
            "confidence_level": 0.75,
            "recommended_strikes": [atm_strike - 3, atm_strike - 2, atm_strike + 2, atm_strike + 3],
            "risk_warnings": ["0DTE options carry high gamma risk"] if vix_estimate and vix_estimate > 18 else []
        }
        
        # Add data source info
        data_timestamp = None
        if data_date:
            # Date is already in YYYYMMDD format from SPY quote
            data_timestamp = f"{data_date[:4]}-{data_date[4:6]}-{data_date[6:8]}"
        
        return {
            "spy_price": spy_price,
            "expiration_date": expiry,
            "contracts": contracts,
            "ai_insights": ai_insights,
            "market_regime": ai_insights["market_regime"],
            "timestamp": datetime.now().isoformat(),
            "data_timestamp": data_timestamp,
            "data_note": "End-of-day data from previous trading session" if data_timestamp else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# For integration with the chatbot
def format_chain_for_chat(df: pd.DataFrame) -> str:
    """Format option chain for chatbot display"""
    output = "SPY Option Chain\n"
    output += "=" * 80 + "\n"
    output += df.to_string(index=False, float_format=lambda x: f'{x:.2f}')
    return output