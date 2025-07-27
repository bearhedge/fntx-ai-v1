"""
ASCII Art Generator - Creates shaded, pencil-sketch style ASCII art for trading NFTs

This module provides rich ASCII art generation with depth, shading, and texture.
"""

from typing import Dict, List, Tuple, Optional
import math
from datetime import datetime


class ASCIIArtGenerator:
    """Generate shaded ASCII art with pencil-sketch aesthetic"""
    
    def __init__(self):
        # Character palettes for different shading levels
        self.shading_palette = {
            'light': ' ·˙⁺',
            'medium_light': '·:;+=',
            'medium': '░▒▓▓▒░',
            'medium_dark': '▓█▓▒░▒▓',
            'dark': '█████',
            'gradient': ' ·:;+=xX#%@█',
            'texture': '░▒▓█▀▄▌▐│',
            'dots': '⣀⣄⣤⣦⣶⣷⣿',
        }
        
        # Special effect characters
        self.effects = {
            'sparkle': '✦✧★☆✨',
            'energy': '◢◣◤◥◆◇',
            'shapes': '○●□■▪▫',
            'arrows': '↑↗→↘↓↙←↖',
            'money': '$¢£¥€₿',
        }
        
    def generate_trading_nft(self, metrics: Dict) -> str:
        """Generate main trading NFT with shaded aesthetic"""
        
        net_pnl = metrics.get('net_pnl', 0)
        
        if net_pnl > 1000:
            return self._generate_profit_mountain(metrics)
        elif net_pnl > 0:
            return self._generate_profit_waves(metrics)
        elif net_pnl > -1000:
            return self._generate_neutral_zen(metrics)
        else:
            return self._generate_loss_valley(metrics)
    
    def _generate_profit_mountain(self, metrics: Dict) -> str:
        """Generate mountain/peak design for big profit days"""
        
        pnl = metrics.get('net_pnl', 0)
        date = metrics.get('date', 'UNKNOWN')
        
        # Dynamic mountain height based on profit
        peak_height = min(10, 5 + int(pnl / 500))
        
        art = f"""
█████████████████████████████████████████████████████████████
██                    FNTX TRADING DAY                     ██
██                     {date:^10}                        ██
█████████████████████████████████████████████████████████████
██                                                         ██
██                         ▄█▄                             ██
██                        ▄███▄                            ██
██                       ▄█████▄      +${pnl:,.0f}           ██
██                      ▄███▓███▄                          ██
██                     ▄█████████▄                         ██
██                    ▄███▓█▓█▓███▄                        ██
██                   ▄█████████████▄                       ██
██                  ▄███▓█▓███▓█▓███▄                      ██
██                 ▄█████████████████▄                     ██
██                ▄███▓█▓█████▓█▓█▓███▄                    ██
██               ▄███████████████████████▄                 ██
██              ░░▒▒▓▓███████████████▓▓▒▒░░                ██
██             ░░░░░░▒▒▒▓▓▓▓▓▓▓▓▓▒▒▒░░░░░░               ██
██                                                         ██
██  Win Rate: {metrics.get('win_rate', 0):>5.1f}% ████████████░░░  Sharpe: {metrics.get('sharpe_30d', 0):>4.1f}  ██
██                                                         ██
█████████████████████████████████████████████████████████████
"""
        return art
    
    def _generate_profit_waves(self, metrics: Dict) -> str:
        """Generate wave pattern for moderate profit days"""
        
        pnl = metrics.get('net_pnl', 0)
        win_rate = metrics.get('win_rate', 0)
        
        # Create wave effect with shading
        wave_chars = "░▒▓█▓▒░"
        wave_offset = int(pnl / 100) % len(wave_chars)
        
        art = f"""
╔═══════════════════════════════════════════════════════════╗
║                    PROFIT WAVES                           ║
║                  +${pnl:>8,.2f}                            ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║     ░░▒▒▓▓██▓▓▒▒░░      ░░▒▒▓▓██▓▓▒▒░░                  ║
║   ░▒▓█████████████▓▒░  ░▒▓█████████████▓▒░               ║
║  ▒▓███████████████████▓▓███████████████████▓▒             ║
║ ▓█████████████████████████████████████████████▓           ║
║█████████████████████████████████████████████████          ║
║ ▓█████████████████████████████████████████████▓           ║
║  ▒▓███████████████████▓▓███████████████████▓▒             ║
║   ░▒▓█████████████▓▒░  ░▒▓█████████████▓▒░               ║
║     ░░▒▒▓▓██▓▓▒▒░░      ░░▒▒▓▓██▓▓▒▒░░                  ║
║                                                           ║
║  Performance Bar: {"█" * int(win_rate/5)}{"░" * (20-int(win_rate/5))}   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
        return art
    
    def _generate_neutral_zen(self, metrics: Dict) -> str:
        """Generate zen garden pattern for neutral days"""
        
        art = f"""
