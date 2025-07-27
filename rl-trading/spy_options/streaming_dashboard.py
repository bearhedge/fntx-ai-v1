#!/usr/bin/env python3
"""
REAL Streaming Dashboard - Actually uses streaming data
NOT polling, NOT fake streaming
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

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.append(str(Path(__file__).parent))

from data_pipeline.streaming_theta_connector import LocalThetaConnector
from terminal_ui.straddle_options_panel import StraddleOptionsPanel


class StreamingDashboard:
    """Dashboard that ACTUALLY uses streaming data"""
    
    def __init__(self):
        self.console = Console()
        self.connector = LocalThetaConnector()
        self.straddle_panel = StraddleOptionsPanel(num_strikes=10)
        
        # Latest data from streaming
        self.latest_data = None
        self.update_count = 0
        self.last_update_time = None
        
    async def on_streaming_update(self, data):
        """Called by streaming connector when new data arrives"""
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
        """Update all panels with streaming data"""
        if not self.latest_data:
            layout["header"].update(Panel("Waiting for streaming data...", title="Status"))
            return
            
        # Header with REAL prices
        spy_price = self.latest_data.get('spy_price_realtime', 0) or self.latest_data.get('spy_price', 0)
        header_text = Text()
        header_text.append(f"SPY: ${spy_price:.2f} ", style="bold cyan")
        header_text.append(f"(Yahoo realtime: ${self.latest_data.get('spy_price_realtime', 0):.2f}) ", style="green")
        header_text.append(f"| Updates: {self.update_count} ", style="yellow")
        header_text.append(f"| Last: {self.last_update_time.strftime('%H:%M:%S') if self.last_update_time else 'Never'}")
        
        layout["header"].update(Panel(header_text, title="STREAMING Live Data"))
        
        # Options chain
        options_chain = self.latest_data.get('options_chain', [])
        if options_chain:
            options_panel = self.straddle_panel.create_panel(
                options_chain,
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
        
        stats.add_row("Streaming Port:", "11000 (MDDS)")
        stats.add_row("Options Count:", str(len(self.latest_data.get('options_chain', []))))
        stats.add_row("SPY Delayed:", f"${self.latest_data.get('spy_price', 0):.2f}")
        stats.add_row("SPY Realtime:", f"${self.latest_data.get('spy_price_realtime', 0):.2f}")
        stats.add_row("Update Rate:", f"{self.update_count / max(1, (datetime.now() - self.last_update_time).total_seconds() if self.last_update_time else 1):.1f}/sec")
        
        layout["right"].update(Panel(stats, title="Streaming Stats"))
        
        # Footer
        layout["footer"].update(Panel(
            f"REAL Streaming Active | Press Ctrl+C to exit | {datetime.now().strftime('%H:%M:%S')}",
            style="green"
        ))
        
    async def run(self):
        """Run the streaming dashboard"""
        print("Starting REAL streaming dashboard...")
        print("Using Theta Data client on port 11000")
        print("Yahoo Finance for real-time SPY\n")
        
        # Connect streaming callback
        self.connector.on_market_update = self.on_streaming_update
        
        # Start streaming
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
                
        print(f"\nTotal streaming updates received: {self.update_count}")
        print("This was REAL streaming - NOT polling!")


async def main():
    dashboard = StreamingDashboard()
    await dashboard.run()


if __name__ == "__main__":
    asyncio.run(main())