"""
Terminal NFT Viewer - Display trading NFTs in CLI with rich visualizations

Provides multiple viewing modes for trading performance NFTs without requiring a web browser.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich import box
from rich.progress import Progress, BarColumn, TextColumn
import asyncio
from .ascii_art_generator import ASCIIArtGenerator

# For advanced terminal graphics
try:
    import plotext as plt
    PLOTEXT_AVAILABLE = True
except ImportError:
    PLOTEXT_AVAILABLE = False


class TerminalNFTViewer:
    """Display trading NFTs in terminal with various visualization modes"""
    
    def __init__(self):
        self.console = Console()
        self.view_modes = ['card', 'chart', 'detailed', 'gallery', 'ascii', 'shaded', 'labubu']
        self.ascii_generator = ASCIIArtGenerator()
        
    def display_trading_nft(self, metrics: Dict, mode: str = 'card'):
        """Display NFT in specified mode"""
        
        if mode == 'card':
            self._display_card_view(metrics)
        elif mode == 'chart':
            self._display_chart_view(metrics)
        elif mode == 'detailed':
            self._display_detailed_view(metrics)
        elif mode == 'gallery':
            self._display_gallery_view([metrics])  # Single item gallery
        elif mode == 'ascii':
            self._display_ascii_art(metrics)
        elif mode == 'shaded':
            self._display_shaded_art(metrics)
        elif mode == 'labubu':
            self._display_labubu_character(metrics)
        else:
            self.console.print(f"[red]Unknown view mode: {mode}[/red]")
    
    def _display_card_view(self, metrics: Dict):
        """Display NFT as a trading card"""
        
        # Determine colors based on performance
        net_pnl = metrics.get('net_pnl', 0)
        pnl_color = "green" if net_pnl >= 0 else "red"
        
        # Create card layout
        card = f"""
