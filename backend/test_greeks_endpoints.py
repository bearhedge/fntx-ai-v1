#!/usr/bin/env python3
"""
Comprehensive test script to check all possible Greeks and IV endpoints
to determine if Standard subscription is active
"""
import requests
import json
from datetime import datetime, timedelta

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
            print(f"Response: {json.dumps(data, indent=2)[:500]}...")  # Show first 500 chars
            return True, data
        except:
            print(f"Response: {response.text[:200]}")
            return False, response.text
    except Exception as e:
        print(f"Error: {str(e)}")
        return False, None

def main():
    # Test parameters
    root = "SPY"
    exp = "20250717"  # July 17, 2025
    strike = "600000"  # $600
    right = "C"
    
    # Dates for historical testing
    from_date = "20250624"
    to_date = "20250625"
    
    print("=" * 80)
    print("COMPREHENSIVE GREEKS & IV ENDPOINT TEST")
    print("=" * 80)
    print(f"Testing with: {root} {exp} {int(strike)/1000:.0f} {right}")
    print(f"Date range: {from_date} to {to_date}")
    
    # 1. Test snapshot endpoints
    print("\n\n=== SNAPSHOT ENDPOINTS ===")
    
    endpoints = [
        # Standard Greeks endpoints
        (f"{THETA_HTTP_API}/v2/snapshot/option/greeks?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Standard Greeks Snapshot"),
        
        # IV endpoints
        (f"{THETA_HTTP_API}/v2/snapshot/option/iv?root={root}&exp={exp}&strike={strike}&right={right}", 
         "IV Snapshot (short form)"),
        (f"{THETA_HTTP_API}/v2/snapshot/option/implied_volatility?root={root}&exp={exp}&strike={strike}&right={right}", 
         "IV Snapshot (full form)"),
        
        # Alternative formats
        (f"{THETA_HTTP_API}/v2/snapshot/option/greek?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Greek Snapshot (singular)"),
        (f"{THETA_HTTP_API}/v2/snapshot/option/vol?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Vol Snapshot"),
        (f"{THETA_HTTP_API}/v2/snapshot/option/volatility?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Volatility Snapshot"),
    ]
    
    # 2. Test historical endpoints
    print("\n\n=== HISTORICAL ENDPOINTS ===")
    
    hist_endpoints = [
        # Historical Greeks
        (f"{THETA_HTTP_API}/v2/hist/option/greeks?root={root}&exp={exp}&strike={strike}&right={right}&from={from_date}&to={to_date}", 
         "Historical Greeks"),
        
        # Historical IV
        (f"{THETA_HTTP_API}/v2/hist/option/iv?root={root}&exp={exp}&strike={strike}&right={right}&from={from_date}&to={to_date}", 
         "Historical IV (short)"),
        (f"{THETA_HTTP_API}/v2/hist/option/implied_volatility?root={root}&exp={exp}&strike={strike}&right={right}&from={from_date}&to={to_date}", 
         "Historical IV (full)"),
        
        # Alternative formats
        (f"{THETA_HTTP_API}/v2/hist/option/greek?root={root}&exp={exp}&strike={strike}&right={right}&from={from_date}&to={to_date}", 
         "Historical Greek (singular)"),
    ]
    
    endpoints.extend(hist_endpoints)
    
    # 3. Test bulk endpoints
    print("\n\n=== BULK ENDPOINTS ===")
    
    bulk_endpoints = [
        # Bulk snapshot
        (f"{THETA_HTTP_API}/v2/bulk_snapshot/option/greeks?root={root}", 
         "Bulk Greeks Snapshot"),
        (f"{THETA_HTTP_API}/v2/bulk_snapshot/option/iv?root={root}", 
         "Bulk IV Snapshot"),
        (f"{THETA_HTTP_API}/v2/bulk_snapshot/option/implied_volatility?root={root}", 
         "Bulk IV Snapshot (full)"),
        
        # Bulk with exp
        (f"{THETA_HTTP_API}/v2/bulk_snapshot/option/greeks?root={root}&exp={exp}", 
         "Bulk Greeks with Expiration"),
    ]
    
    endpoints.extend(bulk_endpoints)
    
    # 4. Test list endpoints
    print("\n\n=== LIST/DOCUMENTATION ENDPOINTS ===")
    
    doc_endpoints = [
        (f"{THETA_HTTP_API}/v2/list", "List all endpoints"),
        (f"{THETA_HTTP_API}/v2/list/option", "List option endpoints"),
        (f"{THETA_HTTP_API}/v2/list/option/snapshot", "List option snapshot endpoints"),
        (f"{THETA_HTTP_API}/v2/list/option/hist", "List option historical endpoints"),
        (f"{THETA_HTTP_API}/v2/docs", "Documentation"),
        (f"{THETA_HTTP_API}/v2/help", "Help"),
    ]
    
    endpoints.extend(doc_endpoints)
    
    # Run all tests
    successful_endpoints = []
    for url, desc in endpoints:
        success, data = test_endpoint(url, desc)
        if success:
            successful_endpoints.append((url, desc, data))
    
    # 5. Test known working endpoints for comparison
    print("\n\n=== KNOWN WORKING ENDPOINTS (for comparison) ===")
    
    working = [
        (f"{THETA_HTTP_API}/v2/snapshot/option/quote?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Option Quote (known working)"),
        (f"{THETA_HTTP_API}/v2/snapshot/option/ohlc?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Option OHLC (known working)"),
        (f"{THETA_HTTP_API}/v2/snapshot/option/open_interest?root={root}&exp={exp}&strike={strike}&right={right}", 
         "Option OI (known working)"),
    ]
    
    for url, desc in working:
        test_endpoint(url, desc)
    
    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY OF RESULTS")
    print("=" * 80)
    
    if successful_endpoints:
        print(f"\n✓ Found {len(successful_endpoints)} successful endpoints:")
        for url, desc, data in successful_endpoints:
            print(f"  - {desc}")
            if isinstance(data, dict) and 'header' in data:
                print(f"    Format: {data.get('header', {}).get('format', 'Unknown')}")
    else:
        print("\n✗ No Greeks or IV endpoints returned successful responses")
    
    print("\n" + "=" * 80)
    print("SUBSCRIPTION STATUS ANALYSIS")
    print("=" * 80)
    
    # Check if any Greeks/IV endpoints worked
    greeks_found = any("greek" in url.lower() for url, _, _ in successful_endpoints)
    iv_found = any("iv" in url.lower() or "volat" in url.lower() for url, _, _ in successful_endpoints)
    
    if greeks_found or iv_found:
        print("✓ Standard subscription appears to be ACTIVE")
        print("  - Greeks endpoints available" if greeks_found else "  - No Greeks endpoints found")
        print("  - IV endpoints available" if iv_found else "  - No IV endpoints found")
    else:
        print("✗ Standard subscription does NOT appear to be active yet")
        print("  - No Greeks or IV endpoints returned data")
        print("  - Billing cycle starts July 18th, so this is expected")
        print("  - Only Value-tier endpoints (quote, ohlc, open_interest) are working")

if __name__ == "__main__":
    main()