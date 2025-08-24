"""
Welcome Screen - Simple landing page after successful login
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Label, Button
from textual.containers import Container, Vertical, Horizontal, Center, Middle
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from ..services.auth_service import get_auth_service


class WelcomeScreen(Screen):
    """Simple welcome screen after login"""
    
    BINDINGS = [
        Binding("escape", "logout", "Logout (ESC)"),
        Binding("q", "quit", "Quit (Q)"),
        Binding("l", "logout", "Logout (L)"),
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
                        # ASCII Art Header
                        yield Static(
                            "[bold cyan]╔════════════════════════════════════════╗[/bold cyan]\n"
                            "[bold cyan]║[/bold cyan]      [bold green]FNTX TRADING TERMINAL[/bold green]        [bold cyan]║[/bold cyan]\n"
                            "[bold cyan]╚════════════════════════════════════════╝[/bold cyan]",
                            id="header-art"
                        )
                        
                        # Welcome message
                        yield Label(
                            f"\n[bold green]Welcome, {username}![/bold green]",
                            id="welcome-message"
                        )
                        
                        # Connection status
                        yield Label(
                            "[cyan]✓ Connected to Supabase[/cyan]",
                            id="connection-status"
                        )
                        
                        # Instructions Panel
                        instructions_text = Text()
                        instructions_text.append("Navigation Keys\n", style="bold yellow")
                        instructions_text.append("─" * 20 + "\n", style="dim cyan")
                        instructions_text.append("ESC or L", style="bold white")
                        instructions_text.append(" - Logout\n", style="cyan")
                        instructions_text.append("Q       ", style="bold white")
                        instructions_text.append(" - Quit App\n", style="cyan")
                        
                        panel = Panel(
                            instructions_text,
                            border_style="cyan",
                            title="[bold]Controls[/bold]",
                            width=30
                        )
                        yield Static(panel, id="instructions-panel")
                        
                        # Buttons for mouse users
                        with Horizontal(id="button-container"):
                            yield Button("Logout", variant="warning", id="logout-btn")
                            yield Button("Quit", variant="error", id="quit-btn")
                        
                        # Status footer
                        yield Label(
                            "\n[dim cyan]Session Active | Ready for Trading Functions[/dim cyan]",
                            id="status-footer"
                        )
    
    def on_button_pressed(self, event):
        """Handle button clicks"""
        button_id = event.button.id
        if button_id == "logout-btn":
            self.action_logout()
        elif button_id == "quit-btn":
            self.action_quit()
    
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
    background: #0a0a0a;
}

#welcome-container {
    width: 100%;
    height: 100%;
    background: #0a0a0a;
}

#welcome-content {
    align: center middle;
    width: auto;
    height: auto;
    padding: 2;
}

#header-art {
    text-align: center;
    width: 100%;
    margin-bottom: 2;
}

#welcome-message {
    text-align: center;
    width: 100%;
    height: 2;
    content-align: center middle;
    margin-bottom: 1;
}

#connection-status {
    text-align: center;
    width: 100%;
    height: 2;
    content-align: center middle;
    margin-bottom: 2;
}

#instructions-panel {
    align: center middle;
    margin-bottom: 2;
}

#button-container {
    align: center middle;
    width: auto;
    height: 3;
    margin-top: 1;
}

#logout-btn {
    margin-right: 2;
    width: 12;
    background: #ff6b00;
}

#quit-btn {
    width: 12;
    background: #ff0000;
}

#status-footer {
    text-align: center;
    width: 100%;
    margin-top: 2;
}
"""