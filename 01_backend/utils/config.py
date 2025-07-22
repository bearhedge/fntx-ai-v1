#!/usr/bin/env python3
"""
FNTX AI Configuration Management
Centralized configuration for all backend services and agents.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_project_root() -> str:
    """
    Get the project root directory dynamically.
    Looks for backend directory to determine project root.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up from backend/utils to find project root
    while current_dir != "/" and current_dir:
        # Check if this directory contains '01_backend' folder
        if os.path.exists(os.path.join(current_dir, "01_backend")) and \
           os.path.exists(os.path.join(current_dir, "01_backend", "agents")):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    
    # Fallback to current working directory
    return os.getcwd()

class Config:
    """Application configuration"""
    
    # Project root directory
    PROJECT_ROOT: str = get_project_root()
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8002"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "True").lower() == "true"
    
    # IBKR Configuration
    IBKR_HOST: str = os.getenv("IBKR_HOST", "127.0.0.1")
    IBKR_PORT: int = int(os.getenv("IBKR_PORT", "4001"))  # Live account
    IBKR_CLIENT_ID: int = int(os.getenv("IBKR_CLIENT_ID", "1"))
    
    # EnvironmentWatcher IBKR Configuration
    ENV_IBKR_CLIENT_ID: int = int(os.getenv("ENV_IBKR_CLIENT_ID", "3"))
    
    # Market Data Configuration
    VIX_LOW_THRESHOLD: float = float(os.getenv("VIX_LOW_THRESHOLD", "15.0"))
    VIX_HIGH_THRESHOLD: float = float(os.getenv("VIX_HIGH_THRESHOLD", "25.0"))
    SPY_SUPPORT_THRESHOLD: float = float(os.getenv("SPY_SUPPORT_THRESHOLD", "0.02"))
    VOLUME_SPIKE_THRESHOLD: float = float(os.getenv("VOLUME_SPIKE_THRESHOLD", "1.5"))
    
    # Monitoring Configuration
    MONITORING_INTERVAL: int = int(os.getenv("MONITORING_INTERVAL", "30"))  # seconds
    
    # Risk Management
    MAX_DAILY_RISK: float = float(os.getenv("MAX_DAILY_RISK", "0.02"))
    POSITION_LIMIT: int = int(os.getenv("POSITION_LIMIT", "3"))
    STOP_LOSS_MULTIPLIER: float = float(os.getenv("STOP_LOSS_MULTIPLIER", "3.0"))
    TAKE_PROFIT_MULTIPLIER: float = float(os.getenv("TAKE_PROFIT_MULTIPLIER", "0.5"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Dynamic Paths
    LOGS_DIR: str = os.path.join(PROJECT_ROOT, "08_logs")
    MEMORY_BASE_PATH: str = os.getenv("MEMORY_BASE_PATH", os.path.join(PROJECT_ROOT, "01_backend", "agents", "memory"))
    
    @classmethod
    def get_memory_path(cls, filename: str) -> str:
        """Get full path for memory file"""
        return os.path.join(cls.MEMORY_BASE_PATH, filename)
    
    @classmethod
    def get_log_path(cls, filename: str) -> str:
        """Get full path for log file"""
        return os.path.join(cls.LOGS_DIR, filename)

# Global config instance
config = Config()