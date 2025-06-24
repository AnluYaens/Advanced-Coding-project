"""
Sidebar navigation component.
"""

import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage
from src.ui.config.theme import PALETTE
from src.ui.config.typography import Typography
from src.ui.components.buttons import AnimatedButton


class Sidebar(ctk.CTkFrame):
    """Sidebar navigation component."""
    
    def __init__(self, parent, tab_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(
            fg_color=PALETTE["sidebar"], 
            width=220, 
            corner_radius=0
        )
        self.pack_propagate(False)
        
        self.tab_callback = tab_callback
        self.nav_buttons = {}
        self.emoji_icons = {}
        
        self._create_header()
        self._load_icons()
        self._create_nav_buttons()
        
    def _create_header(self):
        """Create sidebar header."""
        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=16, pady=(20, 30))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, 
            text="Budget", 
            font=Typography.HEADING_1, 
            text_color=PALETTE["text"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header, 
            text="Tracker Assistant", 
            font=Typography.get_font(14, "normal"), 
            text_color=PALETTE["text-secondary"]
        ).pack(anchor="w")
        
    def _load_icons(self):
        """Load navigation icons."""
        def _load(path, size=(24, 24)):
            try:
                return CTkImage(
                    light_image=Image.open(path).resize(size, Image.Resampling.LANCZOS),
                    dark_image=Image.open(path).resize(size, Image.Resampling.LANCZOS),
                    size=size
                )
            except Exception as e:
                print(f"Error loading icon {path}: {e}")
                return None

        icon_paths = {
            "Dashboard": "src/assets/icons/dashboard.png",
            "Add Expense": "src/assets/icons/add_expense.png",
            "All Transactions": "src/assets/icons/all_transactions.png",
            "Analytics": "src/assets/icons/analytics.png",
            "AI Insights": "src/assets/icons/ai_insights.png",
            "Set Budget": "src/assets/icons/set_budget.png",
            "Currency": "src/assets/icons/currency.png",
            "Contact": "src/assets/icons/contact.png",
        }
        
        for name, path in icon_paths.items():
            self.emoji_icons[name] = _load(path)
            
    def _create_nav_buttons(self):
        """Create navigation buttons."""
        for tab_name in self.emoji_icons.keys():
            btn = AnimatedButton(
                self,
                text=f"  {tab_name}",
                anchor="w",
                height=48,
                fg_color="transparent",
                hover_color=PALETTE["bg-hover"],
                text_color=PALETTE["text-secondary"],
                font=Typography.get_font(15, "medium"),
                command=lambda t=tab_name: self.tab_callback(t),
                image=self.emoji_icons.get(tab_name),
                compound="left",
                corner_radius=8
            )
            btn.pack(fill="x", padx=16, pady=2)
            self.nav_buttons[tab_name] = btn
            
    def set_active_tab(self, tab_name):
        """Set the visual state of the active navigation tab."""
        for name, btn in self.nav_buttons.items():
            is_active = name == tab_name
            btn.configure(
                fg_color=PALETTE["accent"] if is_active else "transparent",
                text_color=PALETTE["text"] if is_active else PALETTE["text-secondary"]
            )