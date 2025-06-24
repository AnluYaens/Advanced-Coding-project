"""
Views for expense management - adding expenses and viewing transactions.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime

from src.ui.config.theme import PALETTE, CATEGORY_COLORS
from src.ui.config.typography import Typography
from src.ui.components.buttons import AnimatedButton
from src.ui.components.cards import GlassCard
from src.ui.utils.helpers import create_header, create_empty_placeholder
from src.core.database import (
    add_expense, get_all_expenses, update_expense, delete_payment
)
from src.core.models import Expense


class AddExpenseView:
    """View for adding new expenses."""
    
    def __init__(self, parent, refresh_callback):
        self.parent = parent
        self.refresh_callback = refresh_callback
        
        # --- Form variables ---
        self.expense_amount_var = tk.StringVar(value="")
        self.expense_cat_var = tk.StringVar(value="Groceries")
        self.expense_desc_var = tk.StringVar(value="")
        
    def create(self):
        """Create the add expense form."""
        create_header(self.parent, "Add New Expense")
        
        form_card = GlassCard(self.parent)
        form_card.pack(fill="x", padx=30, pady=16)
        
        form_content = ctk.CTkFrame(form_card, fg_color="transparent")
        form_content.pack(padx=40, pady=40)
        
        # --- Amount field ---
        ctk.CTkLabel(
            form_content, 
            text="Amount", 
            font=Typography.get_font(14, "semibold")
        ).pack(anchor="w", pady=(0, 6))
        amount_entry = ctk.CTkEntry(
            form_content, 
            textvariable=self.expense_amount_var, 
            width=350, 
            height=44, 
            placeholder_text="0.00",
            font=Typography.get_font(16, "normal"), 
            fg_color=PALETTE["input"],
            border_color=PALETTE["border"], 
            corner_radius=8
        )
        amount_entry.pack(anchor="w", pady=(0, 20))
        amount_entry.focus()
        
        # --- Category field ---
        ctk.CTkLabel(
            form_content, 
            text="Category", 
            font=Typography.get_font(14, "semibold")
        ).pack(anchor="w", pady=(0, 6))
        category_menu = ctk.CTkOptionMenu(
            form_content, 
            variable=self.expense_cat_var, 
            values=["Groceries", "Electronics", "Entertainment", "Other"],
            width=350, 
            height=44, 
            fg_color=PALETTE["accent"], 
            font=Typography.get_font(14, "normal"),
            dropdown_font=Typography.BODY, 
            corner_radius=8
        )
        category_menu.pack(anchor="w", pady=(0, 20))
        
        # --- Description field ---
        ctk.CTkLabel(
            form_content, 
            text="Description (optional)", 
            font=Typography.get_font(14, "semibold")
        ).pack(anchor="w", pady=(0, 6))
        desc_entry = ctk.CTkEntry(
            form_content, 
            textvariable=self.expense_desc_var, 
            width=350, 
            height=44,
            placeholder_text="What did you buy?", 
            font=Typography.get_font(14, "normal"),
            fg_color=PALETTE["input"], 
            border_color=PALETTE["border"], 
            corner_radius=8
        )
        desc_entry.pack(anchor="w", pady=(0, 32))
        
        # --- Buttons ---
        btn_frame = ctk.CTkFrame(form_content, fg_color="transparent")
        btn_frame.pack(anchor="w")
        
        save_btn = AnimatedButton(
            btn_frame, 
            text="💾 Save Expense", 
            width=180, 
            height=44, 
            command=self._save_expense,
            fg_color=PALETTE["success"], 
            hover_color=PALETTE["success-light"],
            font=Typography.get_font(14, "bold"), 
            corner_radius=8
        )
        save_btn.pack(side="left", padx=(0, 12))
        
        clear_btn = AnimatedButton(
            btn_frame, 
            text="🗑️ Clear Form", 
            width=140, 
            height=44, 
            command=self._clear_expense_form,
            fg_color=PALETTE["gray-700"], 
            hover_color=PALETTE["gray-600"],
            font=Typography.get_font(14, "normal"), 
            corner_radius=8
        )
        clear_btn.pack(side="left")
        
    def _save_expense(self):
        """Save the expense to database."""
        try:
            amount = float(self.expense_amount_var.get().strip().replace(',', '.'))
            if not (0 < amount <= 1_000_000):
                raise ValueError("Amount must be positive and not excessively large.")
                
            add_expense(
                amount, 
                self.expense_cat_var.get(), 
                self.expense_desc_var.get().strip()[:200]
            )
            
            messagebox.showinfo("Success", f"Expense of ${amount:.2f} recorded successfully!")
            self._clear_expense_form()
        except ValueError as e:
            messagebox.showwarning("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save expense: {str(e)}")

    def _clear_expense_form(self):
        """Clear the expense form."""
        if self.expense_amount_var:
            self.expense_amount_var.set("")
        if self.expense_cat_var:
            self.expense_cat_var.set("Groceries")
        if self.expense_desc_var:
            self.expense_desc_var.set("")
