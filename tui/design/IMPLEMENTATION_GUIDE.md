# FNTX Professional Cyberpunk - Implementation Guide

## Quick Start Code Examples

### 1. Base Terminal Configuration

```python
# terminal_config.py
import os
import sys
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Tuple

class Theme(Enum):
    PRECISION_MATRIX = "matrix"
    FINANCIAL_DISTRICT = "neon"
    DATA_STREAM = "stream"
    TERMINAL_ZERO = "zero"
    QUANTUM_GRID = "quantum"

@dataclass
class ColorScheme:
    """Professional color definitions with RGB values"""
    background: str
    foreground: str
    primary: str
    secondary: str
    accent: str
    success: str
    error: str
    warning: str
    
    def to_escape_codes(self) -> Dict[str, str]:
        """Convert to ANSI escape sequences"""
        return {
            'bg': f'\033[48;2;{self.background}m',
            'fg': f'\033[38;2;{self.foreground}m',
            'primary': f'\033[38;2;{self.primary}m',
            'secondary': f'\033[38;2;{self.secondary}m',
            'accent': f'\033[38;2;{self.accent}m',
            'success': f'\033[38;2;{self.success}m',
            'error': f'\033[38;2;{self.error}m',
            'warning': f'\033[38;2;{self.warning}m',
            'reset': '\033[0m'
        }

# Theme Definitions
THEMES = {
    Theme.PRECISION_MATRIX: ColorScheme(
        background="0;0;0",       # Pure Black
        foreground="224;224;224", # Clean Silver
        primary="0;255;65",       # Phosphor Green
        secondary="0;143;17",     # Dark Matrix Green
        accent="255;255;255",     # Pure White
        success="0;255;65",       # Primary Green
        error="255;0;64",         # Matrix Red
        warning="255;176;0"       # Amber
    ),
    Theme.FINANCIAL_DISTRICT: ColorScheme(
        background="10;10;10",    # Deep Black
        foreground="224;224;224", # Clean Silver
        primary="0;245;255",      # Neon Cyan
        secondary="255;0;110",    # Neon Pink
        accent="255;234;0",       # Golden Hour
        success="0;255;136",      # Mint Green
        error="255;0;64",         # Warning Red
        warning="255;176;0"       # Amber
    ),
    Theme.DATA_STREAM: ColorScheme(
        background="1;11;20",     # Deep Ocean
        foreground="224;224;224", # Clean Silver
        primary="0;212;255",      # Data Blue
        secondary="0;149;204",    # Stream Blue
        accent="0;255;212",       # Quantum Cyan
        success="0;255;149",      # Confirm Green
        error="255;51;102",       # Alert Red
        warning="255;176;0"       # Warning
    ),
    Theme.TERMINAL_ZERO: ColorScheme(
        background="0;0;0",       # Absolute Black
        foreground="255;255;255", # Pure White
        primary="0;255;0",        # Single Green
        secondary="51;51;51",     # Subtle Gray
        accent="0;255;0",         # Single Green
        success="0;255;0",        # Green
        error="255;0;0",          # Pure Red
        warning="255;255;0"       # Yellow
    ),
    Theme.QUANTUM_GRID: ColorScheme(
        background="3;0;18",      # Quantum Void
        foreground="224;224;224", # Clean Silver
        primary="139;0;255",      # Quantum Purple
        secondary="0;191;255",    # Particle Blue
        accent="255;0;255",       # Probability Pink
        success="0;255;0",        # Collapse Green
        error="255;0;0",          # Uncertainty Red
        warning="255;176;0"       # Warning
    )
}
```

### 2. Border System Implementation

