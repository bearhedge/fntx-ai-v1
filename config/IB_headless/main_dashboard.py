#!/usr/bin/env python3
"""
FNTX Trading Dashboard - Unified Implementation
Combines Matrix login with 10-panel trading dashboard
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Label, DataTable, Button, ProgressBar
from textual.screen import Screen
from textual.reactive import reactive
from textual.binding import Binding
from textual import events
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich import box
from datetime import datetime, timedelta
import asyncio
import random
import math
import pytz

# Import the matrix login screen
import sys
sys.path.append('/home/info/fntx-ai-v1')
from tui.screens.matrix_login import MatrixLoginScreen, MatrixRainBackground
from tui.widgets.glow_input import GlowInput, PsychedelicButton


class OptionsChainPanel(Static):
    """Live options chain with wave visualization"""
    
    def __init__(self):
        super().__init__()
        self.update_count = 0
        
    def on_mount(self):
        self.set_interval(3, self.refresh_data)
        
    def refresh_data(self):
        self.update_count += 1
        self.update(self.render_options_chain())
        
    def render_options_chain(self):
        table = Table(title="📊 OPTIONS CHAIN - SPY", box=box.DOUBLE_EDGE, 
                     title_style="bold cyan", border_style="green")
        
        # Headers
        table.add_column("Strike", style="yellow", justify="center")
        table.add_column("Bid", style="cyan")
        table.add_column("Ask", style="cyan")
        table.add_column("Last", style="white")
        table.add_column("Volume", style="magenta")
        table.add_column("OI", style="blue")
        table.add_column("IV", style="green")
        
        # Generate mock options data
        current_price = 448.50 + random.uniform(-2, 2)
        
        for offset in range(-5, 6):
            strike = int(current_price) + offset
            
            # Color based on moneyness
            if abs(strike - current_price) < 1:
                strike_color = "[bold yellow]"  # ATM
            elif strike < current_price:
                strike_color = "[green]"  # ITM
            else:
                strike_color = "[red]"  # OTM
            
            bid = round(abs(current_price - strike) * 0.1 + random.uniform(0.1, 0.5), 2)
            ask = bid + 0.05
            last = bid + 0.02
            volume = random.randint(100, 5000)
            oi = random.randint(1000, 20000)
            iv = round(16 + abs(offset) * 2 + random.uniform(-2, 2), 1)
            
            table.add_row(
                f"{strike_color}{strike}",
                f"${bid:.2f}",
                f"${ask:.2f}",
                f"${last:.2f}",
                str(volume),
                str(oi),
                f"{iv}%"
            )
        
        return Panel(table, border_style="green", title=f"Update #{self.update_count}")


class StraddlePanel(Static):
    """ATM straddle analysis with wave pattern"""
    
    def on_mount(self):
        self.set_interval(3, self.refresh_data)
        
    def refresh_data(self):
        self.update(self.render_straddle())
        
    def render_straddle(self):
        current_price = 448.50 + random.uniform(-2, 2)
        atm_strike = round(current_price)
        
        # Wave pattern visualization
        wave_viz = """
        ╔═══════════════════════════════════╗
        ║      WAVE PATTERN SPREADING       ║
        ╠═══════════════════════════════════╣
        ║         ○ ATM: $448               ║
        ║      ╱─────╲                      ║
        ║    ╱ Wave 1 ╲  [$447-449]         ║
        ║  ╱  Wave 2   ╲ [$445-451]         ║
        ║ ╱   Wave 3    ╲[$443-453]         ║
        ╚═══════════════════════════════════╝
        """
        
        table = Table(box=box.SIMPLE)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        straddle_cost = round(random.uniform(3.5, 4.5), 2)
        breakeven_up = atm_strike + straddle_cost
        breakeven_down = atm_strike - straddle_cost
        
        table.add_row("ATM Strike", f"${atm_strike}")
        table.add_row("Straddle Cost", f"${straddle_cost}")
        table.add_row("Breakeven Up", f"${breakeven_up:.2f}")
        table.add_row("Breakeven Down", f"${breakeven_down:.2f}")
        table.add_row("Expected Move", f"±${straddle_cost:.2f}")
        table.add_row("IV Rank", f"{random.randint(20, 80)}%")
        
        content = Text(wave_viz, style="green") + Text("\n") + table
        
        return Panel(content, title="🌊 STRADDLE ANALYSIS", border_style="cyan")


class AIReasoningPanel(Static):
    """Display AI trading logic"""
    
    def on_mount(self):
        self.set_interval(5, self.update_reasoning)
        
    def update_reasoning(self):
        self.update(self.render_reasoning())
        
    def render_reasoning(self):
        reasons = [
            "📈 Market showing bullish momentum, VIX below 20",
            "⚡ High volume detected in 450 calls",
            "🎯 Wave 3 spread optimal at current IV levels",
            "⏰ Approaching power hour - increasing position size",
            "🔄 Delta-neutral maintained with 5-wave distribution",
            "💡 ML model confidence: 87% for current setup"
        ]
        
        selected = random.sample(reasons, 3)
        
        text = Text()
        for reason in selected:
            text.append(f"• {reason}\n", style="green")
        text.append(f"\nConfidence Score: {random.randint(75, 95)}%", style="bold yellow")
        
        return Panel(text, title="🤖 AI REASONING", border_style="magenta")


class MandatePanel(Static):
    """Risk guardrails display"""
    
    def render(self):
        daily_loss = random.randint(1000, 3000)
        max_loss = 5000
        positions = random.randint(3, 7)
        max_positions = 10
        
        content = f"""
