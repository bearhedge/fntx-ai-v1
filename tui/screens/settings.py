"""
Settings Screen - Configure application settings
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Label, Button, Input, Switch
from textual.widget import Widget
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from ...commands.config import load_config, save_config, DEFAULT_CONFIG


class SettingsScreen(Widget):
    """Settings configuration screen"""
    
    def compose(self) -> ComposeResult:
        """Create settings layout"""
        with Vertical():
            yield Label("[bold cyan]SETTINGS & CONFIGURATION[/bold cyan]", id="settings-title")
            yield APISettingsPanel()
            yield TradingSettingsPanel()
            yield UISettingsPanel()
            with Horizontal(id="settings-buttons"):
                yield Button("Save Settings", id="save-button", variant="primary")
                yield Button("Reset Defaults", id="reset-button", variant="warning")
                
    def on_mount(self) -> None:
        """Initialize settings screen"""
        self.query_one("#settings-title").styles.text_align = "center"
        self.query_one("#settings-title").styles.padding = 1
        self.query_one("#settings-buttons").styles.padding = 1
        self.query_one("#settings-buttons").styles.align = ("center", "middle")
        

class APISettingsPanel(Static):
    """API configuration panel"""
    
    def compose(self) -> ComposeResult:
        """Create API settings"""
        yield Static(id="api-settings-content")
        
    def on_mount(self) -> None:
        """Initialize API settings"""
        self.styles.height = 12
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Load and display API settings"""
        config = load_config()
        api_config = config.get('api', {})
        
        table = Table(title="API Configuration", box=box.ROUNDED)
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Connection", style="dim white")
        
        # Theta Terminal
        theta = api_config.get('theta_terminal', {})
        theta_status = "[green]Enabled[/]" if theta.get('enabled') else "[red]Disabled[/]"
        theta_conn = f"{theta.get('host')}:{theta.get('port')}" if theta.get('enabled') else "N/A"
        table.add_row("Theta Terminal", theta_status, theta_conn)
        
        # IBKR
        ibkr = api_config.get('ibkr', {})
        ibkr_status = "[green]Enabled[/]" if ibkr.get('enabled') else "[red]Disabled[/]"
        ibkr_conn = f"{ibkr.get('host')}:{ibkr.get('port')}" if ibkr.get('enabled') else "N/A"
        table.add_row("IBKR Gateway", ibkr_status, ibkr_conn)
        
        # Database
        db = api_config.get('database', {})
        db_status = "[green]Enabled[/]" if db.get('enabled') else "[red]Disabled[/]"
        db_conn = f"{db.get('user')}@{db.get('host')}:{db.get('port')}" if db.get('enabled') else "N/A"
        table.add_row("Database", db_status, db_conn)
        
        panel = Panel(table, border_style="cyan")
        self.query_one("#api-settings-content").update(panel)


class TradingSettingsPanel(Static):
    """Trading parameters panel"""
    
    def compose(self) -> ComposeResult:
        """Create trading settings"""
        yield Static(id="trading-settings-content")
        
    def on_mount(self) -> None:
        """Initialize trading settings"""
        self.styles.height = 10
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Load and display trading settings"""
        config = load_config()
        trading = config.get('trading', {})
        
        table = Table(title="Trading Parameters", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Default Quantity", str(trading.get('default_quantity', 1)))
        table.add_row("Max Position Size", str(trading.get('max_position_size', 10)))
        table.add_row("Stop Loss Multiplier", f"{trading.get('stop_loss_multiplier', 3.5)}x")
        table.add_row("Delta Limit", f"< {trading.get('delta_limit', 0.4)}")
        table.add_row("VIX Threshold", f"< {trading.get('vix_threshold', 20)}")
        
        panel = Panel(table, border_style="cyan")
        self.query_one("#trading-settings-content").update(panel)


class UISettingsPanel(Static):
    """UI preferences panel"""
    
    def compose(self) -> ComposeResult:
        """Create UI settings"""
        yield Static(id="ui-settings-content")
        
    def on_mount(self) -> None:
        """Initialize UI settings"""
        self.styles.height = 8
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Load and display UI settings"""
        config = load_config()
        ui = config.get('ui', {})
        
        table = Table(title="UI Preferences", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Theme", ui.get('theme', 'default'))
        table.add_row("Refresh Rate", f"{ui.get('refresh_rate', 3)}s")
        table.add_row("Monitor Layout", ui.get('monitor_layout', 'full'))
        table.add_row("Show ASCII Art", "Yes" if ui.get('show_ascii_art', True) else "No")
        
        panel = Panel(table, border_style="cyan")
        self.query_one("#ui-settings-content").update(panel)