```python
# borders.py
from enum import Enum
from typing import List, Optional

class BorderStyle(Enum):
    SINGLE = "single"
    DOUBLE = "double"
    ROUNDED = "rounded"
    HEAVY = "heavy"
    DASHED = "dashed"

class BorderChars:
    """Unicode box drawing characters for pristine borders"""
    
    STYLES = {
        BorderStyle.SINGLE: {
            'top_left': '┌', 'top_right': '┐',
            'bottom_left': '└', 'bottom_right': '┘',
            'horizontal': '─', 'vertical': '│',
            'cross': '┼', 't_down': '┬', 't_up': '┴',
            't_right': '├', 't_left': '┤'
        },
        BorderStyle.DOUBLE: {
            'top_left': '╔', 'top_right': '╗',
            'bottom_left': '╚', 'bottom_right': '╝',
            'horizontal': '═', 'vertical': '║',
            'cross': '╬', 't_down': '╦', 't_up': '╩',
            't_right': '╠', 't_left': '╣'
        },
        BorderStyle.ROUNDED: {
            'top_left': '╭', 'top_right': '╮',
            'bottom_left': '╰', 'bottom_right': '╯',
            'horizontal': '─', 'vertical': '│',
            'cross': '┼', 't_down': '┬', 't_up': '┴',
            't_right': '├', 't_left': '┤'
        },
        BorderStyle.HEAVY: {
            'top_left': '┏', 'top_right': '┓',
            'bottom_left': '┗', 'bottom_right': '┛',
            'horizontal': '━', 'vertical': '┃',
            'cross': '╋', 't_down': '┳', 't_up': '┻',
            't_right': '┣', 't_left': '┫'
        }
    }

class PrecisionPanel:
    """Clean, professional panel with perfect alignment"""
    
    def __init__(self, 
                 width: int, 
                 height: int,
                 style: BorderStyle = BorderStyle.SINGLE,
                 title: Optional[str] = None):
        self.width = width
        self.height = height
        self.style = style
        self.title = title
        self.chars = BorderChars.STYLES[style]
        
    def render(self, content: List[str] = None) -> str:
        """Render panel with pristine borders"""
        lines = []
        
        # Top border with optional title
        if self.title:
            title_str = f" {self.title} "
            padding = self.width - len(title_str) - 2
            left_pad = padding // 2
            right_pad = padding - left_pad
            top = (self.chars['top_left'] + 
                   self.chars['horizontal'] * left_pad +
                   title_str +
                   self.chars['horizontal'] * right_pad +
                   self.chars['top_right'])
        else:
            top = (self.chars['top_left'] + 
                   self.chars['horizontal'] * (self.width - 2) +
                   self.chars['top_right'])
        lines.append(top)
        
        # Content area
        content_height = self.height - 2
        if content:
            for i in range(content_height):
                if i < len(content):
                    # Ensure content fits width with proper padding
                    line = content[i][:self.width - 4]
                    padding = self.width - len(line) - 2
                    lines.append(
                        f"{self.chars['vertical']} {line}{' ' * padding}{self.chars['vertical']}"
                    )
                else:
                    # Empty line
                    lines.append(
                        f"{self.chars['vertical']}{' ' * (self.width - 2)}{self.chars['vertical']}"
                    )
        else:
            # Empty panel
            for _ in range(content_height):
                lines.append(
                    f"{self.chars['vertical']}{' ' * (self.width - 2)}{self.chars['vertical']}"
                )
        
        # Bottom border
        bottom = (self.chars['bottom_left'] + 
                  self.chars['horizontal'] * (self.width - 2) +
                  self.chars['bottom_right'])
        lines.append(bottom)
        
        return '\n'.join(lines)
```

### 3. Data Grid Component

```python
# data_grid.py
from typing import List, Dict, Any, Optional
from enum import Enum

class Alignment(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"

class DataGrid:
    """Professional data grid with perfect alignment"""
    
    def __init__(self, 
                 columns: List[Dict[str, Any]],
                 data: List[Dict[str, Any]],
                 show_header: bool = True,
                 border_style: BorderStyle = BorderStyle.SINGLE):
        self.columns = columns
        self.data = data
        self.show_header = show_header
        self.chars = BorderChars.STYLES[border_style]
        
    def _format_cell(self, 
                     value: Any, 
                     width: int, 
                     align: Alignment = Alignment.LEFT) -> str:
        """Format cell with proper alignment"""
        str_value = str(value)
        if len(str_value) > width:
            str_value = str_value[:width-1] + '…'
        
        if align == Alignment.LEFT:
            return str_value.ljust(width)
        elif align == Alignment.RIGHT:
            return str_value.rjust(width)
        else:  # CENTER
            return str_value.center(width)
    
    def render(self) -> str:
        """Render the data grid with pristine alignment"""
        lines = []
        
        # Calculate column widths
        col_widths = {}
        for col in self.columns:
            col_widths[col['key']] = max(
                len(col['label']),
                max(len(str(row.get(col['key'], ''))) for row in self.data) if self.data else 0
            ) + 2  # Padding
        
        # Top border
        segments = []
        for i, col in enumerate(self.columns):
            width = col_widths[col['key']]
            segments.append(self.chars['horizontal'] * width)
        
        top_border = (
            self.chars['top_left'] +
            self.chars['t_down'].join(segments) +
            self.chars['top_right']
        )
        lines.append(top_border)
        
        # Header
        if self.show_header:
            header_cells = []
            for col in self.columns:
                width = col_widths[col['key']]
                align = col.get('align', Alignment.LEFT)
                header_cells.append(
                    self._format_cell(col['label'], width - 2, align)
                )
            header_line = (
                self.chars['vertical'] + ' ' +
                f" {self.chars['vertical']} ".join(header_cells) + ' ' +
                self.chars['vertical']
            )
            lines.append(header_line)
            
            # Header separator
            segments = []
            for col in self.columns:
                width = col_widths[col['key']]
                segments.append(self.chars['horizontal'] * width)
            separator = (
                self.chars['t_right'] +
                self.chars['cross'].join(segments) +
                self.chars['t_left']
            )
            lines.append(separator)
        
        # Data rows
        for row in self.data:
            cells = []
            for col in self.columns:
                width = col_widths[col['key']]
                align = col.get('align', Alignment.LEFT)
                value = row.get(col['key'], '')
                
                # Apply formatting based on column type
                if col.get('type') == 'currency':
                    value = f"${value:,.2f}" if isinstance(value, (int, float)) else value
                elif col.get('type') == 'percent':
                    value = f"{value:+.2f}%" if isinstance(value, (int, float)) else value
                
                cells.append(self._format_cell(value, width - 2, align))
            
            data_line = (
                self.chars['vertical'] + ' ' +
                f" {self.chars['vertical']} ".join(cells) + ' ' +
                self.chars['vertical']
            )
            lines.append(data_line)
        
        # Bottom border
        segments = []
        for col in self.columns:
            width = col_widths[col['key']]
            segments.append(self.chars['horizontal'] * width)
        bottom_border = (
            self.chars['bottom_left'] +
            self.chars['t_up'].join(segments) +
            self.chars['bottom_right']
        )
        lines.append(bottom_border)
        
        return '\n'.join(lines)
```

