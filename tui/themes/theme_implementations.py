"""
FNTX Trading Terminal - Cyberpunk Theme Implementations
Hong Kong-inspired cyberpunk aesthetics with Japanese minimalism
"""

import random
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ThemeType(Enum):
    BASELINE = "baseline"
    MATRIX = "matrix"
    NEON = "neon"
    GLITCH = "glitch"
    CYBER = "cyber"
    VINTAGE = "vintage"

@dataclass
class ColorScheme:
    """Color scheme for each theme"""
    background: str
    primary: str
    secondary: str
    accent: str
    profit: str
    loss: str
    warning: str
    border: str
    special_effect: str

class BaseTheme:
    """Base theme class with common functionality"""
    
    def __init__(self):
        self.colors = self.get_color_scheme()
        self.effects_enabled = True
        self.animation_level = "medium"
        
    def get_color_scheme(self) -> ColorScheme:
        """Override in subclasses"""
        raise NotImplementedError
    
    def apply_color(self, text: str, color: str) -> str:
        """Apply ANSI color codes to text"""
        color_codes = {
            'black': '\033[30m',
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'cyan': '\033[36m',
            'white': '\033[37m',
            'bright_green': '\033[92m',
            'bright_red': '\033[91m',
            'bright_cyan': '\033[96m',
            'bright_magenta': '\033[95m',
            'reset': '\033[0m'
        }
        return f"{color_codes.get(color, '')}{text}{color_codes['reset']}"
    
    def render_border(self, width: int, style: str = "single") -> str:
        """Render themed border"""
        borders = {
            "single": "─│┌┐└┘",
            "double": "═║╔╗╚╝",
            "heavy": "━┃┏┓┗┛"
        }
        return borders.get(style, borders["single"])

class MatrixRainTheme(BaseTheme):
    """Matrix-inspired falling code theme"""
    
    def __init__(self):
        super().__init__()
        self.rain_chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"
        self.rain_columns = {}
        self.last_update = time.time()
        
    def get_color_scheme(self) -> ColorScheme:
        return ColorScheme(
            background="#000000",
            primary="#00FF41",
            secondary="#00CC33",
            accent="#008F11",
            profit="#39FF14",
            loss="#FF1744",
            warning="#FFAA00",
            border="#00FF41",
            special_effect="#008F11"
        )
    
    def generate_rain_column(self, height: int) -> List[str]:
        """Generate a single column of matrix rain"""
        column = []
        for _ in range(height):
            if random.random() > 0.7:
                char = random.choice(self.rain_chars)
                # Apply phosphor glow effect
                if random.random() > 0.8:
                    char = self.apply_color(char, 'bright_green')
                else:
                    char = self.apply_color(char, 'green')
                column.append(char)
            else:
                column.append(' ')
        return column
    
    def render_with_rain(self, content: str, width: int, height: int) -> str:
        """Overlay matrix rain on content"""
        # Update rain columns every 500ms
        current_time = time.time()
        if current_time - self.last_update > 0.5:
            self.update_rain(width, height)
            self.last_update = current_time
        
        lines = content.split('\n')
        output = []
        
        for y, line in enumerate(lines[:height]):
            # Overlay rain on empty spaces
            rendered_line = ""
            for x, char in enumerate(line[:width]):
                if char == ' ' and x in self.rain_columns:
                    if y < len(self.rain_columns[x]):
                        rendered_line += self.rain_columns[x][y]
                    else:
                        rendered_line += char
                else:
                    rendered_line += char
            output.append(rendered_line)
        
        return '\n'.join(output)
    
    def update_rain(self, width: int, height: int):
        """Update rain column positions"""
        # Update 5-10 columns per cycle
        columns_to_update = random.randint(5, 10)
        for _ in range(columns_to_update):
            col = random.randint(0, width - 1)
            self.rain_columns[col] = self.generate_rain_column(height)
    
    def create_loading_animation(self) -> str:
        """Matrix-style loading animation"""
        frames = [
            "Accessing the Matrix...",
            "Decoding data streams...",
            "Synchronizing with the Grid...",
            "Connection established."
        ]
        animation = []
        for frame in frames:
            matrix_frame = f"""
╔════════════════════════════════════════╗
║  {''.join(random.choice(self.rain_chars) for _ in range(38))}  ║
║  {self.apply_color(frame.center(38), 'bright_green')}  ║
║  {''.join(random.choice(self.rain_chars) for _ in range(38))}  ║
╚════════════════════════════════════════╝
"""
            animation.append(matrix_frame)
        return animation

