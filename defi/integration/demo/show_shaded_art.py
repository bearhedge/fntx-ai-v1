#!/usr/bin/env python3
"""
Show Shaded ASCII Art - Demonstrates the new pencil-sketch style NFT visualizations
"""

import sys
sys.path.append('..')
from defi.cli.nft_terminal_viewer import TerminalNFTViewer
from defi.cli.ascii_art_generator import ASCIIArtGenerator
from rich.console import Console
from rich.panel import Panel

def main():
    """Show all shaded ASCII art styles"""
    
    console = Console()
    viewer = TerminalNFTViewer()
    generator = ASCIIArtGenerator()
    
    console.print("\n[bold cyan]🎨 FNTX Shaded ASCII Art NFT Demo[/bold cyan]\n")
    console.print("This shows the pencil-sketch style ASCII art with depth and shading.\n")
    
    # Test different P&L scenarios
    scenarios = [
        {
            'name': 'Big Profit Day - Mountain Peak',
            'metrics': {
                'date': '2025-01-26',
                'net_pnl': 5250.75,
                'opening_balance': 215000,
                'closing_balance': 220250.75,
                'win_rate': 88.5,
                'sharpe_30d': 2.8,
                'contracts_traded': 125,
                'implied_turnover': 5625000,
                'delta_exposure': -0.08,
                'gamma_exposure': 0.015,
                'theta_decay': 285,
                'vega_exposure': -35,
                'token_id': 156,
                'version': 1,
                'block_number': 45123456,
                'ipfs_hash': 'QmXoypizjW3WknFjJnKLwHCnL72vedxjQkDDP'
            }
        },
        {
            'name': 'Moderate Profit - Ocean Waves',
            'metrics': {
                'date': '2025-01-25',
                'net_pnl': 850.25,
                'opening_balance': 215000,
                'closing_balance': 215850.25,
                'win_rate': 72.5,
                'sharpe_30d': 1.9,
                'contracts_traded': 67,
                'implied_turnover': 3015000,
                'delta_exposure': -0.15,
                'gamma_exposure': 0.023,
                'theta_decay': 125,
                'vega_exposure': -50,
                'token_id': 155,
                'version': 1,
                'block_number': 45123000,
                'ipfs_hash': 'QmYjKwHCnL72vedxjQkDDPXoypizjW3WknF'
            }
        },
        {
            'name': 'Neutral Day - Zen Garden',
            'metrics': {
                'date': '2025-01-24',
                'net_pnl': -75.50,
                'opening_balance': 215000,
                'closing_balance': 214924.50,
                'win_rate': 50.0,
                'sharpe_30d': 0.2,
                'contracts_traded': 32,
                'implied_turnover': 1440000,
                'delta_exposure': -0.02,
                'gamma_exposure': 0.005,
                'theta_decay': 45,
                'vega_exposure': -10,
                'token_id': 154,
                'version': 1,
                'block_number': 45122500,
                'ipfs_hash': 'QmL72vedxjQkDDPXoypizjW3WknFjJnKwHCn'
            }
        },
        {
            'name': 'Loss Day - Shadow Valley',
            'metrics': {
                'date': '2025-01-23',
                'net_pnl': -2750.00,
                'opening_balance': 217750,
                'closing_balance': 215000,
                'win_rate': 25.0,
                'sharpe_30d': -1.5,
                'contracts_traded': 89,
                'implied_turnover': 4005000,
                'delta_exposure': -0.35,
                'gamma_exposure': 0.045,
                'theta_decay': -180,
                'vega_exposure': -125,
                'token_id': 153,
                'version': 2,  # Corrected version
                'block_number': 45122000,
                'ipfs_hash': 'QmvedxjQkDDPXoypizjW3WknFjJnKwHCnL72'
            }
        }
    ]
    
    # Show each scenario
    for i, scenario in enumerate(scenarios):
        if i > 0:
            console.print("\n" + "="*80 + "\n")
        
        console.print(f"[bold yellow]{scenario['name']}[/bold yellow]\n")
        
        # Show shaded art view
        console.print("[cyan]Shaded ASCII Art View:[/cyan]")
        viewer.display_trading_nft(scenario['metrics'], mode='shaded')
        
        console.print("\n[cyan]Labubu Character View:[/cyan]")
        viewer.display_trading_nft(scenario['metrics'], mode='labubu')
    
    # Show the shading palette
    console.print("\n" + "="*80 + "\n")
    console.print("[bold yellow]ASCII Shading Palette Examples[/bold yellow]\n")
    
    palette_demo = """
Light to Dark Gradient:
  [ ] → [·] → [:] → [░] → [▒] → [▓] → [█]

Texture Examples:
  Clouds:    ·∴∵∴·  ∴∵∴∵∴  ∵∴∵∴∵
  Waves:     ░▒▓▓▒░  ▒▓██▓▒  ▓████▓
  Mountains: ▄███▄  ▄█████▄  ▄███████▄
  Shadows:   ▓▓▓▓▓  ▒▒▒▒▒▒▒  ░░░░░░░░░

Special Effects:
  Energy:    ◢◣◤◥  ◆◇◆◇  ○●○●
  Sparkles:  ✦✧★☆  ✨✨✨  ·˙⁺˙·
  Money:     $$$$$  €€€€€  ₿₿₿₿₿
"""
    
    console.print(Panel(palette_demo, title="Shading Techniques", expand=False))
    
    # Connection to blockchain
    console.print("\n[bold green]Blockchain Integration[/bold green]")
    console.print("""
Each ASCII art NFT is connected to the blockchain:

1. [cyan]On-Chain Data[/cyan]: Transaction hash, block number, token ID
2. [cyan]IPFS Storage[/cyan]: Full 36 metrics + ASCII art stored on IPFS
3. [cyan]CLI Display[/cyan]: Rich terminal visualization of on-chain NFT
4. [cyan]Verification[/cyan]: Anyone can verify via Polygonscan + IPFS hash

The CLI displays what's stored immutably on the blockchain,
making your trading performance both beautiful and verifiable.
""")


if __name__ == "__main__":
    main()