### 4. Status Indicators

```python
# indicators.py
from enum import Enum
from typing import Optional

class Status(Enum):
    ACTIVE = "●"
    INACTIVE = "○"
    PENDING = "◐"
    PROCESSING = "◑"
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    UP = "▲"
    DOWN = "▼"
    UNCHANGED = "═"
    VOLATILE = "◈"
    FAST = "⚡"

class StatusIndicator:
    """Professional status indicators with color support"""
    
    def __init__(self, theme: Theme):
        self.colors = THEMES[theme].to_escape_codes()
    
    def format(self, 
               status: Status, 
               label: Optional[str] = None,
               value: Optional[str] = None) -> str:
        """Format status with appropriate color"""
        
        # Determine color based on status
        if status in [Status.ACTIVE, Status.SUCCESS, Status.UP]:
            color = self.colors['success']
        elif status in [Status.ERROR, Status.DOWN]:
            color = self.colors['error']
        elif status in [Status.WARNING, Status.VOLATILE]:
            color = self.colors['warning']
        elif status in [Status.PENDING, Status.PROCESSING]:
            color = self.colors['accent']
        else:
            color = self.colors['fg']
        
        # Build formatted string
        result = f"{color}{status.value}{self.colors['reset']}"
        
        if label:
            result = f"{result} {label}"
        
        if value:
            result = f"{result}: {value}"
        
        return result
```

### 5. Animation Manager

```python
# animations.py
import time
import threading
from typing import Callable, List, Optional

class AnimationFrame:
    """Single frame of animation"""
    def __init__(self, content: str, duration: float = 0.1):
        self.content = content
        self.duration = duration

class Animation:
    """Manages clean, professional animations"""
    
    def __init__(self, 
                 frames: List[AnimationFrame],
                 loop: bool = False):
        self.frames = frames
        self.loop = loop
        self.running = False
        self._thread = None
    
    def start(self, callback: Callable[[str], None]):
        """Start animation with callback for each frame"""
        self.running = True
        
        def run():
            while self.running:
                for frame in self.frames:
                    if not self.running:
                        break
                    callback(frame.content)
                    time.sleep(frame.duration)
                
                if not self.loop:
                    self.running = False
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the animation"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

# Predefined animations
class Animations:
    @staticmethod
    def loading_bar(width: int = 20) -> List[AnimationFrame]:
        """Clean loading bar animation"""
        frames = []
        for i in range(width + 1):
            filled = '■' * i
            empty = '□' * (width - i)
            percent = (i / width) * 100
            content = f"[{filled}{empty}] {percent:.0f}%"
            frames.append(AnimationFrame(content, 0.05))
        return frames
    
    @staticmethod
    def data_pulse() -> List[AnimationFrame]:
        """Subtle data pulse effect"""
        chars = ['◯', '○', '◐', '◑', '◒', '◓', '●', '◓', '◒', '◑', '◐', '○']
        return [AnimationFrame(c, 0.1) for c in chars]
    
    @staticmethod
    def matrix_rain(height: int = 10) -> List[AnimationFrame]:
        """Matrix rain effect for margins"""
        import random
        frames = []
        for _ in range(30):
            lines = []
            for _ in range(height):
                line = ''.join(random.choice(['0', '1', ' ', '╹', '╻']) 
                              for _ in range(5))
                lines.append(line)
            frames.append(AnimationFrame('\n'.join(lines), 0.1))
        return frames
```

