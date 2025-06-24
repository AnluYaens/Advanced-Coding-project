"""
Helper functions for the UI components.
"""

import customtkinter as ctk
from datetime import datetime
from src.ui.config.theme import PALETTE
from src.ui.config.typography import Typography


def create_empty_placeholder(parent, icon, title, subtitle):
    """
    Creates a standardized placeholder for when there is no data.
    
    Args:
        parent: Parent widget
        icon (str): Icon/emoji to display
        title (str): Main title text
        subtitle (str): Subtitle/description text
    """
    placeholder_frame = ctk.CTkFrame(parent, fg_color="transparent")
    placeholder_frame.pack(expand=True, fill="both", padx=10, pady=20)
    
    center_frame = ctk.CTkFrame(placeholder_frame, fg_color="transparent")
    center_frame.pack(expand=True)

    ctk.CTkLabel(
        center_frame,
        text=icon,
        font=Typography.get_font(40),
        text_color=PALETTE["text-tertiary"]
    ).pack(pady=(0, 10))
    
    ctk.CTkLabel(
        center_frame,
        text=title,
        font=Typography.HEADING_2,
        text_color=PALETTE["text"]
    ).pack()
    
    ctk.CTkLabel(
        center_frame,
        text=subtitle,
        font=Typography.BODY,
        text_color=PALETTE["text-secondary"],
        wraplength=210
    ).pack(pady=(4, 0))


def create_header(parent, title, show_date=False):
    """
    Helper to create a standard tab header.
    
    Args:
        parent: Parent widget
        title (str): Header title
        show_date (bool): Whether to show current date
    """
    header_frame = ctk.CTkFrame(parent, fg_color="transparent")
    header_frame.pack(fill="x", padx=30, pady=(20, 5))
    
    ctk.CTkLabel(
        header_frame, 
        text=title, 
        font=Typography.DISPLAY, 
        text_color=PALETTE["text"]
    ).pack(side="left")
    
    if show_date:
        ctk.CTkLabel(
            header_frame, 
            text=datetime.now().strftime("%B %Y"), 
            font=Typography.BODY, 
            text_color=PALETTE["text-secondary"]
        ).pack(side="right", pady=(8, 0))

    separator = ctk.CTkFrame(parent, height=1, fg_color=PALETTE["border"])
    separator.pack(fill="x", padx=30, pady=(5, 16))


def format_currency(amount):
    """Format amount as currency string."""
    return f"${amount:.2f}"


def truncate_text(text, max_length=20):
    """Truncate text with ellipsis if too long."""
    if text and len(text) > max_length:
        return text[:max_length] + "..."
    return text or ""