#!/usr/bin/env python3
"""
Database connection module for FNTX trading system
Provides PostgreSQL connection management for trade data access
"""

import os
import sys
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from the correct .env file
# First try project root, then rl-trading/spy_options directory
env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rl-trading', 'spy_options', '.env')
]

for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

# Connection pool for efficiency (optional, can be None)
connection_pool = None

def get_trade_db_connection():
    """
    Get a connection to the trade database
    
    Returns:
        psycopg2.connection: Database connection object or None if connection fails
    """
    try:
        # Get connection parameters from environment
        db_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'options_data'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # Check if password is set
        if not db_params['password']:
            logger.error("Database password not found in environment variables")
            return None
        
        # Create connection
        conn = psycopg2.connect(**db_params)
        
        # Set autocommit to False for transaction support
        conn.autocommit = False
        
        logger.info(f"Successfully connected to database {db_params['database']} on {db_params['host']}:{db_params['port']}")
        return conn
        
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {e}")
        return None

def init_connection_pool(minconn=1, maxconn=10):
    """
    Initialize a connection pool for better performance
    
    Args:
        minconn: Minimum number of connections
        maxconn: Maximum number of connections
    """
    global connection_pool
    
    try:
        db_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'options_data'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn, maxconn, **db_params
        )
        logger.info("Database connection pool initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        connection_pool = None

def get_connection_from_pool():
    """
    Get a connection from the pool if available
    
    Returns:
        psycopg2.connection: Database connection or None
    """
    global connection_pool
    
    if connection_pool:
        try:
            return connection_pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
    
    # Fallback to regular connection
    return get_trade_db_connection()

def return_connection_to_pool(conn):
    """
    Return a connection to the pool
    
    Args:
        conn: Connection to return
    """
    global connection_pool
    
    if connection_pool and conn:
        try:
            connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
            # Close the connection if we can't return it
            try:
                conn.close()
            except:
                pass

def close_connection_pool():
    """Close all connections in the pool"""
    global connection_pool
    
    if connection_pool:
        try:
            connection_pool.closeall()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")
        finally:
            connection_pool = None