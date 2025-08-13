"""
ASCII Chart Components for FNTX Trading CLI
"""
from typing import List
from .ascii_art import SPARKLINE_CHARS, BOX_CHARS

def create_vix_chart(values: List[float], width: int = 23, height: int = 9) -> List[str]:
    """Create VIX line chart similar to terminal UI"""
    if not values or len(values) < 2:
        return [
            "22┤" + " " * width,
            "21┤" + " " * width,
            "20├" + "─" * width,
            "19┤   Loading Data..." + " " * (width - 18),
            "18┤" + " " * width,
            "17┤" + " " * width,
            "16┤" + " " * width,
            "15┤" + " " * width,
            "14┤" + " " * width,
            "  └" + "─" * width,
            "   Jul 30  Jul 31  Aug 1"
        ]
    
    # Fixed Y-axis range
    y_min = 14
    y_max = 22
    y_levels = [22, 21, 20, 19, 18, 17, 16, 15, 14]
    
    # Compress data to fit chart width
    compression_ratio = len(values) / width
    compressed_values = []
    
    for i in range(width):
        start_idx = int(i * compression_ratio)
        end_idx = int((i + 1) * compression_ratio)
        if end_idx > start_idx:
            window_values = values[start_idx:end_idx]
            avg_value = sum(window_values) / len(window_values)
            compressed_values.append(avg_value)
        else:
            compressed_values.append(values[min(start_idx, len(values)-1)])
    
    # Create empty chart grid
    chart_grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Plot the line
    for col, vix_val in enumerate(compressed_values):
        # Find closest Y level
        best_row = 0
        min_distance = abs(vix_val - y_levels[0])
        
        for row, level in enumerate(y_levels):
            distance = abs(vix_val - level)
            if distance < min_distance:
                min_distance = distance
                best_row = row
        
        chart_grid[best_row][col] = '•'
    
    # Build chart lines
    chart_lines = []
    
    for row, level in enumerate(y_levels):
        if level == 20:
            # VIX=20 threshold line
            line = "20├"
            for col in range(width):
                if chart_grid[row][col] == '•':
                    line += '•'
                else:
                    line += '─'
        else:
            line = f"{level:2d}┤"
            for col in range(width):
                line += chart_grid[row][col]
        
        chart_lines.append(line)
    
    # Bottom border and date axis
    chart_lines.append("  └" + "─" * width)
    chart_lines.append("   Jul 30  Jul 31  Aug 1")
    
    return chart_lines

def create_sparkline(values: List[float], width: int = 10) -> str:
    """Create a sparkline from values"""
    if not values:
        return " " * width
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return SPARKLINE_CHARS[4] * width
    
    # Normalize and compress values
    normalized = []
    compression_ratio = len(values) / width
    
    for i in range(width):
        start_idx = int(i * compression_ratio)
        end_idx = int((i + 1) * compression_ratio)
        
        if end_idx > start_idx:
            window = values[start_idx:end_idx]
            avg_val = sum(window) / len(window)
        else:
            avg_val = values[min(start_idx, len(values)-1)]
        
        # Normalize to 0-7 range
        norm_val = (avg_val - min_val) / (max_val - min_val)
        char_idx = int(norm_val * 7)
        char_idx = min(7, max(0, char_idx))
        normalized.append(SPARKLINE_CHARS[char_idx])
    
    return ''.join(normalized)

def create_progress_bar(value: float, max_value: float, width: int = 20, 
                       show_percentage: bool = True) -> str:
    """Create a progress bar"""
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(100, max(0, (value / max_value) * 100))
    
    filled_width = int((percentage / 100) * width)
    empty_width = width - filled_width
    
    bar = "█" * filled_width + "░" * empty_width
    
    if show_percentage:
        return f"{bar} {percentage:3.0f}%"
    else:
        return bar

def create_histogram(values: List[float], width: int = 30, height: int = 10, 
                    label: str = "") -> List[str]:
    """Create a simple histogram"""
    if not values:
        return ["No data available"]
    
    max_val = max(values)
    if max_val == 0:
        max_val = 1
    
    lines = []
    
    # Title
    if label:
        lines.append(label.center(width))
        lines.append("")
    
    # Calculate bar heights
    bar_heights = []
    for val in values:
        bar_height = int((val / max_val) * height)
        bar_heights.append(bar_height)
    
    # Draw histogram from top to bottom
    for h in range(height, 0, -1):
        line = ""
        for bar_h in bar_heights:
            if bar_h >= h:
                line += "█"
            else:
                line += " "
        lines.append(line)
    
    # Bottom border
    lines.append("─" * len(bar_heights))
    
    return lines