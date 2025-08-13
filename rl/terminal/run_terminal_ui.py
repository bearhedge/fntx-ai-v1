#!/usr/bin/env python3
"""
Entry point for the SPY Options Trading Terminal UI
Combines live data, AI model, and interactive terminal display
"""
import asyncio
import argparse
import sys
import os
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from dotenv import load_dotenv
import logging

# Enable debug logging to file (not console to avoid dashboard corruption)
logging.basicConfig(level=logging.INFO, filename='terminal_ui.log', filemode='a')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "01_backend"))

# from stable_baselines3 import PPO  # Optional, will use mock if not available
from data_pipeline import MockThetaConnector, ThetaDataConnector, FeatureEngine, PositionTracker
from data_pipeline.data_aggregator import DataAggregator
from data_pipeline.smart_suggestion_engine import SmartSuggestionEngine
from terminal_ui import TradingDashboard
from terminal_ui.trading_mode import TradingMode, detect_trading_mode, ModeConfig
from position_manager import PositionManager
from exercise_logger import exercise_logger


class RLAPIIntegration:
    """Handles RL API calls and prediction caching"""
    
    def __init__(self, rl_api_url: str = "http://localhost:8100/predict"):
        self.rl_api_url = rl_api_url
        self.data_aggregator = DataAggregator(interval_minutes=5)
        self.last_rl_prediction = None
        self.rl_prediction_time = None
        self.rl_prediction_valid_until = None
        self.is_updating = False
        
        # Statistics
        self.rl_calls = 0
        self.rl_errors = 0
    
    async def get_rl_prediction(self, market_data: Dict, current_time: datetime, 
                               http_client: httpx.AsyncClient) -> Optional[Dict]:
        """Get RL model prediction when 5-minute bar completes"""
        try:
            self.is_updating = True
            
            # Calculate 8-feature vector
            features = self.data_aggregator.calculate_rl_features(current_time)
            
            # Get the completed bar
            completed_bar = self.data_aggregator.get_latest_bar()
            
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
            
            print(f"\n🤖 Calling RL API at {current_time.strftime('%H:%M:%S')}")
            
            # Make async HTTP request
            response = await http_client.post(self.rl_api_url, json=payload)
            response.raise_for_status()
            
            # Parse response
            prediction = response.json()
            
            # Ensure prediction has required fields
            if 'action' not in prediction:
                print(f"⚠️  RL API response missing 'action' field: {prediction}")
                self.is_updating = False
                return None
                
            # Add confidence if missing (for backward compatibility)
            if 'confidence' not in prediction:
                # Calculate confidence from action probabilities if available
                if 'action_probabilities' in prediction:
                    action = prediction['action']
                    prediction['confidence'] = prediction['action_probabilities'][action]
                else:
                    prediction['confidence'] = 0.5  # Default confidence
            
            # Store prediction
            self.last_rl_prediction = prediction
            self.rl_prediction_time = current_time
            self.rl_prediction_valid_until = current_time + timedelta(minutes=5)
            
            self.rl_calls += 1
            self.is_updating = False
            
            # Display prediction
            action_names = ['HOLD', 'SELL CALL', 'SELL PUT']
            action_name = action_names[prediction['action']]
            confidence = prediction['confidence']
            
            print(f"✓ RL Prediction: {action_name} (confidence: {confidence:.1%})")
            print(f"  Valid until: {self.rl_prediction_valid_until.strftime('%H:%M:%S')}")
            print(f"  Action probabilities: {prediction.get('action_probabilities', 'N/A')}")
            
            # Log detailed prediction info
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"RL Prediction received: action={prediction['action']}, confidence={confidence:.3f}")
            
            return prediction
            
        except httpx.RequestError as e:
            print(f"🚨 RL API request failed: {e}")
            self.rl_errors += 1
            self.is_updating = False
            return None
        except Exception as e:
            print(f"❌ RL prediction error: {e}")
            self.rl_errors += 1
            self.is_updating = False
            return None
    
    def update_tick(self, price: float, volume: float = 1, timestamp: datetime = None):
        """Update aggregator with new tick data"""
        return self.data_aggregator.update(price, volume, timestamp)
    
    def should_get_prediction(self, current_time: datetime) -> bool:
        """Check if we should get a new RL prediction"""
        # If no prediction yet, check if we can make one
        if not self.rl_prediction_valid_until:
            # Wait for first complete bar
            return self.data_aggregator.get_latest_bar() is not None
        
        # Check if current prediction expired AND we're at a 5-minute boundary
        if current_time < self.rl_prediction_valid_until:
            return False
            
        # Check if we're at a 5-minute boundary (within 2 seconds)
        current_second = current_time.second
        current_minute = current_time.minute
        
        # Only trigger at 5-minute boundaries (0, 5, 10, 15, etc.)
        is_five_minute_boundary = (current_minute % 5 == 0)
        is_near_start = (current_second < 2)  # Within first 2 seconds
        
        return is_five_minute_boundary and is_near_start
    
    def get_current_prediction(self, current_time: datetime) -> Optional[Dict]:
        """Get current valid prediction or None"""
        if (self.last_rl_prediction and 
            self.rl_prediction_valid_until and 
            current_time < self.rl_prediction_valid_until):
            return self.last_rl_prediction
        return None
    
    def get_status(self, current_time: datetime) -> Dict:
        """Get RL API status for display"""
        if self.is_updating:
            return {
                'rl_prediction_active': True,
                'rl_api_status': 'updating',
                'rl_confidence': 0,
                'prediction_time': current_time.strftime('%H:%M:%S'),
                'next_update_in': 'Loading...'
            }
        
        if self.get_current_prediction(current_time):
            time_until_next = self.rl_prediction_valid_until - current_time
            minutes_left = int(time_until_next.total_seconds() / 60)
            seconds_left = int(time_until_next.total_seconds() % 60)
            
            return {
                'rl_prediction_active': True,
                'rl_api_status': 'active',
                'rl_confidence': self.last_rl_prediction['confidence'],
                'prediction_time': self.rl_prediction_time.strftime('%H:%M:%S'),
                'next_update_in': f"{minutes_left}m {seconds_left}s"
            }
        
        # Waiting for first prediction
        return {
            'rl_prediction_active': False,
            'rl_api_status': 'waiting',
            'waiting_for_next_bar': True,
            'next_bar_in': self._time_until_next_bar(current_time)
        }
    
    def _time_until_next_bar(self, current_time: datetime) -> str:
        """Calculate time until next 5-minute bar"""
        current_minute = current_time.minute
        
        # Find next 5-minute boundary
        next_boundary = ((current_minute // 5) + 1) * 5
        if next_boundary >= 60:
            next_boundary = 0
            next_time = current_time.replace(hour=current_time.hour + 1, minute=0, second=0, microsecond=0)
        else:
            next_time = current_time.replace(minute=next_boundary, second=0, microsecond=0)
        
        time_diff = next_time - current_time
        minutes = int(time_diff.total_seconds() / 60)
        seconds = int(time_diff.total_seconds() % 60)
        
        return f"{minutes}m {seconds}s"


async def main():
    """Main entry point for terminal UI"""
    # Get project root and load environment variables from config/.env file
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / 'config' / '.env'
    load_dotenv(env_path)
    
    parser = argparse.ArgumentParser(
        description='SPY 0DTE Options Trading Terminal with AI'
    )
    
    # Model arguments
    parser.add_argument('--model', type=str,
                       default='../models/gpu_trained/fresh_ppo_model.zip',
                       help='Path to trained PPO model')
    
    # Data source arguments
    parser.add_argument('--theta-key', type=str,
                       help='Theta Terminal API key (not needed for local)')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock data instead of live')
    parser.add_argument('--local-theta', action='store_true',
                       help='Use local Theta Terminal on port 25510')
    parser.add_argument('--yahoo-spy', action='store_true',
                       help='Use Yahoo Finance for real-time SPY price')
    
    # Trading mode is now automatic based on weekday/weekend
    # Keep --mock for backward compatibility
    
    # Trading parameters
    parser.add_argument('--capital', type=float, default=80000,
                       help='Trading capital (override with IBKR data if --ibkr-token provided)')
    parser.add_argument('--contracts', type=int, default=1,
                       help='Max contracts per trade')
    
    # IBKR Flex Query parameters
    parser.add_argument('--ibkr-token', type=str,
                       help='IBKR Flex Query token for fetching account data')
    parser.add_argument('--ibkr-query-id', type=str,
                       help='IBKR Flex Query ID for account summary')
    parser.add_argument('--force-ibkr-refresh', action='store_true',
                       help='Force refresh from IBKR even if database has data')
    
    # UI parameters
    parser.add_argument('--update-rate', type=float, default=None,
                       help='Update frequency in seconds')
    parser.add_argument('--demo', action='store_true',
                       help='Run in demo mode (no real trades)')
    
    # RL API parameters
    parser.add_argument('--rl-api-url', type=str,
                       default='http://localhost:8100/predict',
                       help='RL API endpoint URL')
    parser.add_argument('--enable-rl', action='store_true',
                       help='Enable RL API integration')
    
    # Position tracking parameters
    parser.add_argument('--enable-ib', action='store_true',
                       help='Enable IB Gateway for trade execution (not position tracking)')
    parser.add_argument('--ib-port', type=int, default=4001,
                       help='IB Gateway port (default: 4001)')
    parser.add_argument('--use-database', action='store_true', default=False,
                       help='Use database for position tracking (default: False)')
    
    args = parser.parse_args()
    
    # Auto-detect trading mode based on weekday/weekend
    trading_mode = detect_trading_mode(force_mock=args.mock)
    
    # Get mode configuration
    mode_config = ModeConfig.get_config(trading_mode)
    
    # Override mock flag based on mode
    if trading_mode == TradingMode.WEEKEND:
        args.mock = True
    elif trading_mode == TradingMode.WEEKDAY:
        args.mock = False
    
    # Override database usage based on mode
    if mode_config['use_database'] and not args.use_database:
        print(f"Note: {trading_mode.value.upper()} mode recommends database usage")
        args.use_database = mode_config['use_database']
    
    # Fetch account balance with proper architecture
    actual_capital = None
    capital_source = None
    base_currency = None  # Will be detected from FlexQuery response
    ibkr_positions = {}  # Store IBKR positions for dashboard
    ibkr_exercises = []  # Store IBKR exercises for dashboard
    
    # Always try ALM database first for most current NAV
    print("\n" + "="*60)
    print("Fetching Account Balance")
    print("="*60)
    
    # Step 1: Try ALM database first for accurate NAV
    if args.use_database:
        try:
            print("Fetching from ALM database...")
            from backend.data.database.trade_db import get_trade_db_connection
            conn = get_trade_db_connection()
            if conn:
                with conn.cursor() as cursor:
                    # Get latest NAV from ALM reporting system (most current data)
                    cursor.execute("""
                        SELECT summary_date, closing_nav_hkd, 'ALM_Reporting' as source
                        FROM alm_reporting.daily_summary
                        ORDER BY summary_date DESC
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    if result and result[1] is not None:
                        snapshot_date, closing_nav_hkd, source = result
                        # Use HKD directly
                        actual_capital = float(closing_nav_hkd)
                        base_currency = "HKD"
                        capital_source = f"ALM Database (as of {snapshot_date})"
                        print(f"✓ ALM NAV: {actual_capital:,.2f} {base_currency}")
                        print(f"  Last updated: {snapshot_date} (from ALM reporting)")
                    else:
                        print("⚠️  No ALM reporting data available in database")
                conn.close()
        except Exception as e:
            print(f"⚠️  Error checking ALM database: {e}")
    
    
    
    # NO FALLBACK TO MOCK DATA - Exit if no balance available
    if actual_capital is None:
        print(f"\n{'='*60}")
        print("❌ ERROR: No account balance data available!")
        print(f"{'='*60}")
        print("\nTo fix this:")
        print("  1. Make sure ALM database is populated")
        print("  2. Run daily_flex_import.py to update ALM data")
        print("  3. Check database connection settings")
        print(f"\n{'='*60}\n")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("SPY 0DTE Options Trading Terminal")
    print(f"{'='*60}")
    print(f"Trading Mode: {trading_mode.value.upper()}")
    print(f"  - Update Rate: {mode_config['update_rate']}s")
    print(f"  - Data Source: {mode_config['data_source']}")
    print(f"  - Trading Enabled: {mode_config['enable_trading']}")
    print(f"  - Display Mode: {mode_config['display_mode']}")
    print(f"Model: {args.model}")
    print(f"Data: {'Mock' if args.mock else 'Local Theta' if args.local_theta else 'Live'}")
    # Display capital with currency
    if base_currency and base_currency != "USD":
        print(f"Capital: {actual_capital:,.0f} {base_currency} ({capital_source})")
    else:
        print(f"Capital: ${actual_capital:,.0f} ({capital_source})")
    print(f"Max Contracts: {args.contracts}")
    print(f"Mode: {'DEMO' if args.demo else 'LIVE'}")
    print(f"RL API: {'ENABLED' if args.enable_rl else 'DISABLED'}")
    if args.enable_rl:
        print(f"RL API URL: {args.rl_api_url}")
    print(f"Position Tracking: {mode_config['position_tracking'].upper()}")
    print(f"IB Gateway: {'ENABLED' if args.enable_ib else 'DISABLED (Execution Only)'}")
    if args.enable_ib:
        print(f"IB Port: {args.ib_port}")
    print(f"{'='*60}\n")
    
    # Initialize components
    print("Initializing components...")
    
    # 1. Load model
    try:
        model_path = Path(args.model)
        
        # First check if model file exists
        if not model_path.exists():
            # Try default path if argument path doesn't exist
            default_model_path = Path(__file__).parent / 'models' / 'gpu_trained' / 'ppo_gpu_test_20250706_074954.zip'
            if default_model_path.exists():
                model_path = default_model_path
                print(f"Using default model: {model_path}")
            else:
                print(f"✗ Model not found at: {args.model}")
                print(f"✗ Default model not found at: {default_model_path}")
                sys.exit(1)
        
        # Try to load the model
        try:
            from stable_baselines3 import PPO
            model = PPO.load(str(model_path))
            print(f"✓ Trained RL model loaded from: {model_path}")
            print("✓ Using real PPO model for predictions")
        except ImportError as e:
            print("✗ stable_baselines3 is required but not installed")
            print("  Run: pip install stable-baselines3[extra]")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error loading PPO model: {e}")
            print("  Model file may be corrupted or incompatible")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Unexpected error during model loading: {e}")
        sys.exit(1)
    
    # 2. Initialize data connector
    try:
        yahoo_connector = None
        
        if args.mock:
            data_connector = MockThetaConnector()
        elif args.local_theta:
            from data_pipeline.rest_theta_connector import RESTThetaConnector
            data_connector = RESTThetaConnector()
            print("Using Theta Terminal REST connector with fast polling")
            
            # Optionally add Yahoo for SPY price
            if args.yahoo_spy:
                from data_pipeline.yahoo_finance_connector import YahooFinanceConnector
                yahoo_connector = YahooFinanceConnector()
                print("Using Yahoo Finance for real-time SPY price")
        else:
            if not args.theta_key:
                print("✗ Theta API key required for live data")
                print("  Use --mock for testing with mock data")
                print("  Use --local-theta for local Theta Terminal")
                sys.exit(1)
            data_connector = ThetaDataConnector(args.theta_key)
        
        await data_connector.start()
        print("✓ Data connector started")
        
        # Start Yahoo connector if enabled
        if yahoo_connector:
            await yahoo_connector.start()
            print("✓ Yahoo Finance connector started")
            
            # Create a wrapper that merges Yahoo SPY price with Theta options data
            class MergedDataConnector:
                def __init__(self, theta_conn, yahoo_conn):
                    self.theta = theta_conn
                    self.yahoo = yahoo_conn
                    
                def get_current_snapshot(self):
                    # Get data from both sources
                    theta_data = self.theta.get_current_snapshot()
                    yahoo_data = self.yahoo.get_current_snapshot()
                    
                    # Use Yahoo's SPY price if available, otherwise fall back to Theta
                    if yahoo_data.get('spy_price', 0) > 0:
                        theta_data['spy_price'] = yahoo_data['spy_price']
                        theta_data['spy_price_realtime'] = yahoo_data['spy_price']
                    
                    return theta_data
                    
                async def stop(self):
                    await self.theta.stop()
                    await self.yahoo.stop()
            
            # Replace data connector with merged version
            original_connector = data_connector
            data_connector = MergedDataConnector(original_connector, yahoo_connector)
    except Exception as e:
        print(f"✗ Error starting data connector: {e}")
        sys.exit(1)
    
    # 3. Initialize other components
    position_tracker = PositionTracker()
    feature_engine = FeatureEngine(position_tracker)
    suggestion_engine = SmartSuggestionEngine()
    
    print("✓ Feature engine initialized")
    print("✓ Suggestion engine initialized")
    
    # 4. Initialize RL API integration if enabled
    rl_integration = None
    if args.enable_rl:
        rl_integration = RLAPIIntegration(args.rl_api_url)
        print("✓ RL API integration initialized")
    
    # 5. Initialize position tracking
    position_manager = None
    db_position_tracker = None
    cleanup_manager = None
    
    # Use database for position tracking
    if args.use_database:
        from data_pipeline.database_position_tracker import AsyncDatabasePositionTracker
        db_position_tracker = AsyncDatabasePositionTracker()
        db_connected = await db_position_tracker.start()
        if db_connected:
            print("✓ Database position tracking started")
        else:
            print("⚠️  Database connection failed - position tracking disabled")
    
    # IB Gateway only for execution if needed
    if args.enable_ib:
        position_manager = PositionManager()
        ib_connected = await position_manager.start()
        if ib_connected:
            print("✓ IB Gateway connected for trade execution")
        else:
            print("⚠️  IB Gateway not connected - manual execution required")
    
    # Check if cleanup manager is running as a service
    # We don't start it here - it runs independently via systemd
    cleanup_manager = None
    if not args.mock and trading_mode == TradingMode.WEEKDAY:
        try:
            # Create a status client to get updates from the running service
            from cleanup.cleanup_status_client import CleanupStatusClient
            # Get DB password outside of dictionary to avoid scoping issue
            # Use correct database credentials
            cleanup_manager = CleanupStatusClient({
                'host': 'localhost',
                'database': 'options_data',
                'user': 'postgres',
                'password': 'theta_data_2024'
            })
            
            # Test connection
            status = cleanup_manager.get_cleanup_status()
            if status.get('service_status', '').startswith('Check with:'):
                print("ℹ️  Cleanup Manager Status:")
                print("  - Service may not be running")
                print("  - Check with: sudo systemctl status cleanup-manager")
                print("  - Start with: sudo systemctl start cleanup-manager.timer")
            else:
                print("✓ Cleanup Manager Status Client initialized")
                print(f"  - Mode: {status.get('mode', 'unknown')}")
                if status.get('spy_price', 0) > 0:
                    print(f"  - Monitoring with 0.03% threshold (${status.get('threshold_dollars', 0):.2f})")
            
        except Exception as e:
            print(f"⚠️  Could not initialize cleanup manager client: {e}")
    
    # 6. Create dashboard with mode-specific update rate
    dashboard_update_rate = mode_config['update_rate'] if not args.update_rate else args.update_rate
    dashboard = TradingDashboard(update_frequency=dashboard_update_rate, capital=actual_capital)
    # Update capital with currency info
    dashboard.update_capital(actual_capital, f"{capital_source} ({base_currency})")
    # Set IBKR positions if available
    if ibkr_positions:
        dashboard.set_ibkr_positions(ibkr_positions)
        print(f"✓ IBKR positions set: {list(ibkr_positions.keys())}")
    
    # Set IBKR option events (exercises, assignments, expirations) if available
    if ibkr_exercises:
        dashboard.set_ibkr_exercises(ibkr_exercises)
        print(f"✓ IBKR option events found: {len(ibkr_exercises)} events")
        # Group by type for summary
        by_type = {}
        for ex in ibkr_exercises:
            ex_type = ex['type']
            if ex_type not in by_type:
                by_type[ex_type] = []
            by_type[ex_type].append(ex)
        
        # Show summary by type
        for event_type, events in by_type.items():
            print(f"   {event_type}: {len(events)} events")
            for ex in events:
                print(f"     - {ex['symbol']} on {ex['date']}")
    
    print(f"✓ Dashboard created (update rate: {dashboard_update_rate}s)")
    
    # Wait for market data
    print("\nWaiting for market data...")
    await asyncio.sleep(2)
    
    # Check data
    test_data = data_connector.get_current_snapshot()
    if test_data['spy_price']:
        print(f"✓ Receiving data - SPY: ${test_data['spy_price']:.2f}")
    else:
        print("⚠️  No market data yet")
    
    print(f"\n{'='*60}")
    print("Terminal UI Ready!")
    print("Press Ctrl+C to exit")
    print(f"{'='*60}\n")
    
    # Run dashboard
    try:
        await dashboard.run(
            data_connector,
            feature_engine,
            model,
            suggestion_engine,
            rl_integration=rl_integration,
            position_manager=position_manager,
            db_position_tracker=db_position_tracker,
            cleanup_manager=cleanup_manager
        )
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        # Cleanup
        await data_connector.stop()
        print("✓ Data connector stopped")
        
        if position_manager:
            await position_manager.stop()
            print("✓ Position manager stopped")
            
        if db_position_tracker:
            await db_position_tracker.stop()
            print("✓ Database position tracker stopped")
        
        # Show session summary
        print(f"\n{'='*60}")
        print("Session Summary")
        print(f"{'='*60}")
        print(f"Total Updates: {dashboard.update_count}")
        print(f"Duration: {datetime.now() - dashboard.last_update if dashboard.last_update else 'N/A'}")
        print(f"Suggestions Made: {len(suggestion_engine.recent_rejections)}")
        
        if rl_integration:
            print(f"\nRL API Statistics:")
            print(f"  RL API Calls: {rl_integration.rl_calls}")
            print(f"  RL API Errors: {rl_integration.rl_errors}")
            if rl_integration.rl_calls > 0:
                success_rate = (rl_integration.rl_calls - rl_integration.rl_errors) / rl_integration.rl_calls
                print(f"  Success Rate: {success_rate:.1%}")
        
        # Show RLHF feedback summary
        if hasattr(dashboard, 'feedback_collector'):
            feedback_summary = dashboard.feedback_collector.get_session_summary()
            print(f"\nRLHF Feedback Summary:")
            print(f"  Suggestions Made: {feedback_summary['suggestions_made']}")
            print(f"  Accepted: {feedback_summary['suggestions_accepted']}")
            print(f"  Rejected: {feedback_summary['suggestions_rejected']}")
        
        # --- Display ALM Performance Narrative ---
        print(f"\n{'='*60}")
        import click
        import subprocess
        import os
        click.echo(click.style("--- Generating Month-to-Date Performance Narrative ---", fg="yellow"))
        try:
            # Construct the absolute path to the performance script
            performance_script_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), '..', 'show_performance.sh'
            ))
            if not os.path.exists(performance_script_path):
                raise FileNotFoundError(f"Performance script not found at: {performance_script_path}")
    
            # Execute the script and capture the output
            result = subprocess.run(
                [performance_script_path],
                capture_output=True,
                text=True,
                check=True
            )
            # Use click.echo to print the output
            click.echo(result.stdout)
            click.echo(click.style("--- End of Performance Narrative ---\n", fg="yellow"))
    
        except FileNotFoundError as e:
            click.echo(click.style(f"Error: {e}", fg="red"))
        except subprocess.CalledProcessError as e:
            click.echo(click.style("Error executing performance narrative script:", fg="red"))
            click.echo(click.style(e.stderr, fg="red"))
        except Exception as e:
            click.echo(click.style(f"An unexpected error occurred: {e}", fg="red"))
            print(f"  Acceptance Rate: {feedback_summary.get('acceptance_rate', 0):.1%}")
            print(f"  Feedback Provided: {feedback_summary['feedback_provided']}")
            
            # Export feedback for training if any was collected
            if feedback_summary['feedback_provided'] > 0:
                export_path = dashboard.feedback_collector.export_for_training()
                print(f"  Exported feedback to: {export_path}")
        
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())