### 6. Main Dashboard Implementation

```python
# dashboard.py
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

class FNTXDashboard:
    """Main trading dashboard with professional cyberpunk aesthetic"""
    
    def __init__(self, theme: Theme = Theme.PRECISION_MATRIX):
        self.theme = theme
        self.colors = THEMES[theme].to_escape_codes()
        self.width = self._get_terminal_width()
        self.height = self._get_terminal_height()
        
        # Initialize components
        self.header_panel = None
        self.portfolio_panel = None
        self.positions_grid = None
        self.market_panel = None
        self.order_panel = None
        
        self._init_layout()
    
    def _get_terminal_width(self) -> int:
        """Get terminal width"""
        return os.get_terminal_size().columns
    
    def _get_terminal_height(self) -> int:
        """Get terminal height"""
        return os.get_terminal_size().lines
    
    def _init_layout(self):
        """Initialize dashboard layout based on terminal size"""
        
        # Responsive layout based on width
        if self.width >= 120:
            # Full layout
            self.layout = "full"
            self.panels_per_row = 4
        elif self.width >= 80:
            # Standard layout
            self.layout = "standard"
            self.panels_per_row = 2
        else:
            # Compact layout
            self.layout = "compact"
            self.panels_per_row = 1
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def render_header(self) -> str:
        """Render professional header"""
        timestamp = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
        
        if self.theme == Theme.PRECISION_MATRIX:
            title = "FNTX TRADING v2.0"
            subtitle = "MATRIX.PRECISION"
        elif self.theme == Theme.FINANCIAL_DISTRICT:
            title = "FNTX 金融終端"
            subtitle = "HONG KONG"
        elif self.theme == Theme.DATA_STREAM:
            title = "FNTX DATA STREAM"
            subtitle = "FLOW VISUALIZATION"
        elif self.theme == Theme.TERMINAL_ZERO:
            title = "FNTX"
            subtitle = "ZERO"
        else:  # QUANTUM_GRID
            title = "QUANTUM GRID"
            subtitle = "ψ = Σ(profit × probability)"
        
        # Build header with clean borders
        header = PrecisionPanel(
            self.width,
            3,
            BorderStyle.DOUBLE if self.theme != Theme.TERMINAL_ZERO else BorderStyle.SINGLE
        )
        
        content = [
            f"{title} │ {timestamp} │ {subtitle} │ {self.colors['success']}● CONNECTED{self.colors['reset']}"
        ]
        
        return header.render(content)
    
    def render_portfolio(self, data: Dict[str, Any]) -> str:
        """Render portfolio overview panel"""
        panel = PrecisionPanel(
            self.width // 2 if self.layout != "compact" else self.width,
            8,
            BorderStyle.SINGLE,
            "PORTFOLIO OVERVIEW"
        )
        
        # Format portfolio data
        content = [
            f"Account: {data.get('account', 'N/A')}",
            f"Balance: ${data.get('balance', 0):,.2f}",
            f"Day P&L: {self.colors['success']}{data.get('day_pnl', 0):+,.2f}{self.colors['reset']}",
            f"Margin: {data.get('margin_used', 0):.1f}%",
            f"Positions: {data.get('position_count', 0)}"
        ]
        
        return panel.render(content)
    
    def render_positions(self, positions: List[Dict[str, Any]]) -> str:
        """Render positions data grid"""
        columns = [
            {'key': 'symbol', 'label': 'Symbol', 'align': Alignment.LEFT},
            {'key': 'side', 'label': 'Side', 'align': Alignment.CENTER},
            {'key': 'quantity', 'label': 'Qty', 'align': Alignment.RIGHT},
            {'key': 'entry', 'label': 'Entry', 'align': Alignment.RIGHT, 'type': 'currency'},
            {'key': 'current', 'label': 'Current', 'align': Alignment.RIGHT, 'type': 'currency'},
            {'key': 'pnl', 'label': 'P&L', 'align': Alignment.RIGHT, 'type': 'currency'},
            {'key': 'pnl_pct', 'label': 'P&L%', 'align': Alignment.RIGHT, 'type': 'percent'},
        ]
        
        grid = DataGrid(columns, positions, border_style=BorderStyle.SINGLE)
        return grid.render()
    
    def render(self, data: Dict[str, Any]):
        """Render complete dashboard"""
        self.clear_screen()
        
        # Apply theme colors
        print(self.colors['bg'] + self.colors['fg'])
        
        # Render components
        print(self.render_header())
        print()
        print(self.render_portfolio(data['portfolio']))
        print()
        print(self.render_positions(data['positions']))
        
        # Reset colors
        print(self.colors['reset'])

# Example usage
if __name__ == "__main__":
    # Sample data
    sample_data = {
        'portfolio': {
            'account': 'FNT-8834521',
            'balance': 10234567.89,
            'day_pnl': 45234.67,
            'margin_used': 45.2,
            'position_count': 10
        },
        'positions': [
            {
                'symbol': 'SPY',
                'side': 'LONG',
                'quantity': 1000,
                'entry': 445.32,
                'current': 448.67,
                'pnl': 3350,
                'pnl_pct': 0.75
            },
            {
                'symbol': 'QQQ',
                'side': 'LONG',
                'quantity': 500,
                'entry': 368.45,
                'current': 371.23,
                'pnl': 1390,
                'pnl_pct': 0.75
            }
        ]
    }
    
    # Create and render dashboard
    dashboard = FNTXDashboard(Theme.PRECISION_MATRIX)
    dashboard.render(sample_data)
```

