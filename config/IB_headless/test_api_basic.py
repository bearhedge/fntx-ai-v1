#!/usr/bin/env python3
"""
Test basic API connectivity and search for ARM options
"""

import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.IB_headless.ib_rest_auth_consolidated import IBRestAuth

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api():
    """Test API connectivity and ARM search"""
    
    # Initialize auth
    auth = IBRestAuth(
        consumer_key='BEARHEDGE',
        realm='limited_poa'
    )
    
    print("\n" + "="*60)
    print("TESTING IBKR API CONNECTIVITY")
    print("="*60)
    
    # Test 1: Check accounts
    print("\n1. Testing /portfolio/accounts...")
    response = auth.make_authenticated_request('GET', '/portfolio/accounts')
    if response:
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.text[:500]}")
        else:
            print(f"Error: {response.text}")
    else:
        print("No response")
    
    # Test 2: Try different search endpoints
    print("\n2. Testing contract search endpoints...")
    
    # Try /trsrv/secdef/search (different endpoint)
    print("\n2a. Trying /trsrv/secdef/search...")
    response = auth.make_authenticated_request(
        'GET',
        '/trsrv/secdef/search',
        params={'symbol': 'ARM'}
    )
    
    if response:
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found: {json.dumps(data, indent=2)[:1000]}")
        else:
            print(f"Error: {response.text}")
    else:
        print("No response")
    
    # Try /iserver/secdef/search
    print("\n2b. Trying /iserver/secdef/search...")
    response = auth.make_authenticated_request(
        'GET',
        '/iserver/secdef/search',
        params={'symbol': 'ARM', 'name': 'false'}
    )
    
    if response:
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found: {json.dumps(data, indent=2)[:1000]}")
        else:
            print(f"Error: {response.text}")
    else:
        print("No response")
    
    # Test 3: Try searching for SPY first (known to work)
    print("\n3. Testing with SPY (control test)...")
    response = auth.make_authenticated_request(
        'GET',
        '/trsrv/secdef/search',
        params={'symbol': 'SPY'}
    )
    
    if response:
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SPY found: {json.dumps(data, indent=2)[:500]}...")
        else:
            print(f"Error: {response.text}")
    else:
        print("No response")

if __name__ == "__main__":
    test_api()