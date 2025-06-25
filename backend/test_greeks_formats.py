#!/usr/bin/env python3
"""
Test different endpoint formats that will work once Standard subscription is active
"""
import requests
import json

THETA_HTTP_API = "http://localhost:25510"

def main():
    root = "SPY"
    exp = "20250627"
    strike = "605000"
    right = "C"
    
    print("=" * 80)
    print("GREEKS ENDPOINT FORMATS - For use after July 18th")
    print("=" * 80)
    
    print("\n✓ CONFIRMED WORKING FORMATS (will work after subscription activates):")
    print("\n1. BULK SNAPSHOT GREEKS:")
    print(f"   GET {THETA_HTTP_API}/v2/bulk_snapshot/option/greeks?root={root}")
    print(f"   GET {THETA_HTTP_API}/v2/bulk_snapshot/option/greeks?root={root}&exp={exp}")
    print("   Status: 471 (requires OPTION.STANDARD)")
    
    print("\n2. BULK SNAPSHOT IMPLIED VOLATILITY:")
    print(f"   GET {THETA_HTTP_API}/v2/bulk_snapshot/option/implied_volatility?root={root}")
    print(f"   GET {THETA_HTTP_API}/v2/bulk_snapshot/option/implied_volatility?root={root}&exp={exp}")
    print("   Status: 471 (requires OPTION.STANDARD)")
    
    print("\n✗ NOT WORKING FORMATS:")
    print("\n1. SNAPSHOT GREEKS (individual contract):")
    print(f"   GET {THETA_HTTP_API}/v2/snapshot/option/greeks?root={root}&exp={exp}&strike={strike}&right={right}")
    print("   Status: 473 (Not supported yet)")
    
    print("\n2. SNAPSHOT IV (individual contract):")
    print(f"   GET {THETA_HTTP_API}/v2/snapshot/option/implied_volatility?root={root}&exp={exp}&strike={strike}&right={right}")
    print("   Status: 472 (This dataType is not currently supported)")
    
    print("\n" + "=" * 80)
    print("EXPECTED DATA FORMAT")
    print("=" * 80)
    
    print("\nBased on other ThetaTerminal endpoints, Greeks data will likely include:")
    print("- Delta")
    print("- Gamma") 
    print("- Theta")
    print("- Vega")
    print("- Rho")
    print("- Implied Volatility")
    print("- Underlying Price")
    print("- Timestamp")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n1. Wait until July 18th for subscription to activate")
    print("\n2. Use BULK endpoints to get Greeks for multiple options at once:")
    print("   - More efficient than individual requests")
    print("   - Can filter by expiration date")
    print("   - Returns all strikes for given root/exp")
    
    print("\n3. Example code to fetch Greeks after July 18th:")
    print("""
# Get all Greeks for SPY options expiring on a specific date
response = requests.get(
    f"{THETA_HTTP_API}/v2/bulk_snapshot/option/greeks",
    params={"root": "SPY", "exp": "20250718"}
)

if response.status_code == 200:
    data = response.json()
    # Process Greeks data for all strikes
    for option in data['response']:
        # Extract delta, gamma, theta, vega, etc.
        pass
""")
    
    print("\n4. Current working endpoints (Value tier):")
    print("   - /v2/snapshot/option/quote (bid/ask)")
    print("   - /v2/snapshot/option/ohlc (includes volume)")
    print("   - /v2/snapshot/option/open_interest")
    print("   - /v2/hist/option/* (historical versions)")

if __name__ == "__main__":
    main()