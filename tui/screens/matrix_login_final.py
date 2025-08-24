#!/usr/bin/env python3
"""
Combined working version with proper matrix rain and login form
"""
from textual.app import App, ComposeResult
from textual.containers import Container, Center, Vertical, Horizontal
from textual.widgets import Static, Label, LoadingIndicator
from textual.screen import Screen
from textual.binding import Binding
from textual.message import Message
from rich.text import Text
from datetime import datetime
import random
import math
import asyncio

from ..components.glow_input import GlowInput, PsychedelicButton
from ..services.auth_service import get_auth_service


class ProperMatrixRainWidget(Static):
    """Matrix rain with proper falling columns"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.columns = []
        self.frame_count = 0
        self.grid = None
        self.style_grid = None
        
    def on_mount(self):
        """Initialize on mount with proper size detection"""
        self.call_after_refresh(self._initialize_columns)
        # Increased to 60 FPS for smoother animation
        self.set_interval(1/60, self.update_animation)
        
    def _initialize_columns(self):
        """Initialize columns after size is known"""
        width = self.size.width
        height = self.size.height
        
        if width <= 0 or height <= 0:
            return
            
        # Reduce columns for better performance while maintaining density
        num_columns = min(width // 4, 60)
        self.columns = []
        
        for i in range(num_columns):
            col_x = int((i * width) / num_columns)
            # More speed variations to prevent batching
            speed = 0.5 + (random.random() * 1.5)  # Range: 0.5 to 2.0
            trail_length = random.randint(12, 20)
            self.columns.append({
                'x': col_x,
                'y': float(random.randint(-height, 0)),  # Use float for smoother movement
                'speed': speed,
                'chars': [self._random_char() for _ in range(trail_length)],
                'length': trail_length,
                'phase': random.random()  # Random phase to prevent sync
            })
    
    def _random_char(self):
        """Get a random matrix character"""
        chars = ['0','1','ア','イ','ウ','!','@','#','$','%','^','&','*']
        return random.choice(chars)
    
    def update_animation(self):
        """Update the animation"""
        height = self.size.height
        
        for col in self.columns:
            col['y'] += col['speed']
            
            # Reset column when it goes off screen
            if col['y'] > height + col['length']:
                col['y'] = random.randint(-height, -10)
                col['chars'] = [self._random_char() for _ in range(col['length'])]
            
            # Reduce character changes to improve performance
            if random.random() < 0.05:  # Reduced from 10% to 5%
                idx = random.randint(0, len(col['chars']) - 1)
                col['chars'][idx] = self._random_char()
        
        self.refresh()
    
    def render(self) -> Text:
        """Render the matrix rain"""
        width = self.size.width
        height = self.size.height
        
        if width <= 0 or height <= 0:
            return Text("")
        
        # Pre-allocate or reuse grids for performance
        if self.grid is None or len(self.grid) != height or len(self.grid[0]) != width:
            self.grid = [[' ' for _ in range(width)] for _ in range(height)]
            self.style_grid = [[None for _ in range(width)] for _ in range(height)]
        else:
            # Clear existing grids
            for row in self.grid:
                for i in range(len(row)):
                    row[i] = ' '
            for row in self.style_grid:
                for i in range(len(row)):
                    row[i] = None
        
        # Render columns
        for col in self.columns:
            x = col['x']
            if 0 <= x < width:
                for i, char in enumerate(col['chars']):
                    y = int(col['y'] - i)
                    if 0 <= y < height:
                        self.grid[y][x] = char
                        # Gradient effect based on position in trail
                        if i == 0:
                            self.style_grid[y][x] = "bright_green bold"
                        elif i < 3:
                            self.style_grid[y][x] = "green"
                        elif i < 8:
                            self.style_grid[y][x] = "rgb(0,180,0)"
                        else:
                            self.style_grid[y][x] = "rgb(0,100,0)"
        
        # Build text with styling
        text = Text()
        for y in range(height):
            for x in range(width):
                char = self.grid[y][x]
                style = self.style_grid[y][x]
                if style:
                    text.append(char, style=style)
                else:
                    text.append(char)
            if y < height - 1:
                text.append('\n')
        
        return text


class MatrixLoginScreen(Screen):
    """Working login screen with matrix rain background"""
    
    BINDINGS = [
        Binding("escape", "quit", "Quit"),
        Binding("tab", "next_field", "Next Field", show=False),
        Binding("shift+tab", "prev_field", "Previous Field", show=False),
    ]
    
    class LoginSuccess(Message):
        """Message sent when login is successful"""
        def __init__(self, user_data: dict):
            self.user_data = user_data
            super().__init__()
    
    def __init__(self):
        super().__init__()
        self.auth_service = get_auth_service()
        self.is_loading = False
        self.error_message = None
    
    def compose(self) -> ComposeResult:
        """Create the layout with both widgets in same container"""
        with Container(id="main-container"):
            # Matrix background
            yield ProperMatrixRainWidget(id="matrix-rain")
            
            # Login form overlay
            with Container(id="login-form"):
                # Logo
                yield Static(self.LOGO, id="logo")
                
                # Title
                yield Label("[bold cyan]TRADING TERMINAL[/bold cyan]", id="title")
                
                # Error message container
                yield Label("", id="error-message", classes="error-hidden")
                
                # Form fields
                yield GlowInput(
                    placeholder="Enter Username",
                    id="username",
                    classes="glow-input"
                )
                yield GlowInput(
                    placeholder="Enter Password",
                    password=True,
                    id="password",
                    classes="glow-input"
                )
                
                # Loading indicator (hidden by default)
                yield LoadingIndicator(id="loading", classes="loading-hidden")
                
                # Buttons container
                with Horizontal(id="button-container"):
                    yield PsychedelicButton(
                        "ENTER",
                        id="submit-button"
                    )
                    yield PsychedelicButton(
                        "CREATE ACCOUNT",
                        id="register-button"
                    )
    
    def on_mount(self):
        """Focus username on mount"""
        self.query_one("#username").focus()
    
    def action_quit(self):
        """Quit the app"""
        self.app.exit()
    
    def action_next_field(self):
        """Move to next input field"""
        if self.query_one("#username").has_focus:
            self.query_one("#password").focus()
        elif self.query_one("#password").has_focus:
            self.query_one("#submit-button").focus()
    
    def action_prev_field(self):
        """Move to previous input field"""
        if self.query_one("#password").has_focus:
            self.query_one("#username").focus()
        elif self.query_one("#submit-button").has_focus:
            self.query_one("#password").focus()
    
    async def on_input_submitted(self, event):
        """Handle Enter key in input fields"""
        if event.input.id == "username":
            self.query_one("#password").focus()
        elif event.input.id == "password":
            await self.handle_login()
    
    async def on_psychedelic_button_pressed(self, event):
        """Handle button clicks"""
        if event.button.id == "submit-button":
            await self.handle_login()
        elif event.button.id == "register-button":
            # Switch to registration screen (to be implemented)
            self.app.push_screen("register")
    
    def show_error(self, message: str):
        """Show error message"""
        error_label = self.query_one("#error-message")
        error_label.update(f"[bold red]{message}[/bold red]")
        error_label.remove_class("error-hidden")
        error_label.add_class("error-visible")
    
    def hide_error(self):
        """Hide error message"""
        error_label = self.query_one("#error-message")
        error_label.update("")
        error_label.remove_class("error-visible")
        error_label.add_class("error-hidden")
    
    def show_loading(self):
        """Show loading indicator"""
        self.query_one("#loading").remove_class("loading-hidden")
        self.query_one("#loading").add_class("loading-visible")
        self.query_one("#submit-button").disabled = True
        self.query_one("#register-button").disabled = True
        self.is_loading = True
    
    def hide_loading(self):
        """Hide loading indicator"""
        self.query_one("#loading").remove_class("loading-visible")
        self.query_one("#loading").add_class("loading-hidden")
        self.query_one("#submit-button").disabled = False
        self.query_one("#register-button").disabled = False
        self.is_loading = False
    
    async def handle_login(self):
        """Handle login form submission"""
        if self.is_loading:
            return
        
        # Get form values
        username = self.query_one("#username").value.strip()
        password = self.query_one("#password").value
        
        # Validate inputs
        if not username:
            self.show_error("Username is required")
            self.query_one("#username").focus()
            return
        
        if not password:
            self.show_error("Password is required")
            self.query_one("#password").focus()
            return
        
        # Hide any previous errors
        self.hide_error()
        
        # Show loading
        self.show_loading()
        
        try:
            # Attempt login
            user_data = await self.auth_service.login(username, password)
            
            # Post success message
            self.post_message(self.LoginSuccess(user_data))
            
        except Exception as e:
            self.hide_loading()
            error_msg = str(e)
            
            # Parse common Supabase error messages
            if "invalid" in error_msg.lower() and ("credentials" in error_msg.lower() or "password" in error_msg.lower()):
                self.show_error("Invalid email or password")
            elif "not confirmed" in error_msg.lower():
                self.show_error("Please confirm your email before logging in")
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                self.show_error("Connection error: Please check your internet connection")
            else:
                # Show the actual error message from Supabase
                if "Login failed:" in error_msg:
                    self.show_error(error_msg.replace("Login failed: ", ""))
                else:
                    self.show_error(f"Login failed: {error_msg}")
    
    LOGO = """
