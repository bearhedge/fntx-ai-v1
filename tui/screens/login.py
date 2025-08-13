"""
Login Screen - Matrix-themed psychedelic login interface
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Center, Middle
from textual.widgets import Static, Label, Button
from textual.screen import Screen
from textual.binding import Binding
from textual import events
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from datetime import datetime
import random
import math

from ..effects.matrix_rain import MatrixRainEffect
from ..widgets.glow_input import GlowInput, PsychedelicButton


class LoginScreen(Screen):
    """Matrix-themed login screen with psychedelic effects"""
    
    BINDINGS = [
        Binding("enter", "submit", "Login", priority=True),
        Binding("tab", "next_field", "Next Field"),
        Binding("shift+tab", "previous_field", "Previous Field"),
        Binding("escape", "toggle_mode", "Switch Mode"),
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
    ]
    
    # ASCII Art FNTX Logo
    FNTX_LOGO = """
███████╗███╗   ██╗████████╗██╗  ██╗
██╔════╝████╗  ██║╚══██╔══╝╚██╗██╔╝
█████╗  ██╔██╗ ██║   ██║    ╚███╔╝ 
██╔══╝  ██║╚██╗██║   ██║    ██╔██╗ 
██║     ██║ ╚████║   ██║   ██╔╝ ██╗
╚═╝     ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝
"""
    
    def __init__(self):
        super().__init__()
        self.login_mode = True  # True for login, False for register
        self.logo_phase = 0.0
        self.last_update = datetime.now()
        
    def compose(self) -> ComposeResult:
        """Create the login screen layout"""
        # Container with layers for proper z-ordering
        with Container(id="main-container"):
            # Matrix rain background - fills entire screen on background layer
            yield MatrixRainEffect(id="matrix-rain")
            
            # Login form overlay container on foreground layer
            with Container(id="login-overlay"):
                # Center the login form within the overlay
                with Center(id="login-wrapper"):
                    with Container(id="login-container"):
                        # Logo with pulsing effect
                        yield Static(id="logo", classes="logo")
                        
                        # Title
                        yield Label(id="title", classes="title")
                        
                        # Login form
                        with Vertical(id="form-container"):
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
                            
                            # Email field for registration (hidden by default)
                            yield GlowInput(
                                placeholder="Enter Email",
                                id="email",
                                classes="glow-input hidden"
                            )
                            
                            with Horizontal(id="button-container"):
                                yield PsychedelicButton(
                                    "ENTER THE TRADING MATRIX",
                                    id="submit-button"
                                )
                                
                        # Mode toggle
                        yield Label(
                            "[cyan]Press ESC to switch mode[/cyan]",
                            id="mode-hint",
                            classes="hint"
                        )
                    
    def on_mount(self):
        """Initialize the login screen"""
        self.update_logo()
        self.update_title()
        self.set_interval(0.1, self.animate_logo)
        
        # Focus username field
        self.query_one("#username").focus()
        
    def animate_logo(self):
        """Animate the logo with pulsing effect"""
        now = datetime.now()
        delta_time = (now - self.last_update).total_seconds()
        self.last_update = now
        
        self.logo_phase += delta_time * 2
        self.update_logo()
        
    def update_logo(self):
        """Update logo with rainbow effect"""
        logo_widget = self.query_one("#logo")
        
        # Calculate color based on phase
        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
        color_idx = int(self.logo_phase) % len(colors)
        color = colors[color_idx]
        
        # Apply pulsing scale effect
        scale = 1.0 + 0.1 * abs(math.sin(self.logo_phase))
        
        # Create styled logo
        styled_logo = Text()
        for line in self.FNTX_LOGO.strip().split('\n'):
            styled_logo.append(line, style=f"bold {color}")
            styled_logo.append('\n')
            
        logo_widget.update(Align.center(styled_logo))
        
    def update_title(self):
        """Update title based on mode"""
        title_widget = self.query_one("#title")
        if self.login_mode:
            title_text = "[bold cyan]FNTX TRADING TERMINAL[/bold cyan]\n[dim]Press ENTER to continue[/dim]"
        else:
            title_text = "[bold magenta]JOIN THE FNTX NETWORK[/bold magenta]\n[dim]Create your account[/dim]"
            
        title_widget.update(Align.center(Text(title_text)))
        
    def action_submit(self):
        """Handle form submission"""
        username = self.query_one("#username").value
        password = self.query_one("#password").value
        
        if not self.login_mode:
            email = self.query_one("#email").value
            if not email:
                self.notify("Email required for registration", severity="error")
                return
                
        if not username or not password:
            self.notify("Username and password required", severity="error")
            return
            
        # For demo, accept any credentials
        if self.login_mode:
            self.notify(f"Welcome to the Matrix, {username}", severity="success")
        else:
            self.notify(f"Registration successful, {username}", severity="success")
            
        # Transition to main app
        self.app.action_show_dashboard()
        
    def action_toggle_mode(self):
        """Toggle between login and register mode"""
        self.login_mode = not self.login_mode
        self.update_title()
        
        # Toggle email field visibility
        email_field = self.query_one("#email")
        if self.login_mode:
            email_field.add_class("hidden")
        else:
            email_field.remove_class("hidden")
            
        # Update button text
        button = self.query_one("#submit-button")
        if self.login_mode:
            button.label = "ENTER THE MATRIX"
        else:
            button.label = "JOIN THE RESISTANCE"
        button.value = button.label
        
        # Update matrix rain effect
        matrix = self.query_one("#matrix-rain", MatrixRainEffect)
        if not self.login_mode:
            matrix.change_characters("binary")  # More ominous for registration
        else:
            matrix.change_characters("mixed")
            
    def action_quit(self):
        """Quit the application"""
        self.app.exit()
            
    def action_next_field(self):
        """Move to next input field"""
        focused = self.app.focused
        if focused and focused.id == "username":
            self.query_one("#password").focus()
        elif focused and focused.id == "password":
            if not self.login_mode:
                self.query_one("#email").focus()
            else:
                self.query_one("#submit-button").focus()
        elif focused and focused.id == "email":
            self.query_one("#submit-button").focus()
            
    def action_previous_field(self):
        """Move to previous input field"""
        focused = self.app.focused
        if focused and focused.id == "password":
            self.query_one("#username").focus()
        elif focused and focused.id == "email":
            self.query_one("#password").focus()
        elif focused and focused.id == "submit-button":
            if not self.login_mode:
                self.query_one("#email").focus()
            else:
                self.query_one("#password").focus()


# CSS Styles for the login screen
LOGIN_CSS = """
LoginScreen {
    background: black;
}

#main-container {
    width: 100%;
    height: 100%;
}

#matrix-rain {
    width: 100%;
    height: 100%;
}

#login-overlay {
    width: 100%;
    height: 100%;
}

#login-wrapper {
    width: 100%;
    height: 100%;
    align: center middle;
}

#login-container {
    background: rgba(0, 0, 0, 0.85);
    border: double #00ff00;
    padding: 2;
    width: 60;
    height: auto;
    min-height: 30;
    max-height: 40;
}

.logo {
    height: 6;
    margin-bottom: 1;
}

.title {
    height: 3;
    text-align: center;
    margin-bottom: 2;
}

#form-container {
    width: 100%;
    height: auto;
    align: center middle;
}

.glow-input {
    width: 40;
    margin: 1;
}

.hidden {
    display: none;
}

#button-container {
    width: 100%;
    height: 3;
    align: center middle;
    margin-top: 2;
}

#submit-button {
    width: 30;
}

.hint {
    width: 100%;
    text-align: center;
    margin-top: 2;
}
"""