"""
Risk Manager Screen - Mandates and compliance monitoring
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Label, ProgressBar
from textual.widget import Widget
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from ...commands.risk import get_mock_risk_data
from ...ui.charts import create_vix_chart
from ...ui.ascii_art import SYMBOLS


class RiskScreen(Widget):
    """Risk manager screen"""
    
    def compose(self) -> ComposeResult:
        """Create risk layout"""
        with Vertical():
            yield RiskHeader()
            with Grid():
                yield MandatesPanel()
                yield VIXPanel()
            yield ComplianceDetails()
            
            
class RiskHeader(Static):
    """Header showing risk score and compliance rate"""
    
    def compose(self) -> ComposeResult:
        """Create header"""
        yield Static(id="risk-header-content")
        
    def on_mount(self) -> None:
        """Initialize header"""
        self.styles.height = 5
        self.styles.width = "100%"
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh header data"""
        data = get_mock_risk_data()
        
        # Determine colors based on thresholds
        risk_color = "green" if data['risk_score'] < 0.5 else "yellow" if data['risk_score'] < 0.8 else "red"
        compliance_color = "green" if data['compliance_rate'] > 80 else "yellow" if data['compliance_rate'] > 60 else "red"
        
        text = Text()
        text.append("╔═══════════════════════════════════════════════════════════════════╗\n", style="cyan")
        text.append("║                        RISK MANAGER                               ║\n", style="bold cyan")
        text.append("╚═══════════════════════════════════════════════════════════════════╝\n", style="cyan")
        text.append("\n")
        text.append(f"Risk Score: [{risk_color}]{data['risk_score']:.2f}[/] | ", style="white")
        text.append(f"Compliance: [{compliance_color}]{data['compliance_rate']:.1f}%[/]", style="white")
        
        self.query_one("#risk-header-content").update(text)
        

class MandatesPanel(Static):
    """Trading mandates panel"""
    
    def compose(self) -> ComposeResult:
        """Create mandates panel"""
        yield Static(id="mandates-content")
        
    def on_mount(self) -> None:
        """Initialize panel"""
        self.styles.grid_column_span = 1
        self.styles.height = "100%"
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh mandates data"""
        data = get_mock_risk_data()
        
        table = Table(title="Mandates", box=box.ROUNDED)
        table.add_column("Mandate", style="cyan")
        table.add_column("Status", style="white")
        
        for mandate in data['mandates']:
            # Compliance symbol
            if mandate['compliant']:
                symbol = f"[green]{SYMBOLS['check']}[/green]"
            else:
                symbol = f"[red]{SYMBOLS['cross']}[/red]"
                
            # Format mandate
            mandate_text = f"{mandate['number']}. {mandate['label']}: {mandate['value']}"
            table.add_row(mandate_text, symbol)
            
        panel = Panel(table, border_style="cyan")
        self.query_one("#mandates-content").update(panel)
        

class VIXPanel(Static):
    """VIX trend panel"""
    
    def compose(self) -> ComposeResult:
        """Create VIX panel"""
        yield Static(id="vix-panel-content")
        
    def on_mount(self) -> None:
        """Initialize panel"""
        self.styles.grid_column_span = 1
        self.styles.height = "100%"
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh VIX data"""
        data = get_mock_risk_data()
        
        # Create VIX chart
        chart_lines = create_vix_chart(data['vix_data'])
        
        text = Text()
        text.append(f"VIX: {data['current_vix']} Risk: ", style="bold white")
        if data['current_vix'] < 20:
            text.append("✓\n\n", style="green")
        else:
            text.append("✗\n\n", style="red")
            
        for line in chart_lines:
            text.append(line + "\n", style="cyan")
            
        panel = Panel(text, title="VIX Trends (72H)", border_style="cyan", box=box.ROUNDED)
        self.query_one("#vix-panel-content").update(panel)
        

class ComplianceDetails(Static):
    """Detailed compliance information"""
    
    def compose(self) -> ComposeResult:
        """Create compliance details"""
        yield Static(id="compliance-content")
        
    def on_mount(self) -> None:
        """Initialize compliance details"""
        self.styles.height = 12
        self.refresh_data()
        
    def refresh_data(self) -> None:
        """Refresh compliance data"""
        data = get_mock_risk_data()
        
        text = Text()
        text.append("Compliance Details\n", style="bold cyan")
        text.append("─" * 50 + "\n", style="dim cyan")
        
        # Show non-compliant mandates with details
        non_compliant = [m for m in data['mandates'] if not m['compliant']]
        
        if non_compliant:
            for mandate in non_compliant:
                text.append(f"\n✗ {mandate['label']}: {mandate['value']}\n", style="red")
                
                # Add specific guidance
                if mandate['label'] == 'Stop Loss':
                    text.append("  → Add stop losses to all positions\n", style="dim yellow")
                elif mandate['label'] == 'Time Gate':
                    text.append("  → Wait for market to open\n", style="dim yellow")
                elif mandate['label'] == 'Black Swan':
                    text.append("  → VIX above 20 - elevated volatility\n", style="dim yellow")
                    
            text.append(f"\n⚠ Risk Warnings:\n", style="bold yellow")
            text.append(f"• {len(non_compliant)} mandates out of compliance\n", style="yellow")
            text.append("• Trading may be restricted or higher risk\n", style="yellow")
        else:
            text.append("\n✓ All Clear: All mandates compliant!\n", style="bold green")
            text.append("• Trading conditions optimal\n", style="green")
            text.append("• Risk levels within acceptable range\n", style="green")
            
        panel = Panel(text, border_style="cyan" if non_compliant else "green")
        self.query_one("#compliance-content").update(panel)