"""
Preview Tool - Allows traders to preview their daily signature before blockchain submission

This tool validates data, shows what will be posted, and estimates costs.
"""

import json
import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
import asyncio

from ..signatures.data_verifier import DataVerifier, VerificationResult
from ..signatures.merkle_tree import TradingDataMerkleTree


@dataclass
class PreviewResult:
    """Result of signature preview"""
    date: str
    metrics_hash: str
    key_metrics: Dict
    verification: VerificationResult
    estimated_gas: int
    fntx_cost: int
    warnings: List[str]
    
    
class SignaturePreviewTool:
    """Tool for previewing trading signatures before submission"""
    
    def __init__(self):
        self.console = Console()
        self.verifier = DataVerifier()
        
    async def preview_signature(self,
                              date: datetime,
                              trading_data: Dict,
                              market_data: Dict,
                              account_data: Dict) -> PreviewResult:
        """
        Preview what will be posted to blockchain
        
        Shows:
        - Data validation results
        - Key metrics that will be stored on-chain
        - Metrics hash
        - Estimated costs
        - Warnings/suggestions
        """
        
        # Step 1: Run verification
        verification = await self.verifier.verify_data_integrity(
            trading_data, market_data, account_data
        )
        
        # Step 2: Calculate key on-chain metrics
        key_metrics = self._extract_key_metrics(trading_data, account_data)
        
        # Step 3: Generate metrics hash (what goes on-chain)
        all_metrics = self._compile_all_metrics(date, trading_data, market_data, account_data)
        merkle_tree = TradingDataMerkleTree(all_metrics)
        metrics_hash = merkle_tree.root
        
        # Step 4: Estimate costs
        estimated_gas = 250000  # Approximate gas for posting
        fntx_cost = 10  # 10 FNTX tokens
        
        # Step 5: Generate warnings
        warnings = self._generate_warnings(trading_data, account_data, verification)
        
        result = PreviewResult(
            date=date.strftime('%Y-%m-%d'),
            metrics_hash=metrics_hash,
            key_metrics=key_metrics,
            verification=verification,
            estimated_gas=estimated_gas,
            fntx_cost=fntx_cost,
            warnings=warnings
        )
        
        return result
    
    def display_preview(self, preview: PreviewResult):
        """Display preview in a formatted way"""
        
        # Create main layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="verification", size=8),
            Layout(name="metrics", size=12),
            Layout(name="costs", size=6),
            Layout(name="warnings", size=6)
        )
        
        # Header
        header = Panel(
            f"[bold cyan]Trading Signature Preview[/bold cyan]\n"
            f"Date: {preview.date}",
            box=box.ROUNDED
        )
        layout["header"].update(header)
        
        # Verification Status
        if preview.verification.is_valid:
            verification_panel = Panel(
                "[bold green]✓ Data Verification Passed[/bold green]\n\n"
                "All mathematical checks passed\n"
                "All logical constraints satisfied\n"
                "Cross-references validated",
                title="Verification Status",
                border_style="green"
            )
        else:
            error_list = "\n".join([f"• {error}" for error in preview.verification.errors[:5]])
            verification_panel = Panel(
                f"[bold red]✗ Data Verification Failed[/bold red]\n\n"
                f"Errors found:\n{error_list}",
                title="Verification Status",
                border_style="red"
            )
        layout["verification"].update(verification_panel)
        
        # Key Metrics Table
        metrics_table = Table(title="Key On-Chain Metrics", box=box.ROUNDED)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="white")
        
        metrics_table.add_row("Net P&L", f"${preview.key_metrics['net_pnl']:,.2f}")
        metrics_table.add_row("Ending Balance", f"${preview.key_metrics['balance_end']:,.2f}")
        metrics_table.add_row("Win Rate (30d)", f"{preview.key_metrics['win_rate']}%")
        metrics_table.add_row("Sharpe Ratio (30d)", f"{preview.key_metrics['sharpe_30d']}")
        metrics_table.add_row("Contracts Traded", f"{preview.key_metrics['contracts_traded']:,}")
        metrics_table.add_row("Implied Turnover", f"${preview.key_metrics['implied_turnover']:,.2f}")
        metrics_table.add_row("Metrics Hash", f"{preview.metrics_hash[:16]}...")
        
        layout["metrics"].update(Panel(metrics_table, title="What Goes On-Chain"))
        
        # Cost Estimation
        cost_table = Table(box=box.SIMPLE)
        cost_table.add_column("Cost Type", style="yellow")
        cost_table.add_column("Amount", style="white")
        
        cost_table.add_row("FNTX Tokens", f"{preview.fntx_cost} FNTX")
        cost_table.add_row("Estimated Gas", f"{preview.estimated_gas:,} units")
        cost_table.add_row("Network", "Polygon (MATIC)")
        
        layout["costs"].update(Panel(cost_table, title="Estimated Costs", border_style="yellow"))
        
        # Warnings
        if preview.warnings:
            warning_text = "\n".join([f"⚠️  {warning}" for warning in preview.warnings[:5]])
        else:
            warning_text = "[green]No warnings - ready to submit![/green]"
        
        layout["warnings"].update(Panel(warning_text, title="Warnings & Suggestions"))
        
        # Print the layout
        self.console.print(layout)
        
        # Show submit command
        if preview.verification.is_valid:
            self.console.print("\n[bold green]Ready to submit![/bold green]")
            self.console.print("Run: [cyan]fntx signature submit --date " + preview.date + "[/cyan]")
        else:
            self.console.print("\n[bold red]Please fix errors before submitting[/bold red]")
    
    def _extract_key_metrics(self, trading_data: Dict, account_data: Dict) -> Dict:
        """Extract the key metrics that go on-chain"""
        
        return {
            'net_pnl': float(trading_data.get('net_pnl', 0)),
            'balance_end': float(account_data.get('closing_balance', 0)),
            'win_rate': float(trading_data.get('win_rate_30d', 0)),
            'sharpe_30d': float(trading_data.get('sharpe_ratio_30d', 0)),
            'contracts_traded': int(trading_data.get('contracts_traded', 0)),
            'implied_turnover': float(trading_data.get('implied_turnover', 0))
        }
    
    def _compile_all_metrics(self, date: datetime, trading_data: Dict, 
                           market_data: Dict, account_data: Dict) -> Dict:
        """Compile all 36 metrics for hashing"""
        
        # This would include all 36 fields as defined in the contract
        # Simplified for demo
        metrics = {
            'date': date.strftime('%Y%m%d'),
            'timestamp': int(date.timestamp()),
            'trading_day_num': trading_data.get('trading_day_num', 1),
            **self._extract_key_metrics(trading_data, account_data),
            # ... add all other fields
        }
        
        return metrics
    
    def _generate_warnings(self, trading_data: Dict, account_data: Dict, 
                         verification: VerificationResult) -> List[str]:
        """Generate helpful warnings and suggestions"""
        
        warnings = []
        
        # Add verification warnings
        warnings.extend(verification.warnings)
        
        # Check for common issues
        if trading_data.get('contracts_traded', 0) == 0:
            warnings.append("No trading activity recorded for this day")
        
        win_rate = trading_data.get('win_rate_30d', 0)
        if win_rate > 90:
            warnings.append(f"Unusually high win rate ({win_rate}%) - please verify")
        
        sharpe = trading_data.get('sharpe_ratio_30d', 0)
        if sharpe > 5:
            warnings.append(f"Very high Sharpe ratio ({sharpe}) - please verify calculations")
        
        # Check balance consistency
        deposits = account_data.get('deposits', 0)
        withdrawals = account_data.get('withdrawals', 0)
        if deposits > 0 or withdrawals > 0:
            warnings.append(f"Account had cash flows: +${deposits:,.2f} / -${withdrawals:,.2f}")
        
        return warnings


async def preview_command(date_str: str):
    """Command line interface for preview tool"""
    
    # Parse date
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Load data (would come from backend.data.database/calculation engine)
    trading_data = {
        'net_pnl': 1250.50,
        'win_rate_30d': 67.5,
        'sharpe_ratio_30d': 2.1,
        'contracts_traded': 45,
        'implied_turnover': 2025000,
        'trading_day_num': 156,
        # ... other fields
    }
    
    market_data = {
        'spy_price': 450.25,
        'vix': 15.2,
        # ... other fields
    }
    
    account_data = {
        'opening_balance': 215000,
        'closing_balance': 216250.50,
        'deposits': 0,
        'withdrawals': 0,
        # ... other fields
    }
    
    # Create preview tool
    tool = SignaturePreviewTool()
    
    # Generate preview
    preview = await tool.preview_signature(date, trading_data, market_data, account_data)
    
    # Display results
    tool.display_preview(preview)


# Example of how to integrate with CLI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        asyncio.run(preview_command(sys.argv[1]))
    else:
        print("Usage: python preview_tool.py YYYY-MM-DD")