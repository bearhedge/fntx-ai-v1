#!/usr/bin/env python3
"""
FNTX Trading Dashboard - Standalone Demo
A fully functional trading dashboard with cyberpunk theme
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label, Button, Input
from textual.screen import Screen
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich import box
from datetime import datetime, timedelta
import random
import pytz
import asyncio


class CyberpunkInput(Input):
    """Cyberpunk themed input field"""
    DEFAULT_CSS = """
    CyberpunkInput {
        background: rgba(0, 255, 0, 0.1);
        border: tall #00ff00;
        padding: 0 1;
        margin: 1;
    }
    CyberpunkInput:focus {
        border: double #00ff00;
    }
    """


class MatrixRainEffect(Static):
    """Simple matrix rain effect for background"""
    
    def on_mount(self):
        self.set_interval(0.1, self.update_rain)
        self.drops = []
        self._init_drops()
    
    def _init_drops(self):
        """Initialize rain drops"""
        for _ in range(20):
            self.drops.append({
                'x': random.randint(0, 60),
                'y': random.randint(-20, 0),
                'speed': random.uniform(0.5, 2.0),
                'chars': [random.choice('01アイウエオ!@#$%^&*') for _ in range(10)]
            })
    
    def update_rain(self):
        """Update rain animation"""
        for drop in self.drops:
            drop['y'] += drop['speed']
            if drop['y'] > 20:
                drop['y'] = random.randint(-20, -5)
                drop['x'] = random.randint(0, 60)
        self.refresh()
    
    def render(self):
        """Render the rain effect"""
        lines = []
        for _ in range(15):
            line = ""
            for _ in range(60):
                if random.random() < 0.05:
                    char = random.choice('01アイウエオ!@#$%^&*')
                    line += f"[green]{char}[/green]"
                else:
                    line += " "
            lines.append(line)
        return Text.from_markup("\n".join(lines))


class LoginScreen(Screen):
    """Cyberpunk login screen"""
    
    def compose(self) -> ComposeResult:
        yield Container(
            MatrixRainEffect(),
            Container(
                Static("""
