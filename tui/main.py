#!/usr/bin/env python3
"""
FNTX Trading Terminal - Main Application Entry Point
"""
import os
import sys
import asyncio
from textual.app import App, ComposeResult
from textual.css.query import NoMatches
from textual.screen import Screen
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tui.screens.matrix_login_final import MatrixLoginScreen, MATRIX_LOGIN_CSS
from tui.screens.matrix_register import MatrixRegisterScreen, MATRIX_REGISTER_CSS
from tui.screens.welcome import WelcomeScreen, WELCOME_CSS
from tui.services.auth_service import get_auth_service, initialize_auth_service
from tui.services.api_client import close_api_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FNTXTradingApp(App):
    """Main FNTX Trading Terminal Application"""
    
    CSS = "\n".join([
        MATRIX_LOGIN_CSS,
        MATRIX_REGISTER_CSS,
        WELCOME_CSS,
        """
        /* Global app styles */
        Screen {
            align: center middle;
        }
        """
    ])
    
    TITLE = "FNTX Trading Terminal"
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self.auth_service = get_auth_service()
        
    async def on_mount(self):
        """Initialize the application"""
        # Initialize auth service
        await initialize_auth_service()
        
        # Check if user is already authenticated
        if self.auth_service.is_authenticated():
            # Go directly to welcome screen
            await self.push_screen(WelcomeScreen())
        else:
            # Show login screen
            await self.push_screen(MatrixLoginScreen())
            
        # Install screens
        self.install_screen(MatrixRegisterScreen(), name="register")
        
    async def on_matrix_login_screen_login_success(self, message):
        """Handle successful login"""
        logger.info(f"User logged in: {message.user_data.get('username')}")
        
        # Remove login screen and show welcome screen
        self.pop_screen()
        await self.push_screen(WelcomeScreen())
        
    async def on_matrix_register_screen_registration_success(self, message):
        """Handle successful registration"""
        logger.info(f"User registered: {message.user_data.get('username')}")
        
        # Remove registration screen and show welcome screen
        self.pop_screen()
        await self.push_screen(WelcomeScreen())
        
    async def on_shutdown(self):
        """Cleanup on app shutdown"""
        await close_api_client()
        
    def action_quit(self):
        """Quit the application"""
        self.exit()


def main():
    """Main entry point"""
    # Disable mouse tracking for cleaner terminal experience
    os.environ['TEXTUAL_MOUSE'] = '0'
    
    # Create and run the app
    app = FNTXTradingApp()
    app.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTerminal closed.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)