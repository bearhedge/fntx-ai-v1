"""
Matrix Rain Effect - Psychedelic falling characters animation
"""
import random
from datetime import datetime
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.console import Console
from rich.color import Color
import math

class MatrixRainColumn:
    """Single column of falling Matrix characters"""
    
    # Character sets from the Matrix.html
    CHAR_SETS = {
        'binary': ['0', '1'],
        'hex': ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F'],
        'katakana': ['ア','イ','ウ','エ','オ','カ','キ','ク','ケ','コ','サ','シ','ス','セ','ソ',
                      'タ','チ','ツ','テ','ト','ナ','ニ','ヌ','ネ','ノ','ハ','ヒ','フ','ヘ','ホ',
                      'マ','ミ','ム','メ','モ','ヤ','ユ','ヨ','ラ','リ','ル','レ','ロ','ワ','ヲ','ン'],
        'symbols': ['!','@','#','$','%','^','&','*','(',')','_','+','=','{','}','|','[',']',
                    '\\',':','"',';',"'",'<','>','?',',','.','/','-','~','`'],
        'mixed': ['0','1','A','B','C','ア','イ','ウ','!','@','#','$','%','^','&','*','X','Y','Z',
                  '♠','♥','♦','♣','★','☆','♪','♫','∞','∆','Ω','π','Σ','Φ','Ψ','α','β','γ','δ','ε']
    }
    
    def __init__(self, height: int, position: int = 0, speed: float = 1.0, char_set: str = 'mixed'):
        self.height = height
        self.position = position
        self.speed = speed
        self.char_set = char_set
        self.chars = []
        self.trail_length = random.randint(10, 25)  # Longer trails
        self.y_position = random.uniform(-height, 0)
        self.reset()
        
    def reset(self):
        """Reset the column with new random characters"""
        self.chars = [self._random_char() for _ in range(self.trail_length)]
        self.y_position = random.uniform(-self.height, 0)
        
    def _random_char(self) -> str:
        """Get a random character from the current set"""
        return random.choice(self.CHAR_SETS[self.char_set])
        
    def update(self, delta_time: float):
        """Update column position"""
        self.y_position += self.speed * delta_time * 20  # Adjust speed multiplier
        
        # Reset if column has fallen off screen
        if self.y_position > self.height + self.trail_length:
            self.reset()
            
        # Randomly change a character
        if random.random() < 0.1:
            idx = random.randint(0, len(self.chars) - 1)
            self.chars[idx] = self._random_char()


