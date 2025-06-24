"""
Card components with glass morphism effects.
"""

import customtkinter as ctk
from src.ui.config.theme import PALETTE


class GlassCard(ctk.CTkFrame):
    """Card with glass morphism effect."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"]
        )