╔═══════════════════════════════╗
║      MANDATE STATUS           ║
╠═══════════════════════════════╣
║ Daily Loss Limit: ${max_loss}     ║
║ Current Loss: ${daily_loss} ({int(daily_loss/max_loss*100)}%)║
║ {"█" * int(daily_loss/max_loss*20)}{"░" * (20 - int(daily_loss/max_loss*20))}║
║                               ║
║ Max Positions: {max_positions}             ║
║ Open Positions: {positions}             ║
║ {"█" * int(positions/max_positions*20)}{"░" * (20 - int(positions/max_positions*20))}║
║                               ║
║ Trading Hours: 09:30-16:00    ║
║ Status: ACTIVE ✓              ║
╚═══════════════════════════════╝
        """
        return Panel(Text(content, style="yellow"), title="🛡️ MANDATE GUARDRAILS", border_style="yellow")


class MarketTimerPanel(Static):
    """Trading time optimization"""
    
    def on_mount(self):
        self.set_interval(1, self.update_timer)
        
    def update_timer(self):
        self.update(self.render_timer())
        
    def render_timer(self):
        now = datetime.now(pytz.timezone('US/Eastern'))
        market_close = now.replace(hour=16, minute=0, second=0)
        time_to_close = market_close - now
        
        current_hour = now.hour
        if 14 <= current_hour < 16:
            timing_score = 0.95
            status = "🔥 OPTIMAL WINDOW"
            color = "green"
        elif 9 <= current_hour < 10:
            timing_score = 0.7
            status = "📊 MORNING OPEN"
            color = "yellow"
        else:
            timing_score = 0.4
            status = "⏳ WAITING"
            color = "red"
        
        content = f"""
Current Time: {now.strftime('%H:%M:%S')} ET
Time to Close: {str(time_to_close).split('.')[0]}

Timing Score: {timing_score:.0%}
{"█" * int(timing_score * 20)}{"░" * int((1-timing_score) * 20)}

Status: {status}

Preferred Window: 14:00-16:00 ET
Next Optimal: {max(0, 14 - current_hour)}h {max(0, 60 - now.minute) if current_hour < 14 else 0}m
        """
        
        return Panel(Text(content, style=color), title="⏰ MARKET TIMER", border_style=color)


class StatisticsPanel(Static):
    """Performance metrics"""
    
    def render(self):
        stats = f"""
📊 Today's Performance
━━━━━━━━━━━━━━━━━━━━
P&L: [green]+$1,234.56[/green]
Trades: 12
Win Rate: 75%
Sharpe: 1.85

📈 Weekly Stats
━━━━━━━━━━━━━━━━━━━━
P&L: [green]+$5,432.10[/green]
Trades: 67
Win Rate: 71%
Max DD: -$890

