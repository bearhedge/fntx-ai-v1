#!/usr/bin/env python3
"""
Test script to trigger model training and see real computations in FNTX Computer
"""

import requests
import time
import json

def test_model_training():
    """Test the model training endpoint"""
    print("Testing SPY 0DTE Model Training Pipeline...")
    
    # API endpoint
    url = "http://localhost:8002/api/ml/train-models"
    
    try:
        # Trigger model training
        print("\n🤖 Triggering model training pipeline...")
        response = requests.post(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Pipeline started successfully!")
            print(f"   Status: {result['status']}")
            print(f"   Message: {result['message']}")
            print(f"   Timestamp: {result['timestamp']}")
            print("\n🖥️  Check the FNTX Computer display to see real-time computation steps!")
            print("   The model training will show:")
            print("   - Data preparation steps")
            print("   - Individual model training (LSTM, GRU, CNN, Attention)")
            print("   - Training epochs with loss and accuracy")
            print("   - Ensemble model creation")
            print("   - Backtesting results with daily P&L")
            
            # Keep script running to observe WebSocket updates
            print("\n⏳ Monitoring training progress (press Ctrl+C to exit)...")
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
    test_model_training()