[bold cyan]
███████╗███╗   ██╗████████╗██╗  ██╗
██╔════╝████╗  ██║╚══██╔══╝╚██╗██╔╝
█████╗  ██╔██╗ ██║   ██║    ╚███╔╝ 
██╔══╝  ██║╚██╗██║   ██║    ██╔██╗ 
██║     ██║ ╚████║   ██║   ██╔╝ ██╗
╚═╝     ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝
[/bold cyan]
                """, id="logo"),
                Label("TRADING TERMINAL ACCESS", id="title"),
                CyberpunkInput(placeholder="Username", id="username"),
                CyberpunkInput(placeholder="Password", password=True, id="password"),
                Button("ENTER THE MATRIX", variant="primary", id="login-btn"),
                id="login-form"
            ),
            id="login-container"
        )
    
    def on_button_pressed(self, event):
        """Handle login button"""
        if event.button.id == "login-btn":
            self.app.push_screen(DashboardScreen())


class DashboardScreen(Screen):
    """Main trading dashboard"""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh All"),
        Binding("space", "toggle", "Pause/Resume"),
    ]
    
    def compose(self) -> ComposeResult:
        # Header
        yield Static("[bold green]╔═══════════════════════════════════════════════════════════════╗[/bold green]")
        yield Static("[bold green]║              FNTX AUTOMATED TRADING DASHBOARD                 ║[/bold green]")
        yield Static("[bold green]╚═══════════════════════════════════════════════════════════════╝[/bold green]")
        
        # Main grid layout
        with Container(id="dashboard-grid"):
            # Row 1
            with Horizontal(classes="panel-row"):
                yield Static(id="options-panel", classes="panel")
                yield Static(id="straddle-panel", classes="panel")
                yield Static(id="timer-panel", classes="panel")
            
            # Row 2
            with Horizontal(classes="panel-row"):
                yield Static(id="features-panel", classes="panel")
                yield Static(id="ai-panel", classes="panel")
                yield Static(id="stats-panel", classes="panel")
            
            # Row 3
            with Horizontal(classes="panel-row"):
                yield Static(id="mandate-panel", classes="panel")
                yield Static(id="risk-panel", classes="panel")
                yield Static(id="rlhf-panel", classes="panel")
        
        # Status bar
        yield Label("[cyan]Q: Quit | R: Refresh | Space: Pause/Resume[/cyan]", id="status")
    
    def on_mount(self):
        """Start updating panels"""
        self.set_interval(3, self.update_panels)
        self.update_panels()
    
    def update_panels(self):
        """Update all dashboard panels"""
        # Options Chain Panel
        self.query_one("#options-panel").update(self._render_options_chain())
        
        # Straddle Panel
        self.query_one("#straddle-panel").update(self._render_straddle())
        
        # Timer Panel
        self.query_one("#timer-panel").update(self._render_timer())
        
        # Features Panel
        self.query_one("#features-panel").update(self._render_features())
        
        # AI Reasoning Panel
        self.query_one("#ai-panel").update(self._render_ai_reasoning())
        
        # Statistics Panel
        self.query_one("#stats-panel").update(self._render_statistics())
        
        # Mandate Panel
        self.query_one("#mandate-panel").update(self._render_mandate())
        
        # Risk Manager Panel
        self.query_one("#risk-panel").update(self._render_risk_manager())
        
        # RLHF Panel
        self.query_one("#rlhf-panel").update(self._render_rlhf())
    
    def _render_options_chain(self):
        """Render options chain panel"""
        table = Table(title="OPTIONS CHAIN", box=box.DOUBLE_EDGE, 
                     title_style="bold cyan", border_style="green")
        
        table.add_column("Strike", style="yellow")
        table.add_column("Bid", style="cyan")
        table.add_column("Ask", style="cyan")
        table.add_column("Vol", style="magenta")
        
        current = 448.50
        for i in range(-3, 4):
            strike = int(current) + i
            bid = round(abs(current - strike) * 0.1 + random.uniform(0.5, 1.5), 2)
            ask = bid + 0.05
            vol = random.randint(100, 5000)
            
            color = "yellow" if abs(strike - current) < 1 else "white"
            table.add_row(
                f"[{color}]{strike}[/{color}]",
                f"${bid:.2f}",
                f"${ask:.2f}",
                str(vol)
            )
        
        return Panel(table, border_style="green")
    
    def _render_straddle(self):
        """Render straddle analysis"""
        content = f"""[cyan]ATM STRADDLE[/cyan]
━━━━━━━━━━━━━━━
Strike: $448
Cost: ${random.uniform(3.5, 4.5):.2f}
Breakeven: ±3.8%
IV Rank: {random.randint(20, 80)}%

[green]WAVE PATTERN:[/green]
  ○ ATM
 ╱ ╲ Wave 1
╱   ╲ Wave 2"""
        return Panel(Text(content), title="🌊 STRADDLE", border_style="cyan")
    
    def _render_timer(self):
        """Render market timer"""
        now = datetime.now(pytz.timezone('US/Eastern'))
        hour = now.hour
        
        if 14 <= hour < 16:
            status = "[green]🔥 OPTIMAL[/green]"
            score = 95
        elif 9 <= hour < 10:
            status = "[yellow]📊 MORNING[/yellow]"
            score = 70
        else:
            status = "[red]⏳ WAITING[/red]"
            score = 40
        
        content = f"""Time: {now.strftime('%H:%M:%S')} ET

