#!/usr/bin/env python3
"""
Test Greeks endpoints with current market data
"""
import requests
import json
from datetime import datetime

THETA_HTTP_API = "http://localhost:25510"

def test_endpoint(url, description):
    """Test an endpoint and display the result"""
    print(f"\nTesting: {description}")
    print(f"URL: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        # Try to parse as JSON
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            return response.status_code, data
        except:
            print(f"Response: {response.text[:200]}")
            return response.status_code, response.text
    except Exception as e:
        print(f"Error: {str(e)}")
        return None, None

def main():
    # Use current/near date options
    root = "SPY"
    exp = "20250627"  # This Friday
    strike = "605000"  # $605 (closer to current SPY price)
    right = "C"
    
    print("=" * 80)
    print("GREEKS & IV ENDPOINT TEST - CURRENT OPTIONS")
    print("=" * 80)
    print(f"Testing with: {root} {exp} {int(strike)/1000:.0f} {right}")
    
    # First, verify this option exists
    print("\n=== VERIFY OPTION EXISTS ===")
    quote_url = f"{THETA_HTTP_API}/v2/snapshot/option/quote?root={root}&exp={exp}&strike={strike}&right={right}"
    status, data = test_endpoint(quote_url, "Option Quote (to verify option exists)")
    
    # Test Greeks endpoints
    print("\n=== GREEKS ENDPOINTS ===")
    
    # Status code 471 means "OPTION.STANDARD or higher is required"
    # Status code 472 means "Unable to retrieve snapshot" (option doesn't exist)
    # Status code 473 means "Not supported yet"
    
    greeks_tests = [
        # Snapshot Greeks
        (f"{THETA_HTTP_API}/v2/snapshot/option/greeks?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Snapshot Greeks - specific contract"),
        
        # Bulk Greeks (requires just root)
        (f"{THETA_HTTP_API}/v2/bulk_snapshot/option/greeks?root={root}", 
         "Bulk Snapshot Greeks - all SPY"),
        
        (f"{THETA_HTTP_API}/v2/bulk_snapshot/option/greeks?root={root}&exp={exp}", 
         "Bulk Snapshot Greeks - specific expiration"),
        
        # IV endpoints
        (f"{THETA_HTTP_API}/v2/snapshot/option/implied_volatility?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Snapshot IV - specific contract"),
        
        (f"{THETA_HTTP_API}/v2/bulk_snapshot/option/implied_volatility?root={root}", 
         "Bulk Snapshot IV - all SPY"),
    ]
    
    status_471_count = 0
    status_473_count = 0
    
    for url, desc in greeks_tests:
        status, response = test_endpoint(url, desc)
        if status == 471:
            status_471_count += 1
        elif status == 473:
            status_473_count += 1
    
    # Also test with a definitely existing option (SPY ATM)
    print("\n=== TEST WITH ATM OPTION ===")
    atm_strike = "606000"  # $606 (very close to current price)
    
    atm_tests = [
        (f"{THETA_HTTP_API}/v2/snapshot/option/greeks?root={root}&exp={exp}&strike={atm_strike}&right={right}", 
         "Greeks for ATM option"),
        (f"{THETA_HTTP_API}/v2/snapshot/option/implied_volatility?root={root}&exp={exp}&strike={atm_strike}&right={right}", 
         "IV for ATM option"),
    ]
    
    for url, desc in atm_tests:
        status, response = test_endpoint(url, desc)
    
    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS OF RESULTS")
    print("=" * 80)
    
    print(f"\nStatus Code Summary:")
    print(f"- 471 responses (OPTION.STANDARD required): {status_471_count}")
    print(f"- 473 responses (Not supported yet): {status_473_count}")
    
    print("\n" + "=" * 80)
    print("SUBSCRIPTION STATUS")
    print("=" * 80)
    
    if status_471_count > 0:
        print("\n✓ GOOD NEWS: The Greeks/IV endpoints exist and are recognized!")
        print("✗ BAD NEWS: Your Standard subscription is NOT active yet")
        print("\nThe status code 471 specifically means:")
        print("  'OPTION.STANDARD or higher is required to access this request'")
        print("\nThis confirms:")
        print("  1. The endpoints DO exist in ThetaTerminal")
        print("  2. They require Standard subscription (which you have)")
        print("  3. Your subscription is not active until July 18th billing cycle")
        print("\nOnce July 18th arrives, these endpoints should start working!")
    else:
        print("\n✗ No clear indication of subscription status")
        print("  The endpoints may not be properly configured")

if __name__ == "__main__":
    main()