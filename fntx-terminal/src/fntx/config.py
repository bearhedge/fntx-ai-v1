"""
Configuration management for FNTX Terminal.

Handles both demo and live mode configurations.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import tomllib

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "options_data"
    user: str = "postgres"
    password: str = ""
    
@dataclass
class APIConfig:
    """API configuration."""
    base_url: str = "http://localhost:8080"
    theta_key: str = ""
    timeout: int = 30
    
@dataclass
class DisplayConfig:
    """Display configuration."""
    theme: str = "cyberpunk"
    refresh_rate: int = 3
    animations: bool = True
    panel_layout: str = "10_panel_grid"
    
@dataclass
class TradingConfig:
    """Trading parameters for display."""
    max_daily_loss: float = 5000.0
    max_positions: int = 10
    trading_hours: str = "09:30-16:00"
    preferred_window: str = "14:00-16:00"

@dataclass
class Config:
    """Main configuration container."""
    mode: str = "demo"  # demo or live
    database: DatabaseConfig = None
    api: APIConfig = None
    display: DisplayConfig = None
    trading: TradingConfig = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.api is None:
            self.api = APIConfig()
        if self.display is None:
            self.display = DisplayConfig()
        if self.trading is None:
            self.trading = TradingConfig()

class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager."""
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        
    def _get_default_config_path(self) -> Path:
        """Get default configuration path."""
        # Check environment variable
        if env_path := os.environ.get('FNTX_CONFIG'):
            return Path(env_path)
        
        # Check standard locations
        locations = [
            Path.home() / '.fntx' / 'config.toml',
            Path.home() / '.config' / 'fntx' / 'config.toml',
        ]
        
        for path in locations:
            if path.exists():
                return path
        
        # Default to user home
        return Path.home() / '.fntx' / 'config.toml'
    
    def _load_config(self) -> Config:
        """Load configuration from file or use defaults."""
        config = Config()
        
        # Override from environment
        config.mode = os.environ.get('FNTX_MODE', 'demo')
        config.display.theme = os.environ.get('FNTX_THEME', 'cyberpunk')
        config.display.refresh_rate = int(os.environ.get('FNTX_REFRESH', '3'))
        config.display.animations = os.environ.get('FNTX_ANIMATIONS', '1') == '1'
        
        # Load from file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'rb') as f:
                    data = tomllib.load(f)
                    
                # Update config from file
                if 'database' in data:
                    config.database = DatabaseConfig(**data['database'])
                if 'api' in data:
                    config.api = APIConfig(**data['api'])
                if 'display' in data:
                    for key, value in data['display'].items():
                        if hasattr(config.display, key):
                            setattr(config.display, key, value)
                if 'trading' in data:
                    config.trading = TradingConfig(**data['trading'])
                    
                logger.info(f"Loaded configuration from {self.config_path}")
                
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
                logger.info("Using default configuration")
        else:
            logger.info(f"No config file found at {self.config_path}")
            logger.info("Using default configuration")
        
        return config
    
    def save_config(self, path: Optional[Path] = None) -> None:
        """Save current configuration to file."""
        save_path = path or self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary
        config_dict = {
            'database': asdict(self.config.database),
            'api': asdict(self.config.api),
            'display': asdict(self.config.display),
            'trading': asdict(self.config.trading),
        }
        
        # Write TOML file
        import tomli_w
        with open(save_path, 'wb') as f:
            tomli_w.dump(config_dict, f)
        
        logger.info(f"Saved configuration to {save_path}")
    
    def is_live_mode(self) -> bool:
        """Check if running in live mode."""
        return self.config.mode == 'live'
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.config.mode == 'demo'
    
    def get_theme_path(self) -> Path:
        """Get path to theme file."""
        if self.config.display.theme == 'custom':
            custom_path = Path.home() / '.fntx' / 'themes' / 'custom.toml'
            if custom_path.exists():
                return custom_path
        
        # Use built-in theme
        return Path(__file__).parent / 'themes' / f'{self.config.display.theme}.toml'
    
    def validate_live_mode(self) -> bool:
        """Validate configuration for live mode."""
        if not self.config.database.password:
            logger.error("Database password not configured")
            return False
        
        if not self.config.api.theta_key and self.config.mode == 'live':
            logger.warning("Theta API key not configured")
        
        return True

# Global configuration instance
_config_manager: Optional[ConfigManager] = None

def get_config() -> Config:
    """Get global configuration instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.config

def get_config_manager() -> ConfigManager:
    """Get global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager