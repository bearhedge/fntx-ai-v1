#!/usr/bin/env python3
"""
FNTX Terminal - Main Entry Point

This module provides the command-line interface for the FNTX Trading Terminal.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional

def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress noisy libraries
    if not debug:
        logging.getLogger("textual").setLevel(logging.WARNING)
        logging.getLogger("rich").setLevel(logging.WARNING)

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='fntx',
        description='FNTX Terminal - Cyberpunk Trading Dashboard',
        epilog='Enter the Matrix of Trading'
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--demo',
        action='store_true',
        default=True,
        help='Run in demo mode with sample data (default)'
    )
    mode_group.add_argument(
        '--live',
        action='store_true',
        help='Run in live mode with real data connection'
    )
    
    # Display options
    parser.add_argument(
        '--theme',
        type=str,
        default='cyberpunk',
        choices=['cyberpunk', 'matrix', 'minimal', 'custom'],
        help='Color theme for the terminal'
    )
    parser.add_argument(
        '--refresh',
        type=int,
        default=3,
        help='Update frequency in seconds (default: 3)'
    )
    parser.add_argument(
        '--no-animations',
        action='store_true',
        help='Disable animations for better performance'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Display current configuration and exit'
    )
    
    # Testing and debugging
    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Test database connection and exit'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser.parse_args()

def get_config_path(custom_path: Optional[str] = None) -> Path:
    """Get the configuration file path."""
    if custom_path:
        return Path(custom_path)
    
    # Check for config in standard locations
    config_locations = [
        Path.home() / '.fntx' / 'config.toml',
        Path.home() / '.config' / 'fntx' / 'config.toml',
        Path('/etc/fntx/config.toml'),
    ]
    
    for path in config_locations:
        if path.exists():
            return path
    
    # Default to user home config
    return Path.home() / '.fntx' / 'config.toml'

def show_config(args: argparse.Namespace) -> None:
    """Display current configuration."""
    config_path = get_config_path(args.config)
    
    print("FNTX Terminal Configuration")
    print("=" * 40)
    print(f"Config Path: {config_path}")
    print(f"Mode: {'Live' if args.live else 'Demo'}")
    print(f"Theme: {args.theme}")
    print(f"Refresh Rate: {args.refresh} seconds")
    print(f"Animations: {'Disabled' if args.no_animations else 'Enabled'}")
    print(f"Debug: {'Enabled' if args.debug else 'Disabled'}")
    
    if config_path.exists():
        print("\nConfiguration file found!")
        print("Content:")
        print("-" * 40)
        with open(config_path, 'r') as f:
            print(f.read())
    else:
        print("\nNo configuration file found.")
        print("Running in demo mode by default.")

def test_connection(args: argparse.Namespace) -> bool:
    """Test database connection for live mode."""
    print("Testing connection...")
    
    if not args.live:
        print("✓ Demo mode - no connection needed")
        return True
    
    try:
        from .services.database import test_database_connection
        config_path = get_config_path(args.config)
        
        if test_database_connection(config_path):
            print("✓ Database connection successful")
            return True
        else:
            print("✗ Database connection failed")
            return False
            
    except ImportError:
        print("✗ Live mode dependencies not installed")
        print("  Install with: pip install fntx-terminal[live]")
        return False
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

def main() -> int:
    """Main entry point for FNTX Terminal."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    # Handle special commands
    if args.show_config:
        show_config(args)
        return 0
    
    if args.test_connection:
        return 0 if test_connection(args) else 1
    
    # Set environment variables for the app
    os.environ['FNTX_MODE'] = 'live' if args.live else 'demo'
    os.environ['FNTX_THEME'] = args.theme
    os.environ['FNTX_REFRESH'] = str(args.refresh)
    os.environ['FNTX_ANIMATIONS'] = '0' if args.no_animations else '1'
    
    if args.config:
        os.environ['FNTX_CONFIG'] = args.config
    
    # Disable mouse tracking for cleaner experience
    os.environ['TEXTUAL_MOUSE'] = '0'
    
    try:
        logger.info("Starting FNTX Terminal...")
        logger.info(f"Mode: {'Live' if args.live else 'Demo'}")
        logger.info(f"Theme: {args.theme}")
        
        # Import and run the app
        from .app import FNTXTerminalApp
        
        app = FNTXTerminalApp()
        app.run()
        
        logger.info("FNTX Terminal closed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\n\nTerminal closed.")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nError: {e}")
        print("Please check the logs for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())