class MatrixRainEffect(Static):
    """Matrix rain effect widget with psychedelic colors"""
    
    # Character sets for the effect
    CHAR_SETS = {
        'binary': ['0', '1'],
        'hex': ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F'],
        'katakana': ['ア','イ','ウ','エ','オ','カ','キ','ク','ケ','コ','サ','シ','ス','セ','ソ',
                      'タ','チ','ツ','テ','ト','ナ','ニ','ヌ','ネ','ノ','ハ','ヒ','フ','ヘ','ホ',
                      'マ','ミ','ム','メ','モ','ヤ','ユ','ヨ','ラ','リ','ル','レ','ロ','ワ','ヲ','ン'],
        'symbols': ['!','@','#','$','%','^','&','*','(',')','_','+','=','{','}','|','[',']',
                    '\\',':','"',';',"'",'<','>','?',',','.','/','-','~','`'],
        'mixed': ['0','1','A','B','C','ア','イ','ウ','!','@','#','$','%','^','&','*','X','Y','Z',
                  '♠','♥','♦','♣','★','☆','♪','♫','∞','∆','Ω','π','Σ','Φ','Ψ','α','β','γ','δ','ε']
    }
    
    # Rainbow colors for the effect
    RAINBOW_PHASES = [
        (255, 0, 0),     # Red
        (255, 128, 0),   # Orange
        (255, 255, 0),   # Yellow
        (128, 255, 0),   # Light Green
        (0, 255, 0),     # Green
        (0, 255, 128),   # Teal
        (0, 128, 255),   # Light Blue
        (136, 0, 255),   # Purple
    ]
    
    # Reactive properties
    char_set = reactive("mixed")
    speed_multiplier = reactive(1.0)
    column_count = reactive(50)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.columns = []
        self.last_update = datetime.now()
        self.color_phase = 0.0
        self.frame_count = 0
        
    def on_mount(self):
        """Initialize the effect when mounted"""
        # Log that we're mounting
        self.app.log("MatrixRainEffect: Mounting...")
        
        # Initialize columns with proper size
        self._initialize_columns()
        
        # Log size info
        self.app.log(f"MatrixRainEffect: Size is {self.size.width}x{self.size.height}")
        
        # Start the animation timer
        self.set_interval(0.05, self.update_rain)  # 20 FPS
        
        self.app.log("MatrixRainEffect: Animation timer started")
        
    def on_resize(self, event) -> None:
        """Handle resize events"""
        self._on_size_change()
        
    def _on_size_change(self):
        """Reinitialize columns when size changes"""
        width = self.size.width
        height = self.size.height
        
        # Only initialize if we have a valid size
        if width > 0 and height > 0:
            self._initialize_columns()
        
    def _initialize_columns(self):
        """Create initial columns"""
        width = self.size.width if self.size.width > 0 else 80
        height = self.size.height if self.size.height > 0 else 24
        
        # Clear existing columns
        self.columns = []
        
        # Create more columns for better coverage
        actual_columns = min(self.column_count, width // 2)  # At least 2 chars spacing
            
        # Distribute columns evenly across width with some randomness
        for i in range(actual_columns):
            # Base position evenly distributed
            base_x = (i * width) // actual_columns
            # Add some randomness to avoid perfect grid
            x_pos = base_x + random.randint(-1, 1)
            x_pos = max(0, min(width - 1, x_pos))  # Keep in bounds
            
            speed = random.uniform(0.5, 2.0) * self.speed_multiplier
            column = MatrixRainColumn(
                height=height,
                position=x_pos,
                speed=speed,
                char_set=self.char_set
            )
            # Start columns at different heights for immediate effect
            column.y_position = random.uniform(0, height)
            self.columns.append(column)
            
    def update_rain(self):
        """Update the rain animation"""
        # Update each column
        for column in self.columns:
            column.update(0.05)  # Update with fixed delta time
            
        # Refresh to trigger a new render
        self.refresh()
        
    def _get_rainbow_color(self, offset: float = 0) -> str:
        """Get rainbow color at current phase with offset"""
        phase = (self.color_phase + offset) % len(self.RAINBOW_PHASES)
        idx = int(phase)
        frac = phase - idx
        
        # Interpolate between colors
        color1 = self.RAINBOW_PHASES[idx]
        color2 = self.RAINBOW_PHASES[(idx + 1) % len(self.RAINBOW_PHASES)]
        
        r = int(color1[0] * (1 - frac) + color2[0] * frac)
        g = int(color1[1] * (1 - frac) + color2[1] * frac)
        b = int(color1[2] * (1 - frac) + color2[2] * frac)
        
        return f"rgb({r},{g},{b})"
        
    def render(self) -> Text:
        """Render the Matrix rain effect"""
        width = self.size.width if self.size.width > 0 else 80
        height = self.size.height if self.size.height > 0 else 24
        
        # Always increment frame count to show activity
        self.frame_count += 1
        
        # Initialize columns if we haven't yet
        if not self.columns and width > 0 and height > 0:
            self._initialize_columns()
        
        # Create a 2D grid to track what character to render at each position
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        styles = [[None for _ in range(width)] for _ in range(height)]
        
        # Render each column
        for column in self.columns:
            x = int(column.position)
            if 0 <= x < width:
                # Calculate where this column's characters should appear
                y_start = int(column.y_position)
                
                # Draw the trail
                for i, char in enumerate(column.chars):
                    y = y_start - i
                    if 0 <= y < height:
                        grid[y][x] = char
                        
                        # Style based on position in trail
                        if i == 0:
                            # Head - brightest
                            styles[y][x] = "bold #00ff00"
                        elif i < 3:
                            # Near head - bright
                            styles[y][x] = "#00dd00"
                        elif i < 6:
                            # Middle - medium
                            styles[y][x] = "#00aa00"
                        elif i < 10:
                            # Tail - dim
                            styles[y][x] = "#007700"
                        else:
                            # Very tail - very dim
                            styles[y][x] = "#004400"
        
        # Build the output text
        text = Text()
        for y in range(height):
            for x in range(width):
                char = grid[y][x]
                style = styles[y][x]
                if style:
                    text.append(char, style=style)
                else:
                    text.append(char)
            
            if y < height - 1:
                text.append("\n")
        
        return text
        
    def change_speed(self, multiplier: float):
        """Change the speed of the rain"""
        self.speed_multiplier = multiplier
        for column in self.columns:
            column.speed = random.uniform(0.5, 2.0) * multiplier
            
    def change_characters(self, char_set: str):
        """Change the character set"""
        if char_set in MatrixRainColumn.CHAR_SETS:
            self.char_set = char_set
            for column in self.columns:
                column.char_set = char_set
                column.reset()
                
    def add_columns(self, count: int = 10):
        """Add more columns to the rain"""
        width = self.size.width
        for _ in range(count):
            x_pos = random.randint(0, width - 1)
            speed = random.uniform(0.5, 2.0) * self.speed_multiplier
            column = MatrixRainColumn(
                height=self.size.height,
                position=x_pos,
                speed=speed,
                char_set=self.char_set
            )
            self.columns.append(column)