"""
View for displaying and managing all transaction records.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime

from src.ui.config.theme import PALETTE, CATEGORY_COLORS
from src.ui.config.typography import Typography
from src.ui.components.buttons import AnimatedButton
from src.ui.utils.helpers import create_header, create_empty_placeholder
from src.core.database import get_all_expenses, update_expense, delete_payment
from src.core.models import Expense


class AllTransactionsView:
    """View for displaying all transactions."""
    
    def __init__(self, parent):
        self.parent = parent
        self.transaction_list_frame = None
        self.filter_category_var = tk.StringVar(value="All")
        self.filter_month_var = tk.StringVar(value="All")
        self.months_map = {name: i for i, name in enumerate([
            "All", "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])}
        
    def create(self):
        """Create the all transactions view."""
        # --- Configure grid ---
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(2, weight=1)

        # --- Header ---
        header_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        ctk.CTkLabel(
            header_frame, 
            text="All Transactions", 
            font=Typography.DISPLAY, 
            text_color=PALETTE["text"]
        ).pack(side="left")

        # --- Filter panel ---
        filter_frame = ctk.CTkFrame(self.parent, fg_color=PALETTE["card"], height=60)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=(15, 10))
        
        # --- Category filter ---
        ctk.CTkLabel(
            filter_frame, 
            text="Category:", 
            font=Typography.BODY
        ).pack(side="left", padx=(16, 8), pady=10)
        
        categories = ["All", "Groceries", "Entertainment", "Electronics", "Other"]
        ctk.CTkOptionMenu(
            filter_frame, 
            variable=self.filter_category_var, 
            values=categories, 
            width=150, 
            font=Typography.BODY, 
            fg_color=PALETTE["input"]
        ).pack(side="left", pady=10)

        # --- Month filter ---
        ctk.CTkLabel(
            filter_frame, 
            text="Month:", 
            font=Typography.BODY
        ).pack(side="left", padx=(24, 8), pady=10)
        
        months = ["All", "January", "February", "March", "April", "May", "June", 
                 "July", "August", "September", "October", "November", "December"]
        ctk.CTkOptionMenu(
            filter_frame, 
            variable=self.filter_month_var, 
            values=months, 
            width=150, 
            font=Typography.BODY, 
            fg_color=PALETTE["input"]
        ).pack(side="left", pady=10)

        # --- Apply button ---
        apply_btn = AnimatedButton(
            filter_frame, 
            text="Apply Filters", 
            height=30, 
            command=self._refresh_transaction_list
        )
        apply_btn.pack(side="left", padx=24)

        # --- Transaction list ---
        self.transaction_list_frame = ctk.CTkScrollableFrame(
            self.parent, 
            fg_color=PALETTE["card"], 
            corner_radius=12
        )
        self.transaction_list_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 10))

        # --- Initial load ---
        self._refresh_transaction_list()

    def _refresh_transaction_list(self):
        """Refresh the transaction list with filters."""
        # --- Clear list ---
        for widget in self.transaction_list_frame.winfo_children():
            widget.destroy()

        # --- Show loading ---
        loading_label = ctk.CTkLabel(
            self.transaction_list_frame,
            text="🔄 Loading transactions...",
            font=Typography.BODY,
            text_color=PALETTE["text-secondary"]
        )
        loading_label.pack(expand=True)

        # --- Load data after UI update ---
        self.parent.after(50, lambda: self._load_and_display_transactions(loading_label))

    def _load_and_display_transactions(self, loading_label):
        """Load and display transactions."""
        loading_label.destroy()
        
        # --- Get filter values ---
        category = self.filter_category_var.get()
        month = self.months_map[self.filter_month_var.get()]
        current_year = datetime.now().year

        # --- Get filtered data ---
        all_expenses = get_all_expenses(
            limit=50, 
            category=category, 
            month=month, 
            year=current_year
        )

        # --- Display data ---
        if not all_expenses:
            create_empty_placeholder(
                self.transaction_list_frame, 
                "📂", 
                "No Transactions Found", 
                "Try adjusting your filters or add a new expense."
            )
            return

        for expense in all_expenses:
            self._create_transaction_row(expense)

    def _create_transaction_row(self, expense: Expense):
        """Create a transaction row widget."""
        # --- Main container ---
        main_row_container = ctk.CTkFrame(self.transaction_list_frame, fg_color="transparent")
        main_row_container.pack(fill="x")

        # --- Content frame ---
        content_frame = ctk.CTkFrame(main_row_container, fg_color="transparent", height=55)
        content_frame.pack(fill="x", padx=10, pady=5)
        
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # --- Category column ---
        category_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        category_frame.grid(row=0, column=0, sticky="ns", padx=(0, 15))
        
        color = CATEGORY_COLORS.get(expense.category, PALETTE["text-tertiary"])
        ctk.CTkLabel(
            category_frame, 
            text="●", 
            font=Typography.get_font(18), 
            text_color=color
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            category_frame, 
            text=expense.category, 
            font=Typography.BODY
        ).pack(side="left")

        # --- Description and date column ---
        desc_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        desc_frame.grid(row=0, column=1, sticky="nsew", padx=15)
        
        desc_text = expense.description or "No description"
        ctk.CTkLabel(
            desc_frame, 
            text=desc_text, 
            font=Typography.BODY, 
            anchor="s", 
            justify="left"
        ).grid(row=0, column=0, sticky="sw")
        
        ctk.CTkLabel(
            desc_frame, 
            text=expense.date.strftime('%B %d, %Y'), 
            font=Typography.CAPTION, 
            text_color=PALETTE["text-secondary"], 
            anchor="n", 
            justify="left"
        ).grid(row=1, column=0, sticky="nw")
        
        desc_frame.grid_rowconfigure((0, 1), weight=1)

        # --- Amount and actions column ---
        actions_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=2, sticky="ns", padx=(15, 5))
        
        ctk.CTkLabel(
            actions_frame, 
            text=f"${expense.amount:.2f}", 
            font=Typography.get_font(16, "bold"), 
            width=90, 
            anchor="e"
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        delete_btn = AnimatedButton(
            actions_frame, 
            text="🗑️", 
            width=30, 
            height=30,
            fg_color="transparent", 
            hover_color=PALETTE["error"],
            command=lambda exp_id=expense.id: self._delete_expense(exp_id)
        )
        delete_btn.pack(side="left")
        
        edit_btn = AnimatedButton(
            actions_frame, 
            text="✏️", 
            width=30, 
            height=30, 
            fg_color="transparent", 
            hover_color=PALETTE["warning"],
            command=lambda exp=expense: self._open_edit_window(exp)
        )
        edit_btn.pack(side="left", padx=(4, 0))
        
        # --- Separator line ---
        ctk.CTkFrame(
            main_row_container, 
            fg_color=PALETTE["border"], 
            height=1
        ).pack(fill="x", padx=10)

    def _delete_expense(self, expense_id: int):
        """Delete an expense with confirmation."""
        confirmed = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete this expense (ID: {expense_id})?",
            icon='warning'
        )
        
        if confirmed:
            try:
                if delete_payment(expense_id):
                    messagebox.showinfo("Success", f"Expense ID {expense_id} has been deleted.")
                    self._refresh_transaction_list()
                else:
                    messagebox.showerror("Error", f"Could not find expense with ID {expense_id}.")
            except Exception as e:
                messagebox.showerror("Database Error", f"An error occurred while deleting the expense: {e}")

    def _open_edit_window(self, expense: Expense):
        """Open edit window for expense."""
        edit_window = ctk.CTkToplevel(self.parent)
        edit_window.title(f"Edit Expense ID: {expense.id}")
        edit_window.geometry("400x450")
        edit_window.resizable(False, False)
        edit_window.transient(self.parent)
        edit_window.grab_set()
        edit_window.configure(fg_color=PALETTE["bg-elevated"])

        # --- Form ---
        form_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        form_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # --- Amount field ---
        ctk.CTkLabel(form_frame, text="Amount", font=Typography.BODY).pack(anchor="w")
        amount_var = tk.StringVar(value=f"{expense.amount:.2f}")
        ctk.CTkEntry(form_frame, textvariable=amount_var, font=Typography.BODY).pack(fill="x", pady=(0, 10))

        # --- Category field ---
        ctk.CTkLabel(form_frame, text="Category", font=Typography.BODY).pack(anchor="w")
        cat_var = tk.StringVar(value=expense.category)
        categories = ["Groceries", "Entertainment", "Electronics", "Other"]
        ctk.CTkOptionMenu(form_frame, variable=cat_var, values=categories).pack(fill="x", pady=(0, 10))

        # --- Description field ---
        ctk.CTkLabel(form_frame, text="Description", font=Typography.BODY).pack(anchor="w")
        desc_var = tk.StringVar(value=expense.description or "")
        ctk.CTkEntry(form_frame, textvariable=desc_var, font=Typography.BODY).pack(fill="x", pady=(0, 10))

        # --- Date field ---
        ctk.CTkLabel(form_frame, text="Date (YYYY-MM-DD)", font=Typography.BODY).pack(anchor="w")
        date_var = tk.StringVar(value=expense.date.strftime('%Y-%m-%d'))
        ctk.CTkEntry(form_frame, textvariable=date_var, font=Typography.BODY).pack(fill="x", pady=(0, 20))

        # --- Save button ---
        save_btn = AnimatedButton(
            form_frame, 
            text="Save Changes",
            command=lambda: self._save_expense_changes(
                expense.id, amount_var, cat_var, desc_var, date_var, edit_window
            )
        )
        save_btn.pack(pady=10)

    def _save_expense_changes(self, expense_id, amount_var, cat_var, desc_var, date_var, window):
        """Save expense changes."""
        try:
            new_data = {
                "amount": float(amount_var.get()),
                "category": cat_var.get(),
                "description": desc_var.get(),
                "date": date_var.get()
            }
            update_expense(expense_id, new_data)
            messagebox.showinfo("Success", "Expense updated successfully.")
            window.destroy()
            self._refresh_transaction_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update expense: {e}", parent=window)