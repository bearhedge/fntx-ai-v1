"""
MCP System Configuration
"""

import os
from typing import Dict, Any


def get_mcp_config() -> Dict[str, Any]:
    """
    Get MCP configuration from environment variables with defaults.
    
    Returns:
        Configuration dictionary for MCP system
    """
    return {
        # Redis Configuration
        'redis_host': os.getenv('MCP_REDIS_HOST', 'localhost'),
        'redis_port': int(os.getenv('MCP_REDIS_PORT', '6379')),
        'redis_password': os.getenv('MCP_REDIS_PASSWORD'),
        'redis_db': int(os.getenv('MCP_REDIS_DB', '0')),
        
        # PostgreSQL Configuration
        'postgres_host': os.getenv('MCP_POSTGRES_HOST', 'localhost'),
        'postgres_port': int(os.getenv('MCP_POSTGRES_PORT', '5432')),
        'postgres_database': os.getenv('MCP_POSTGRES_DATABASE', 'fntx_mcp'),
        'postgres_user': os.getenv('MCP_POSTGRES_USER', 'postgres'),
        'postgres_password': os.getenv('MCP_POSTGRES_PASSWORD'),
        
        # Google Cloud Storage Configuration
        'gcs_bucket': os.getenv('MCP_GCS_BUCKET', 'fntx-mcp-storage'),
        'gcs_credentials_path': os.getenv('MCP_GCS_CREDENTIALS_PATH'),
        
        # Pinecone Configuration
        'pinecone_api_key': os.getenv('MCP_PINECONE_API_KEY'),
        'pinecone_environment': os.getenv('MCP_PINECONE_ENVIRONMENT', 'us-east-1'),
        'pinecone_index': os.getenv('MCP_PINECONE_INDEX', 'fntx-agent-memories'),
        
        # OpenAI Configuration
        'openai_api_key': os.getenv('MCP_OPENAI_API_KEY', os.getenv('OPENAI_API_KEY')),
        'embedding_model': os.getenv('MCP_EMBEDDING_MODEL', 'text-embedding-ada-002'),
        
        # Memory Tier Thresholds
        'hot_threshold_hours': int(os.getenv('MCP_HOT_THRESHOLD_HOURS', '24')),
        'warm_threshold_days': int(os.getenv('MCP_WARM_THRESHOLD_DAYS', '7')),
        
        # Archival Configuration
        'archive_after_days': int(os.getenv('MCP_ARCHIVE_AFTER_DAYS', '30')),
        'archive_compression': os.getenv('MCP_ARCHIVE_COMPRESSION', 'true').lower() == 'true',
        
        # Performance Settings
        'batch_size': int(os.getenv('MCP_BATCH_SIZE', '100')),
        'max_concurrent_operations': int(os.getenv('MCP_MAX_CONCURRENT', '10')),
        
        # Debug Settings
        'debug_mode': os.getenv('MCP_DEBUG', 'false').lower() == 'true',
        'log_level': os.getenv('MCP_LOG_LEVEL', 'INFO')
    }


# Development configuration overrides
DEV_CONFIG = {
    'redis_host': 'localhost',
    'postgres_host': 'localhost',
    'debug_mode': True,
    'log_level': 'DEBUG'
}

# Production configuration overrides
PROD_CONFIG = {
    'debug_mode': False,
    'log_level': 'WARNING',
    'batch_size': 500,
    'max_concurrent_operations': 50
}


def get_environment_config() -> Dict[str, Any]:
    """
    Get configuration based on environment.
    
    Returns:
        Environment-specific configuration
    """
    env = os.getenv('MCP_ENVIRONMENT', 'development')
    base_config = get_mcp_config()
    
    if env == 'development':
        base_config.update(DEV_CONFIG)
    elif env == 'production':
        base_config.update(PROD_CONFIG)
        
    return base_config