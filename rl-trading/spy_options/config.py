"""
Configuration settings for SPY Options RL Trading System
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME', 'options_data'),  # Historical data is here!
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'theta_data_2024')
}

# Trading configuration
TRADING_CONFIG = {
    'symbol': 'SPY',
    'contract_multiplier': 100,
    'commission_per_contract': 0.65,
    'market_open': {'hour': 9, 'minute': 30},
    'market_close': {'hour': 16, 'minute': 0},
    'trading_days_per_year': 252
}

# Risk levels configuration - affects stop loss and wait time only
RISK_LEVELS = {
    'LOW': {
        'stop_multiple': 3,      # 3x stop loss
        'wait_hours': 2,         # Wait 2 hours after open (minimum)
        'max_position_pct': 100  # No position restrictions
    },
    'MEDIUM': {
        'stop_multiple': 4,      # 4x stop loss
        'wait_hours': 3,         # Wait 3 hours after open
        'max_position_pct': 100  # No position restrictions
    },
    'HIGH': {
        'stop_multiple': 5,      # 5x stop loss
        'wait_hours': 4,         # Wait 4 hours after open (maximum)
        'max_position_pct': 100  # No position restrictions
    }
}

# RL Training configuration
RL_CONFIG = {
    'train_start_date': '2022-12-01',
    'train_end_date': '2024-12-31',
    'validation_start_date': '2025-01-01',
    'validation_end_date': '2025-04-30',
    'test_start_date': '2025-05-01',
    'test_end_date': '2025-06-30'
}

# Model paths
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models')
LOG_PATH = os.path.join(os.path.dirname(__file__), 'logs')
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')