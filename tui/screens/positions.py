"""
Positions Screen - Interactive positions management
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, DataTable, Label, Button
from textual.widget import Widget
from textual.binding import Binding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from ...commands.positions import get_mock_positions, calculate_summary
from ...ui.colors import style_pnl


class PositionsScreen(Widget):
    """Positions screen with interactive table"""
    
    BINDINGS = [
        Binding("enter", "select_position", "Select"),
        Binding("c", "close_position", "Close"),
        Binding("s", "set_stop", "Set Stop"),
        Binding("r", "refresh", "Refresh"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create positions layout"""
        with Vertical():
            yield PositionsHeader()
            yield PositionsTable()
            yield PositionsSummary()
            
            
class PositionsHeader(Static):
    """Header for positions screen"""
    
    def compose(self) -> ComposeResult:
        """Create header"""
        yield Label("[bold cyan]ACTIVE POSITIONS (USD)[/bold cyan]", id="positions-title")
        
    def on_mount(self) -> None:
        """Style the header"""
        self.styles.height = 3
        self.styles.width = "100%"
        self.styles.text_align = "center"
        self.styles.padding = 1
        

class PositionsTable(Static):
    """Interactive positions table"""
    
    def compose(self) -> ComposeResult:
        """Create the data table"""
        yield DataTable(id="positions-table")
        
    def on_mount(self) -> None:
        """Initialize the table"""
        self.styles.height = "70%"
        table = self.query_one("#positions-table", DataTable)
        
        # Add columns
        table.add_column("Strike", key="strike")
        table.add_column("Type", key="type")
        table.add_column("Qty", key="qty")
        table.add_column("Entry", key="entry")
        table.add_column("Current", key="current")
        table.add_column("P&L", key="pnl")
        table.add_column("Stop", key="stop")
        table.add_column("Status", key="status")
        
        # Style the table
        table.zebra_stripes = True
        table.cursor_type = "row"
        table.show_cursor = True
        
        # Load data
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh positions data"""
        positions = get_mock_positions()
        table = self.query_one("#positions-table", DataTable)
        
        # Clear existing rows
        table.clear()
        
        # Add positions
        for pos in positions:
            # Determine status
            if pos['stop'] is None:
                status = "⚠ UNPROTECTED"
                status_style = "yellow"
            elif pos['pnl'] > 0:
                status = "✓ PROFIT"
                status_style = "green"
            elif pos['pnl'] < 0:
                status = "✗ LOSS"
                status_style = "red"
            else:
                status = "ACTIVE"
                status_style = "white"
                
            # Format values
            stop_text = f"${pos['stop']:.2f}" if pos['stop'] else "NONE"
            pnl_text = style_pnl(pos['pnl'])
            
            # Add row
            table.add_row(
                str(pos['strike']),
                pos['type'],
                str(pos['qty']),
                f"${pos['entry']:.2f}",
                f"${pos['current']:.2f}",
                pnl_text,
                stop_text,
                f"[{status_style}]{status}[/]",
                key=f"pos_{pos['strike']}_{pos['type']}"
            )
            
    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection"""
        self.notify(f"Selected position: {event.row_key}")


class PositionsSummary(Static):
    """Summary panel for positions"""
    
    def compose(self) -> ComposeResult:
        """Create summary panel"""
        yield Static(id="positions-summary-content")
        
    def on_mount(self) -> None:
        """Initialize summary"""
        self.styles.height = 10
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh summary data"""
        positions = get_mock_positions()
        summary = calculate_summary(positions)
        
        # Create summary text
        text = Text()
        text.append("═" * 60 + "\n", style="cyan")
        text.append("SUMMARY\n", style="bold cyan")
        text.append("─" * 60 + "\n", style="cyan")
        
        # Summary stats
        text.append(f"Total Positions: {summary['positions_count']} ", style="white")
        text.append(f"({summary['call_qty']}C, {summary['put_qty']}P)\n", style="white")
        
        text.append("Total P&L (USD): ", style="white")
        text.append(style_pnl(summary['total_pnl']) + "\n")
        
        text.append("Total P&L (HKD): ", style="white")
        text.append(style_pnl(summary['total_pnl_hkd']) + " (@ 7.7)\n")
        
        if summary['unprotected'] > 0:
            text.append(f"\n⚠ WARNING: {summary['unprotected']} UNPROTECTED POSITIONS\n", style="bold yellow")
            text.append("Consider adding stop losses to protect against adverse moves.", style="dim yellow")
            
        # Performance indicator
        if summary['total_pnl'] > 0:
            text.append("\n✓ Performance: Profitable session!", style="green")
        elif summary['total_pnl'] < 0:
            text.append("\n✗ Performance: Currently in drawdown", style="red")
        else:
            text.append("\n• Performance: Break-even", style="white")
            
        panel = Panel(text, border_style="cyan", box=box.ROUNDED)
        self.query_one("#positions-summary-content").update(panel)