class HongKongNeonTheme(BaseTheme):
    """Hong Kong neon cityscape theme"""
    
    def __init__(self):
        super().__init__()
        self.neon_pulse_phase = 0
        self.cjk_decorators = {
            'finance': '金融',
            'options': '期權',
            'trading': '交易',
            'profit': '利潤',
            'loss': '損失',
            'portfolio': '投資組合',
            'hong_kong': '香港'
        }
        
    def get_color_scheme(self) -> ColorScheme:
        return ColorScheme(
            background="#0A0014",
            primary="#FF006E",
            secondary="#00F5FF",
            accent="#8B00FF",
            profit="#00FF88",
            loss="#FF3366",
            warning="#FFFF00",
            border="#FF00FF",
            special_effect="#FF00FF"
        )
    
    def create_neon_border(self, width: int, title: str = "") -> str:
        """Create pulsing neon border"""
        self.neon_pulse_phase = (self.neon_pulse_phase + 1) % 10
        
        # Create glow effect based on phase
        if self.neon_pulse_phase < 5:
            border_char = "═"
            corner_chars = "╔╗╚╝"
        else:
            border_char = "━"
            corner_chars = "┏┓┗┛"
        
        if title:
            # Add CJK decorators
            cjk = self.cjk_decorators.get('trading', '交易')
            title_with_cjk = f" {cjk} {title} {cjk} "
            padding = (width - len(title_with_cjk)) // 2
            top = f"{corner_chars[0]}{'═' * padding}{title_with_cjk}{'═' * (width - padding - len(title_with_cjk))}{corner_chars[1]}"
        else:
            top = f"{corner_chars[0]}{'═' * width}{corner_chars[1]}"
        
        return top
    
    def apply_neon_glow(self, text: str, intensity: float = 0.8) -> str:
        """Apply neon glow effect to text"""
        if intensity > 0.5:
            # Strong glow
            return f"\033[1;35;45m{text}\033[0m"  # Bright magenta with background
        else:
            # Soft glow
            return self.apply_color(text, 'bright_magenta')
    
    def render_skyline_background(self, width: int) -> str:
        """Render Hong Kong skyline ASCII art"""
        skyline = """
    ╱|╲    ┃┃    ╱|╲     ║║     ╱╲      ┃┃
   ╱ | ╲   ┃┃   ╱ | ╲    ║║    ╱  ╲     ┃┃
  ╱  |  ╲  ┃┃  ╱  |  ╲   ║║   ╱____╲    ┃┃
 ╱   |   ╲ ┃┃ ╱   |   ╲  ║║  ╱      ╲   ┃┃
═════════════════════════════════════════════
"""
        return self.apply_color(skyline, 'cyan')

class GlitchArtTheme(BaseTheme):
    """Glitch art and data corruption aesthetic"""
    
    def __init__(self):
        super().__init__()
        self.glitch_chars = "▓▒░█▄▀▐▌"
        self.corruption_patterns = [
            "░▒▓█▓▒░",
            "▀▄▀▄▀▄",
            "▌▐▌▐▌▐",
            "█░█░█░"
        ]
        
    def get_color_scheme(self) -> ColorScheme:
        return ColorScheme(
            background="#0D0D0D",
            primary="#FFFFFF",
            secondary="#FF0090",
            accent="#00FFFF",
            profit="#00FF00",
            loss="#FF0000",
            warning="#FFFF00",
            border="#FF00FF",
            special_effect="#FF00FF"
        )
    
    def apply_glitch(self, text: str, intensity: float = 0.3) -> str:
        """Apply glitch effect to text"""
        if random.random() > intensity:
            return text
        
        glitched = ""
        for char in text:
            if random.random() < 0.1:  # 10% chance to glitch each character
                # RGB channel shift effect
                if random.random() < 0.33:
                    glitched += self.apply_color(char, 'red')
                elif random.random() < 0.66:
                    glitched += self.apply_color(char, 'cyan')
                else:
                    glitched += self.apply_color(char, 'yellow')
            else:
                glitched += char
        
        return glitched
    
    def create_glitch_border(self, width: int) -> str:
        """Create glitched border effect"""
        border = ""
        for _ in range(width):
            if random.random() < 0.2:
                border += random.choice(self.glitch_chars)
            else:
                border += "═"
        return border
    
    def corrupt_text(self, text: str, corruption_level: float = 0.1) -> str:
        """Introduce visual corruption to text"""
        corrupted = ""
        for char in text:
            if random.random() < corruption_level and char != ' ':
                # Replace with similar-looking corrupted character
                replacements = {
                    'A': '▲', 'E': '3', 'I': '1', 'O': '0',
                    'S': '$', 'T': '┬', 'L': '└', 'N': '╪'
                }
                corrupted += replacements.get(char.upper(), char)
            else:
                corrupted += char
        return corrupted