Score: {score}%
{'█' * (score//10)}{'░' * (10-score//10)}

{status}

Target: 14:00-16:00"""
        return Panel(Text(content), title="⏰ TIMER", border_style="yellow")
    
    def _render_features(self):
        """Render market features"""
        content = f"""[cyan]MARKET DATA[/cyan]
━━━━━━━━━━━━
VIX: {random.uniform(15, 18):.1f} ↓
P/C: 0.68
Volume: 78M
RSI: 58
MACD: Bullish"""
        return Panel(Text(content), title="📈 FEATURES", border_style="blue")
    
    def _render_ai_reasoning(self):
        """Render AI logic"""
        reasons = [
            "High volume in 450 calls",
            "VIX below 20 - bullish",
            "Wave 3 optimal now",
            "87% model confidence"
        ]
        content = "\n".join([f"• {r}" for r in random.sample(reasons, 3)])
        return Panel(Text(f"[green]{content}[/green]"), title="🤖 AI LOGIC", border_style="magenta")
    
    def _render_statistics(self):
        """Render statistics"""
        content = f"""[green]TODAY[/green]
P&L: +$1,234
Trades: 12
Win: 75%

[cyan]WEEK[/cyan]
P&L: +$5,432
Sharpe: 1.85"""
        return Panel(Text(content), title="📊 STATS", border_style="white")
    
    def _render_mandate(self):
        """Render mandate panel"""
        loss = random.randint(1000, 3000)
        positions = random.randint(3, 7)
        
        content = f"""[yellow]LIMITS[/yellow]
━━━━━━━━━
Loss: ${loss}/5000
{'█' * (loss//500)}{'░' * (10-loss//500)}

Pos: {positions}/10
{'█' * positions}{'░' * (10-positions)}

[green]✓ ACTIVE[/green]"""
        return Panel(Text(content), title="🛡️ MANDATE", border_style="yellow")
    
    def _render_risk_manager(self):
        """Render risk positions"""
        content = """[white]POSITIONS[/white]
━━━━━━━━━━━
SPY 448C +$234
SPY 450C +$120
SPY 445P -$45

Greeks:
Δ +0.15 Θ -45"""
        return Panel(Text(content), title="💼 RISK", border_style="orange")
    
    def _render_rlhf(self):
        """Render RLHF feedback"""
        content = """[magenta]FEEDBACK[/magenta]
━━━━━━━━━
Last: ⭐⭐⭐⭐
Avg: ⭐⭐⭐⭐

[Override]
[Approve]"""
        return Panel(Text(content), title="🎮 RLHF", border_style="magenta")
    
    def action_quit(self):
        """Quit application"""
        self.app.exit()
    
    def action_refresh(self):
        """Force refresh"""
        self.update_panels()
    
    def action_toggle(self):
        """Toggle pause/resume"""
        self.notify("Trading Paused/Resumed", severity="info")


class TradingDashboardApp(App):
    """Main trading dashboard application"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #login-container {
        align: center middle;
    }
    
    #login-form {
        width: 50;
        height: 25;
        background: rgba(0, 0, 0, 0.9);
        border: double #00ff00;
        padding: 2;
    }
    
    #logo {
        text-align: center;
        margin-bottom: 1;
    }
    
    #title {
        text-align: center;
        color: #00ff00;
        margin-bottom: 2;
    }
    
    #dashboard-grid {
        height: 100%;
    }
    
    .panel-row {
        height: 33%;
        width: 100%;
        margin: 0;
    }
    
    .panel {
        width: 33%;
        height: 100%;
        margin: 0;
    }
    
    #status {
        dock: bottom;
        height: 1;
        text-align: center;
        background: #1a1a2e;
    }
    
    Button {
        width: 100%;
        margin-top: 2;
    }
    """
    
    def on_mount(self):
        """Start with login screen"""
        self.push_screen(LoginScreen())


def main():
    """Launch the dashboard"""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║                                                        ║
    ║              FNTX TRADING DASHBOARD v1.0              ║
    ║                                                        ║
    ║         Automated Options Trading Interface           ║
    ║            With Wave-Pattern Spreading                ║
    ║                                                        ║
    ║  Instructions:                                         ║
    ║  1. Enter any username/password to login              ║
    ║  2. View real-time trading panels                     ║
    ║  3. Press Q to quit, R to refresh                     ║
    ║                                                        ║
    ╚════════════════════════════════════════════════════════╝
    
    Loading Matrix Interface...
    """)
    
    app = TradingDashboardApp()
    app.run()


if __name__ == "__main__":
    main()