#!/usr/bin/env python3
"""
Check IBKR API status and server time
"""

import requests
import json

def check_api_status():
    """Check if IBKR API is accessible"""
    print("Checking IBKR API Status")
    print("="*60)
    
    # Check OAuth endpoint
    try:
        response = requests.get(
            "https://api.ibkr.com/v1/api/oauth",
            timeout=10
        )
        print(f"OAuth Base URL: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error accessing OAuth endpoint: {e}")
    
    # Check if we can get any response
    try:
        response = requests.post(
            "https://api.ibkr.com/v1/api/oauth/request_token",
            headers={"Authorization": "OAuth oauth_consumer_key=\"TEST\""},
            timeout=10
        )
        print(f"\nRequest Token Test: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Check server time (if available)
    try:
        response = requests.get(
            "https://api.ibkr.com/v1/api/time",
            timeout=10
        )
        print(f"\nServer Time Check: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api_status()