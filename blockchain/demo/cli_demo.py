#!/usr/bin/env python3
"""
CLI Demo - Shows how the blockchain signature system works in terminal

This demonstrates the complete flow from preview to submission to NFT viewing.
"""

import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint

# Import our components
sys.path.append('..')
from blockchain_integration.verification.preview_tool import SignaturePreviewTool
from cli.nft_terminal_viewer import TerminalNFTViewer


class FNTXCliDemo:
    """Interactive demo of the FNTX blockchain signature system"""
    
    def __init__(self):
        self.console = Console()
        self.preview_tool = SignaturePreviewTool()
        self.nft_viewer = TerminalNFTViewer()
        
    async def run(self):
        """Run the interactive demo"""
        
        self.console.clear()
        self.console.print(Panel.fit(
            "[bold cyan]FNTX Blockchain Signature System Demo[/bold cyan]\n\n"
            "This demo shows how trading signatures work in the CLI",
            border_style="cyan"
        ))
        
        while True:
            self.console.print("\n[bold]Choose an option:[/bold]")
            self.console.print("1. Preview today's signature")
            self.console.print("2. View NFT gallery")
            self.console.print("3. Submit signature (testnet)")
            self.console.print("4. Correct a signature")
            self.console.print("5. View detailed metrics")
            self.console.print("6. Exit")
            
            choice = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6"])
            
            if choice == "1":
                await self.preview_signature()
            elif choice == "2":
                self.view_nft_gallery()
            elif choice == "3":
                await self.submit_signature()
            elif choice == "4":
                await self.correct_signature()
            elif choice == "5":
                self.view_detailed_metrics()
            elif choice == "6":
                break
            
            if choice != "6":
                input("\nPress Enter to continue...")
                self.console.clear()
    
    async def preview_signature(self):
        """Demo: Preview signature before submission"""
        
        self.console.print("\n[bold yellow]Previewing Today's Trading Signature[/bold yellow]\n")
        
        # Sample data
        date = datetime.now()
        trading_data = {
            'net_pnl': Decimal('2450.50'),
            'gross_pnl': Decimal('2650.00'),
            'commissions': Decimal('-150.00'),
            'interest_expense': Decimal('-50.00'),
            'win_rate_30d': 82.5,
            'sharpe_ratio_30d': 2.3,
            'contracts_traded': 67,
            'implied_turnover': Decimal('3015000'),
            'trading_day_num': 156,
        }
        
        market_data = {'spy_price': Decimal('450.25'), 'vix': 15.2}
        account_data = {
            'opening_balance': Decimal('215000'),
            'closing_balance': Decimal('217450.50'),
            'deposits': Decimal('0'),
            'withdrawals': Decimal('0'),
        }
        
        # Generate preview
        preview = await self.preview_tool.preview_signature(
            date, trading_data, market_data, account_data
        )
        
        # Display preview
        self.preview_tool.display_preview(preview)
        
        if preview.verification.is_valid:
            self.console.print("\n[green]✓ Ready to submit to blockchain![/green]")
        else:
            self.console.print("\n[red]✗ Please fix errors before submitting[/red]")
    
    def view_nft_gallery(self):
        """Demo: View NFT gallery"""
        
        self.console.print("\n[bold yellow]NFT Gallery View[/bold yellow]\n")
        
        # Generate sample NFTs for multiple days
        records = []
        base_pnl = 1500
        
        for i in range(7):
            day_pnl = base_pnl + (i - 3) * 500
            record = {
                'date': f"2025-01-{20+i}",
                'net_pnl': day_pnl,
                'win_rate': 65 + i * 3,
                'sharpe_30d': 1.5 + i * 0.2,
                'contracts_traded': 40 + i * 5,
                'implied_turnover': 2000000 + i * 200000,
                'delta_exposure': -0.1 + i * 0.02,
                'gamma_exposure': 0.01 + i * 0.002,
                'theta_decay': 100 + i * 10,
                'vega_exposure': -40 + i * 5,
            }
            records.append(record)
        
        # Show gallery
        self.nft_viewer._display_gallery_view(records)
        
        # Ask if user wants to see detailed view
        if Confirm.ask("\nView a specific day in detail?"):
            day = Prompt.ask("Enter day (20-26)", choices=[str(i) for i in range(20, 27)])
            index = int(day) - 20
            
            self.console.clear()
            self.console.print(f"\n[bold]Detailed View - January {day}, 2025[/bold]\n")
            
            # Show different view modes
            modes = ['card', 'chart', 'detailed', 'ascii']
            for mode in modes:
                self.console.print(f"\n[cyan]View Mode: {mode.upper()}[/cyan]")
                self.nft_viewer.display_trading_nft(records[index], mode=mode)
                
                if mode != modes[-1]:
                    if not Confirm.ask("\nShow next view mode?"):
                        break
    
    async def submit_signature(self):
        """Demo: Submit signature to blockchain"""
        
        self.console.print("\n[bold yellow]Submitting Signature to Testnet[/bold yellow]\n")
        
        # Simulate submission process
        with self.console.status("[cyan]Preparing signature data...") as status:
            await asyncio.sleep(1)
            status.update("[cyan]Verifying data integrity...")
            await asyncio.sleep(1)
            status.update("[cyan]Generating Merkle tree...")
            await asyncio.sleep(1)
            status.update("[cyan]Submitting to blockchain...")
            await asyncio.sleep(2)
        
        # Show result
        tx_hash = "0x742d35cc6634c0532925a3b844bc9e7595f82f3d1234567890abcdef"
        self.console.print(Panel(
            f"[green]✓ Signature submitted successfully![/green]\n\n"
            f"Transaction Hash: [cyan]{tx_hash}[/cyan]\n"
            f"Block Number: 45,123,456\n"
            f"Gas Used: 245,678\n"
            f"FNTX Burned: 10\n\n"
            f"[yellow]Grace Period Active:[/yellow] 23 hours 45 minutes remaining\n"
            f"You can correct this signature until tomorrow at 00:00 UTC",
            title="Submission Complete",
            border_style="green"
        ))
        
        # Show NFT
        self.console.print("\n[bold]Your NFT has been minted:[/bold]")
        sample_nft = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'net_pnl': 2450.50,
            'win_rate': 82.5,
            'sharpe_30d': 2.3,
            'contracts_traded': 67,
            'token_id': 156,
            'version': 1,
        }
        self.nft_viewer.display_trading_nft(sample_nft, mode='ascii')
    
    async def correct_signature(self):
        """Demo: Correct a signature within grace period"""
        
        self.console.print("\n[bold yellow]Correcting a Signature[/bold yellow]\n")
        
        # Show current signature
        self.console.print("[dim]Current signature on blockchain:[/dim]")
        self.console.print("Date: 2025-01-25")
        self.console.print("Net P&L: [red]$1,250.50[/red] (incorrect)")
        self.console.print("Version: 1")
        self.console.print("Grace Period: [green]18 hours remaining[/green]")
        
        if Confirm.ask("\nCorrect this signature?"):
            self.console.print("\n[cyan]New values:[/cyan]")
            self.console.print("Net P&L: [green]$2,450.50[/green] (corrected)")
            
            with self.console.status("[cyan]Burning old NFT and minting new one...") as status:
                await asyncio.sleep(2)
                status.update("[cyan]Submitting corrected data...")
                await asyncio.sleep(2)
            
            self.console.print(Panel(
                "[green]✓ Signature corrected successfully![/green]\n\n"
                "Version updated: 1 → 2\n"
                "FNTX burned for correction: 5\n"
                "Old NFT burned, new NFT minted",
                title="Correction Complete",
                border_style="green"
            ))
    
    def view_detailed_metrics(self):
        """Demo: View detailed metrics"""
        
        self.console.print("\n[bold yellow]Detailed Metrics View[/bold yellow]\n")
        
        metrics = {
            'date': '2025-01-26',
            'trading_day_num': 156,
            'opening_balance': 215000,
            'closing_balance': 217450.50,
            'deposits': 0,
            'withdrawals': 0,
            'gross_pnl': 2650,
            'commissions': -150,
            'interest_expense': -50,
            'net_pnl': 2450.50,
            'win_rate_30d': 82.5,
            'win_rate_mtd': 79.2,
            'win_rate_ytd': 77.8,
            'win_rate_all_time': 75.5,
            'sharpe_30d': 2.3,
            'sharpe_mtd': 2.1,
            'sharpe_ytd': 1.9,
            'sharpe_all_time': 1.8,
            'volatility_30d': 12.5,
            'volatility_mtd': 11.8,
            'volatility_ytd': 10.9,
            'volatility_all_time': 10.2,
            'contracts_traded': 67,
            'implied_turnover': 3015000,
            'delta_exposure': -0.15,
            'gamma_exposure': 0.023,
            'theta_decay': 125,
            'vega_exposure': -50,
            'dpi': 0.075,
            'tvpi': 1.087,
            'rvpi': 1.087,
        }
        
        self.nft_viewer._display_detailed_view(metrics)


async def main():
    """Run the demo"""
    demo = FNTXCliDemo()
    
    try:
        await demo.run()
    except KeyboardInterrupt:
        demo.console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        demo.console.print(f"\n[red]Error: {e}[/red]")
    finally:
        demo.console.print("\n[cyan]Thank you for trying the FNTX CLI demo![/cyan]")


if __name__ == "__main__":
    asyncio.run(main())