class MinimalistCyberTheme(BaseTheme):
    """Clean, minimalist cyberpunk aesthetic"""
    
    def __init__(self):
        super().__init__()
        self.circuit_patterns = [
            "─═╪╫╬═─",
            "──•──•──",
            "═══╬═══",
            "─┤├─┤├─"
        ]
        
    def get_color_scheme(self) -> ColorScheme:
        return ColorScheme(
            background="#000000",
            primary="#E0E0E0",
            secondary="#00D4FF",
            accent="#00D4FF",
            profit="#00FF9F",
            loss="#FF0055",
            warning="#FFAA00",
            border="#404040",
            special_effect="#FFFFFF"
        )
    
    def create_circuit_border(self, width: int, node_spacing: int = 8) -> str:
        """Create circuit-pattern border"""
        border = ""
        for i in range(width):
            if i % node_spacing == 0:
                border += "╬"  # Node
            elif i % 2 == 0:
                border += "═"  # Double line
            else:
                border += "─"  # Single line
        return border
    
    def format_data_field(self, label: str, value: str, width: int = 30) -> str:
        """Format data field with minimal cyber styling"""
        separator = "::"
        formatted = f"{label}{separator}{value}"
        padding = width - len(formatted)
        if padding > 0:
            formatted += " " * padding
        return formatted
    
    def create_node_connector(self, source: str, target: str) -> str:
        """Create visual connection between nodes"""
        return f"{source} ══╬══> {target}"

class VintageTerminalTheme(BaseTheme):
    """Retro CRT terminal aesthetic"""
    
    def __init__(self):
        super().__init__()
        self.phosphor_color = "amber"  # or "green"
        self.scanline_phase = 0
        self.flicker_chance = 0.01
        
    def get_color_scheme(self) -> ColorScheme:
        if self.phosphor_color == "amber":
            return ColorScheme(
                background="#000000",
                primary="#FFAA00",
                secondary="#FF8800",
                accent="#FFFF00",
                profit="#00FF00",
                loss="#FF8800",
                warning="#FFFF00",
                border="#FFAA00",
                special_effect="#FFCC00"
            )
        else:  # green phosphor
            return ColorScheme(
                background="#000000",
                primary="#00FF00",
                secondary="#00CC00",
                accent="#00FF00",
                profit="#00FF00",
                loss="#FF0000",
                warning="#FFFF00",
                border="#00FF00",
                special_effect="#00FF00"
            )
    
    def apply_scanlines(self, text: str, density: float = 0.3) -> str:
        """Apply CRT scanline effect"""
        lines = text.split('\n')
        output = []
        
        for i, line in enumerate(lines):
            if i % 2 == self.scanline_phase:
                # Apply scanline effect
                dimmed = ""
                for char in line:
                    if char != ' ':
                        # Dim the character slightly
                        dimmed += self.apply_color(char, 'bright_green' if self.phosphor_color == 'green' else 'yellow')
                    else:
                        dimmed += char
                output.append(dimmed)
            else:
                output.append(line)
        
        self.scanline_phase = (self.scanline_phase + 1) % 2
        return '\n'.join(output)
    
    def apply_phosphor_glow(self, text: str) -> str:
        """Apply phosphor persistence effect"""
        # Simulate phosphor afterglow
        return f"\033[1m{text}\033[0m"  # Bold for glow effect
    
    def create_crt_frame(self, content: str, width: int, height: int) -> str:
        """Create CRT-style curved frame"""
        # Top curve
        top = "  ╔" + "═" * (width - 4) + "╗  "
        top2 = " ╱" + " " * (width - 2) + "╲ "
        
        # Bottom curve
        bottom2 = " ╲" + " " * (width - 2) + "╱ "
        bottom = "  ╚" + "═" * (width - 4) + "╝  "
        
        # Apply content with side borders
        lines = content.split('\n')
        framed = [top, top2]
        
        for line in lines[:height-4]:
            framed.append(f"│ {line[:width-4].ljust(width-4)} │")
        
        framed.extend([bottom2, bottom])
        
        # Apply flicker effect occasionally
        if random.random() < self.flicker_chance:
            return self.apply_color('\n'.join(framed), 'bright_green')
        
        return '\n'.join(framed)
    
    def create_retro_ascii_logo(self) -> str:
        """Create retro ASCII art logo"""
        logo = """
  ▄▄▄▄▄ ▄   ▄ ▄▄▄▄▄ ▄   ▄
  █     ██  █   █   ▀▄ ▄▀
  ████  █ ▀▄█   █    ▄▀▄ 
  █     █   █   █   ▄▀ ▀▄
  █     █   █   █   ▀   ▀
"""
        return self.apply_phosphor_glow(logo)