╔══════════════════════════════════════════════════╗
║             [bold cyan]FNTX TRADING CHRONICLE[/bold cyan]             ║
║                  #{metrics.get('date', 'N/A')}                   ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║              [{pnl_color}]███████████████████[/{pnl_color}]              ║
║              [{pnl_color}]██ DAILY RESULT ██[/{pnl_color}]              ║
║              [{pnl_color}]███████████████████[/{pnl_color}]              ║
║                                                  ║
║         [bold {pnl_color}]P&L: ${net_pnl:+,.2f}[/bold {pnl_color}]                    ║
║                                                  ║
╠══════════════════════════════════════════════════╣
║  [cyan]Performance Metrics[/cyan]                            ║
║  ├─ Win Rate:     {metrics.get('win_rate', 0):>5.1f}% {"█" * int(metrics.get('win_rate', 0) / 10):<10}  ║
║  ├─ Sharpe (30d): {metrics.get('sharpe_30d', 0):>5.2f}  {"▓" * min(5, int(abs(metrics.get('sharpe_30d', 0))))}  ║
║  ├─ Contracts:    {metrics.get('contracts_traded', 0):>5d}  {"░" * min(10, metrics.get('contracts_traded', 0) // 10)}  ║
║  └─ Volume:      ${metrics.get('implied_turnover', 0):>8,.0f}              ║
║                                                  ║
║  [yellow]Greeks Exposure[/yellow]                                ║
║        Δ = {metrics.get('delta_exposure', 0):>6.2f}    Γ = {metrics.get('gamma_exposure', 0):>6.3f}      ║
║        Θ = {metrics.get('theta_decay', 0):>6.0f}    V = {metrics.get('vega_exposure', 0):>6.0f}      ║
║                                                  ║
╠══════════════════════════════════════════════════╣
║  [dim]Token ID: {metrics.get('token_id', 'N/A')}  |  Version: {metrics.get('version', 1)}[/dim]         ║
╚══════════════════════════════════════════════════╝
"""
        
        # Display with proper formatting
        self.console.print(Panel(card, expand=False))
    
    def _display_chart_view(self, metrics: Dict):
        """Display performance charts in terminal"""
        
        if not PLOTEXT_AVAILABLE:
            self.console.print("[yellow]Install plotext for chart view: pip install plotext[/yellow]")
            return self._display_simple_chart(metrics)
        
        # Create performance chart
        plt.clear_data()
        plt.theme('dark')
        
        # P&L bar chart
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        pnl_values = metrics.get('daily_pnls', [100, -50, 200, 150, 300])
        
        plt.bar(days, pnl_values, color='green+' if sum(pnl_values) > 0 else 'red+')
        plt.title(f"Weekly P&L - Total: ${sum(pnl_values):+,.2f}")
        plt.show()
        
        # Win rate progress bar
        win_rate = metrics.get('win_rate', 0)
        self._display_progress_bar("Win Rate", win_rate, 100, "green")
        
        # Greeks radar (simplified)
        self._display_greeks_chart(metrics)
    
    def _display_simple_chart(self, metrics: Dict):
        """Fallback chart using only rich library"""
        
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="pnl_chart", size=10),
            Layout(name="metrics", size=8),
            Layout(name="greeks", size=6)
        )
        
        # Header
        net_pnl = metrics.get('net_pnl', 0)
        header_color = "green" if net_pnl >= 0 else "red"
        layout["header"].update(
            Panel(f"[bold {header_color}]Daily P&L: ${net_pnl:+,.2f}[/bold {header_color}]", 
                  title=f"Date: {metrics.get('date', 'N/A')}")
        )
        
        # Simple P&L visualization
        pnl_chart = self._create_ascii_bar_chart(
            metrics.get('recent_pnls', [100, -50, 200, 150, 300, 250, 400])
        )
        layout["pnl_chart"].update(Panel(pnl_chart, title="7-Day P&L Trend"))
        
        # Metrics table
        metrics_table = Table(box=box.SIMPLE)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="white")
        metrics_table.add_column("Visual", style="green")
        
        win_rate = metrics.get('win_rate', 0)
        metrics_table.add_row(
            "Win Rate", 
            f"{win_rate:.1f}%",
            "●" * int(win_rate / 10) + "○" * (10 - int(win_rate / 10))
        )
        
        sharpe = metrics.get('sharpe_30d', 0)
        metrics_table.add_row(
            "Sharpe Ratio",
            f"{sharpe:.2f}",
            "▓" * min(5, int(abs(sharpe)))
        )
        
        contracts = metrics.get('contracts_traded', 0)
        metrics_table.add_row(
            "Contracts",
            str(contracts),
            "░" * min(10, contracts // 10)
        )
        
        layout["metrics"].update(Panel(metrics_table, title="Performance Metrics"))
        
        # Greeks visualization
        greeks_visual = self._create_greeks_visual(metrics)
        layout["greeks"].update(Panel(greeks_visual, title="Greeks Exposure"))
        
        self.console.print(layout)
    
    def _display_detailed_view(self, metrics: Dict):
        """Display all metrics in detailed tabular format"""
        
        # Create multiple tables for different metric categories
        tables = []
        
        # Account State Table
        account_table = Table(title="Account State", box=box.ROUNDED)
        account_table.add_column("Metric", style="cyan")
        account_table.add_column("Value", style="white", justify="right")
        
        account_table.add_row("Opening Balance", f"${metrics.get('opening_balance', 0):,.2f}")
        account_table.add_row("Closing Balance", f"${metrics.get('closing_balance', 0):,.2f}")
        account_table.add_row("Deposits", f"${metrics.get('deposits', 0):,.2f}")
        account_table.add_row("Withdrawals", f"${metrics.get('withdrawals', 0):,.2f}")
        tables.append(account_table)
        
        # P&L Breakdown Table
        pnl_table = Table(title="P&L Breakdown", box=box.ROUNDED)
        pnl_table.add_column("Component", style="cyan")
        pnl_table.add_column("Amount", style="white", justify="right")
        
        pnl_table.add_row("Gross P&L", f"${metrics.get('gross_pnl', 0):+,.2f}")
        pnl_table.add_row("Commissions", f"${metrics.get('commissions', 0):+,.2f}")
        pnl_table.add_row("Interest", f"${metrics.get('interest_expense', 0):+,.2f}")
        pnl_table.add_row("Other Fees", f"${metrics.get('other_fees', 0):+,.2f}")
        pnl_table.add_row("Net P&L", f"${metrics.get('net_pnl', 0):+,.2f}", style="bold")
        tables.append(pnl_table)
        
        # Performance Metrics Table
        perf_table = Table(title="Performance Metrics", box=box.ROUNDED)
        perf_table.add_column("Timeframe", style="cyan")
        perf_table.add_column("Win Rate", justify="right")
        perf_table.add_column("Sharpe", justify="right")
        perf_table.add_column("Volatility", justify="right")
        
        for timeframe in ['30d', 'mtd', 'ytd', 'all_time']:
            perf_table.add_row(
                timeframe.upper(),
                f"{metrics.get(f'win_rate_{timeframe}', 0):.1f}%",
                f"{metrics.get(f'sharpe_{timeframe}', 0):.2f}",
                f"{metrics.get(f'volatility_{timeframe}', 0):.1f}%"
            )
        tables.append(perf_table)
        
        # Display all tables in columns
        self.console.print(Columns(tables[:2]))
        self.console.print(Columns([tables[2]]))
        
        # Greeks Panel
        greeks_text = f"""
Delta:  {metrics.get('delta_exposure', 0):>8.3f}  [{'green' if metrics.get('delta_exposure', 0) >= 0 else 'red'}]{'█' * abs(int(metrics.get('delta_exposure', 0) * 10))}[/]
        Gamma:  {metrics.get('gamma_exposure', 0):>8.3f}  [yellow]{'▓' * abs(int(metrics.get('gamma_exposure', 0) * 100))}[/]
        Theta:  {metrics.get('theta_decay', 0):>8.0f}  [green]{'░' * min(10, abs(int(metrics.get('theta_decay', 0) / 10)))}[/]
        Vega:   {metrics.get('vega_exposure', 0):>8.0f}  [blue]{'▒' * min(10, abs(int(metrics.get('vega_exposure', 0) / 10)))}[/]
        """
        self.console.print(Panel(greeks_text, title="Greeks Exposure"))
    
    def _display_gallery_view(self, metrics_list: List[Dict]):
        """Display multiple NFTs in gallery format"""
        
        # Create mini cards for each day
        cards = []
        for metrics in metrics_list[:6]:  # Show max 6 in gallery
            net_pnl = metrics.get('net_pnl', 0)
            color = "green" if net_pnl >= 0 else "red"
            
            mini_card = f"""
┌─────────────┐
│ {metrics.get('date', 'N/A')[:10]:^11} │
├─────────────┤
│ [{color}]${net_pnl:+8.0f}[/{color}] │
│ Win: {metrics.get('win_rate', 0):>5.1f}% │
│ Sharpe: {metrics.get('sharpe_30d', 0):>4.1f} │
└─────────────┘
"""
            cards.append(mini_card)
        
        # Display in columns
        self.console.print(Columns(cards, equal=True, expand=True))
    
    def _display_ascii_art(self, metrics: Dict):
        """Display pure ASCII art representation"""
        
        net_pnl = metrics.get('net_pnl', 0)
        win_rate = metrics.get('win_rate', 0)
        
        # Generate ASCII art based on performance
        if net_pnl > 1000:
            art = """
                    🚀
                   /|\\
                  / | \\
                 /  |  \\
                /___|___\\
               [PROFIT!]
            """
        elif net_pnl > 0:
            art = """
                  📈
                 ╱ ╲
                ╱   ╲
               ╱     ╲
              ╱_______╲
              [GREEN]
            """
        else:
            art = """
                  📉
                 ╲   ╱
                  ╲ ╱
                   X
                  ╱ ╲
                 [LOSS]
            """
        
        # Create full ASCII display
        display = f"""
        ╔═══════════════════════════════════════╗
        ║      FNTX TRADING DAY VISUALIZATION   ║
        ╠═══════════════════════════════════════╣
        ║                                       ║
        ║{art:^39}║
        ║                                       ║
        ║         Date: {metrics.get('date', 'N/A'):^20}    ║
        ║         P&L:  ${net_pnl:+10,.2f}          ║
        ║         Win:  {win_rate:>5.1f}% {'█' * int(win_rate/10):<10}    ║
        ║                                       ║
        ╚═══════════════════════════════════════╝
        """
        
        self.console.print(display)
    
    def _display_shaded_art(self, metrics: Dict):
        """Display shaded pencil-sketch style ASCII art"""
        
        # Generate main shaded art
        shaded_art = self.ascii_generator.generate_trading_nft(metrics)
        
        # Add blockchain info
        blockchain_info = f"""
╔═══════════════════════════════════════════════════════════╗
║                BLOCKCHAIN VERIFICATION                    ║
╠═══════════════════════════════════════════════════════════╣
║  Network: Polygon          Block: #{metrics.get('block_number', 'PENDING')}  ║
║  Token ID: #{metrics.get('token_id', 'N/A')}    Version: {metrics.get('version', 1)}         ║
║  IPFS: {metrics.get('ipfs_hash', 'QmPending...')[:20]}...              ║
╚═══════════════════════════════════════════════════════════╝
"""
        
        # Display everything
        self.console.print(shaded_art)
        self.console.print(blockchain_info)
        
        # Add Greeks visualization
        greeks_visual = self.ascii_generator.generate_greeks_visualization(metrics)
        self.console.print(greeks_visual)
        
        # Add performance meter
        perf_meter = self.ascii_generator.generate_performance_meter(metrics)
        self.console.print(Panel(perf_meter, title="Performance Metrics", box=box.ROUNDED))
    
    def _display_labubu_character(self, metrics: Dict):
        """Display Labubu character based on performance"""
        
        # Get appropriate Labubu
        labubu = self.ascii_generator.generate_labubu_character(metrics)
        
        # Create a nice frame
        net_pnl = metrics.get('net_pnl', 0)
        date = metrics.get('date', 'Unknown')
        
        frame = f"""
╔══════════════════════════════════════════════════╗
║            FNTX TRADING LABUBU                   ║
║              {date:^20}                  ║
╠══════════════════════════════════════════════════╣
{labubu}
╠══════════════════════════════════════════════════╣
║  P&L: ${net_pnl:+10,.2f}      Win Rate: {metrics.get('win_rate', 0):>5.1f}%  ║
║  Sharpe: {metrics.get('sharpe_30d', 0):>6.2f}         Contracts: {metrics.get('contracts_traded', 0):>5}  ║
╚══════════════════════════════════════════════════╝
"""
        
        # Color based on performance
        if net_pnl > 0:
            self.console.print(frame, style="green")
        elif net_pnl < 0:
            self.console.print(frame, style="red")
        else:
            self.console.print(frame, style="yellow")
    
    def _create_ascii_bar_chart(self, values: List[float]) -> str:
        """Create simple ASCII bar chart"""
        
        if not values:
            return "No data available"
        
        # Normalize values
        max_val = max(abs(v) for v in values)
        if max_val == 0:
            max_val = 1
        
        chart_lines = []
        chart_lines.append("  $1000 │")
        chart_lines.append("   $500 │")
        chart_lines.append("     $0 ├" + "─" * (len(values) * 4))
        chart_lines.append("  -$500 │")
        
        # Add bars
        bar_line = "        │"
        for val in values:
            if val >= 0:
                height = int((val / max_val) * 4)
                bar = " " * (4 - height) + "█" * height
                bar_line += bar
            else:
                bar_line += "░░░█"
        
        return "\n".join(chart_lines) + "\n" + bar_line
    
    def _create_greeks_visual(self, metrics: Dict) -> str:
        """Create Greeks exposure visualization"""
        
        delta = metrics.get('delta_exposure', 0)
        gamma = metrics.get('gamma_exposure', 0)
        theta = metrics.get('theta_decay', 0)
        vega = metrics.get('vega_exposure', 0)
        
        visual = f"""
            Greeks Radar
                Δ
                |
                |
        Θ ------+------ Γ
                |
                |
                V
                
        Delta: {delta:>6.2f}
        Gamma: {gamma:>6.3f}
        Theta: {theta:>6.0f}
        Vega:  {vega:>6.0f}
        """
        
        return visual
    
    def _display_progress_bar(self, label: str, value: float, max_value: float, color: str):
        """Display a progress bar"""
        
        progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        )
        
        with progress:
            task = progress.add_task(label, total=max_value)
            progress.update(task, completed=value)
    
    def browse_collection(self, trader_address: str, records: List[Dict]):
        """Interactive NFT collection browser"""
        
        current_index = 0
        
        while True:
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Display current NFT
            self.console.print(f"\n[bold]NFT Collection Browser - {trader_address}[/bold]")
            self.console.print(f"[dim]Showing {current_index + 1} of {len(records)}[/dim]\n")
            
            if records:
                self.display_trading_nft(records[current_index], mode='card')
            
            # Navigation instructions
            self.console.print("\n[dim]Navigation: ← Previous | → Next | Q Quit | C Chart | D Details[/dim]")
            
            # Get user input
            key = input()
            
            if key.lower() == 'q':
                break
            elif key.lower() == 'c':
                self.display_trading_nft(records[current_index], mode='chart')
                input("\nPress Enter to continue...")
            elif key.lower() == 'd':
                self.display_trading_nft(records[current_index], mode='detailed')
                input("\nPress Enter to continue...")
            # Add arrow key navigation logic here


# CLI command integration
async def nft_viewer_command(args):
    """CLI command handler for NFT viewing"""
    
    viewer = TerminalNFTViewer()
    
    # Sample data for demonstration
    sample_metrics = {
        'date': '2025-01-26',
        'net_pnl': 2450.50,
        'opening_balance': 215000,
        'closing_balance': 217450.50,
        'gross_pnl': 2650,
        'commissions': -150,
        'interest_expense': -50,
        'win_rate': 82.5,
        'sharpe_30d': 2.3,
        'volatility_30d': 12.5,
        'contracts_traded': 67,
        'implied_turnover': 3015000,
        'delta_exposure': -0.15,
        'gamma_exposure': 0.023,
        'theta_decay': 125,
        'vega_exposure': -50,
        'token_id': 1,
        'version': 1
    }
    
    if args.mode == 'gallery':
        # Generate multiple days for gallery
        records = []
        for i in range(7):
            record = sample_metrics.copy()
            record['date'] = f"2025-01-{20+i}"
            record['net_pnl'] = sample_metrics['net_pnl'] + (i - 3) * 500
            records.append(record)
        viewer._display_gallery_view(records)
    else:
        viewer.display_trading_nft(sample_metrics, mode=args.mode)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View trading NFTs in terminal')
    parser.add_argument(
        '--mode',
        choices=['card', 'chart', 'detailed', 'gallery', 'ascii'],
        default='card',
        help='Display mode for NFT'
    )
    parser.add_argument(
        '--date',
        help='Date to view (YYYY-MM-DD)'
    )
    
    args = parser.parse_args()
    
    # Run viewer
    asyncio.run(nft_viewer_command(args))