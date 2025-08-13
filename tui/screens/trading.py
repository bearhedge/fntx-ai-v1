"""
Trading Screen - Execute trades with options chain
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, DataTable, Label, Button, Input
from textual.widget import Widget
from rich.panel import Panel
from rich.text import Text

from ...commands.trade import get_mock_options_chain
from ...ui.tables import create_options_chain_table


class TradingScreen(Widget):
    """Trading screen with options chain"""
    
    def compose(self) -> ComposeResult:
        """Create trading layout"""
        with Vertical():
            yield Label("[bold cyan]SPY OPTIONS TRADING[/bold cyan]", id="trading-title")
            yield OptionsChainPanel()
            yield TradingControls()
            yield Static(id="trade-status")
            
    def on_mount(self) -> None:
        """Initialize trading screen"""
        self.query_one("#trading-title").styles.text_align = "center"
        self.query_one("#trading-title").styles.padding = 1
        

class OptionsChainPanel(Static):
    """Options chain display"""
    
    def compose(self) -> ComposeResult:
        """Create options chain"""
        yield Static(id="options-chain-content")
        
    def on_mount(self) -> None:
        """Initialize options chain"""
        self.styles.height = "60%"
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh options chain data"""
        chain_data = get_mock_options_chain()
        
        # Create the options chain table using existing function
        table = create_options_chain_table(chain_data)
        
        # Convert Rich table to text for display
        panel = Panel(table, title="SPY 0DTE Options Chain", border_style="cyan")
        self.query_one("#options-chain-content").update(panel)


class TradingControls(Container):
    """Trading control panel"""
    
    def compose(self) -> ComposeResult:
        """Create trading controls"""
        with Vertical():
            with Container(classes="trading-inputs"):
                yield Label("Strike:")
                yield Input(placeholder="628", id="strike-input")
                yield Label("Side:")
                yield Input(placeholder="call/put", id="side-input")
                yield Label("Quantity:")
                yield Input(placeholder="1", id="qty-input", type="integer")
            yield Button("Execute Trade", id="execute-button", variant="primary")
            
    def on_mount(self) -> None:
        """Style the controls"""
        self.styles.height = 10
        self.styles.padding = 1
        
    def on_button_pressed(self, event) -> None:
        """Handle trade execution"""
        if event.button.id == "execute-button":
            strike = self.query_one("#strike-input", Input).value or "628"
            side = self.query_one("#side-input", Input).value or "call"
            qty = self.query_one("#qty-input", Input).value or "1"
            
            # Update status
            status = Text()
            status.append("✓ Trade Executed!\n", style="bold green")
            status.append(f"Sold {qty} SPY {strike} {side.upper()}\n", style="white")
            status.append("[Demo Mode - No real trade placed]", style="dim yellow")
            
            panel = Panel(status, border_style="green")
            self.app.query_one("#trade-status").update(panel)