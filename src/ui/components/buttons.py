"""
Button components with enhanced interactions and animations.
"""

import customtkinter as ctk
from src.ui.config.theme import PALETTE


class AnimatedButton(ctk.CTkButton):
    """Button with hover and press animations."""
    
    def __init__(self, *args, **kwargs):
        self.default_color = kwargs.get('fg_color', PALETTE["accent"])
        self.hover_color = kwargs.get('hover_color', PALETTE["accent-hover"])
        super().__init__(*args, **kwargs)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event=None):
        """Handle mouse enter event."""
        self.configure(fg_color=self.hover_color)

    def _on_leave(self, event=None):
        """Handle mouse leave event."""
        self.configure(fg_color=self.default_color)

    def _on_press(self, event=None):
        """Handle button press event."""
        self.configure(fg_color=PALETTE["accent-dark"])

    def _on_release(self, event):
        """Handle button release event."""
        if self.winfo_containing(event.x_root, event.y_root) == self:
            self.configure(fg_color=self.hover_color)
        else:
            self.configure(fg_color=self.default_color)