"""
FNTX Terminal - Main Application

The core application class that manages screens and navigation.
"""

import os
import sys
import asyncio
import logging
from typing import Optional
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Label
from textual.containers import Container, Vertical, Horizontal
from textual.binding import Binding

from .config import get_config, get_config_manager
from .screens.login import MatrixLoginScreen
from .screens.dashboard import DashboardScreen
from .demo.data_generator import DemoDataGenerator

logger = logging.getLogger(__name__)

class FNTXTerminalApp(App):
    """Main FNTX Terminal Application."""
    
    CSS = """
    Screen {
        align: center middle;
        background: $background;
    }
    
    .title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 1;
    }
    """
    
    TITLE = "FNTX Terminal"
    SUB_TITLE = "Enter the Matrix of Trading"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
    ]
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.config = get_config()
        self.config_manager = get_config_manager()
        self.data_generator = None
        
        # Set theme
        self._load_theme()
        
        # Initialize demo data generator if in demo mode
        if self.config_manager.is_demo_mode():
            self.data_generator = DemoDataGenerator()
    
    def _load_theme(self) -> None:
        """Load and apply theme."""
        theme_name = self.config.display.theme
        
        # Define built-in themes
        themes = {
            'cyberpunk': {
                'primary': '#00ff41',      # Matrix green
                'secondary': '#39ff14',    # Neon green
                'accent': '#ff00ff',       # Magenta
                'warning': '#ffff00',      # Yellow
                'error': '#ff0040',        # Red
                'background': '#0a0a0a',   # Deep black
                'surface': '#1a1a2e',      # Dark blue
                'text': '#c0c0c0',         # Silver
            },
            'matrix': {
                'primary': '#00ff00',      # Pure green
                'secondary': '#008f11',    # Dark green
                'accent': '#ffffff',       # White
                'warning': '#ffff00',      # Yellow
                'error': '#ff0000',        # Red
                'background': '#000000',   # Black
                'surface': '#0a0a0a',      # Near black
                'text': '#00ff00',         # Green text
            },
            'minimal': {
                'primary': '#ffffff',      # White
                'secondary': '#888888',    # Gray
                'accent': '#0088ff',       # Blue
                'warning': '#ff8800',      # Orange
                'error': '#ff0000',        # Red
                'background': '#000000',   # Black
                'surface': '#111111',      # Dark gray
                'text': '#ffffff',         # White text
            }
        }
        
        # Apply theme colors
        if theme_name in themes:
            theme = themes[theme_name]
            for color_name, color_value in theme.items():
                self.design.colors[color_name] = color_value
    
    async def on_mount(self) -> None:
        """Initialize the application on mount."""
        logger.info(f"Starting FNTX Terminal in {self.config.mode} mode")
        
        # Check if we should skip login in demo mode
        if self.config_manager.is_demo_mode():
            # Go straight to dashboard in demo mode
            await self.push_screen(DashboardScreen())
        else:
            # Show login screen for live mode
            await self.push_screen(MatrixLoginScreen())
    
    async def action_quit(self) -> None:
        """Quit the application."""
        logger.info("Shutting down FNTX Terminal")
        
        # Cleanup
        if self.data_generator:
            await self.data_generator.cleanup()
        
        self.exit()
    
    async def action_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
    
    def on_login_success(self, username: str) -> None:
        """Handle successful login."""
        logger.info(f"User logged in: {username}")
        self.pop_screen()
        self.push_screen(DashboardScreen())
    
    def run(self, **kwargs) -> None:
        """Run the application."""
        try:
            # Set up environment
            if not os.environ.get('TERM'):
                os.environ['TERM'] = 'xterm-256color'
            
            # Run the app
            super().run(**kwargs)
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            raise

class WelcomeScreen(Screen):
    """Welcome screen for first-time users."""
    
    def compose(self) -> ComposeResult:
        """Create welcome screen layout."""
        yield Container(
            Vertical(
                Label("Welcome to FNTX Terminal", classes="title"),
                Label("A Cyberpunk Trading Dashboard"),
                Label(""),
                Label("Press any key to continue..."),
                classes="welcome-container",
            ),
            classes="centered",
        )
    
    def on_key(self) -> None:
        """Handle any key press."""
        self.app.pop_screen()