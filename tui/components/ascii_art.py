"""
ASCII Art Assets for FNTX Trading CLI
"""

# Main FNTX Banner
FNTX_BANNER = """
███████╗███╗   ██╗████████╗██╗  ██╗
██╔════╝████╗  ██║╚══██╔══╝╚██╗██╔╝
█████╗  ██╔██╗ ██║   ██║    ╚███╔╝ 
██╔══╝  ██║╚██╗██║   ██║    ██╔██╗ 
██║     ██║ ╚████║   ██║   ██╔╝ ██╗
╚═╝     ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝"""

# Trading Terminal Banner
TRADING_BANNER = """
████████╗██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ 
   ██║   ██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███╗
   ██║   ██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
   ██║   ██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝"""

# Options ASCII Art
OPTIONS_ART = """
 ██████╗ ██████╗ ████████╗██╗ ██████╗ ███╗   ██╗███████╗
██╔═══██╗██╔══██╗╚══██╔══╝██║██╔═══██╗████╗  ██║██╔════╝
██║   ██║██████╔╝   ██║   ██║██║   ██║██╔██╗ ██║███████╗
██║   ██║██╔═══╝    ██║   ██║██║   ██║██║╚██╗██║╚════██║
╚██████╔╝██║        ██║   ██║╚██████╔╝██║ ╚████║███████║
 ╚═════╝ ╚═╝        ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝"""

# Box Drawing Characters
BOX_CHARS = {
    'top_left': '┌',
    'top_right': '┐',
    'bottom_left': '└',
    'bottom_right': '┘',
    'horizontal': '─',
    'vertical': '│',
    'cross': '┼',
    'tee_down': '┬',
    'tee_up': '┴',
    'tee_right': '├',
    'tee_left': '┤'
}

# Double Line Box Characters
DOUBLE_BOX = {
    'top_left': '╔',
    'top_right': '╗',
    'bottom_left': '╚',
    'bottom_right': '╝',
    'horizontal': '═',
    'vertical': '║',
    'cross': '╬',
    'tee_down': '╦',
    'tee_up': '╩',
    'tee_right': '╠',
    'tee_left': '╣'
}

# Status Symbols
SYMBOLS = {
    'check': '✓',
    'cross': '✗',
    'warning': '⚠️',
    'alert': '🚨',
    'pending': '⏳',
    'refresh': '🔄',
    'target': '🎯',
    'chart': '📊',
    'up_arrow': '▲',
    'down_arrow': '▼',
    'right_arrow': '→',
    'left_arrow': '←',
    'bullet': '•',
    'star': '★'
}

# Progress Bar Characters
PROGRESS_CHARS = {
    'filled': '█',
    'empty': '░',
    'partial': '▓'
}

# Sparkline Characters
SPARKLINE_CHARS = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

def create_box(width, height, title="", style="single"):
    """Create an ASCII box with optional title"""
    chars = BOX_CHARS if style == "single" else DOUBLE_BOX
    
    lines = []
    
    # Top line
    if title:
        title_padded = f" {title} "
        top_line = (chars['top_left'] + chars['horizontal'] + title_padded + 
                   chars['horizontal'] * (width - len(title_padded) - 2) + chars['top_right'])
    else:
        top_line = chars['top_left'] + chars['horizontal'] * (width - 2) + chars['top_right']
    lines.append(top_line)
    
    # Middle lines
    for _ in range(height - 2):
        lines.append(chars['vertical'] + ' ' * (width - 2) + chars['vertical'])
    
    # Bottom line
    bottom_line = chars['bottom_left'] + chars['horizontal'] * (width - 2) + chars['bottom_right']
    lines.append(bottom_line)
    
    return '\n'.join(lines)

def create_separator(width, style="single"):
    """Create a horizontal separator line"""
    chars = BOX_CHARS if style == "single" else DOUBLE_BOX
    return chars['tee_right'] + chars['horizontal'] * (width - 2) + chars['tee_left']