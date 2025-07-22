#!/usr/bin/env python3
"""
Configuration for ThetaTerminal data downloader
"""
import os
from datetime import datetime, timedelta

# ThetaTerminal API
THETA_HTTP_API = "http://localhost:25510"

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'options_data',
    'user': 'postgres',
    'password': os.environ.get('DB_PASSWORD', 'theta_data_2024'),  # Set via environment variable
}

# Download configuration
DOWNLOAD_CONFIG = {
    'start_date': '20170101',  # 8 years of data (2017-2024)
    'end_date': datetime.now().strftime('%Y%m%d'),
    'interval_ms': 60000,  # 1-minute bars
    'batch_size_days': 30,  # Download 1 month at a time
    'rate_limit_delay': 0.1,  # Seconds between API calls
    'max_retries': 3,
    'retry_delay': 5,  # Seconds
}

# SPY specific configuration
SPY_CONFIG = {
    'symbol': 'SPY',
    'strike_range': 50,  # Strikes ±$50 from ATM
    'min_volume_threshold': 0,  # Include all contracts for ML training
    
    # Approximate ATM prices by year for intelligent strike selection
    'atm_estimates': {
        2017: 250,
        2018: 280,
        2019: 320,
        2020: 350,
        2021: 420,
        2022: 450,
        2023: 400,
        2024: 500,
        2025: 600,
    }
}

# Data types available by subscription level
DATA_TYPES = {
    'value': ['ohlc', 'oi'],  # Previous subscription
    'standard': ['ohlc', 'oi', 'greeks', 'iv', 'trade', 'quote'],  # Current subscription
}

# Current subscription level - UPGRADED TO STANDARD!
SUBSCRIPTION_LEVEL = 'standard'  # Account upgraded to Standard with 8 years access

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'filename': '/home/info/fntx-ai-v1/08_logs/theta_downloader.log',
}

# Storage paths
DATA_PATHS = {
    'raw_data': '/home/info/fntx-ai-v1/04_data/raw',
    'processed_data': '/home/info/fntx-ai-v1/04_data/processed',
    'checkpoints': '/home/info/fntx-ai-v1/04_data/checkpoints',
}

# Create directories if they don't exist
for path in DATA_PATHS.values():
    os.makedirs(path, exist_ok=True)