class ThemeManager:
    """Manages theme switching and application"""
    
    def __init__(self):
        self.themes = {
            ThemeType.BASELINE: BaseTheme(),
            ThemeType.MATRIX: MatrixRainTheme(),
            ThemeType.NEON: HongKongNeonTheme(),
            ThemeType.GLITCH: GlitchArtTheme(),
            ThemeType.CYBER: MinimalistCyberTheme(),
            ThemeType.VINTAGE: VintageTerminalTheme()
        }
        self.current_theme = ThemeType.BASELINE
        self.active_theme = self.themes[self.current_theme]
        
    def switch_theme(self, theme_type: ThemeType) -> bool:
        """Switch to a different theme (sub-100ms operation)"""
        start_time = time.time()
        
        try:
            # Cleanup current theme
            self.cleanup_current_theme()
            
            # Apply new theme
            self.current_theme = theme_type
            self.active_theme = self.themes[theme_type]
            
            # Initialize new theme
            self.initialize_theme()
            
            elapsed = (time.time() - start_time) * 1000
            if elapsed > 100:
                print(f"Warning: Theme switch took {elapsed:.2f}ms")
            
            return True
            
        except Exception as e:
            print(f"Error switching theme: {e}")
            return False
    
    def cleanup_current_theme(self):
        """Cleanup resources from current theme"""
        # Clear any active animations or effects
        if hasattr(self.active_theme, 'cleanup'):
            self.active_theme.cleanup()
    
    def initialize_theme(self):
        """Initialize new theme resources"""
        # Pre-compute static elements for performance
        if hasattr(self.active_theme, 'initialize'):
            self.active_theme.initialize()
    
    def get_current_colors(self) -> ColorScheme:
        """Get current theme's color scheme"""
        return self.active_theme.colors
    
    def render_with_theme(self, content: str, width: int = 80, height: int = 24) -> str:
        """Render content with current theme effects"""
        # Apply theme-specific rendering
        if isinstance(self.active_theme, MatrixRainTheme):
            return self.active_theme.render_with_rain(content, width, height)
        elif isinstance(self.active_theme, VintageTerminalTheme):
            return self.active_theme.apply_scanlines(content)
        elif isinstance(self.active_theme, GlitchArtTheme):
            return self.active_theme.apply_glitch(content)
        else:
            return content

# Performance monitoring decorator
def measure_performance(func):
    """Decorator to measure function performance"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000
        if elapsed > 16:  # Warning if frame takes longer than 16ms (60fps)
            print(f"Performance warning: {func.__name__} took {elapsed:.2f}ms")
        return result
    return wrapper

# Example usage
if __name__ == "__main__":
    # Initialize theme manager
    manager = ThemeManager()
    
    # Test theme switching
    print("Testing theme switching performance...")
    
    for theme in ThemeType:
        start = time.time()
        success = manager.switch_theme(theme)
        elapsed = (time.time() - start) * 1000
        print(f"{theme.value}: {'✓' if success else '✗'} ({elapsed:.2f}ms)")
    
    # Test rendering
    sample_content = """
    ┌─[ PORTFOLIO OVERVIEW ]─────────────────┐
    │ Account: FN-7X9K2     Status: ONLINE   │
    │ Balance: $127,439.82  P&L: +$2,891.23  │
    └─────────────────────────────────────────┘
    """
    
    print("\nTesting theme rendering:")
    for theme in [ThemeType.MATRIX, ThemeType.NEON, ThemeType.GLITCH]:
        manager.switch_theme(theme)
        rendered = manager.render_with_theme(sample_content)
        print(f"\n{theme.value} Theme:")
        print(rendered)