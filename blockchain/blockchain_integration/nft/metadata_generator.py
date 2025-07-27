"""
NFT Metadata Generator - Creates visual representations of daily trading performance

Generates SVG images and metadata for trading performance NFTs.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple
import math


class TradingNFTGenerator:
    """Generate NFT metadata and visuals from trading data"""
    
    def __init__(self):
        self.color_schemes = {
            'profit': ['#10b981', '#34d399', '#6ee7b7'],  # Green shades
            'loss': ['#ef4444', '#f87171', '#fca5a5'],     # Red shades
            'neutral': ['#6366f1', '#818cf8', '#a5b4fc']   # Blue shades
        }
    
    def generate_metadata(self, 
                         date: str,
                         trading_metrics: Dict,
                         trader_address: str,
                         token_id: int) -> Dict:
        """
        Generate NFT metadata including visual representation
        
        Returns metadata in OpenSea standard format
        """
        
        # Generate SVG image
        svg_image = self.generate_trading_visualization(trading_metrics)
        
        # Calculate rarity traits
        traits = self._calculate_traits(trading_metrics)
        
        metadata = {
            "name": f"FNTX Trading Day #{date}",
            "description": f"Immutable trading performance record for {date}. "
                          f"Net P&L: ${trading_metrics.get('net_pnl', 0):,.2f}",
            "image": f"data:image/svg+xml;base64,{self._encode_svg(svg_image)}",
            "external_url": f"https://fntx.ai/trader/{trader_address}/day/{date}",
            "attributes": traits,
            "properties": {
                "date": date,
                "trader": trader_address,
                "metrics_hash": trading_metrics.get('metrics_hash', ''),
                "version": trading_metrics.get('version', 1),
                "category": "Trading Performance"
            }
        }
        
        return metadata
    
    def generate_trading_visualization(self, metrics: Dict) -> str:
        """
        Generate SVG visualization of trading performance
        
        Creates a unique visual representation based on:
        - P&L (color and size)
        - Volatility (shape complexity)
        - Win rate (pattern density)
        - Greeks (rotation and distortion)
        """
        
        # Determine color scheme
        net_pnl = metrics.get('net_pnl', 0)
        if net_pnl > 100:
            colors = self.color_schemes['profit']
        elif net_pnl < -100:
            colors = self.color_schemes['loss']
        else:
            colors = self.color_schemes['neutral']
        
        # Create SVG
        svg_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg width="800" height="800" viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg">',
            
            # Background
            f'<rect width="800" height="800" fill="#111827"/>',
            
            # Grid pattern
            self._create_grid_pattern(),
        ]
        
        # Central performance circle
        center_x, center_y = 400, 400
        
        # Main performance indicator (size based on turnover)
        turnover = metrics.get('implied_turnover', 1000000)
        main_radius = min(250, 50 + math.log10(max(1, turnover)) * 20)
        
        svg_parts.append(
            f'<circle cx="{center_x}" cy="{center_y}" r="{main_radius}" '
            f'fill="{colors[0]}" opacity="0.8"/>'
        )
        
        # Win rate rings
        win_rate = metrics.get('win_rate', 50)
        num_rings = int(win_rate / 10)
        for i in range(num_rings):
            ring_radius = main_radius + (i + 1) * 15
            svg_parts.append(
                f'<circle cx="{center_x}" cy="{center_y}" r="{ring_radius}" '
                f'fill="none" stroke="{colors[1]}" stroke-width="2" opacity="{0.6 - i*0.05}"/>'
            )
        
        # Greeks visualization (four petals)
        greeks = {
            'delta': metrics.get('delta_exposure', 0),
            'gamma': metrics.get('gamma_exposure', 0),
            'theta': metrics.get('theta_decay', 0),
            'vega': metrics.get('vega_exposure', 0)
        }
        
        for i, (greek, value) in enumerate(greeks.items()):
            angle = i * 90  # 0, 90, 180, 270 degrees
            petal_length = 50 + abs(value) * 100
            petal_x = center_x + petal_length * math.cos(math.radians(angle))
            petal_y = center_y + petal_length * math.sin(math.radians(angle))
            
            svg_parts.append(
                f'<ellipse cx="{center_x}" cy="{center_y}" '
                f'rx="{petal_length/2}" ry="30" '
                f'fill="{colors[2]}" opacity="0.5" '
                f'transform="rotate({angle} {center_x} {center_y})"/>'
            )
        
        # Volatility particles
        volatility = metrics.get('volatility_30d', 10)
        num_particles = int(volatility * 2)
        for i in range(num_particles):
            angle = (360 / num_particles) * i
            distance = main_radius + 50 + (i % 3) * 20
            x = center_x + distance * math.cos(math.radians(angle))
            y = center_y + distance * math.sin(math.radians(angle))
            size = 3 + (i % 3) * 2
            
            svg_parts.append(
                f'<circle cx="{x}" cy="{y}" r="{size}" fill="{colors[1]}" opacity="0.7"/>'
            )
        
        # Performance metrics text
        svg_parts.extend([
            # Date
            f'<text x="400" y="50" text-anchor="middle" fill="white" font-size="24" font-family="monospace">',
            f'{metrics.get("date", "UNKNOWN")}',
            '</text>',
            
            # Net P&L
            f'<text x="400" y="400" text-anchor="middle" fill="white" font-size="32" font-weight="bold" font-family="monospace">',
            f'${net_pnl:+,.0f}',
            '</text>',
            
            # Bottom stats
            f'<text x="200" y="750" text-anchor="middle" fill="{colors[0]}" font-size="16" font-family="monospace">',
            f'Win Rate: {win_rate:.1f}%',
            '</text>',
            
            f'<text x="400" y="750" text-anchor="middle" fill="{colors[0]}" font-size="16" font-family="monospace">',
            f'Sharpe: {metrics.get("sharpe_30d", 0):.2f}',
            '</text>',
            
            f'<text x="600" y="750" text-anchor="middle" fill="{colors[0]}" font-size="16" font-family="monospace">',
            f'Contracts: {metrics.get("contracts_traded", 0)}',
            '</text>',
        ])
        
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    def _create_grid_pattern(self) -> str:
        """Create background grid pattern"""
        
        return '''
        <defs>
            <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
                <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#1f2937" stroke-width="1"/>
            </pattern>
        </defs>
        <rect width="800" height="800" fill="url(#grid)"/>
        '''
    
    def _calculate_traits(self, metrics: Dict) -> List[Dict]:
        """Calculate NFT traits for rarity"""
        
        traits = []
        
        # Performance tier
        net_pnl = metrics.get('net_pnl', 0)
        if net_pnl > 5000:
            performance_tier = "Legendary"
        elif net_pnl > 2000:
            performance_tier = "Epic"
        elif net_pnl > 500:
            performance_tier = "Rare"
        elif net_pnl > 0:
            performance_tier = "Profitable"
        else:
            performance_tier = "Learning"
        
        traits.append({
            "trait_type": "Performance Tier",
            "value": performance_tier
        })
        
        # Win rate category
        win_rate = metrics.get('win_rate', 0)
        if win_rate > 80:
            win_category = "Master"
        elif win_rate > 65:
            win_category = "Expert"
        elif win_rate > 50:
            win_category = "Skilled"
        else:
            win_category = "Developing"
        
        traits.append({
            "trait_type": "Win Rate Category",
            "value": win_category
        })
        
        # Risk profile
        sharpe = metrics.get('sharpe_30d', 0)
        if sharpe > 3:
            risk_profile = "Ultra Efficient"
        elif sharpe > 2:
            risk_profile = "Highly Efficient"
        elif sharpe > 1:
            risk_profile = "Risk Adjusted"
        else:
            risk_profile = "Risk Seeking"
        
        traits.append({
            "trait_type": "Risk Profile",
            "value": risk_profile
        })
        
        # Volume tier
        contracts = metrics.get('contracts_traded', 0)
        if contracts > 100:
            volume_tier = "High Volume"
        elif contracts > 50:
            volume_tier = "Active"
        elif contracts > 10:
            volume_tier = "Moderate"
        else:
            volume_tier = "Conservative"
        
        traits.append({
            "trait_type": "Volume Tier",
            "value": volume_tier
        })
        
        # Special achievements
        if win_rate > 90 and net_pnl > 1000:
            traits.append({
                "trait_type": "Achievement",
                "value": "Perfect Day"
            })
        
        if metrics.get('max_drawdown_30d', -100) > -2:
            traits.append({
                "trait_type": "Achievement", 
                "value": "Risk Master"
            })
        
        # Numeric traits
        traits.extend([
            {
                "trait_type": "Net P&L",
                "value": float(net_pnl),
                "display_type": "number"
            },
            {
                "trait_type": "Win Rate",
                "value": float(win_rate),
                "display_type": "percentage"
            },
            {
                "trait_type": "Sharpe Ratio",
                "value": float(metrics.get('sharpe_30d', 0)),
                "display_type": "number"
            },
            {
                "trait_type": "Contracts Traded",
                "value": int(contracts),
                "display_type": "number"
            }
        ])
        
        return traits
    
    def _encode_svg(self, svg: str) -> str:
        """Encode SVG to base64"""
        import base64
        return base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    
    def generate_collection_metadata(self, trader_address: str) -> Dict:
        """Generate collection-level metadata"""
        
        return {
            "name": "FNTX Trading Chronicles",
            "description": "Immutable on-chain trading performance records. "
                          "Each NFT represents a single day of verified trading activity.",
            "image": "https://fntx.ai/collection-image.png",
            "external_link": f"https://fntx.ai/trader/{trader_address}",
            "seller_fee_basis_points": 250,  # 2.5%
            "fee_recipient": trader_address
        }


# Example usage
if __name__ == "__main__":
    generator = TradingNFTGenerator()
    
    # Sample metrics
    sample_metrics = {
        'date': '2025-01-26',
        'net_pnl': 2450.50,
        'win_rate': 75.5,
        'sharpe_30d': 2.3,
        'contracts_traded': 67,
        'implied_turnover': 3015000,
        'volatility_30d': 12.5,
        'delta_exposure': -0.15,
        'gamma_exposure': 0.02,
        'theta_decay': 125,
        'vega_exposure': -50
    }
    
    # Generate metadata
    metadata = generator.generate_metadata(
        date='2025-01-26',
        trading_metrics=sample_metrics,
        trader_address='0x742d35Cc6634C0532925a3b844Bc9e7595f82f3d',
        token_id=1
    )
    
    # Save example
    with open('/tmp/sample_nft_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("Sample NFT metadata generated!")
    print(f"View at: /tmp/sample_nft_metadata.json")