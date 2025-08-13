"""
Glowing Input Widget - Psychedelic input fields with rainbow glow effect
"""
from textual.widgets import Input, Button
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.style import Style
import math
from datetime import datetime


class GlowInput(Input):
    """Input field with animated rainbow glow effect"""
    
    # Rainbow colors for glow effect
    GLOW_COLORS = [
        "#ff0000",  # Red
        "#ff8800",  # Orange
        "#ffff00",  # Yellow
        "#88ff00",  # Light Green
        "#00ff00",  # Green
        "#00ff88",  # Teal
        "#0088ff",  # Light Blue
        "#8800ff",  # Purple
    ]
    
    glow_active = reactive(True)
    glow_phase = reactive(0.0)
    
    def __init__(self, placeholder: str = "", password: bool = False, **kwargs):
        super().__init__(placeholder=placeholder, password=password, **kwargs)
        self.last_update = datetime.now()
        
    def on_mount(self):
        """Start the glow animation"""
        if self.glow_active:
            self.set_interval(0.05, self.update_glow)
            
    def update_glow(self):
        """Update the glow animation phase"""
        now = datetime.now()
        delta_time = (now - self.last_update).total_seconds()
        self.last_update = now
        
        # Update phase for smooth color transition
        self.glow_phase += delta_time * 2  # Full cycle every 0.5 seconds
        if self.glow_phase >= len(self.GLOW_COLORS):
            self.glow_phase -= len(self.GLOW_COLORS)
            
        # Force a refresh to update the glow effect
        self.refresh()
        
    def get_current_glow_color(self) -> str:
        """Get the current glow color based on animation phase"""
        if not self.glow_active:
            return "#ffffff"
            
        # Interpolate between colors
        idx = int(self.glow_phase)
        frac = self.glow_phase - idx
        
        color1 = self.GLOW_COLORS[idx]
        color2 = self.GLOW_COLORS[(idx + 1) % len(self.GLOW_COLORS)]
        
        # Simple hex color interpolation
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
        def rgb_to_hex(r, g, b):
            return f"#{r:02x}{g:02x}{b:02x}"
            
        r1, g1, b1 = hex_to_rgb(color1)
        r2, g2, b2 = hex_to_rgb(color2)
        
        r = int(r1 * (1 - frac) + r2 * frac)
        g = int(g1 * (1 - frac) + g2 * frac)
        b = int(b1 * (1 - frac) + b2 * frac)
        
        return rgb_to_hex(r, g, b)
        
    def render_styles(self) -> str:
        """Apply glow effect to the input styling"""
        # Get base styles
        base_styles = super().render_styles()
        
        # Add glow effect using CSS-like properties
        if self.glow_active and self.has_focus:
            color = self.get_current_glow_color()
            # Note: Textual doesn't support box-shadow directly, 
            # but we can simulate with border colors
            return f"{base_styles} border: solid {color};"
        
        return base_styles


class PsychedelicButton(Button):
    """Button with psychedelic gradient animation"""
    
    class Pressed(Message):
        """Message sent when button is pressed"""
        def __init__(self, button):
            self.button = button
            super().__init__()
    
    def __init__(self, label: str = "ENTER", **kwargs):
        super().__init__(label, **kwargs)
        self.can_focus = True
        self.gradient_phase = 0.0
        self.last_update = datetime.now()
        
    def on_mount(self):
        """Start gradient animation"""
        self.set_interval(0.05, self.update_gradient)
        
    def update_gradient(self):
        """Update gradient animation"""
        now = datetime.now()
        delta_time = (now - self.last_update).total_seconds()
        self.last_update = now
        
        self.gradient_phase += delta_time * 3  # Faster animation
        self.refresh()
    
    def on_click(self):
        """Handle button click"""
        self.post_message(self.Pressed(self))
        
    def render_styles(self) -> str:
        """Apply psychedelic styling"""
        base_styles = super().render_styles()
        
        # Calculate color based on phase
        hue = (self.gradient_phase * 60) % 360
        color1 = f"hsl({hue}, 100%, 50%)"
        color2 = f"hsl({(hue + 60) % 360}, 100%, 50%)"
        
        if self.has_focus:
            return f"{base_styles} background: {color1}; color: black; font-weight: bold;"
        else:
            return f"{base_styles} background: {color2}; color: white;"