📉 Monthly Stats
━━━━━━━━━━━━━━━━━━━━
P&L: [green]+$18,765.43[/green]
Trades: 284
Win Rate: 68%
Best Day: +$3,456
        """
        return Panel(Text(stats), title="📊 STATISTICS", border_style="blue")


class TradingDashboard(Screen):
    """Main trading dashboard with 10 panels"""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("space", "pause", "Pause/Resume"),
        Binding("?", "help", "Help"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create the 10-panel layout"""
        
        # Header
        yield Label("FNTX TRADING DASHBOARD", id="header")
        
        # Main container with 3x3 grid + bottom panel
        with Container(id="main-grid"):
            # Top row
            with Horizontal(classes="panel-row"):
                yield OptionsChainPanel(id="options-chain")
                yield StraddlePanel(id="straddle")
                yield MarketTimerPanel(id="timer")
            
            # Middle row
            with Horizontal(classes="panel-row"):
                yield Static(self.render_features(), id="features")
                yield AIReasoningPanel(id="reasoning")
                yield StatisticsPanel(id="statistics")
            
            # Bottom row
            with Horizontal(classes="panel-row"):
                yield MandatePanel(id="mandate")
                yield Static(self.render_risk_manager(), id="risk")
                yield Static(self.render_rlhf(), id="rlhf")
            
        # Status bar
        yield Label("Press ? for help | Space to pause | Q to quit", id="status-bar")
    
    def render_features(self):
        """Features panel"""
        features = """
VIX: 16.3 ↓
P/C Ratio: 0.68
SPY Volume: 78M
RSI: 58
MACD: Bullish
Breadth: 65% ↑
        """
        return Panel(Text(features, style="cyan"), title="📈 FEATURES", border_style="cyan")
    
    def render_risk_manager(self):
        """Risk manager panel"""
        positions = """
Symbol  Qty  P&L     Status
━━━━━━━━━━━━━━━━━━━━━━━━━
SPY 448C  5  +$234   ✓
SPY 450C  3  +$120   ✓
SPY 445P  2  -$45    ⚠
SPY 452C  1  +$67    ✓

Portfolio Greeks:
Delta: +0.15  Gamma: 0.02
Theta: -45    Vega: +120
        """
        return Panel(Text(positions, style="white"), title="💼 RISK MANAGER", border_style="orange")
    
    def render_rlhf(self):
        """RLHF feedback panel"""
        feedback = """
Recent Decisions:
━━━━━━━━━━━━━━━━━━━━━
1. Buy SPY 448C ⭐⭐⭐⭐⭐
2. Sell SPY 445P ⭐⭐⭐
3. Hold positions ⭐⭐⭐⭐

[Rate Last Trade]
⭐ ⭐ ⭐ ⭐ ⭐

[Override] [Approve]
        """
        return Panel(Text(feedback, style="magenta"), title="🎮 RLHF FEEDBACK", border_style="magenta")
    
    def action_quit(self):
        """Quit the application"""
        self.app.exit()
    
    def action_refresh(self):
        """Force refresh all panels"""
        self.refresh()
    
    def action_pause(self):
        """Pause/resume updates"""
        self.notify("Trading paused/resumed", severity="info")


class FNTXTradingApp(App):
    """Main application combining login and dashboard"""
    
    CSS = """
    #header {
        height: 3;
        background: black;
        color: #00ff00;
        text-align: center;
        text-style: bold;
        border: double #00ff00;
    }
    
    #main-grid {
        height: 100%;
        padding: 1;
    }
    
    .panel-row {
        height: 33%;
        width: 100%;
    }
    
    #status-bar {
        dock: bottom;
        height: 1;
        background: #1a1a2e;
        color: #00ff00;
        text-align: center;
    }
    
    OptionsChainPanel, StraddlePanel, MarketTimerPanel {
        width: 33%;
        height: 100%;
        margin: 0 1;
    }
    
    #features, #reasoning, #statistics {
        width: 33%;
        height: 100%;
        margin: 0 1;
    }
    
    #mandate, #risk, #rlhf {
        width: 33%;
        height: 100%;
        margin: 0 1;
    }
    
    MatrixLoginScreen {
        background: black;
    }
    """
    
    def on_mount(self):
        """Start with login screen"""
        self.push_screen(MatrixLoginScreen())
    
    def action_show_dashboard(self):
        """Transition from login to dashboard"""
        self.pop_screen()
        self.push_screen(TradingDashboard())


def main():
    """Launch the trading dashboard"""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║           FNTX TRADING DASHBOARD v1.0            ║
    ║                                                   ║
    ║         Automated Options Trading System         ║
    ║            With Wave-Pattern Spreading           ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
    
    Starting Matrix Authentication...
    """)
    
    app = FNTXTradingApp()
    app.run()


if __name__ == "__main__":
    main()