"""
Trading Dashboard Screen for FNTX Terminal

10-panel trading interface with real-time data visualization.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, DataTable, Label, ProgressBar
from textual.containers import Container, Grid, Vertical, Horizontal
from textual.reactive import reactive
from textual import work
import asyncio
from datetime import datetime
import pytz

class Panel(Container):
    """Base panel widget for dashboard."""
    
    def __init__(self, title: str, content: str = "", **kwargs):
        super().__init__(**kwargs)
        self.border_title = title
        self.content_widget = Static(content)
    
    def compose(self) -> ComposeResult:
        yield self.content_widget
    
    def update_content(self, content: str):
        """Update panel content."""
        self.content_widget.update(content)

class DashboardScreen(Screen):
    """Main trading dashboard screen."""
    
    CSS = """
    DashboardScreen {
        background: $background;
    }
    
    #dashboard-grid {
        grid-size: 3 3;
        grid-gutter: 1;
        padding: 1;
        height: 100%;
    }
    
    Panel {
        border: thick $primary;
        padding: 1;
        background: $surface;
    }
    
    Panel:focus {
        border: thick $accent;
    }
    
    #header {
        text-align: center;
        color: $primary;
        text-style: bold;
        padding: 1;
        border-bottom: thick $primary;
    }
    
    #footer {
        text-align: center;
        color: $secondary;
        padding: 1;
        border-top: thick $primary;
    }
    
    .panel-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .profit {
        color: #00ff00;
    }
    
    .loss {
        color: #ff0040;
    }
    
    .neutral {
        color: $text;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.panels = {}
        self.update_task = None
        self.is_demo = True
    
    def compose(self) -> ComposeResult:
        """Create dashboard layout."""
        from ..config import get_config
        self.is_demo = get_config().mode == "demo"
        
        # Header
        mode_text = "[DEMO MODE]" if self.is_demo else "[LIVE TRADING]"
        yield Label(f"FNTX TRADING DASHBOARD {mode_text}", id="header")
        
        # Main grid of panels
        with Grid(id="dashboard-grid"):
            # Row 1
            self.panels['options'] = Panel("Options Chain", self._get_options_data())
            yield self.panels['options']
            
            self.panels['straddle'] = Panel("Straddle Analysis", self._get_straddle_data())
            yield self.panels['straddle']
            
            self.panels['timer'] = Panel("Market Timer", self._get_timer_data())
            yield self.panels['timer']
            
            # Row 2
            self.panels['features'] = Panel("Market Features", self._get_features_data())
            yield self.panels['features']
            
            self.panels['ai'] = Panel("AI Reasoning", self._get_ai_data())
            yield self.panels['ai']
            
            self.panels['stats'] = Panel("Statistics", self._get_stats_data())
            yield self.panels['stats']
            
            # Row 3
            self.panels['mandate'] = Panel("Risk Limits", self._get_mandate_data())
            yield self.panels['mandate']
            
            self.panels['risk'] = Panel("Risk Manager", self._get_risk_data())
            yield self.panels['risk']
            
            self.panels['feedback'] = Panel("RLHF Feedback", self._get_feedback_data())
            yield self.panels['feedback']
        
        # Footer
        yield Label("Q: Quit | R: Refresh | Space: Pause/Resume", id="footer")
    
    async def on_mount(self) -> None:
        """Start data updates when mounted."""
        self.update_task = asyncio.create_task(self.auto_update())
    
    async def on_unmount(self) -> None:
        """Stop updates when unmounted."""
        if self.update_task:
            self.update_task.cancel()
    
    async def auto_update(self) -> None:
        """Auto-update dashboard data."""
        from ..config import get_config
        refresh_rate = get_config().display.refresh_rate
        
        while True:
            try:
                self._update_all_panels()
                await asyncio.sleep(refresh_rate)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                await asyncio.sleep(refresh_rate)
    
    def _update_all_panels(self) -> None:
        """Update all panel contents."""
        self.panels['options'].update_content(self._get_options_data())
        self.panels['straddle'].update_content(self._get_straddle_data())
        self.panels['timer'].update_content(self._get_timer_data())
        self.panels['features'].update_content(self._get_features_data())
        self.panels['ai'].update_content(self._get_ai_data())
        self.panels['stats'].update_content(self._get_stats_data())
        self.panels['mandate'].update_content(self._get_mandate_data())
        self.panels['risk'].update_content(self._get_risk_data())
        self.panels['feedback'].update_content(self._get_feedback_data())
    
    def _get_options_data(self) -> str:
        """Get options chain data."""
        if self.is_demo:
            from ..demo.data_generator import get_demo_options_chain
            return get_demo_options_chain()
        else:
            return "Live options data\n[Connect to data source]"
    
    def _get_straddle_data(self) -> str:
        """Get straddle analysis data."""
        if self.is_demo:
            return """ATM Straddle: SPY 450
            
Premium: $12.50
Breakeven: ±2.8%
IV: 18.5%
Days to Exp: 1

Expected Move: ±$12.60"""
        else:
            return "Live straddle data"
    
    def _get_timer_data(self) -> str:
        """Get market timer data."""
        et = pytz.timezone('US/Eastern')
        now = datetime.now(et)
        
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        
        if now < market_open:
            status = "Pre-Market"
            time_to = market_open - now
            next_event = f"Open in {time_to.seconds // 3600}h {(time_to.seconds % 3600) // 60}m"
        elif now > market_close:
            status = "After Hours"
            next_event = "Market Closed"
        else:
            status = "[green]Market Open[/]"
            time_to = market_close - now
            next_event = f"Close in {time_to.seconds // 3600}h {(time_to.seconds % 3600) // 60}m"
        
        return f"""Current Time: {now.strftime('%H:%M:%S ET')}
Status: {status}
{next_event}

Preferred Window:
14:00 - 16:00 ET
[Optimal timing]"""
    
    def _get_features_data(self) -> str:
        """Get market features data."""
        if self.is_demo:
            return """VIX: 18.5 ↑0.3
P/C Ratio: 0.65
RSI: 58
MACD: Bullish
Volume: Above Avg

Trend: [green]Bullish[/]"""
        else:
            return "Live market features"
    
    def _get_ai_data(self) -> str:
        """Get AI reasoning data."""
        if self.is_demo:
            return """[cyan]Current Analysis:[/]
Market showing bullish momentum
VIX relatively low
Options flow positive

[cyan]Recommendation:[/]
Sell OTM Put Spreads
Target: 440/435
Confidence: [green]85%[/]

[cyan]Risk Assessment:[/]
Max Loss: $500
Probability: 78% profit"""
        else:
            return "Live AI analysis"
    
    def _get_stats_data(self) -> str:
        """Get statistics data."""
        if self.is_demo:
            return """Daily P&L: [green]+$1,234[/]
Weekly: [green]+$3,456[/]
Monthly: [green]+$12,345[/]

Win Rate: 72%
Sharpe: 1.85
Max DD: -8.5%

Trades Today: 12
Avg Size: $5,000"""
        else:
            return "Live statistics"
    
    def _get_mandate_data(self) -> str:
        """Get mandate/risk limits data."""
        return """Daily Loss Limit: $5,000
Current: [green]$1,234[/] (25%)
[▓▓▓▓▓░░░░░░░░░░░░░░░]

Max Positions: 10
Open: 3
[▓▓▓░░░░░░░░░░░░░░░░░]

Trading Hours: 09:30-16:00
Status: [green]ACTIVE ✓[/]"""
    
    def _get_risk_data(self) -> str:
        """Get risk manager data."""
        if self.is_demo:
            return """Open Positions: 3

1. SPY 450P Short
   P&L: [green]+$234[/]
   Delta: -0.15
   
2. SPY 445P Short  
   P&L: [green]+$156[/]
   Delta: -0.08
   
3. SPY 455C Short
   P&L: [loss]-$45[/]
   Delta: -0.22

Total Delta: -0.45
Total P&L: [green]+$345[/]"""
        else:
            return "Live positions"
    
    def _get_feedback_data(self) -> str:
        """Get RLHF feedback data."""
        return """Last Trade Rating: ⭐⭐⭐⭐
User Feedback: Good entry

Recent Ratings:
⭐⭐⭐⭐⭐ (2)
⭐⭐⭐⭐ (5)
⭐⭐⭐ (1)

Avg Score: 4.1/5.0
Total Feedback: 127"""