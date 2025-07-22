#!/usr/bin/env python3
"""Simplified dashboard runner without AI dependencies"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from data_pipeline.streaming_theta_connector import LocalThetaConnector
from terminal_ui import TradingDashboard

# Patch imports to avoid missing modules
sys.modules['stable_baselines3'] = None

# Mock classes
class MockModel:
    def predict(self, obs, deterministic=True):
        import numpy as np
        # Simple logic - always hold for now
        return 0, np.array([1.0, 0.0, 0.0])

class MockFeatureEngine:
    def extract_features(self, market_data, position=None):
        import numpy as np
        # Return dummy features
        features = np.zeros(60)
        feature_dict = {
            'time_to_close': 0.5,
            'rsi': 50.0,
            'iv_rank': 0.5,
            'vix': market_data.get('vix', 18.5),
            'spy_price': market_data.get('spy_price_realtime', market_data.get('spy_price', 0))
        }
        return features, feature_dict

class MockSuggestionEngine:
    def get_suggestion(self, *args, **kwargs):
        return None, "Monitoring market conditions..."

async def main():
    """Run simplified dashboard"""
    print("=" * 60)
    print("SPY 0DTE Options Live Streaming Dashboard")
    print("=" * 60)
    
    # Initialize components
    print("Initializing components...")
    
    # Data connector with streaming
    data_connector = LocalThetaConnector()
    await data_connector.start()
    print("✓ Streaming data connector started")
    
    # Mock components
    model = MockModel()
    feature_engine = MockFeatureEngine()
    suggestion_engine = MockSuggestionEngine()
    
    # Create dashboard
    dashboard = TradingDashboard(update_frequency=1.0)
    print("✓ Dashboard created")
    
    # Wait for initial data
    print("\nWaiting for market data...")
    await asyncio.sleep(3)
    
    # Check data
    test_data = data_connector.get_current_snapshot()
    print(f"✓ SPY (Theta): ${test_data.get('spy_price', 0):.2f}")
    print(f"✓ SPY (Yahoo): ${test_data.get('spy_price_realtime', 0):.2f}")
    print(f"✓ Options chain: {len(test_data.get('options_chain', []))} contracts")
    
    print("\n" + "=" * 60)
    print("Dashboard Ready! Press Ctrl+C to exit")
    print("=" * 60 + "\n")
    
    # Run dashboard
    try:
        await dashboard.run(
            data_connector,
            feature_engine,
            model,
            suggestion_engine
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await data_connector.stop()

if __name__ == "__main__":
    asyncio.run(main())