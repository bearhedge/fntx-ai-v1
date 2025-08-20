"""
Matrix Login Screen for FNTX Terminal

Cyberpunk-themed authentication screen with Matrix rain effect.
"""

import random
import string
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.reactive import reactive
from textual import work
import asyncio

class MatrixRain(Static):
    """Matrix rain effect widget."""
    
    rain_chars = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    
    def __init__(self, width: int = 80, height: int = 20):
        super().__init__("")
        self.width = width
        self.height = height
        self.columns = []
        self.init_rain()
    
    def init_rain(self):
        """Initialize rain columns."""
        self.columns = []
        for _ in range(self.width):
            column = {
                'chars': [' '] * self.height,
                'position': random.randint(-self.height, 0),
                'speed': random.uniform(0.5, 2.0),
                'length': random.randint(5, 15)
            }
            self.columns.append(column)
    
    def update_rain(self):
        """Update rain animation."""
        for col in self.columns:
            # Move column down
            col['position'] += col['speed']
            
            # Reset if off screen
            if col['position'] > self.height + col['length']:
                col['position'] = -col['length']
                col['speed'] = random.uniform(0.5, 2.0)
                col['length'] = random.randint(5, 15)
            
            # Update characters
            for i in range(self.height):
                if col['position'] - col['length'] < i < col['position']:
                    # Character in the rain trail
                    brightness = 1.0 - (col['position'] - i) / col['length']
                    if brightness > 0.8:
                        col['chars'][i] = random.choice(self.rain_chars)
                else:
                    col['chars'][i] = ' '
    
    def render_rain(self) -> str:
        """Render the rain effect."""
        self.update_rain()
        
        lines = []
        for y in range(self.height):
            line = ""
            for x in range(min(self.width, len(self.columns))):
                char = self.columns[x]['chars'][y]
                if char != ' ':
                    # Apply green color gradient
                    pos = self.columns[x]['position']
                    if y == int(pos):
                        # Brightest at the head
                        line += f"[bold bright_green]{char}[/]"
                    elif y > pos - 3:
                        line += f"[green]{char}[/]"
                    else:
                        line += f"[dark_green]{char}[/]"
                else:
                    line += " "
            lines.append(line)
        
        return "\n".join(lines)

class MatrixLoginScreen(Screen):
    """Matrix-themed login screen."""
    
    CSS = """
    MatrixLoginScreen {
        align: center middle;
        background: #0a0a0a;
    }
    
    #matrix-rain {
        width: 100%;
        height: 100%;
        color: #00ff41;
        opacity: 0.3;
    }
    
    #login-container {
        width: 60;
        height: 24;
        background: rgba(10, 10, 10, 0.95);
        border: thick $primary;
        padding: 2;
    }
    
    #title {
        text-align: center;
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #logo {
        text-align: center;
        color: $primary;
        margin-bottom: 2;
    }
    
    Input {
        margin: 1 0;
        background: #1a1a2e;
        border: tall $primary;
        color: $primary;
    }
    
    Input:focus {
        border: tall $accent;
    }
    
    Button {
        width: 100%;
        margin-top: 2;
        background: $primary;
        color: $background;
        text-style: bold;
    }
    
    Button:hover {
        background: $accent;
    }
    
    #demo-notice {
        text-align: center;
        color: $warning;
        margin-top: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.matrix_rain = MatrixRain(width=120, height=30)
        self.auto_update_rain.start()
    
    def compose(self) -> ComposeResult:
        """Create login screen layout."""
        # Background matrix rain
        yield Static(id="matrix-rain")
        
        # Login form container
        with Container(id="login-container"):
            yield Label("FNTX TRADING TERMINAL", id="title")
            yield Static(self._get_logo(), id="logo")
            
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", password=True, id="password")
            
            yield Button("ENTER THE MATRIX", variant="primary", id="login-btn")
            
            # Demo mode notice
            from ..config import get_config
            if get_config().mode == "demo":
                yield Label("[Demo Mode - Press Enter to Continue]", id="demo-notice")
    
    def _get_logo(self) -> str:
        """Get ASCII art logo."""
        return """╔═╗╔╗╔╔╦╗═╗ ╦
╠╣ ║║║ ║ ╔╩╦╝
╚  ╝╚╝ ╩ ╩ ╚═"""
    
    @work(exclusive=True)
    async def auto_update_rain(self):
        """Auto-update matrix rain effect."""
        rain_widget = self.query_one("#matrix-rain", Static)
        while True:
            rain_widget.update(self.matrix_rain.render_rain())
            await asyncio.sleep(0.1)
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle login button press."""
        if event.button.id == "login-btn":
            await self.do_login()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input fields."""
        if event.input.id == "password":
            await self.do_login()
    
    async def do_login(self) -> None:
        """Perform login (demo mode just continues)."""
        from ..config import get_config
        
        if get_config().mode == "demo":
            # In demo mode, just go to dashboard
            self.app.on_login_success("demo_user")
        else:
            # In live mode, would validate credentials
            username = self.query_one("#username", Input).value
            password = self.query_one("#password", Input).value
            
            if username and password:
                # For now, accept any credentials in live mode
                self.app.on_login_success(username)
            else:
                # Show error (would be a notification in full version)
                pass