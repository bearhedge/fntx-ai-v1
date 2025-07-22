#!/usr/bin/env python3
"""
Database connection helper for trade logging
Uses Unix socket to avoid password authentication issues
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_trade_db_connection():
    """Get database connection using Unix socket"""
    # Use Unix socket if localhost
    db_config = {
        "database": os.getenv("DB_NAME", "fntx_trading"),
        "user": os.getenv("DB_USER", "info")
    }
    
    # Check if we should use Unix socket
    host = os.getenv("DB_HOST", "localhost")
    if host == "localhost" or host == "127.0.0.1":
        db_config["host"] = "/var/run/postgresql"
    else:
        db_config["host"] = host
        db_config["port"] = os.getenv("DB_PORT", "5432")
        # Only add password if not using Unix socket
        password = os.getenv("DB_PASSWORD")
        if password:
            db_config["password"] = password
    
    return psycopg2.connect(**db_config)