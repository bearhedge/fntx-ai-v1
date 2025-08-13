"""
Configuration settings for Agent Factory
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "agent-factory"
    service_port: int = 8001
    debug: bool = False
    
    # Ray configuration
    ray_address: str = os.getenv("RAY_ADDRESS", "auto")
    ray_num_cpus: Optional[int] = None
    ray_num_gpus: Optional[int] = None
    
    # Pulsar configuration
    pulsar_url: str = os.getenv("PULSAR_URL", "pulsar://localhost:6650")
    pulsar_topic_prefix: str = "fntx"
    
    # Redis configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_ttl: int = 3600  # 1 hour
    
    # Model storage
    model_dir: str = os.getenv("MODEL_DIR", "/models")
    checkpoint_interval: int = 100  # Steps between checkpoints
    
    # Training configuration
    default_learning_rate: float = 3e-4
    default_batch_size: int = 64
    default_epochs: int = 10
    default_gamma: float = 0.99
    
    # Performance targets (from research paper)
    target_sharpe_ratio: float = 1.30
    min_sharpe_ratio: float = 0.8
    
    # Resource limits
    max_agents_per_user: int = 5
    max_training_time: int = 3600  # 1 hour
    max_model_size_mb: int = 500
    
    # Security
    api_key_header: str = "X-API-Key"
    enable_auth: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()