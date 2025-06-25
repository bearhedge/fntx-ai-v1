#!/usr/bin/env python3
"""
Test script to trigger feature engineering and see real computations in FNTX Computer
"""

import requests
import time
import json

def test_feature_engineering():
    """Test the feature engineering endpoint"""
    print("Testing SPY 0DTE Feature Engineering Pipeline...")
    
    # API endpoint
    url = "http://localhost:8002/api/ml/feature-engineering"
    
    try:
        # Trigger feature engineering
        print("\n📊 Triggering feature engineering pipeline...")
        response = requests.post(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Pipeline started successfully!")
            print(f"   Status: {result['status']}")
            print(f"   Message: {result['message']}")
            print(f"   Timestamp: {result['timestamp']}")
            print("\n🖥️  Check the FNTX Computer display to see real-time computation steps!")
            print("   The feature extraction will process SPY options data and show:")
            print("   - Data loading progress")
            print("   - Feature computation steps")
            print("   - Market regime detection")
            print("   - Volume profile analysis")
            print("   - Statistical arbitrage features")
            
            # Keep script running to observe WebSocket updates
            print("\n⏳ Monitoring computation progress (press Ctrl+C to exit)...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n✅ Test completed!")
                
        else:
            print(f"❌ Failed to start pipeline: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server!")
        print("   Make sure the backend is running: cd backend && python -m uvicorn api.main:app --reload --port 8002")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_feature_engineering()