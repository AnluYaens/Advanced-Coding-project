"""
Loading and status indicator components.
"""

import customtkinter as ctk
from src.ui.config.typography import Typography


class LoadingIndicator(ctk.CTkLabel):
    """Animated loading indicator."""
    
    def __init__(self, parent):
        super().__init__(parent, text="", font=Typography.BODY)
        self.dots = 0
        self.is_loading = False

    def start(self):
        """Start the loading animation."""
        self.is_loading = True
        self.animate()

    def stop(self):
        """Stop the loading animation."""
        self.is_loading = False
        self.configure(text="")

    def animate(self):
        """Animate the loading indicator."""
        if not self.is_loading:
            return
        self.dots = (self.dots + 1) % 4
        self.configure(text="Thinking" + "." * self.dots)
        self.after(300, self.animate)