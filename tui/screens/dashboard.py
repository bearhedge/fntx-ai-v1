"""
Dashboard Screen - Main overview of trading status
"""
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, DataTable, Label
from textual.screen import Screen
from textual.widget import Widget
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# from ...commands.status import get_mock_market_data
# from ...commands.positions import get_mock_positions

# Mock data for testing
def get_mock_market_data():
    return {
        "spy_price": 542.35,
        "vix": 16.24,
        "market_status": "OPEN"
    }

def get_mock_positions():
    return []
# from ...ui.charts import create_vix_chart
# from ...ui.colors import style_pnl

def create_vix_chart():
    return "VIX Chart Placeholder"

def style_pnl(value):
    return f"${value:.2f}"


class DashboardScreen(Screen):
    """Main dashboard screen showing overview"""
    
    def compose(self) -> ComposeResult:
        """Create dashboard layout"""
        with Grid():
            yield MarketOverviewPanel()
            yield AccountSummaryPanel()
            yield AlertsPanel()
            yield RecentPositionsPanel()
            yield VIXChartPanel()
            
    def on_mount(self) -> None:
        """Set up the grid layout"""
        grid = self.query_one(Grid)
        grid.styles.grid_columns = "1fr 1fr 1fr"
        grid.styles.grid_rows = "1fr 1fr 1fr"
        grid.styles.gap = 1
        grid.styles.height = "100%"
        

class MarketOverviewPanel(Static):
    """Market overview panel"""
    
    def compose(self) -> ComposeResult:
        """Create the panel content"""
        yield Static(id="market-overview-content")
        
    def on_mount(self) -> None:
        """Initialize panel"""
        self.styles.column_span = 1
        self.styles.row_span = 1
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh market data"""
        data = get_mock_market_data()
        
        table = Table(title="Market Overview", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("SPY Price", f"${data['spy_price']:.2f}")
        table.add_row("Change", f"+{data['spy_price'] * 0.012:.2f} (+1.2%)")
        table.add_row("Volume", "45.2M")
        table.add_row("VIX Level", f"{data['vix_level']:.1f}")
        
        panel = Panel(table, border_style="cyan")
        self.query_one("#market-overview-content").update(panel)
        

class AccountSummaryPanel(Static):
    """Account summary panel"""
    
    def compose(self) -> ComposeResult:
        """Create the panel content"""
        yield Static(id="account-summary-content")
        
    def on_mount(self) -> None:
        """Initialize panel"""
        self.styles.column_span = 1
        self.styles.row_span = 1
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh account data"""
        data = get_mock_market_data()
        
        table = Table(title="Account Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Positions", str(data['positions_count']))
        table.add_row("Total P&L", style_pnl(data['total_pnl']))
        table.add_row("Win Rate", f"{data['win_rate']:.1f}%")
        table.add_row("Capital", f"${data['capital'] / 7.7:.0f}")  # Convert HKD to USD
        
        panel = Panel(table, border_style="cyan")
        self.query_one("#account-summary-content").update(panel)


class AlertsPanel(Static):
    """Alerts and warnings panel"""
    
    def compose(self) -> ComposeResult:
        """Create the panel content"""
        yield Static(id="alerts-content")
        
    def on_mount(self) -> None:
        """Initialize panel"""
        self.styles.column_span = 1
        self.styles.row_span = 1
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh alerts"""
        text = Text()
        text.append("⚠ 3 Mandates\n", style="yellow")
        text.append("  Out of\n", style="yellow")
        text.append("  Compliance\n", style="yellow")
        text.append("\n")
        text.append("! Check Risk\n", style="red")
        text.append("  Manager", style="red")
        
        panel = Panel(text, title="Alerts", border_style="yellow")
        self.query_one("#alerts-content").update(panel)


class RecentPositionsPanel(Static):
    """Recent positions panel"""
    
    def compose(self) -> ComposeResult:
        """Create the panel content"""
        yield Static(id="positions-content")
        
    def on_mount(self) -> None:
        """Initialize panel"""
        self.styles.column_span = 3
        self.styles.row_span = 1
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh positions data"""
        positions = get_mock_positions()[:3]  # Show top 3
        
        table = Table(title="Recent Positions", box=box.ROUNDED)
        table.add_column("Strike", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Qty", style="white")
        table.add_column("Entry", style="white")
        table.add_column("Current", style="white")
        table.add_column("P&L", style="white")
        table.add_column("Status", style="white")
        
        for pos in positions:
            status = "ACTIVE" if pos['pnl'] == 0 else ("PROFIT" if pos['pnl'] > 0 else "LOSS")
            status_color = "white" if pos['pnl'] == 0 else ("green" if pos['pnl'] > 0 else "red")
            
            # Special warning for unprotected positions
            if pos['stop'] is None:
                status = "⚠ NO STOP"
                status_color = "yellow"
                
            table.add_row(
                str(pos['strike']),
                pos['type'],
                str(pos['qty']),
                f"${pos['entry']:.2f}",
                f"${pos['current']:.2f}",
                style_pnl(pos['pnl']),
                f"[{status_color}]{status}[/]"
            )
        
        panel = Panel(table, border_style="cyan")
        self.query_one("#positions-content").update(panel)


class VIXChartPanel(Static):
    """VIX trend chart panel"""
    
    def compose(self) -> ComposeResult:
        """Create the panel content"""
        yield Static(id="vix-chart-content")
        
    def on_mount(self) -> None:
        """Initialize panel"""
        self.styles.column_span = 3
        self.styles.row_span = 1
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh VIX chart"""
        # Get mock VIX data
        vix_data = [16, 16, 15, 15, 16, 17, 18, 19, 20, 20, 21, 20, 19, 20]
        
        # Create chart
        chart_lines = create_vix_chart(vix_data)
        
        text = Text()
        text.append("VIX Trend (72H)\n", style="bold cyan")
        text.append("Current: 20.4 Risk: ", style="white")
        text.append("✗\n\n", style="red")
        
        for line in chart_lines:
            text.append(line + "\n", style="cyan")
            
        panel = Panel(text, border_style="cyan")
        self.query_one("#vix-chart-content").update(panel)


# Dashboard CSS
DASHBOARD_CSS = """
DashboardScreen {
    background: black;
}

.market-status {
    height: 3;
    border: solid cyan;
    margin: 1;
}

.positions-panel {
    height: 10;
    border: solid green;
    margin: 1;
}

.vix-chart {
    height: 10;
    border: solid cyan;
    margin: 1;
}
"""