┌─────────────────────────────────────────────────────────┐
│                    ZEN TRADING                          │
│                   ≈ BALANCED ≈                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                  │
│       ░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░                │
│      ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒               │
│     ▓███████████████████████████████████▓              │
│     ████░░░░░░░░█████░░░░░░░░░█████░░░░██              │
│     ████░░◯░░░░░█████░░░◯░░░░░█████░░◯░██              │
│     ████░░░░░░░░█████░░░░░░░░░█████░░░░██              │
│     ▓███████████████████████████████████▓              │
│      ▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒               │
│       ░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░                │
│         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                  │
│                                                         │
│      P&L: ${metrics.get('net_pnl', 0):+8,.2f}     Balance: ${metrics.get('closing_balance', 0):,.0f}  │
│                                                         │
└─────────────────────────────────────────────────────────┘
"""
        return art
    
    def _generate_loss_valley(self, metrics: Dict) -> str:
        """Generate valley/shadow design for loss days"""
        
        loss = abs(metrics.get('net_pnl', 0))
        
        art = f"""
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
▓▓                      SHADOW DAY                        ▓▓
▓▓                    -${loss:>8,.2f}                        ▓▓
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
▓▓█████████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█████████████████▓▓
▓▓███████████████▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓███████████████▓▓
▓▓█████████████▓▒░░░░░░░░░░░░░░░░░░░░░░░▒▓█████████████▓▓
▓▓███████████▓▒░░                        ░░▒▓███████████▓▓
▓▓█████████▓▒░                              ░▒▓█████████▓▓
▓▓███████▓▒░        ▼ -${loss:,.0f} ▼           ░▒▓███████▓▓
▓▓█████▓▒░                                    ░▒▓█████▓▓
▓▓███▓▒░            ░░░░░░░░░░░░░░            ░▒▓███▓▓
▓▓█▓▒░          ░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░          ░▒▓█▓▓
▓▓▒░        ░░▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░░        ░▒▓▓
▓▓░     ░░▒▒▓▓███████████████████████▓▓▒▒░░     ░▓▓
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
"""
        return art
    
    def generate_labubu_character(self, metrics: Dict) -> str:
        """Generate Labubu character with shading based on performance"""
        
        pnl = metrics.get('net_pnl', 0)
        
        if pnl > 1000:
            return self._happy_labubu(metrics)
        elif pnl > 0:
            return self._content_labubu(metrics)
        elif pnl > -1000:
            return self._zen_labubu(metrics)
        else:
            return self._sad_labubu(metrics)
    
    def _happy_labubu(self, metrics: Dict) -> str:
        """Happy Labubu for profit days"""
        
        return """
        ░░░░░▒▒▒▒▒▒▒▒▒░░░░░
      ░▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒░
    ░▒▓███████████████████▓▒░
   ▒▓█████████████████████████▓▒
  ▒████████████████████████████▓▒
 ▒██████▓▒░░░▒███▓▒░░░▒████████▒
 ▓█████▒░ ● ░▒███▒░ ● ░▒███████▓
 ██████▒░░░░░▒███▒░░░░░▒████████
 ██████▓▒▒▒▒▓█████▓▒▒▒▒▓████████
 ███████████████████████████████
 ▓██████╰─────────────╯████████▓
 ▒███████ ▀▀▀▀▀▀▀▀▀▀▀ ████████▒
  ▒███████████████████████████▒
   ▒▓█████████████████████████▓▒
    ░▒▓███████████████████▓▒░
      ░▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒░
        ░░░░░▒▒▒▒▒▒▒░░░░░
"""
    
    def _content_labubu(self, metrics: Dict) -> str:
        """Content Labubu for small profit days"""
        
        return """
      ░░▒▒▒▒▒▒▒▒▒▒▒▒▒░░
    ░▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒░
   ▒▓████████████████████▓▒
  ▒████████████████████████▒
 ▒██████░░░░███░░░░████████▒
 ▓█████░ ▪ ░███░ ▪ ░███████▓
 ██████░░░░░███░░░░░████████
 ████████████████████████████
 ███████ ─────────── ████████
 ▓██████             ███████▓
 ▒██████████████████████████▒
  ▒████████████████████████▒
   ▒▓████████████████████▓▒
    ░▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒░
      ░░▒▒▒▒▒▒▒▒▒▒▒▒▒░░
"""
    
    def _zen_labubu(self, metrics: Dict) -> str:
        """Zen Labubu for neutral days"""
        
        return """
      ·∴∵∴∵∴∵∴∵∴∵∴·
    ∴░▒▒▒▒▒▒▒▒▒▒▒▒▒░∴
   ∵▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒∵
  ·▓███████████████████▓·
  ▓█████ ─ ███ ─ ██████▓
  ██████   ███   ███████
  ██████▒▒▒███▒▒▒███████
  ███████████████████████
  ███████ ━━━━━━━ ███████
  ▓██████         ██████▓
  ·▓█████████████████████▓·
   ∵▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒∵
    ∴░▒▒▒▒▒▒▒▒▒▒▒▒▒░∴
      ·∴∵∴∵∴∵∴∵∴∵∴·
