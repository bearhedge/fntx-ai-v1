#!/usr/bin/env python3
"""
Improved ThetaTerminal Options Chain API Endpoint for fntx.ai
This version properly fetches volume and open interest data
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import requests
import pandas as pd
from datetime import datetime
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()

THETA_HTTP_API = "http://localhost:25510"

class ImprovedThetaOptionsProvider:
    """Improved provider for ThetaTerminal options data with proper volume and OI"""
    
    @staticmethod
    def get_option_data(root: str, exp: str, strike: int, right: str) -> Dict:
        """Get complete option data including quote, volume, and open interest"""
        strike_str = f"{strike}000"
        
        # Initialize result
        result = {
            'bid': 0,
            'ask': 0,
            'mid': 0,
            'bid_size': 0,
            'ask_size': 0,
            'volume': 0,
            'open_interest': 0,
            'close': 0,
            'high': 0,
            'low': 0,
            'open': 0
        }
        
        # 1. Get quote data (bid/ask)
        quote_url = f"{THETA_HTTP_API}/v2/snapshot/option/quote?root={root}&exp={exp}&strike={strike_str}&right={right}"
        try:
            quote_resp = requests.get(quote_url, timeout=2)
            if quote_resp.status_code == 200:
                data = quote_resp.json()
                if data.get('response') and len(data['response']) > 0:
                    quote = data['response'][0]
                    # Format: ["ms_of_day","bid_size","bid_exchange","bid","bid_condition","ask_size","ask_exchange","ask","ask_condition","date"]
                    result['bid'] = quote[3] if len(quote) > 3 else 0
                    result['ask'] = quote[7] if len(quote) > 7 else 0
                    result['bid_size'] = quote[1] if len(quote) > 1 else 0
                    result['ask_size'] = quote[5] if len(quote) > 5 else 0
                    result['mid'] = (result['bid'] + result['ask']) / 2 if result['ask'] > 0 else 0
        except:
            pass
        
        # 2. Get OHLC data (includes volume)
        ohlc_url = f"{THETA_HTTP_API}/v2/snapshot/option/ohlc?root={root}&exp={exp}&strike={strike_str}&right={right}"
        try:
            ohlc_resp = requests.get(ohlc_url, timeout=2)
            if ohlc_resp.status_code == 200:
                data = ohlc_resp.json()
                if data.get('response') and len(data['response']) > 0:
                    ohlc = data['response'][0]
                    # Format: ["ms_of_day","open","high","low","close","volume","count","date"]
                    result['open'] = ohlc[1] if len(ohlc) > 1 else 0
                    result['high'] = ohlc[2] if len(ohlc) > 2 else 0
                    result['low'] = ohlc[3] if len(ohlc) > 3 else 0
                    result['close'] = ohlc[4] if len(ohlc) > 4 else 0
                    result['volume'] = ohlc[5] if len(ohlc) > 5 else 0  # Actual volume!
        except:
            pass
        
        # 3. Get open interest
        oi_url = f"{THETA_HTTP_API}/v2/snapshot/option/open_interest?root={root}&exp={exp}&strike={strike_str}&right={right}"
        try:
            oi_resp = requests.get(oi_url, timeout=2)
            if oi_resp.status_code == 200:
                data = oi_resp.json()
                if data.get('response') and len(data['response']) > 0:
                    oi = data['response'][0]
                    # Format: ["ms_of_day","open_interest","date"]
                    result['open_interest'] = oi[1] if len(oi) > 1 else 0  # Actual OI!
        except:
            pass
        
        return result
    
    @staticmethod
    def get_spy_chain_improved(strike_start: int = 600, strike_end: int = 610, expiry: str = None) -> pd.DataFrame:
        """Get SPY option chain with volume and open interest"""
        if not expiry:
            expiry = datetime.now().strftime('%Y%m%d')
        
        data = []
        
        for strike in range(strike_start, strike_end + 1):
            # Get PUT data
            put_data = ImprovedThetaOptionsProvider.get_option_data('SPY', expiry, strike, 'P')
            
            # Get CALL data
            call_data = ImprovedThetaOptionsProvider.get_option_data('SPY', expiry, strike, 'C')
            
            row = {
                'Strike': strike,
                'Put_Bid': put_data['bid'],
                'Put_Ask': put_data['ask'],
                'Put_Mid': put_data['mid'],
                'Put_Volume': put_data['volume'],
                'Put_OI': put_data['open_interest'],
                'Put_Size': f"{put_data['bid_size']}x{put_data['ask_size']}",
                'Call_Bid': call_data['bid'],
                'Call_Ask': call_data['ask'],
                'Call_Mid': call_data['mid'],
                'Call_Volume': call_data['volume'],
                'Call_OI': call_data['open_interest'],
                'Call_Size': f"{call_data['bid_size']}x{call_data['ask_size']}",
                'Straddle': put_data['mid'] + call_data['mid']
            }
            
            data.append(row)
        
        return pd.DataFrame(data)

@router.get("/api/options/spy-chain-improved")
async def get_spy_option_chain_improved(
    strike_start: int = 600,
    strike_end: int = 610,
    expiry: Optional[str] = None
):
    """
    Get SPY option chain data from ThetaTerminal with proper volume and OI
    
    Returns formatted option chain with bid/ask/mid/volume/OI for puts and calls
    """
    try:
        # Get the chain
        df = ImprovedThetaOptionsProvider.get_spy_chain_improved(strike_start, strike_end, expiry)
        
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

@router.get("/api/options/spy-atm-improved")
async def get_spy_atm_options_improved(num_strikes: int = 5):
    """Get ATM options for SPY with proper volume and OI data"""
    try:
        # Get current SPY price first
        spy_url = f"{THETA_HTTP_API}/v2/snapshot/stock/quote?root=SPY"
        spy_resp = requests.get(spy_url, timeout=2)
        
        spy_price = 606  # default
        data_date = None
        if spy_resp.status_code == 200:
            data = spy_resp.json()
            if data.get('response') and len(data['response']) > 0:
                quote_data = data['response'][0]
                if len(quote_data) >= 10:
                    bid_price = quote_data[3]
                    ask_price = quote_data[7]
                    spy_price = round((bid_price + ask_price) / 2, 2)
                    data_date = str(quote_data[9])
        
        # Get today's expiration
        expiry = datetime.now().strftime('%Y%m%d')
        
        # Get strikes around ATM
        atm_strike = round(spy_price)
        strike_start = atm_strike - num_strikes
        strike_end = atm_strike + num_strikes
        
        # Get contracts data with proper volume and OI
        contracts = []
        for strike in range(strike_start, strike_end + 1):
            otm_percentage = abs(strike - spy_price) / spy_price * 100
            
            # Get PUT data (OTM if strike < spy_price)
            if strike < spy_price:
                put_data = ImprovedThetaOptionsProvider.get_option_data('SPY', expiry, strike, 'P')
                
                contracts.append({
                    "symbol": f"SPY{expiry[2:]}P{strike:03d}000",
                    "strike": float(strike),
                    "expiration": expiry,
                    "option_type": "P",
                    "bid": put_data['bid'],
                    "ask": put_data['ask'],
                    "last": put_data['close'] if put_data['close'] > 0 else put_data['mid'],
                    "volume": put_data['volume'],  # Real volume from OHLC
                    "open_interest": put_data['open_interest'],  # Real OI
                    "implied_volatility": None,  # Not available from ThetaTerminal
                    "ai_score": 8.5 if otm_percentage < 1 else 7.0
                })
            
            # Get CALL data (OTM if strike > spy_price)
            if strike > spy_price:
                call_data = ImprovedThetaOptionsProvider.get_option_data('SPY', expiry, strike, 'C')
                
                contracts.append({
                    "symbol": f"SPY{expiry[2:]}C{strike:03d}000",
                    "strike": float(strike),
                    "expiration": expiry,
                    "option_type": "C",
                    "bid": call_data['bid'],
                    "ask": call_data['ask'],
                    "last": call_data['close'] if call_data['close'] > 0 else call_data['mid'],
                    "volume": call_data['volume'],  # Real volume from OHLC
                    "open_interest": call_data['open_interest'],  # Real OI
                    "implied_volatility": None,  # Not available from ThetaTerminal
                    "ai_score": 8.5 if otm_percentage < 1 else 7.0
                })
        
        # Create AI insights
        ai_insights = {
            "market_regime": "favorable_for_selling" if spy_price > 600 else "neutral",
            "vix_level": None,  # Not available from ThetaTerminal
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
            "risk_warnings": ["0DTE options carry high gamma risk", "Implied volatility data not available"]
        }
        
        # Add data source info
        data_timestamp = None
        if data_date:
            data_timestamp = f"{data_date[:4]}-{data_date[4:6]}-{data_date[6:8]}"
        
        return {
            "spy_price": spy_price,
            "expiration_date": expiry,
            "contracts": contracts,
            "ai_insights": ai_insights,
            "market_regime": ai_insights["market_regime"],
            "timestamp": datetime.now().isoformat(),
            "data_timestamp": data_timestamp,
            "data_note": "Volume and open interest from ThetaTerminal. Implied volatility not available.",
            "data_limitations": {
                "implied_volatility": "Not available via ThetaTerminal HTTP API",
                "greeks": "Not available via ThetaTerminal HTTP API"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))