#!/usr/bin/env python3
"""
Synchronized SPY Options Trading Terminal UI
Combines live streaming with 5-minute RL API integration
"""
import asyncio
import argparse
import sys
import httpx
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from data_pipeline import FeatureEngine, PositionTracker
from data_pipeline.data_aggregator import DataAggregator
from data_pipeline.rest_theta_connector import RESTThetaConnector
from data_pipeline.smart_suggestion_engine import SmartSuggestionEngine
from terminal_ui import TradingDashboard

class SynchronizedTradingSystem:
    """Orchestrates live streaming with 5-minute RL API calls"""
    
    def __init__(self, rl_api_url: str = "http://localhost:8100/predict"):
        self.rl_api_url = rl_api_url
        self.data_aggregator = DataAggregator(interval_minutes=5)
        self.last_rl_prediction = None
        self.rl_prediction_time = None
        self.rl_prediction_valid_until = None
        
        # Components
        self.data_connector = None
        self.feature_engine = None
        self.position_tracker = None
        self.suggestion_engine = None
        self.dashboard = None
        
        # State
        self.is_running = False
        self.stats = {
            'total_ticks': 0,
            'completed_bars': 0,
            'rl_calls': 0,
            'rl_errors': 0
        }
    
    async def initialize(self, args):
        """Initialize all components"""
        print("🔧 Initializing synchronized trading system...")
        
        # Initialize data connector
        self.data_connector = RESTThetaConnector()
        await self.data_connector.start()
        print("✓ Data connector started")
        
        # Initialize other components
        self.position_tracker = PositionTracker()
        self.feature_engine = FeatureEngine(self.position_tracker)
        self.suggestion_engine = SmartSuggestionEngine()
        self.dashboard = TradingDashboard(update_frequency=args.update_rate)
        
        print("✓ All components initialized")
        
        # Wait for initial data
        print("⏳ Waiting for initial market data...")
        await asyncio.sleep(2)
        
        test_data = self.data_connector.get_current_snapshot()
        if test_data['spy_price']:
            print(f"✓ Receiving data - SPY: ${test_data['spy_price']:.2f}")
        else:
            print("⚠️  No market data yet")
    
    async def run_main_loop(self):
        """Main orchestration loop"""
        print(f"\n{'='*60}")
        print("🚀 Starting synchronized trading system")
        print(f"{'='*60}")
        
        self.is_running = True
        
        # Create dashboard layout
        layout = self.dashboard.create_layout()
        
        # Start dashboard and main loop concurrently
        dashboard_task = asyncio.create_task(self.run_dashboard_display(layout))
        main_task = asyncio.create_task(self.run_data_loop(layout))
        
        try:
            # Run both tasks concurrently
            await asyncio.gather(dashboard_task, main_task)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down...")
            self.is_running = False
            dashboard_task.cancel()
            main_task.cancel()
    
    async def run_dashboard_display(self, layout):
        """Run the dashboard display in a separate task"""
        from rich.live import Live
        
        with Live(layout, console=self.dashboard.console, 
                 refresh_per_second=1/self.dashboard.update_frequency) as live:
            
            while self.is_running:
                try:
                    await asyncio.sleep(self.dashboard.update_frequency)
                except asyncio.CancelledError:
                    break
    
    async def run_data_loop(self, layout):
        """Main data processing loop"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as http_client:
            
            while self.is_running:
                try:
                    # Get live market data
                    market_data = self.data_connector.get_current_snapshot()
                    
                    if not market_data['spy_price']:
                        await asyncio.sleep(0.5)
                        continue
                    
                    current_time = datetime.now()
                    spy_price = market_data['spy_price']
                    
                    # Track statistics
                    self.stats['total_ticks'] += 1
                    
                    # Update aggregator with new tick
                    completed_bar = self.data_aggregator.update(
                        price=spy_price,
                        volume=1,  # Mock volume for now
                        timestamp=current_time
                    )
                    
                    # Check if 5-minute bar completed
                    if completed_bar:
                        self.stats['completed_bars'] += 1
                        print(f"\n🎯 5-minute bar completed at {completed_bar['timestamp']}")
                        
                        # Get RL prediction
                        await self.get_rl_prediction(
                            market_data, 
                            completed_bar, 
                            current_time, 
                            http_client
                        )
                    
                    # Update dashboard with real-time data
                    await self.update_dashboard_display(
                        layout, 
                        market_data, 
                        current_time
                    )
                    
                    # Wait before next update
                    await asyncio.sleep(0.5)  # 500ms polling
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"❌ Error in data loop: {e}")
                    await asyncio.sleep(1)
    
    async def get_rl_prediction(self, market_data: Dict, completed_bar: Dict, 
                               current_time: datetime, http_client: httpx.AsyncClient):
        """Get RL model prediction for completed 5-minute bar"""
        try:
            # Calculate 8-feature vector
            features = self.data_aggregator.calculate_rl_features(current_time)
            
            # Prepare request payload
            payload = {
                "features": features,
                "market_data": {
                    "spy_price": market_data['spy_price'],
                    "vix": market_data.get('vix', 0),
                    "timestamp": current_time.isoformat(),
                    "completed_bar": completed_bar
                },
                "include_memory": True,
                "include_reasoning": True
            }
            
            print(f"🤖 Calling RL API with features: {[f'{f:.4f}' for f in features[:4]]}")
            
            # Make async HTTP request
            response = await http_client.post(self.rl_api_url, json=payload)
            response.raise_for_status()
            
            # Parse response
            prediction = response.json()
            
            # Store prediction
            self.last_rl_prediction = prediction
            self.rl_prediction_time = current_time
            self.rl_prediction_valid_until = current_time + timedelta(minutes=5)
            
            self.stats['rl_calls'] += 1
            
            # Display prediction
            action_names = ['HOLD', 'SELL CALL', 'SELL PUT']
            action_name = action_names[prediction['action']]
            confidence = prediction['confidence']
            
            print(f"🎯 RL Prediction: {action_name} (confidence: {confidence:.2f})")
            print(f"   Valid until: {self.rl_prediction_valid_until.strftime('%H:%M:%S')}")
            
            return prediction
            
        except httpx.RequestError as e:
            print(f"🚨 RL API request failed: {e}")
            self.stats['rl_errors'] += 1
            return None
        except Exception as e:
            print(f"❌ RL prediction error: {e}")
            self.stats['rl_errors'] += 1
            return None
    
    async def update_dashboard_display(self, layout, market_data: Dict, current_time: datetime):
        """Update dashboard with current data and RL prediction"""
        try:
            # Get current features for display
            features = self.feature_engine.get_model_features(market_data)
            feature_dict = self.feature_engine.features_to_dict(features)
            
            # Use RL prediction if available and valid
            if (self.last_rl_prediction and 
                self.rl_prediction_valid_until and 
                current_time < self.rl_prediction_valid_until):
                
                action = self.last_rl_prediction['action']
                action_probs = self.last_rl_prediction.get('action_probabilities', [0.33, 0.33, 0.34])
                
                # Add countdown to next prediction
                time_until_next = self.rl_prediction_valid_until - current_time
                minutes_left = int(time_until_next.total_seconds() / 60)
                seconds_left = int(time_until_next.total_seconds() % 60)
                
                # Add timing info to constraints
                constraints = {
                    'rl_prediction_active': True,
                    'rl_confidence': self.last_rl_prediction['confidence'],
                    'next_update_in': f"{minutes_left}m {seconds_left}s",
                    'prediction_time': self.rl_prediction_time.strftime('%H:%M:%S')
                }
                
            else:
                # No valid RL prediction, show hold/waiting state
                action = 0
                action_probs = [1.0, 0.0, 0.0]
                constraints = {
                    'rl_prediction_active': False,
                    'waiting_for_next_bar': True,
                    'next_bar_in': self._time_until_next_bar()
                }
            
            # Update dashboard
            self.dashboard.update_display(
                layout,
                market_data,
                features,
                feature_dict,
                action,
                action_probs,
                constraints
            )
            
        except Exception as e:
            print(f"❌ Dashboard update error: {e}")
    
    def _time_until_next_bar(self) -> str:
        """Calculate time until next 5-minute bar"""
        now = datetime.now()
        current_minute = now.minute
        
        # Find next 5-minute boundary
        next_boundary = ((current_minute // 5) + 1) * 5
        if next_boundary >= 60:
            next_boundary = 0
            next_time = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
        else:
            next_time = now.replace(minute=next_boundary, second=0, microsecond=0)
        
        time_diff = next_time - now
        minutes = int(time_diff.total_seconds() / 60)
        seconds = int(time_diff.total_seconds() % 60)
        
        return f"{minutes}m {seconds}s"
    
    async def cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up...")
        
        if self.data_connector:
            await self.data_connector.stop()
            print("✓ Data connector stopped")
        
        # Print session stats
        print(f"\n{'='*60}")
        print("📊 Session Statistics")
        print(f"{'='*60}")
        print(f"Total Ticks: {self.stats['total_ticks']}")
        print(f"Completed 5-min Bars: {self.stats['completed_bars']}")
        print(f"RL API Calls: {self.stats['rl_calls']}")
        print(f"RL API Errors: {self.stats['rl_errors']}")
        if self.stats['rl_calls'] > 0:
            success_rate = (self.stats['rl_calls'] - self.stats['rl_errors']) / self.stats['rl_calls']
            print(f"RL API Success Rate: {success_rate:.1%}")
        print(f"{'='*60}")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Synchronized SPY Options Trading Terminal with RL API'
    )
    
    parser.add_argument('--rl-api-url', type=str,
                       default='http://localhost:8100/predict',
                       help='RL API endpoint URL')
    parser.add_argument('--update-rate', type=float, default=1.0,
                       help='Dashboard update frequency in seconds')
    
    args = parser.parse_args()
    
    # Create system
    system = SynchronizedTradingSystem(args.rl_api_url)
    
    try:
        # Initialize
        await system.initialize(args)
        
        # Run main loop
        await system.run_main_loop()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await system.cleanup()

if __name__ == "__main__":
    asyncio.run(main())