███████╗███╗   ██╗████████╗██╗  ██╗
██╔════╝████╗  ██║╚══██╔══╝╚██╗██╔╝
█████╗  ██╔██╗ ██║   ██║    ╚███╔╝ 
██╔══╝  ██║╚██╗██║   ██║    ██╔██╗ 
██║     ██║ ╚████║   ██║   ██╔╝ ██╗
╚═╝     ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝
"""


MATRIX_LOGIN_CSS = """
MatrixLoginScreen {
    background: black;
}

/* Container for both widgets */
#main-container {
    width: 100%;
    height: 100%;
}

/* Matrix fills the container */
#matrix-rain {
    width: 100%;
    height: 100%;
}

/* Login form positioned in center */
#login-form {
    position: absolute;
    width: 60;
    height: auto;
    min-height: 35;
    background: rgba(0, 0, 0, 0.5);
    border: double #00ff00;
    padding: 2;
    align: center middle;
    offset: 120% 30%;
    margin: 30 -30;
}

#logo {
    height: 6;
    text-align: center;
    margin-bottom: 1;
    width: 100%;
}

#title {
    height: 3;
    text-align: center;
    margin-bottom: 2;
    width: 100%;
}

.glow-input {
    width: 40;
    margin: 1;
    align: center middle;
}

