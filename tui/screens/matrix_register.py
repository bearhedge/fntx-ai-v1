#!/usr/bin/env python3
"""
Registration screen with matrix rain effect
"""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Label, LoadingIndicator
from textual.screen import Screen
from textual.binding import Binding
from textual.message import Message
import re

from .matrix_login_final import ProperMatrixRainWidget
from ..components.glow_input import GlowInput, PsychedelicButton
from ..services.auth_service import get_auth_service
from ..services.api_client import APIError


class PasswordStrengthIndicator(Label):
    """Visual password strength indicator"""
    
    def __init__(self):
        super().__init__("", id="password-strength")
        self.strength_level = 0
        
    def update_strength(self, password: str):
        """Update password strength based on criteria"""
        score = 0
        issues = []
        
        if len(password) >= 8:
            score += 1
        else:
            issues.append("8+ chars")
            
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            issues.append("uppercase")
            
        if re.search(r'[a-z]', password):
            score += 1
        else:
            issues.append("lowercase")
            
        if re.search(r'\d', password):
            score += 1
        else:
            issues.append("number")
            
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        else:
            issues.append("special char")
        
        self.strength_level = score
        
        if score == 0:
            self.update("")
        elif score <= 2:
            self.update(f"[red]Weak - Need: {', '.join(issues)}[/red]")
        elif score <= 3:
            self.update(f"[yellow]Fair - Need: {', '.join(issues)}[/yellow]")
        elif score <= 4:
            self.update(f"[cyan]Good - Need: {', '.join(issues)}[/cyan]")
        else:
            self.update("[green]Strong ✓[/green]")


