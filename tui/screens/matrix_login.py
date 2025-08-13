"""
Matrix Login Screen - Combined Matrix rain effect with login form
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Center
from textual.widgets import Static, Label
from textual.screen import Screen
from textual.binding import Binding
from textual import events
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from datetime import datetime
import random
import math

from ..widgets.glow_input import GlowInput, PsychedelicButton


class MatrixRainBackground(Static):
    """Matrix rain effect background widget"""
    
    # Character sets for the matrix effect
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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.frame_count = 0
        self.columns = []
        self.char_set = 'mixed'
        
    def on_mount(self):
        """Start the matrix animation"""
        self.set_interval(0.1, self.update_matrix)
        self._initialize_columns()
        
    def _initialize_columns(self):
        """Initialize matrix columns"""
        width = self.size.width if self.size.width > 0 else 80
        height = self.size.height if self.size.height > 0 else 40
        
        # Create columns distributed across width
        num_columns = min(50, width // 2)
        self.columns = []
        
        for i in range(num_columns):
            col = {
                'x': (i * width) // num_columns + random.randint(-1, 1),
                'y': random.randint(-height, 0),
                'speed': random.uniform(0.5, 2.0),
                'chars': [random.choice(self.CHAR_SETS[self.char_set]) for _ in range(random.randint(10, 25))],
                'trail_length': random.randint(10, 25)
            }
            self.columns.append(col)
        
    def update_matrix(self):
        """Update the matrix animation"""
        self.frame_count += 1
        
        # Update column positions
        height = self.size.height if self.size.height > 0 else 40
        for col in self.columns:
            col['y'] += col['speed']
            
            # Reset column if it goes off screen
            if col['y'] > height + col['trail_length']:
                col['y'] = random.randint(-height, -10)
                col['chars'] = [random.choice(self.CHAR_SETS[self.char_set]) for _ in range(col['trail_length'])]
                
            # Randomly change characters
            if random.random() < 0.1:
                idx = random.randint(0, len(col['chars']) - 1)
                col['chars'][idx] = random.choice(self.CHAR_SETS[self.char_set])
        
        self.refresh()
        
    def render(self) -> Text:
        """Render the matrix effect as background"""
        width = self.size.width if self.size.width > 0 else 80
        height = self.size.height if self.size.height > 0 else 40
        
        # Create grid for rendering
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        styles = [[None for _ in range(width)] for _ in range(height)]
        
        # Render each column
        for col in self.columns:
            x = col['x']
            if 0 <= x < width:
                # Draw the trail
                for i, char in enumerate(col['chars']):
                    y = int(col['y'] - i)
                    if 0 <= y < height:
                        grid[y][x] = char
                        
                        # Style based on position
                        if i == 0:
                            styles[y][x] = "#00ff00"  # Bright green
                        elif i < 3:
                            styles[y][x] = "#00dd00"
                        elif i < 6:
                            styles[y][x] = "#00aa00"
                        elif i < 10:
                            styles[y][x] = "#007700"
                        else:
                            styles[y][x] = "#004400"  # Dim green
        
        # Build text output
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


class MatrixLoginScreen(Screen):
    """Login screen using the combined matrix widget"""
    
    BINDINGS = [
        Binding("enter", "submit", "Login", priority=True),
        Binding("tab", "next_field", "Next Field"),
        Binding("shift+tab", "previous_field", "Previous Field"),
        Binding("escape", "toggle_mode", "Switch Mode"),
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit"),
    ]
    
    # ASCII Art FNTX Logo
    FNTX_LOGO = """
