"""
Analytics view for spending insights and statistics.
"""

import customtkinter as ctk
from src.ui.config.theme import PALETTE, CATEGORY_COLORS
from src.ui.config.typography import Typography
from src.ui.components.cards import GlassCard
from src.ui.utils.helpers import create_header, create_empty_placeholder
from src.core.database import get_db_session
from src.core.models import Expense


class AnalyticsView:
    """Analytics view with spending insights."""
    
    def __init__(self, parent):
        self.parent = parent
        
    def create(self):
        """Create the analytics view."""
        create_header(self.parent, "Spending Analytics")
        
        try:
            with get_db_session() as session:
                expenses = session.query(Expense).order_by(Expense.date.desc()).all()
                session.expunge_all()
            
            if not expenses:
                create_empty_placeholder(
                    self.parent, 
                    "📊", 
                    "No Expenses Recorded", 
                    "Add some expenses to see your analytics."
                )
                return

            total = sum(e.amount for e in expenses)
            
            # --- Summary cards ---
            summary_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
            summary_frame.pack(fill="x", padx=30, pady=16)
            
            for i in range(3):
                summary_frame.grid_columnconfigure(i, weight=1)
            
            self._create_summary_card(summary_frame, "💰", "Total Expenses", f"${total:.2f}", PALETTE["purple"], 0)
            self._create_summary_card(summary_frame, "📈", "Average Transaction", f"${total/len(expenses):.2f}", PALETTE["blue"], 1)
            self._create_summary_card(summary_frame, "💳", "Total Transactions", str(len(expenses)), PALETTE["green"], 2)
            
            # --- Category breakdown ---
            detail_card = GlassCard(self.parent)
            detail_card.pack(fill="both", expand=True, padx=30, pady=(16, 20))
            
            detail_content = ctk.CTkFrame(detail_card, fg_color="transparent")
            detail_content.pack(padx=20, pady=20, fill="both")
            
            ctk.CTkLabel(
                detail_content, 
                text="Spending by Category", 
                font=Typography.HEADING_2, 
                text_color=PALETTE["text"]
            ).pack(anchor="w", pady=(0, 16))
                
            # --- Calculate category totals ---
            by_category = {}
            for e in expenses:
                category = e.category or "Other"
                by_category[category] = by_category.get(category, 0) + e.amount
            
            # --- Display categories ---
            for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total * 100) if total > 0 else 0
                color = CATEGORY_COLORS.get(cat, PALETTE["text-tertiary"])
                
                cat_frame = ctk.CTkFrame(
                    detail_content, 
                    fg_color=PALETTE["bg-elevated"], 
                    corner_radius=8,
                    height=60
                )
                cat_frame.pack(fill="x", pady=4)
                cat_frame.pack_propagate(False)

                accent_bar = ctk.CTkFrame(cat_frame, width=4, fg_color=color, corner_radius=0)
                accent_bar.pack(side="left", fill="y", padx=(0, 1))

                cat_content = ctk.CTkFrame(cat_frame, fg_color="transparent")
                cat_content.pack(fill="both", expand=True, padx=(12, 16))

                cat_content.grid_columnconfigure(0, weight=1) 
                cat_content.grid_columnconfigure(1, weight=0) 
                cat_content.grid_rowconfigure(0, weight=1)
                
                info_frame = ctk.CTkFrame(cat_content, fg_color="transparent")
                info_frame.grid(row=0, column=0, sticky="w")
                
                ctk.CTkLabel(
                    info_frame, 
                    text=cat, 
                    font=Typography.get_font(14, "semibold"), 
                    text_color=color, 
                    anchor="w"
                ).pack(anchor="w")
                
                ctk.CTkLabel(
                    info_frame, 
                    text=f"{percentage:.1f}% of total", 
                    font=Typography.CAPTION, 
                    text_color=PALETTE["text-tertiary"], 
                    anchor="w"
                ).pack(anchor="w", pady=(2, 0))
                
                ctk.CTkLabel(
                    cat_content, 
                    text=f"${amount:.2f}", 
                    font=Typography.get_font(18, "bold"), 
                    text_color=PALETTE["text"]
                ).grid(row=0, column=1, sticky="e")
                
        except Exception as e:
            create_empty_placeholder(
                self.parent, 
                "❌", 
                "Error Loading Analytics", 
                str(e)
            )

    def _create_summary_card(self, parent, icon, title, value, color, column):
        """Create a summary statistics card."""
        card = GlassCard(parent)
        card.grid(row=0, column=column, padx=6, sticky="ew")
        card.configure(border_color=PALETTE["border-light"])
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(padx=20, pady=20)
         
        # --- Icon background ---
        icon_bg = ctk.CTkFrame(
            content, 
            width=40, 
            height=40, 
            fg_color=PALETTE["bg-elevated"], 
            corner_radius=8
        )
        icon_bg.pack(pady=(0, 8))
        icon_bg.pack_propagate(False)
        
        ctk.CTkLabel(
            icon_bg, 
            text=icon, 
            font=Typography.get_font(20, "normal")
        ).pack(expand=True)
        
        # --- Text ---
        ctk.CTkLabel(
            content, 
            text=title, 
            font=Typography.CAPTION, 
            text_color=PALETTE["text-secondary"]
        ).pack()
        
        ctk.CTkLabel(
            content, 
            text=value, 
            font=Typography.get_font(20, "bold"), 
            text_color=PALETTE["text"]
        ).pack(pady=(4, 0))