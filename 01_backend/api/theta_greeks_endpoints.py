#!/usr/bin/env python3
"""
ThetaTerminal Greeks endpoints for Standard subscription
(Available after July 18th billing cycle)
"""
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

THETA_HTTP_API = "http://localhost:25510"

class ThetaGreeksProvider:
    """Provider for ThetaTerminal Greeks data (requires Standard subscription)"""
    
    @staticmethod
    def get_bulk_greeks(root: str = "SPY", exp: Optional[str] = None) -> pd.DataFrame:
        """
        Get Greeks for all options of a symbol
        This will work after July 18th with Standard subscription
        """
        # Bulk snapshot endpoint for Greeks
        url = f"{THETA_HTTP_API}/v2/bulk_snapshot/option/greeks"
        params = {"root": root}
        if exp:
            params["exp"] = exp
            
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                # Expected format: [contract_id, ms_of_day, delta, gamma, theta, vega, rho, phi, date]
                df = pd.DataFrame(
                    data['response'],
                    columns=['contract_id', 'ms_of_day', 'delta', 'gamma', 'theta', 'vega', 'rho', 'phi', 'date']
                )
                return df
            elif resp.status_code == 471:
                print("ERROR: OPTION.STANDARD subscription required (activates July 18)")
                return pd.DataFrame()
            else:
                print(f"Error {resp.status_code}: {resp.text}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching Greeks: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_bulk_iv(root: str = "SPY", exp: Optional[str] = None) -> pd.DataFrame:
        """
        Get implied volatility for all options of a symbol
        This will work after July 18th with Standard subscription
        """
        # Bulk snapshot endpoint for IV
        url = f"{THETA_HTTP_API}/v2/bulk_snapshot/option/implied_volatility"
        params = {"root": root}
        if exp:
            params["exp"] = exp
            
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                # Expected format: [contract_id, ms_of_day, implied_volatility, date]
                df = pd.DataFrame(
                    data['response'],
                    columns=['contract_id', 'ms_of_day', 'implied_volatility', 'date']
                )
                return df
            elif resp.status_code == 471:
                print("ERROR: OPTION.STANDARD subscription required (activates July 18)")
                return pd.DataFrame()
            else:
                print(f"Error {resp.status_code}: {resp.text}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching IV: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_historical_greeks(root: str, exp: str, strike: int, right: str, 
                            start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get historical Greeks data
        This will work after July 18th with Standard subscription
        """
        # Historical Greeks endpoint
        url = f"{THETA_HTTP_API}/v2/hist/option/greeks"
        params = {
            "root": root,
            "exp": exp,
            "strike": strike * 1000,  # Strike in thousandths
            "right": right,
            "start_date": start_date,
            "end_date": end_date
        }
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                df = pd.DataFrame(data['response'])
                return df
            elif resp.status_code == 471:
                print("ERROR: OPTION.STANDARD subscription required (activates July 18)")
                return pd.DataFrame()
            else:
                print(f"Error {resp.status_code}: {resp.text}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching historical Greeks: {e}")
            return pd.DataFrame()

def test_greeks_access():
    """Test if Greeks access is available (after July 18)"""
    print("Testing ThetaTerminal Greeks Access")
    print("=" * 50)
    
    provider = ThetaGreeksProvider()
    
    # Test 1: Bulk Greeks
    print("\n1. Testing Bulk Greeks for SPY:")
    greeks_df = provider.get_bulk_greeks("SPY", "20250718")
    if not greeks_df.empty:
        print(f"SUCCESS! Got {len(greeks_df)} contracts with Greeks")
        print(greeks_df.head())
    else:
        print("No Greeks data available (subscription not active until July 18)")
    
    # Test 2: Bulk IV
    print("\n2. Testing Bulk Implied Volatility for SPY:")
    iv_df = provider.get_bulk_iv("SPY", "20250718")
    if not iv_df.empty:
        print(f"SUCCESS! Got {len(iv_df)} contracts with IV")
        print(iv_df.head())
    else:
        print("No IV data available (subscription not active until July 18)")
    
    # Test 3: Historical Greeks
    print("\n3. Testing Historical Greeks:")
    hist_greeks = provider.get_historical_greeks(
        "SPY", "20250718", 606, "C", "20250601", "20250630"
    )
    if not hist_greeks.empty:
        print(f"SUCCESS! Got {len(hist_greeks)} historical Greek records")
    else:
        print("No historical Greeks available (subscription not active until July 18)")
    
    print("\n" + "=" * 50)
    print("SUMMARY: Your Standard subscription will activate on July 18.")
    print("After that date, you'll have access to:")
    print("- Real-time Greeks (delta, gamma, theta, vega, rho)")
    print("- Real-time implied volatility")
    print("- Historical Greeks data")
    print("- Historical implied volatility")

if __name__ == "__main__":
    test_greeks_access()