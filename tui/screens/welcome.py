"""
Welcome Screen - Simple landing page after successful login
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Label
from textual.containers import Container, Vertical, Center, Middle
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from ..services.auth_service import get_auth_service


class WelcomeScreen(Screen):
    """Simple welcome screen after login"""
    
    BINDINGS = [
        Binding("escape", "logout", "Logout"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self.auth_service = get_auth_service()
    
    def compose(self) -> ComposeResult:
        """Create the welcome screen layout"""
        username = self.auth_service.get_username() or "User"
        
        with Container(id="welcome-container"):
            with Center():
                with Middle():
                    with Vertical(id="welcome-content"):
                        # Welcome message
                        yield Label(
                            f"[bold green]Welcome, {username}![/bold green]",
                            id="welcome-message"
                        )
                        
                        # Connection status
                        yield Label(
                            "[cyan]✓ Connected to Supabase[/cyan]",
                            id="connection-status"
                        )
                        
                        # Instructions
                        yield Label(
                            "\n[dim]Press ESC to logout | Press Q to quit[/dim]",
                            id="instructions"
                        )
                        
                        # Simple status panel
                        status_text = Text()
                        status_text.append("System Status\n", style="bold cyan")
                        status_text.append("─" * 30 + "\n", style="dim")
                        status_text.append("Authentication: ", style="white")
                        status_text.append("Active\n", style="green")
                        status_text.append("User: ", style="white")
                        status_text.append(f"{username}\n", style="yellow")
                        status_text.append("Session: ", style="white")
                        status_text.append("Valid\n", style="green")
                        
                        panel = Panel(
                            Align.center(status_text),
                            border_style="green",
                            width=40
                        )
                        yield Static(panel, id="status-panel")
    
    def action_logout(self):
        """Logout and return to login screen"""
        from .matrix_login_final import MatrixLoginScreen
        
        # Clear the session
        self.auth_service.logout()
        
        # Pop this screen and show login
        self.app.pop_screen()
        self.app.push_screen(MatrixLoginScreen())
    
    def action_quit(self):
        """Quit the application"""
        self.app.exit()


# CSS for the welcome screen
WELCOME_CSS = """
WelcomeScreen {
    background: black;
}

#welcome-container {
    width: 100%;
    height: 100%;
    background: black;
}

#welcome-content {
    align: center middle;
    width: auto;
    height: auto;
    padding: 2;
}

#welcome-message {
    text-align: center;
    width: 100%;
    height: 3;
    content-align: center middle;
    margin-bottom: 1;
}

#connection-status {
    text-align: center;
    width: 100%;
    height: 2;
    content-align: center middle;
    margin-bottom: 1;
}

#instructions {
    text-align: center;
    width: 100%;
    height: 3;
    content-align: center middle;
    margin-bottom: 2;
}

#status-panel {
    align: center middle;
    margin-top: 2;
}
"""