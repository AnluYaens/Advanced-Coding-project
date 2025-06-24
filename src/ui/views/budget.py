"""
Budget management view for setting spending limits.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from src.ui.config.theme import PALETTE
from src.ui.config.typography import Typography
from src.ui.components.buttons import AnimatedButton
from src.ui.components.cards import GlassCard
from src.ui.utils.helpers import create_header
from src.core.database import save_budget, get_budget


class BudgetView:
    """Budget management view."""
    
    def __init__(self, parent):
        self.parent = parent
        self.total_budget_var = None
        self.category_budget_vars = {}
        
    def create(self):
        """Create the budget management view."""
        create_header(self.parent, "Budget Management")
        
        budget_card = GlassCard(self.parent)
        budget_card.pack(fill="x", padx=30, pady=16)
        
        budget_content = ctk.CTkFrame(budget_card, fg_color="transparent")
        budget_content.pack(padx=40, pady=40)
        
        # --- Get current budget ---
        current = get_budget() or {}
        
        # --- Total budget ---
        ctk.CTkLabel(
            budget_content, 
            text="Total Monthly Budget", 
            font=Typography.HEADING_2, 
            text_color=PALETTE["text"]
        ).pack(anchor="w", pady=(0, 8))
        
        self.total_budget_var = tk.StringVar(value=str(current.get("total", 2000.0)))
        total_entry = ctk.CTkEntry(
            budget_content, 
            textvariable=self.total_budget_var, 
            width=300, 
            height=44, 
            font=Typography.get_font(16, "normal"),
            fg_color=PALETTE["input"], 
            border_color=PALETTE["border"], 
            corner_radius=8
        )
        total_entry.pack(anchor="w", pady=(0, 30))

        # --- Category budgets ---
        ctk.CTkLabel(
            budget_content, 
            text="Category Budgets", 
            font=Typography.HEADING_2, 
            text_color=PALETTE["text"]
        ).pack(anchor="w", pady=(0, 16))
        
        self.category_budget_vars = {}
        categories = [
            ("Groceries", "groceries", 600.0, PALETTE["green"]),
            ("Entertainment", "entertainment", 300.0, PALETTE["pink"]),
            ("Electronics", "electronics", 500.0, PALETTE["blue"]),
            ("Other", "other", 200.0, PALETTE["orange"])
        ]
        
        for display_name, key, default, color in categories:
            cat_frame = ctk.CTkFrame(budget_content, fg_color="transparent")
            cat_frame.pack(fill="x", pady=6)
            
            label_frame = ctk.CTkFrame(cat_frame, fg_color="transparent")
            label_frame.pack(side="left", fill="x", expand=True)
            
            # --- Color indicator ---
            ctk.CTkFrame(
                label_frame, 
                width=10, 
                height=10, 
                fg_color=color, 
                corner_radius=5
            ).pack(side="left", padx=(0, 10))
            
            ctk.CTkLabel(
                label_frame, 
                text=display_name, 
                font=Typography.get_font(13, "medium"), 
                text_color=PALETTE["text"]
            ).pack(side="left")
            
            var = tk.StringVar(value=str(current.get(key, default)))
            self.category_budget_vars[key] = var
            
            entry = ctk.CTkEntry(
                cat_frame, 
                textvariable=var, 
                width=180, 
                height=36, 
                font=Typography.get_font(13, "normal"),
                fg_color=PALETTE["input"], 
                border_color=PALETTE["border"], 
                corner_radius=6
            )
            entry.pack(side="right")
        
        # --- Info tip ---
        info_frame = ctk.CTkFrame(
            budget_content, 
            fg_color=PALETTE["bg-elevated"], 
            corner_radius=8
        )
        info_frame.pack(fill="x", pady=(24, 30))
        
        info_content = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_content.pack(padx=16, pady=12)
        
        ctk.CTkLabel(
            info_content, 
            text="💡", 
            font=Typography.get_font(16, "normal")
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            info_content, 
            text="Tip: Set 0 to disable budget limit for a category", 
            font=Typography.BODY, 
            text_color=PALETTE["info"]
        ).pack(side="left")
        
        # --- Save button ---
        save_budget_btn = AnimatedButton(
            budget_content, 
            text="💾 Save Budget Settings", 
            width=240, 
            height=44, 
            command=self._save_budget_settings,
            fg_color=PALETTE["success"], 
            hover_color=PALETTE["success-light"], 
            font=Typography.get_font(14, "bold"), 
            corner_radius=8
        )
        save_budget_btn.pack(anchor="w")

    def _save_budget_settings(self):
        """Save budget settings to database."""
        try:
            data = {"total": float(self.total_budget_var.get().strip().replace(",", ".") or 0.0)}
            if data["total"] < 0:
                raise ValueError("Total budget cannot be negative.")
                
            for key, var in self.category_budget_vars.items():
                data[key] = float(var.get().strip().replace(",", ".") or 0.0)
                if data[key] < 0:
                    raise ValueError(f"Budget for {key} cannot be negative.")
                    
            save_budget(data)
            messagebox.showinfo("Success", "Budget limits updated successfully!")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save budget: {str(e)}")