#error-message {
    width: 100%;
    height: 2;
    text-align: center;
    margin-bottom: 1;
}

.error-hidden {
    display: none;
}

.error-visible {
    display: block;
    color: #ff0000;
}

#loading {
    width: 100%;
    height: 3;
    align: center middle;
}

.loading-hidden {
    display: none;
}

.loading-visible {
    display: block;
}

#button-container {
    width: 100%;
    height: 3;
    align: center middle;
    margin-top: 2;
}

#submit-button {
    width: 12;
    margin-right: 2;
    align: center middle;
}

#register-button {
    width: 16;
    align: center middle;
}
"""


class TestApp(App):
    """Test application"""
    
    # Disable mouse tracking to prevent ANSI codes in output
    ENABLE_COMMAND_PALETTE = False
    
    def capture_mouse(self, widget):
        """Override capture_mouse to prevent mouse tracking"""
        pass
    
    def release_mouse(self):
        """Override release_mouse to prevent mouse tracking"""
        pass
    
    def on_mount(self):
        self.push_screen(MatrixLoginScreen())


if __name__ == "__main__":
    # Disable mouse tracking to prevent ANSI codes
    import os
    os.environ['TEXTUAL_MOUSE'] = '0'
    os.environ['TERM'] = 'linux'  # Use a terminal that doesn't support mouse
    
    # Disable terminal mouse mode directly
    import sys
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        # Send escape sequence to disable mouse tracking
        sys.stdout.write('\033[?1000l')  # Disable mouse tracking
        sys.stdout.write('\033[?1002l')  # Disable cell motion tracking
        sys.stdout.write('\033[?1003l')  # Disable all motion tracking
        sys.stdout.flush()
    
    print("Testing combined matrix rain with login form...")
    print("You should see:")
    print("1. Falling green matrix characters across the entire screen")
    print("2. Login form centered on top with slight transparency")
    print("3. FNTX logo and form fields")
    app = TestApp()
    app.run(mouse=False)