███████╗███╗   ██╗████████╗██╗  ██╗
██╔════╝████╗  ██║╚══██╔══╝╚██╗██╔╝
█████╗  ██╔██╗ ██║   ██║    ╚███╔╝ 
██╔══╝  ██║╚██╗██║   ██║    ██╔██╗ 
██║     ██║ ╚████║   ██║   ██╔╝ ██╗
╚═╝     ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝
"""
    
    def __init__(self):
        super().__init__()
        self.login_mode = True
        self.logo_phase = 0.0
        self.last_update = datetime.now()
        
    def compose(self) -> ComposeResult:
        """Create the screen with matrix background and login overlay"""
        # Stack the widgets using absolute positioning
        yield MatrixRainBackground(id="matrix-background")
        
        # Login form overlay
        with Center(id="login-wrapper"):
            with Container(id="login-container"):
                # Logo
                yield Static(id="logo", classes="logo")
                
                # Title
                yield Label(id="title", classes="title")
                
                # Form fields
                with Vertical(id="form-container"):
                    yield GlowInput(
                        placeholder="Enter Username",
                        id="username",
                        classes="glow-input"
                    )
                    yield GlowInput(
                        placeholder="Enter Password",
                        password=True,
                        id="password",
                        classes="glow-input"
                    )
                    
                    # Email field for registration (hidden by default)
                    yield GlowInput(
                        placeholder="Enter Email",
                        id="email",
                        classes="glow-input hidden"
                    )
                    
                    with Horizontal(id="button-container"):
                        yield PsychedelicButton(
                            "ENTER THE TRADING MATRIX",
                            id="submit-button"
                        )
                        
                # Mode toggle hint
                yield Label(
                    "[cyan]Press ESC to switch mode[/cyan]",
                    id="mode-hint",
                    classes="hint"
                )
        
    def on_mount(self):
        """Initialize the login screen"""
        self.update_logo()
        self.update_title()
        self.set_interval(0.1, self.animate_logo)
        
        # Focus username field
        self.query_one("#username").focus()
        
    def animate_logo(self):
        """Animate the logo with pulsing effect"""
        now = datetime.now()
        delta_time = (now - self.last_update).total_seconds()
        self.last_update = now
        
        self.logo_phase += delta_time * 2
        self.update_logo()
        
    def update_logo(self):
        """Update logo with rainbow effect"""
        logo_widget = self.query_one("#logo")
        
        # Calculate color based on phase
        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
        color_idx = int(self.logo_phase) % len(colors)
        color = colors[color_idx]
        
        # Create styled logo
        styled_logo = Text()
        for line in self.FNTX_LOGO.strip().split('\n'):
            styled_logo.append(line, style=f"bold {color}")
            styled_logo.append('\n')
            
        logo_widget.update(Align.center(styled_logo))
        
    def update_title(self):
        """Update title based on mode"""
        title_widget = self.query_one("#title")
        if self.login_mode:
            title_text = "[bold cyan]FNTX TRADING TERMINAL[/bold cyan]\n[dim]Press ENTER to continue[/dim]"
        else:
            title_text = "[bold magenta]JOIN THE FNTX NETWORK[/bold magenta]\n[dim]Create your account[/dim]"
            
        title_widget.update(Align.center(Text(title_text)))
        
    def action_submit(self):
        """Handle form submission"""
        username = self.query_one("#username").value
        password = self.query_one("#password").value
        
        if not self.login_mode:
            email = self.query_one("#email").value
            if not email:
                self.notify("Email required for registration", severity="error")
                return
                
        if not username or not password:
            self.notify("Username and password required", severity="error")
            return
            
        # For demo, accept any credentials
        if self.login_mode:
            self.notify(f"Welcome to the Matrix, {username}", severity="success")
        else:
            self.notify(f"Registration successful, {username}", severity="success")
            
        # Transition to main app
        self.app.action_show_dashboard()
        
    def action_toggle_mode(self):
        """Toggle between login and register mode"""
        self.login_mode = not self.login_mode
        self.update_title()
        
        # Toggle email field visibility
        email_field = self.query_one("#email")
        if self.login_mode:
            email_field.add_class("hidden")
        else:
            email_field.remove_class("hidden")
            
        # Update button text
        button = self.query_one("#submit-button")
        if self.login_mode:
            button.label = "ENTER THE MATRIX"
        else:
            button.label = "JOIN THE RESISTANCE"
            
    def action_quit(self):
        """Quit the application"""
        self.app.exit()
            
    def action_next_field(self):
        """Move to next input field"""
        focused = self.app.focused
        if focused and focused.id == "username":
            self.query_one("#password").focus()
        elif focused and focused.id == "password":
            if not self.login_mode:
                self.query_one("#email").focus()
            else:
                self.query_one("#submit-button").focus()
        elif focused and focused.id == "email":
            self.query_one("#submit-button").focus()
            
    def action_previous_field(self):
        """Move to previous input field"""
        focused = self.app.focused
        if focused and focused.id == "password":
            self.query_one("#username").focus()
        elif focused and focused.id == "email":
            self.query_one("#password").focus()
        elif focused and focused.id == "submit-button":
            if not self.login_mode:
                self.query_one("#email").focus()
            else:
                self.query_one("#password").focus()


# CSS for the matrix login screen
MATRIX_LOGIN_CSS = """
MatrixLoginScreen {
    background: black;
}

#matrix-background {
    width: 100%;
    height: 100%;
    background: black;
}

#login-wrapper {
    dock: top;
    width: 100%;
    height: 100%;
    align: center middle;
}

#login-container {
    background: rgba(0, 0, 0, 0.85);
    border: double #00ff00;
    padding: 2;
    width: 60;
    height: auto;
    min-height: 30;
    max-height: 40;
}

.logo {
    height: 6;
    margin-bottom: 1;
}

.title {
    height: 3;
    text-align: center;
    margin-bottom: 2;
}

#form-container {
    width: 100%;
    height: auto;
    align: center middle;
}

.glow-input {
    width: 40;
    margin: 1;
}

.hidden {
    display: none;
}

#button-container {
    width: 100%;
    height: 3;
    align: center middle;
    margin-top: 2;
}

#submit-button {
    width: 30;
}

.hint {
    width: 100%;
    text-align: center;
    margin-top: 2;
}
"""