---

## Performance Optimization Techniques

### 1. Differential Rendering
```python
class DifferentialRenderer:
    """Only update changed portions of screen"""
    
    def __init__(self):
        self.previous_state = {}
        self.current_state = {}
    
    def update_cell(self, row: int, col: int, content: str):
        """Update only if changed"""
        key = f"{row},{col}"
        if self.previous_state.get(key) != content:
            # Move cursor and update
            print(f"\033[{row};{col}H{content}", end='')
            self.current_state[key] = content
    
    def commit(self):
        """Commit current state"""
        self.previous_state = self.current_state.copy()
```

### 2. Buffer Management
```python
class ScreenBuffer:
    """Double buffering for smooth updates"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.front_buffer = [[' ' for _ in range(width)] for _ in range(height)]
        self.back_buffer = [[' ' for _ in range(width)] for _ in range(height)]
    
    def write(self, row: int, col: int, text: str):
        """Write to back buffer"""
        for i, char in enumerate(text):
            if col + i < self.width:
                self.back_buffer[row][col + i] = char
    
    def flip(self):
        """Swap buffers and render"""
        self.front_buffer, self.back_buffer = self.back_buffer, self.front_buffer
        # Render front buffer
        output = '\033[H'  # Home cursor
        for row in self.front_buffer:
            output += ''.join(row) + '\n'
        print(output, end='')
```

---

## Terminal Compatibility

### Detection and Fallback
```python
def detect_terminal_capabilities():
    """Detect terminal features"""
    import subprocess
    
    capabilities = {
        'unicode': True,
        'colors': 256,
        'true_color': False,
        'size': os.get_terminal_size()
    }
    
    # Check for true color support
    try:
        result = subprocess.run(['tput', 'colors'], capture_output=True, text=True)
        capabilities['colors'] = int(result.stdout.strip())
    except:
        pass
    
    # Check for Unicode support
    try:
        print('█')
        capabilities['unicode'] = True
    except:
        capabilities['unicode'] = False
    
    return capabilities

# Adaptive rendering based on capabilities
def get_border_chars(capabilities):
    if capabilities['unicode']:
        return BorderChars.STYLES[BorderStyle.DOUBLE]
    else:
        # ASCII fallback
        return {
            'top_left': '+', 'top_right': '+',
            'bottom_left': '+', 'bottom_right': '+',
            'horizontal': '-', 'vertical': '|',
            'cross': '+', 't_down': '+', 't_up': '+',
            't_right': '+', 't_left': '+'
        }
```

---

## Testing Checklist

- [ ] Test in multiple terminal emulators (iTerm2, Alacritty, Windows Terminal)
- [ ] Verify Unicode rendering
- [ ] Check color accuracy across themes
- [ ] Validate responsive layouts at different sizes
- [ ] Measure render performance (<100ms)
- [ ] Test keyboard navigation
- [ ] Verify screen reader compatibility
- [ ] Check animation smoothness
- [ ] Validate data alignment in grids
- [ ] Test with real-time data updates