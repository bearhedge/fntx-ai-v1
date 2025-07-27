#!/usr/bin/env python3
"""
FNTX AI Logging Configuration
Centralized logging setup for all backend services and agents.
"""

import os
import logging
import logging.handlers
from typing import Optional
from .config import config

def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = None,
    format_string: str = None
) -> logging.Logger:
    """Set up a logger with consistent formatting and handlers"""
    
    logger = logging.getLogger(name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    # Set level
    log_level = level or config.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    format_str = format_string or config.LOG_FORMAT
    formatter = logging.Formatter(format_str)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Ensure logs directory exists
        log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10485760, backupCount=5  # 10MB per file, 5 backups
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_agent_logger(agent_name: str) -> logging.Logger:
    """Get a logger for an agent with standard configuration"""
    log_file = config.get_log_path(f"{agent_name.lower()}.log")
    return setup_logger(agent_name, log_file)

def get_api_logger() -> logging.Logger:
    """Get a logger for the API server"""
    return setup_logger("APIServer", config.get_log_path("api_server.log"))