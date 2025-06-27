"""
Contact and about view for application information.
"""

import customtkinter as ctk
from src.ui.config.theme import PALETTE
from src.ui.config.typography import Typography
from src.ui.components.cards import GlassCard
from src.ui.utils.helpers import create_header


class ContactView:
    """Contact and about information view."""
    
    def __init__(self, parent):
        self.parent = parent
        
    def create(self):
        """Create the contact view."""
        create_header(self.parent, "About & Contact")
        
        # --- Scrollable frame for content ---
        scroll_frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            scrollbar_button_color=PALETTE["accent"],
            scrollbar_button_hover_color=PALETTE["accent-hover"]
        )
        scroll_frame.pack(fill="both", expand=True, padx=10)

        # --- About section ---
        about_card = GlassCard(scroll_frame)
        about_card.pack(fill="x", padx=20, pady=(16, 12))
        
        about_content = ctk.CTkFrame(about_card, fg_color="transparent")
        about_content.pack(padx=40, pady=40)
        
        title_frame = ctk.CTkFrame(about_content, fg_color="transparent")
        title_frame.pack(anchor="w", pady=(0, 12))
        
        ctk.CTkLabel(
            title_frame, 
            text="💰", 
            font=Typography.get_font(30, "normal")
        ).pack(side="left", padx=(0, 12))
        
        title_text_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_text_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_text_frame, 
            text="AI Budget Tracker", 
            font=Typography.HEADING_1, 
            text_color=PALETTE["text"], 
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            about_content, 
            text="Modern budget management application with AI integration", 
            font=Typography.BODY_LARGE, 
            text_color=PALETTE["text-secondary"], 
            wraplength=500, 
            anchor="w"
        ).pack(anchor="w", pady=(20, 24))
        
        # --- Features grid ---
        features_frame = ctk.CTkFrame(about_content, fg_color="transparent")
        features_frame.pack(fill="x")
        
        features = [
            ("🎨", "Modern Design", "Dark theme and innovating widgets"),
            ("🤖", "AI Assistant", "Natural language expense tracking"),
            ("📊", "Analytics", "Visual insights into spending"),
            ("💱", "Currency", "Real-time conversion"),
            ("📂", "Import", "Bank statement support"),
            ("🎯", "Budgeting", "Category management")
        ]
        
        for i in range(2):
            features_frame.grid_columnconfigure(i, weight=1)
            
        for idx, (icon, title, desc) in enumerate(features):
            feature_card = ctk.CTkFrame(
                features_frame, 
                fg_color=PALETTE["bg-elevated"], 
                corner_radius=8
            )
            feature_card.grid(row=idx//2, column=idx%2, padx=6, pady=6, sticky="ew")
            
            feature_content = ctk.CTkFrame(feature_card, fg_color="transparent")
            feature_content.pack(padx=16, pady=16)
            
            ctk.CTkLabel(
                feature_content, 
                text=f"{icon} {title}", 
                font=Typography.get_font(13, "semibold"), 
                text_color=PALETTE["text"], 
                anchor="w"
            ).pack(anchor="w")
            
            ctk.CTkLabel(
                feature_content, 
                text=desc, 
                font=Typography.CAPTION, 
                text_color=PALETTE["text-tertiary"], 
                anchor="w", 
                wraplength=200
            ).pack(anchor="w", pady=(3, 0))
        
        # --- Developer info ---
        dev_card = GlassCard(scroll_frame)
        dev_card.pack(fill="x", padx=20, pady=12)
        
        dev_content = ctk.CTkFrame(dev_card, fg_color="transparent")
        dev_content.pack(padx=40, pady=30)
        
        ctk.CTkLabel(
            dev_content, 
            text="👨‍💻 Developer Information", 
            font=Typography.HEADING_2, 
            text_color=PALETTE["text"]
        ).pack(anchor="w", pady=(0, 16))
        
        contact_info = [
            ("Created by:", "Angel Jaen"),
            ("Email:", "anlujaen@gmail.com"),
            ("GitHub:", "github.com/anlujaen/ai-budget-tracker"),
            ("License:", "MIT License")
        ]
        
        for label, value in contact_info:
            info_frame = ctk.CTkFrame(dev_content, fg_color="transparent")
            info_frame.pack(fill="x", pady=3)
            
            ctk.CTkLabel(
                info_frame, 
                text=label, 
                font=Typography.get_font(12, "medium"), 
                text_color=PALETTE["text-secondary"], 
                width=80, 
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                info_frame, 
                text=value, 
                font=Typography.BODY, 
                text_color=PALETTE["text"], 
                anchor="w"
            ).pack(side="left", padx=(12, 0))