"""
    
    def _sad_labubu(self, metrics: Dict) -> str:
        """Sad Labubu for loss days"""
        
        return """
      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
    ▓▓█████████████████▓▓
   ▓████████████████████▓
  ▓██████████████████████▓
 ▓████████▀▀███▀▀████████▓
 ███████▌ ● ███ ● ▐███████
 ███████▄▄▄▄███▄▄▄▄███████
 █████████████████████████
 ███████ ╭─────────╮ █████
 ▓██████ │ ∩   ∩ │ █████▓
 ▓██████ ╰─────────╯ █████▓
  ▓██████ ˇ     ˇ ██████▓
   ▓████████████████████▓
    ▓▓█████████████████▓▓
      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
"""
    
    def generate_greeks_visualization(self, metrics: Dict) -> str:
        """Generate shaded visualization for Greeks"""
        
        delta = metrics.get('delta_exposure', 0)
        gamma = metrics.get('gamma_exposure', 0)
        theta = metrics.get('theta_decay', 0)
        vega = metrics.get('vega_exposure', 0)
        
        # Normalize values for visualization
        d_bar = self._create_shaded_bar(delta, -1, 1, 20)
        g_bar = self._create_shaded_bar(gamma * 100, -0.1, 0.1, 20)
        t_bar = self._create_shaded_bar(theta, -200, 200, 20)
        v_bar = self._create_shaded_bar(vega, -100, 100, 20)
        
        art = f"""
╔═══════════════════════════════════════╗
║         GREEKS EXPOSURE               ║
╠═══════════════════════════════════════╣
║                                       ║
║  Delta  Δ │{d_bar}│ {delta:>6.3f}  ║
║  Gamma  Γ │{g_bar}│ {gamma:>6.3f}  ║
║  Theta  Θ │{t_bar}│ {theta:>6.0f}  ║
║  Vega   V │{v_bar}│ {vega:>6.0f}  ║
║                                       ║
╚═══════════════════════════════════════╝
"""
        return art
    
    def _create_shaded_bar(self, value: float, min_val: float, max_val: float, width: int) -> str:
        """Create a shaded progress bar"""
        
        # Normalize value to 0-1 range
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))
        
        # Calculate filled portion
        filled = int(normalized * width)
        
        # Create bar with shading
        if value > 0:
            bar = "░" * (width // 2 - filled) + "▒" * min(2, filled) + "▓" * max(0, filled - 2) + "█" * min(2, max(0, filled - 4))
            bar = bar + " " * (width - len(bar))
        else:
            bar = " " * (width // 2 + filled) + "█" * min(2, -filled) + "▓" * max(0, -filled - 2) + "▒" * min(2, max(0, -filled - 4))
            bar = bar + "░" * (width - len(bar))
        
        return bar
    
    def generate_performance_meter(self, metrics: Dict) -> str:
        """Generate a shaded performance meter"""
        
        win_rate = metrics.get('win_rate', 0)
        sharpe = metrics.get('sharpe_30d', 0)
        
        # Create visual meters
        win_meter = self._create_meter(win_rate, 0, 100, "Win Rate")
        sharpe_meter = self._create_meter(sharpe * 20, -100, 100, "Sharpe")
        
        return f"""
{win_meter}
{sharpe_meter}
"""
    
    def _create_meter(self, value: float, min_val: float, max_val: float, label: str) -> str:
        """Create a visual meter with shading"""
        
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))
        filled = int(normalized * 30)
        
        meter = f"{label:>10}: "
        meter += "░" * max(0, 15 - filled)
        meter += "▒" * min(5, filled)
        meter += "▓" * min(10, max(0, filled - 5))
        meter += "█" * max(0, filled - 15)
        meter += "░" * max(0, 30 - filled)
        meter += f" {value:>6.1f}"
        
        return meter


# Utility function to test different styles
def demonstrate_styles():
    """Show different ASCII art styles"""
    
    generator = ASCIIArtGenerator()
    
    # Test metrics
    test_cases = [
        {"name": "Big Profit", "net_pnl": 5000, "win_rate": 85, "sharpe_30d": 2.5},
        {"name": "Small Profit", "net_pnl": 500, "win_rate": 70, "sharpe_30d": 1.8},
        {"name": "Neutral", "net_pnl": 50, "win_rate": 50, "sharpe_30d": 0.5},
        {"name": "Big Loss", "net_pnl": -2000, "win_rate": 30, "sharpe_30d": -1.2},
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Test Case: {test['name']}")
        print(f"{'='*60}")
        
        # Add required fields
        metrics = {
            **test,
            'date': '2025-01-26',
            'closing_balance': 100000 + test['net_pnl'],
            'delta_exposure': -0.15,
            'gamma_exposure': 0.02,
            'theta_decay': 125,
            'vega_exposure': -50,
        }
        
        # Generate art
        print(generator.generate_trading_nft(metrics))
        print(generator.generate_labubu_character(metrics))
        print(generator.generate_greeks_visualization(metrics))


if __name__ == "__main__":
    demonstrate_styles()