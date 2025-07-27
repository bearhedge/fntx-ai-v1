#!/usr/bin/env python3
"""
REST-based Streaming Dashboard - Using fast polling
"""
import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.append(str(Path(__file__).parent))

from data_pipeline.rest_theta_connector import RESTThetaConnector
from terminal_ui.straddle_options_panel import StraddleOptionsPanel


class RESTStreamingDashboard:
    """Dashboard using REST API with fast polling"""
    
    def __init__(self):
        self.console = Console()
        self.connector = RESTThetaConnector()
        self.straddle_panel = StraddleOptionsPanel(num_strikes=10)
        
        # Latest data
        self.latest_data = None
        self.update_count = 0
        self.last_update_time = None
        
    async def on_market_update(self, data):
        """Called when new data arrives"""
        self.latest_data = data
        self.update_count += 1
        self.last_update_time = datetime.now()
        
    def create_layout(self):
        """Create dashboard layout"""
        layout = Layout()
        
        # Split into header, body, footer
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Split body into left and right
        layout["body"].split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=1)
        )
        
        return layout
        
    def update_display(self, layout):
        """Update all panels with data"""
        if not self.latest_data:
            layout["header"].update(Panel("Waiting for data...", title="Status"))
            return
            
        # Header with prices
        spy_price = self.latest_data.get('spy_price_realtime', 0) or self.latest_data.get('spy_price', 0)
        header_text = Text()
        header_text.append(f"SPY: ${spy_price:.2f} ", style="bold cyan")
        header_text.append(f"(Delayed: ${self.latest_data.get('spy_price', 0):.2f}) ", style="dim")
        header_text.append(f"| Updates: {self.update_count} ", style="yellow")
        header_text.append(f"| Rate: {self.update_count / max(1, (datetime.now() - self.connector.market_data['timestamp']).total_seconds() if self.connector.market_data['timestamp'] else 1):.1f}/sec ", style="green")
        header_text.append(f"| {self.last_update_time.strftime('%H:%M:%S') if self.last_update_time else 'Never'}")
        
        layout["header"].update(Panel(header_text, title="Live Market Data (REST API)"))
        
        # Options chain
        options_chain = self.latest_data.get('options_chain', [])
        if options_chain:
            # Filter to ATM strikes
            spy_price = self.latest_data.get('spy_price_realtime', 0) or self.latest_data.get('spy_price', 0)
            atm_options = sorted(options_chain, key=lambda x: abs(x['strike'] - spy_price))[:20]
            
            options_panel = self.straddle_panel.create_panel(
                atm_options,
                spy_price,
                self.latest_data.get('spy_price_realtime'),
                0  # VIX
            )
            layout["left"].update(options_panel)
        else:
            layout["left"].update(Panel("No options data yet...", title="Options Chain"))
            
        # Stats panel
        stats = Table.grid(padding=1)
        stats.add_column(style="cyan", justify="right")
        stats.add_column(style="white")
        
        stats.add_row("API Type:", "REST (Fast Polling)")
        stats.add_row("Poll Rate:", "500ms")
        stats.add_row("Options Count:", str(len(self.latest_data.get('options_chain', []))))
        stats.add_row("SPY Price:", f"${self.latest_data.get('spy_price', 0):.2f}")
        stats.add_row("Yahoo Price:", f"${self.latest_data.get('spy_price_realtime', 0):.2f}")
        stats.add_row("Last Update:", self.last_update_time.strftime('%H:%M:%S.%f')[:-3] if self.last_update_time else "Never")
        
        layout["right"].update(Panel(stats, title="Connection Stats"))
        
        # Footer
        layout["footer"].update(Panel(
            f"REST API Active | Press Ctrl+C to exit | {datetime.now().strftime('%H:%M:%S')}",
            style="green"
        ))
        
    async def run(self):
        """Run the dashboard"""
        print("Starting REST-based dashboard with fast polling...")
        print("Using Theta Data REST API on port 25510")
        print("Yahoo Finance for real-time SPY\n")
        
        # Connect callback
        self.connector.on_market_update = self.on_market_update
        
        # Start connector
        await self.connector.start()
        
        # Create layout
        layout = self.create_layout()
        
        # Run with live display
        with Live(layout, console=self.console, refresh_per_second=2) as live:
            try:
                while True:
                    self.update_display(layout)
                    await asyncio.sleep(0.5)  # Update display twice per second
                    
            except KeyboardInterrupt:
                print("\nStopping...")
            finally:
                await self.connector.stop()
                
        print(f"\nTotal updates received: {self.update_count}")
        print(f"Average update rate: {self.update_count / max(1, (self.last_update_time - self.connector.market_data['timestamp']).total_seconds() if self.last_update_time and self.connector.market_data['timestamp'] else 1):.1f} updates/sec")


async def main():
    dashboard = RESTStreamingDashboard()
    await dashboard.run()


if __name__ == "__main__":
    asyncio.run(main())