class MatrixRegisterScreen(Screen):
    """Registration screen with matrix rain background"""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("tab", "next_field", "Next Field", show=False),
        Binding("shift+tab", "prev_field", "Previous Field", show=False),
    ]
    
    class RegistrationSuccess(Message):
        """Message sent when registration is successful"""
        def __init__(self, user_data: dict):
            self.user_data = user_data
            super().__init__()
    
    def __init__(self):
        super().__init__()
        self.auth_service = get_auth_service()
        self.is_loading = False
        
    def compose(self) -> ComposeResult:
        """Create the layout"""
        with Container(id="main-container"):
            # Matrix background
            yield ProperMatrixRainWidget(id="matrix-rain")
            
            # Registration form overlay
            with Container(id="register-form"):
                # Title
                yield Label("[bold cyan]CREATE ACCOUNT[/bold cyan]", id="title")
                
                # Error message container
                yield Label("", id="error-message", classes="error-hidden")
                
                # Form fields
                yield GlowInput(
                    placeholder="Choose Username",
                    id="username",
                    classes="glow-input"
                )
                
                yield GlowInput(
                    placeholder="Email Address",
                    id="email",
                    classes="glow-input"
                )
                
                yield GlowInput(
                    placeholder="Full Name (optional)",
                    id="fullname",
                    classes="glow-input"
                )
                
                yield GlowInput(
                    placeholder="Create Password",
                    password=True,
                    id="password",
                    classes="glow-input"
                )
                
                # Password strength indicator
                yield PasswordStrengthIndicator()
                
                yield GlowInput(
                    placeholder="Confirm Password",
                    password=True,
                    id="confirm-password",
                    classes="glow-input"
                )
                
                # Loading indicator
                yield LoadingIndicator(id="loading", classes="loading-hidden")
                
                # Buttons
                with Horizontal(id="button-container"):
                    yield PsychedelicButton(
                        "BACK",
                        id="back-button"
                    )
                    yield PsychedelicButton(
                        "CREATE",
                        id="create-button"
                    )
    
    def on_mount(self):
        """Focus username on mount"""
        self.query_one("#username").focus()
        
    def action_back(self):
        """Go back to login screen"""
        self.app.pop_screen()
        
    def action_next_field(self):
        """Move to next input field"""
        focused = None
        inputs = ["#username", "#email", "#fullname", "#password", "#confirm-password"]
        
        for i, input_id in enumerate(inputs):
            if self.query_one(input_id).has_focus:
                focused = i
                break
                
        if focused is not None and focused < len(inputs) - 1:
            self.query_one(inputs[focused + 1]).focus()
        elif focused == len(inputs) - 1:
            self.query_one("#create-button").focus()
            
    def action_prev_field(self):
        """Move to previous input field"""
        focused = None
        inputs = ["#username", "#email", "#fullname", "#password", "#confirm-password"]
        
        for i, input_id in enumerate(inputs):
            if self.query_one(input_id).has_focus:
                focused = i
                break
                
        if focused is not None and focused > 0:
            self.query_one(inputs[focused - 1]).focus()
        elif self.query_one("#create-button").has_focus:
            self.query_one("#confirm-password").focus()
            
    async def on_input_changed(self, event):
        """Handle input changes"""
        if event.input.id == "password":
            # Update password strength indicator
            strength_indicator = self.query_one("#password-strength", PasswordStrengthIndicator)
            strength_indicator.update_strength(event.value)
            
    async def on_input_submitted(self, event):
        """Handle Enter key in input fields"""
        inputs = ["username", "email", "fullname", "password", "confirm-password"]
        
        try:
            current_idx = inputs.index(event.input.id)
            if current_idx < len(inputs) - 1:
                self.query_one(f"#{inputs[current_idx + 1]}").focus()
            else:
                await self.handle_registration()
        except ValueError:
            pass
            
    async def on_psychedelic_button_pressed(self, event):
        """Handle button clicks"""
        if event.button.id == "create-button":
            await self.handle_registration()
        elif event.button.id == "back-button":
            self.app.pop_screen()
            
    def show_error(self, message: str):
        """Show error message"""
        error_label = self.query_one("#error-message")
        error_label.update(f"[bold red]{message}[/bold red]")
        error_label.remove_class("error-hidden")
        error_label.add_class("error-visible")
        
    def hide_error(self):
        """Hide error message"""
        error_label = self.query_one("#error-message")
        error_label.update("")
        error_label.remove_class("error-visible")
        error_label.add_class("error-hidden")
        
    def show_loading(self):
        """Show loading indicator"""
        self.query_one("#loading").remove_class("loading-hidden")
        self.query_one("#loading").add_class("loading-visible")
        self.query_one("#create-button").disabled = True
        self.query_one("#back-button").disabled = True
        self.is_loading = True
        
    def hide_loading(self):
        """Hide loading indicator"""
        self.query_one("#loading").remove_class("loading-visible")
        self.query_one("#loading").add_class("loading-hidden")
        self.query_one("#create-button").disabled = False
        self.query_one("#back-button").disabled = False
        self.is_loading = False
        
    async def handle_registration(self):
        """Handle registration form submission"""
        if self.is_loading:
            return
            
        # Get form values
        username = self.query_one("#username").value.strip()
        email = self.query_one("#email").value.strip()
        fullname = self.query_one("#fullname").value.strip()
        password = self.query_one("#password").value
        confirm_password = self.query_one("#confirm-password").value
        
        # Validate inputs
        if not username:
            self.show_error("Username is required")
            self.query_one("#username").focus()
            return
            
        if len(username) < 3:
            self.show_error("Username must be at least 3 characters")
            self.query_one("#username").focus()
            return
            
        if not re.match("^[a-zA-Z0-9_]+$", username):
            self.show_error("Username can only contain letters, numbers, and underscores")
            self.query_one("#username").focus()
            return
            
        if not email:
            self.show_error("Email is required")
            self.query_one("#email").focus()
            return
            
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            self.show_error("Invalid email format")
            self.query_one("#email").focus()
            return
            
        if not password:
            self.show_error("Password is required")
            self.query_one("#password").focus()
            return
            
        if len(password) < 8:
            self.show_error("Password must be at least 8 characters")
            self.query_one("#password").focus()
            return
            
        if password != confirm_password:
            self.show_error("Passwords do not match")
            self.query_one("#confirm-password").focus()
            return
            
        # Check password strength
        strength_indicator = self.query_one("#password-strength", PasswordStrengthIndicator)
        if strength_indicator.strength_level < 3:
            self.show_error("Password is too weak. Please make it stronger.")
            self.query_one("#password").focus()
            return
            
        # Hide any previous errors
        self.hide_error()
        
        # Show loading
        self.show_loading()
        
        try:
            # Attempt registration
            user_data = await self.auth_service.register(
                username, 
                email, 
                password,
                fullname if fullname else None
            )
            
            # Post success message
            self.post_message(self.RegistrationSuccess(user_data))
            
        except APIError as e:
            self.hide_loading()
            if e.status_code == 400:
                self.show_error(e.detail)
            else:
                self.show_error(f"Registration failed: {e.detail}")
        except Exception as e:
            self.hide_loading()
            self.show_error("Connection error: Please check your internet connection")


# CSS for the registration screen
MATRIX_REGISTER_CSS = """
MatrixRegisterScreen {
    background: black;
}

#main-container {
    width: 100%;
    height: 100%;
}

#matrix-rain {
    width: 100%;
    height: 100%;
}

#register-form {
    position: absolute;
    width: 60;
    height: auto;
    min-height: 45;
    background: rgba(0, 0, 0, 0.5);
    border: double #00ff00;
    padding: 2;
    align: center middle;
    offset: 120% 25%;
    margin: 30 -30;
}

#title {
    height: 3;
    text-align: center;
    margin-bottom: 2;
    width: 100%;
}

#error-message {
    width: 100%;
    height: 2;
    text-align: center;
    margin-bottom: 1;
}

.error-hidden {
    display: none;
}

.error-visible {
    display: block;
    color: #ff0000;
}

.glow-input {
    width: 40;
    margin: 1;
    align: center middle;
}

#password-strength {
    width: 40;
    height: 2;
    text-align: center;
    margin-bottom: 1;
    align: center middle;
}

#loading {
    width: 100%;
    height: 3;
    align: center middle;
}

.loading-hidden {
    display: none;
}

.loading-visible {
    display: block;
}

#button-container {
    width: 100%;
    height: 3;
    align: center middle;
    margin-top: 2;
}

#back-button {
    width: 10;
    margin-right: 2;
    align: center middle;
}

#create-button {
    width: 12;
    align: center middle;
}
"""