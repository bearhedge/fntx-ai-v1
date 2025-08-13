#!/usr/bin/env python3
"""Debug VIX chart to understand why dots appear at wrong levels"""

from terminal_ui.risk_manager_panel import RiskManagerPanel
import numpy as np

def debug_vix_chart():
    """Debug the VIX chart compression and plotting"""
    panel = RiskManagerPanel()
    
    # Get real VIX data
    print("Fetching VIX data...")
    vix_data = panel.get_vix_mountain_data()
    
    if not vix_data:
        print("No VIX data available")
        return
        
    print(f"\nOriginal data: {len(vix_data)} points")
    print(f"Range: {min(vix_data):.2f} - {max(vix_data):.2f}")
    print(f"Current: {vix_data[-1]:.2f}")
    
    # Simulate the compression algorithm
    chart_width = 23
    compression_ratio = len(vix_data) / chart_width
    compressed_values = []
    
    print(f"\nCompression ratio: {compression_ratio:.1f} points per column")
    print("\nCompressed values by column:")
    
    for i in range(chart_width):
        start_idx = int(i * compression_ratio)
        end_idx = int((i + 1) * compression_ratio)
        if end_idx > start_idx:
            window_values = vix_data[start_idx:end_idx]
            avg_value = sum(window_values) / len(window_values)
            compressed_values.append(avg_value)
        else:
            compressed_values.append(vix_data[min(start_idx, len(vix_data)-1)])
        
        # Print first and last 3 columns, plus middle
        if i < 3 or i >= chart_width - 3 or i == chart_width // 2:
            print(f"Col {i:2d}: {compressed_values[-1]:.2f} (from {len(window_values) if end_idx > start_idx else 1} points)")
    
    print("\n...")
    
    # Check which Y-levels would get dots with different thresholds
    y_levels = [22, 21, 20, 19, 18, 17, 16, 15, 14]
    
    print("\nDot detection with threshold 0.3:")
    for level in y_levels:
        dots_at_level = []
        for i, val in enumerate(compressed_values):
            if abs(val - level) < 0.3:
                dots_at_level.append(i)
        if dots_at_level:
            print(f"Y={level}: dots at columns {dots_at_level}")
    
    print("\nDot detection with threshold 0.5:")
    for level in y_levels:
        dots_at_level = []
        for i, val in enumerate(compressed_values):
            if abs(val - level) < 0.5:
                dots_at_level.append(i)
        if dots_at_level:
            print(f"Y={level}: dots at columns {dots_at_level}")
    
    # Show what the chart looks like
    print("\nActual chart output:")
    chart_lines = panel.create_vix_line_chart(vix_data)
    for line in chart_lines:
        print(line)

if __name__ == "__main__":
    debug_vix_chart()