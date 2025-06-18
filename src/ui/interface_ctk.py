import tkinter as tk
from tkinter import messagebox, filedialog
import os
import traceback
import gc

import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.interpolate import PchipInterpolator
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional

from src.core.database import (
    SessionLocal, 
    save_budget, 
    get_budget, 
    add_expense,
    insert_payment,
    get_db_session
)

from src.core.models import Expense
from src.core.ai_engine import chat_completion
from src.services.currency_api import get_exchange_rate

# --- Import bank statement loaders ---
from src.services.bank_statement_loader import load_bank_statement_csv

# --- PDF support toggle ---
PDF_SUPPORT = False
try:
    from src.services.bank_statement_loader_pdf import load_bank_statement_pdf
    PDF_SUPPORT = True
except ImportError:
    print("Warning: bank_statement_loader_pdf not available")

"""
Modern tabbed interface with sidebar navigation:
- Left sidebar: Tab navigation buttons
- Right main area: Tabbed content (Dashboard, Add Expense, Analytics, etc.)
- Clean, unified experience with no popup windows
"""
    
# ──────────────────────── THEME HANDLING ────────────────────────
PALETTE = {
    "bg": "#1a1625",           # darker main background 
    "sidebar": "#2d235f",      # sidebar background
    "card": "#322952",         # card/frame background (lighter than sidebar)
    "accent": "#6d28d9",       # highlight color (buttons, lines)
    "hover": "#7c3aed",        # hover color
    "text": "#f9fafb",         # main text (almost white)
    "text_secondary": "#a0a0a0", # secondary text
    "error": "#ef4444",        # error color
    "success": "#10b981",      # success color
    "warning": "#f59e0b",      # warning color
}

# ──────────────────────── inancial Insights Widget ────────────────────────
class FinancialInsightsWidget(ctk.CTkFrame):
    """AI insights widget for dashboard"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=PALETTE["card"], corner_radius=12)
    
        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            header_frame,
            text="🤖 AI Financial Insights",
            font=("Arial", 16, "bold"),
            text_color=PALETTE["text"]
        ).pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            header_frame,
            text="🔄",
            width=30,
            height=25,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["hover"],
            command=self.refresh_insights,
            font=("Arial", 12)
        )
        self.refresh_btn.pack(side="right")

        # --- Insights container ----
        self.insights_frame = ctk.CTkFrame(self, fg_color=PALETTE["bg"], corner_radius=8)
        self.insights_frame.pack(fill="both", expand=True, padx=15, pady=(0,15))

        # --- Auto-load insights ---
        self.after(100, self.refresh_insights)

    # ──────── Refresh insights ────────
    def refresh_insights(self):
        """Generate insights"""
        for widget in self.insights_frame.winfo_children():
            widget.destroy()
        
        # --- Sample insights ---
        insights = [
            ("💡", "Grocery spending down 15%", PALETTE["success"]),
            ("⚠️", "Entertainment budget 85% used", PALETTE["warning"]),
            ("🎯", "On track to save $280", PALETTE["accent"])
        ]

        for icon, text, color in insights:
            insight_row = ctk.CTkFrame(self.insights_frame, fg_color="transparent")
            insight_row.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(
                insight_row,
                text=icon,
                font=("Arial", 14)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                insight_row,
                text=text,
                font=("Arial", 12),
                text_color=PALETTE["text"],
                anchor="w"
            ).pack(side="left", fill="x", expand=True)

# ──────────────────────── Quick Stats Widget ────────────────────────
class QuickStatsWidget(ctk.CTkFrame):
    """Quick statistics cards for dashboard"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color="transparent")

        # --- Title ---
        ctk.CTkLabel(
            self,
            text="📊 Quick Statistics",
            font=("Arial", 16, "bold"),
            text_color=PALETTE["text"]
        ).pack(anchor="w", padx=5, pady=(0, 10))

        # --- Stats grid ---
        stats_container = ctk.CTkFrame(self, fg_color="transparent")
        stats_container.pack(fill="both", expand=True)

        # --- Configure 2x2 grid ---
        stats_container.grid_columnconfigure((0, 1), weight=1)
        stats_container.grid_rowconfigure((0, 1), weight=1)

        self.create_stats_cards(stats_container)

    # ──────── Create stats cards ────────
    def create_stats_cards(self, parent):
        """Create the 4 stat cards"""
        stats_data = self.calculate_stats()

        cards_info = [
            ("💰", "Total Spent", f"${stats_data['total_spent']:.0f}", f"+{stats_data['spent_change']}%"),
            ("📊", "Daily Avg", f"${stats_data['daily_avg']:.0f}", f"{stats_data['avg_change']:+.0f}%"),
            ("🎯", "Budget Used", f"{stats_data['budget_used']}%", stats_data['budget_status']),
            ("💳", "Transactions", str(stats_data['transaction_count']), f"+{stats_data['trans_change']}")
        ]

        for i, (icon, label, value, change) in enumerate(cards_info):
            card = self.create_single_stat_card(parent, icon, label, value, change)
            card.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="ew")

    # ──────── Create single stat card ────────
    def create_single_stat_card(self, parent, icon, label, value, change):
        """Create individual stat card"""
        card = ctk.CTkFrame(parent, fg_color=PALETTE["card"], corner_radius=8)

        # --- Icon and label ---
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 0))
        
        ctk.CTkLabel(
            header,
            text=icon,
            font=("Arial", 16)
        ).pack(side="left")
        
        ctk.CTkLabel(
            header,
            text=label,
            font=("Arial", 11),
            text_color=PALETTE["text_secondary"]
        ).pack(side="left", padx=(5, 0))

        # --- Value ---
        ctk.CTkLabel(
            card,
            text=value,
            font=("Arial", 20, "bold"),
            text_color=PALETTE["text"]
        ).pack(padx=12, pady=(5, 0))

        # --- Change ---
        ctk.CTkLabel(
            card,
            text=change,
            font=("Arial", 10),
            text_color=PALETTE["accent"]
        ).pack(padx=12, pady=(0, 12))
        
        return card
    
    # ──────── Calculate stats ────────
    def calculate_stats(self):
        """Calculate statistics from database"""
        try:
            with get_db_session() as session:
                now = datetime.now()
                month_start = datetime(now.year, now.month, 1)

                current_expenses = session.query(Expense).filter(
                    Expense.date >= month_start
                ).all()

                total_spent = sum(e.amount for e in current_expenses)
                transaction_count = len(current_expenses)
                
                days_passed = (now - month_start).days + 1
                daily_avg = total_spent / days_passed if days_passed > 0 else 0

                monthly_budget = 2000
                budget_used = (total_spent / monthly_budget * 100) if monthly_budget > 0 else 0
                budget_status = "On Track" if budget_used <= (days_passed / 30 * 100) else "Over Budget"

                return{
                    'total_spent': total_spent,
                    'spent_change': 12,
                    'daily_avg': daily_avg,
                    'avg_change': -5,
                    'budget_used': int(budget_used),
                    'budget_status': budget_status,
                    'transaction_count': transaction_count,
                    'trans_change': 8
                }
        except Exception as e:
            print(f"Error calculating stats: {e}")
            return {
                'total_spent': 0, 'spent_change': 0, 'daily_avg': 0, 'avg_change': 0,
                'budget_used': 0, 'budget_status': "No Data", 'transaction_count': 0, 'trans_change': 0
            }

# ──────────────────────── Global customTkinter config ────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ──────────────────────── Main Application ────────────────────────
class BudgetApp(ctk.CTk):
    """Modern tabbed budget application with sidebar navigation"""

    def __init__(self):
        super().__init__()
        self.title("AI Budget Tracker")
        self.geometry("1200x800")
        self.resizable(True, True)
        self.minsize(1000, 700)

        # --- Colors ---
        self.colors = PALETTE.copy()
        self.configure(fg_color=self.colors["bg"])
        
        # --- State management ---
        self.current_tab = "Dashboard"
        self.main_sections = {}
        
        # --- Initialize variables ---
        self.amount_var = None
        self.from_var = None
        self.to_var = None
        self.result_lbl = None
        self.rate_lbl = None
        
        # --- Build UI ---
        self._create_layout()

    # ──────── Create layout ────────
    def _create_layout(self):
        """Create the main layout with sidebar and tabbed content area"""
        # --- Main container ---
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # --- Configure grid ---
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # --- Create sidebar ---
        self._create_sidebar(main_container)
        
        # --- Create main content area ---
        self._create_content_area(main_container)
        
        # --- Show dashboard by default ---
        self.show_tab("Dashboard")

    # ──────── Create sidebar ────────
    def _create_sidebar(self, parent):
        """Create left sidebar with tab navigation"""
        sidebar = ctk.CTkFrame(parent, fg_color=self.colors["sidebar"], width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        sidebar.grid_propagate(False)
        
        self.main_sections['sidebar'] = sidebar
        
        # --- Header ---
        header = ctk.CTkFrame(sidebar, fg_color="transparent", height=80)
        header.pack(fill="x", padx=20, pady=(20, 30))
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="💰 Budget\nTracker",
            font=("Arial", 20, "bold"),
            text_color=self.colors["text"],
            justify="left"
        ).pack(anchor="w")
        
        # --- Tab navigation buttons ---
        self.tabs_config = [
            ("🏠", "Dashboard"),
            ("➕", "Add Expense"), 
            ("📊", "Analytics"),
            ("🎯", "Set Budget"),
            ("💱", "Currency"),
            ("🤖", "AI Assistant"),
            ("📧", "Contact"),
        ]
        
        self.nav_buttons = {}
        for icon, tab_name in self.tabs_config:
            btn = ctk.CTkButton(
                sidebar,
                text=f"{icon}  {tab_name}",
                anchor="w",
                height=45,
                fg_color="transparent",
                text_color=self.colors["text"],
                hover_color=self.colors["hover"],
                font=("Arial", 14),
                command=lambda t=tab_name: self.show_tab(t)
            )
            btn.pack(fill="x", padx=20, pady=2)
            self.nav_buttons[tab_name] = btn

    # ──────── Create content area ────────
    def _create_content_area(self, parent):
        """Create main content area for tabs"""
        self.content_frame = ctk.CTkScrollableFrame(
            parent, 
            fg_color=self.colors["bg"],
            corner_radius=0
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        self.main_sections['content'] = self.content_frame

    # ──────── Set active tab ────────
    def set_active_tab(self, tab_name):
        """Update navigation button styles"""
        for name, btn in self.nav_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=self.colors["accent"])
            else:
                btn.configure(fg_color="transparent")

    # ──────── Clear content ────────
    def clear_content(self):
        """Clear the main content area"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # ──────── Show tabs ────────
    def show_tab(self, tab_name):
        """Show the selected tab content"""
        self.clear_content()
        self.set_active_tab(tab_name)
        self.current_tab = tab_name
        
        # --- Route to appropriate tab content ---
        if tab_name == "Dashboard":
            self._create_dashboard_tab()
        elif tab_name == "Add Expense":
            self._create_add_expense_tab()
        elif tab_name == "Analytics":
            self._create_analytics_tab()
        elif tab_name == "Set Budget":
            self._create_budget_tab()
        elif tab_name == "Currency":
            self._create_currency_tab()
        elif tab_name == "AI Assistant":
            self._create_ai_assistant_tab()
        elif tab_name == "Contact":
            self._create_contact_tab()

    # ──────────────────────── TAB CONTENT METHODS ────────────────────────

    # ──────── Create dashboard tab ────────
    def _create_dashboard_tab(self):
        """Create dashboard tab content"""
        # --- Dashboard title ---
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="📊 Financial Dashboard",
            font=("Arial", 28, "bold"),
            text_color=self.colors["text"]
        ).pack(side="left")
        
        # --- Top row: Quick stats and AI insights ---
        top_row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=30, pady=10)
        
        # --- Configure grid for top row ---
        top_row.grid_columnconfigure(0, weight=2)
        top_row.grid_columnconfigure(1, weight=1)
        
        # --- Quick stats (2/3 width) ---
        stats_widget = QuickStatsWidget(top_row, fg_color="transparent")
        stats_widget.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        
        # --- AI insights (1/3 width) ---
        insights_widget = FinancialInsightsWidget(top_row)
        insights_widget.grid(row=0, column=1, sticky="ew")
        
        # --- Charts section ---
        self._create_charts_section()

    # ──────── Create add expense tab ────────
    def _create_add_expense_tab(self):
        """Create add expense tab content"""
        # --- Title ---
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="➕ Add New Expense",
            font=("Arial", 28, "bold"),
            text_color=self.colors["text"]
        ).pack(side="left")
        
        # --- Main form card ---
        form_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.colors["card"],
            corner_radius=12
        )
        form_card.pack(fill="x", padx=30, pady=20)
        
        # --- Form content ---
        form_content = ctk.CTkFrame(form_card, fg_color="transparent")
        form_content.pack(padx=50, pady=50)
        
        # --- Amount ---
        ctk.CTkLabel(
            form_content,
            text="Amount",
            font=("Arial", 16, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 8))
        
        self.expense_amount_var = tk.StringVar(value="")
        amount_entry = ctk.CTkEntry(
            form_content,
            textvariable=self.expense_amount_var,
            width=400,
            height=50,
            placeholder_text="0.00",
            font=("Arial", 18)
        )
        amount_entry.pack(anchor="w", pady=(0, 20))
        amount_entry.focus()
        
        # --- Category ---
        ctk.CTkLabel(
            form_content,
            text="Category",
            font=("Arial", 16, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 8))
        
        self.expense_cat_var = tk.StringVar(value="Groceries")
        category_menu = ctk.CTkOptionMenu(
            form_content,
            variable=self.expense_cat_var,
            values=["Groceries", "Electronics", "Entertainment", "Other"],
            width=400,
            height=50,
            fg_color=self.colors["accent"],
            font=("Arial", 16)
        )
        category_menu.pack(anchor="w", pady=(0, 20))
        
        # --- Description ---
        ctk.CTkLabel(
            form_content,
            text="Description (optional)",
            font=("Arial", 16, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 8))
        
        self.expense_desc_var = tk.StringVar()
        desc_entry = ctk.CTkEntry(
            form_content,
            textvariable=self.expense_desc_var,
            width=400,
            height=50,
            placeholder_text="What did you buy?",
            font=("Arial", 16)
        )
        desc_entry.pack(anchor="w", pady=(0, 30))
        
        # --- Buttons ---
        btn_frame = ctk.CTkFrame(form_content, fg_color="transparent")
        btn_frame.pack(anchor="w")
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 Save Expense",
            width=200,
            height=50,
            command=self._save_expense,
            fg_color=self.colors["success"],
            hover_color="#059669",
            font=("Arial", 16, "bold")
        )
        save_btn.pack(side="left", padx=(0, 15))
        
        clear_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ Clear Form",
            width=150,
            height=50,
            command=self._clear_expense_form,
            fg_color="#666",
            hover_color="#555",
            font=("Arial", 16)
        )
        clear_btn.pack(side="left")

    # ──────── Create analytics tab ────────
    def _create_analytics_tab(self):
        """Create analytics tab content"""
        # --- Title ---
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="📊 Spending Analytics",
            font=("Arial", 28, "bold"),
            text_color=self.colors["text"]
        ).pack(side="left")
        
        # --- Analytics content ---
        try:
            with get_db_session() as session:
                exps = session.query(Expense).order_by(Expense.date.desc()).all()
                session.expunge_all()

            if not exps:
                # --- No data message ---
                no_data_card = ctk.CTkFrame(
                    self.content_frame,
                    fg_color=self.colors["card"],
                    corner_radius=12
                )
                no_data_card.pack(fill="x", padx=30, pady=20)
                
                ctk.CTkLabel(
                    no_data_card,
                    text="📈 No expenses recorded yet",
                    font=("Arial", 20, "bold"),
                    text_color=self.colors["text_secondary"]
                ).pack(pady=50)
                
                ctk.CTkLabel(
                    no_data_card,
                    text="Start by adding some expenses to see your analytics here!",
                    font=("Arial", 14),
                    text_color=self.colors["text_secondary"]
                ).pack(pady=(0, 50))
                return
            
            total = sum(e.amount for e in exps)
            
            # --- Summary card ---
            summary_card = ctk.CTkFrame(
                self.content_frame,
                fg_color=self.colors["card"],
                corner_radius=12
            )
            summary_card.pack(fill="x", padx=30, pady=20)
            
            summary_content = ctk.CTkFrame(summary_card, fg_color="transparent")
            summary_content.pack(padx=40, pady=30)
            
            # --- Total expenses ---
            ctk.CTkLabel(
                summary_content,
                text=f"💰 Total Expenses: ${total:.2f}",
                font=("Arial", 24, "bold"),
                text_color=self.colors["text"]
            ).pack(anchor="w", pady=(0, 20))
            
            # --- By category analysis ---
            ctk.CTkLabel(
                summary_content,
                text="📊 Spending by Category:",
                font=("Arial", 18, "bold"),
                text_color=self.colors["text"]
            ).pack(anchor="w", pady=(0, 10))
            
            by_category = {}
            for e in exps:
                cat = e.category or "Other"
                by_category[cat] = by_category.get(cat, 0) + e.amount
            
            for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total * 100) if total > 0 else 0
                
                cat_frame = ctk.CTkFrame(summary_content, fg_color=self.colors["bg"], corner_radius=8)
                cat_frame.pack(fill="x", pady=5)
                
                ctk.CTkLabel(
                    cat_frame,
                    text=f"• {cat}: ${amount:.2f} ({percentage:.1f}%)",
                    font=("Arial", 14),
                    text_color=self.colors["text"]
                ).pack(anchor="w", padx=15, pady=10)
            
            # --- Recent expenses ---
            ctk.CTkLabel(
                summary_content,
                text="🕐 Recent Expenses (last 10):",
                font=("Arial", 18, "bold"),
                text_color=self.colors["text"]
            ).pack(anchor="w", pady=(30, 10))
            
            for e in exps[:10]:
                date_str = e.date.strftime("%m/%d/%Y") if e.date else "Unknown"
                desc = f" - {e.description}" if e.description else ""
                
                exp_frame = ctk.CTkFrame(summary_content, fg_color=self.colors["bg"], corner_radius=8)
                exp_frame.pack(fill="x", pady=2)
                
                ctk.CTkLabel(
                    exp_frame,
                    text=f"{date_str} | {e.category}: ${e.amount:.2f}{desc}",
                    font=("Arial", 12),
                    text_color=self.colors["text_secondary"]
                ).pack(anchor="w", padx=15, pady=8)

        except Exception as e:
            error_card = ctk.CTkFrame(
                self.content_frame,
                fg_color=self.colors["card"],
                corner_radius=12
            )
            error_card.pack(fill="x", padx=30, pady=20)
            
            ctk.CTkLabel(
                error_card,
                text=f"❌ Error loading analytics: {str(e)}",
                font=("Arial", 16),
                text_color=self.colors["error"]
            ).pack(pady=50)

    # ──────── Create budget tab ────────
    def _create_budget_tab(self):
        """Create budget management tab content"""
        # --- Title ---
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="🎯 Budget Management",
            font=("Arial", 28, "bold"),
            text_color=self.colors["text"]
        ).pack(side="left")
        
        # --- Budget form card ---
        budget_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.colors["card"],
            corner_radius=12
        )
        budget_card.pack(fill="x", padx=30, pady=20)
        
        budget_content = ctk.CTkFrame(budget_card, fg_color="transparent")
        budget_content.pack(padx=50, pady=40)
        
        # --- Get current budgets ---
        current = get_budget() or {}
        
        # --- Total budget ---
        ctk.CTkLabel(
            budget_content,
            text="💰 Total Monthly Budget:",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 10))
        
        self.total_budget_var = tk.StringVar(value=str(current.get("total", 2000.0)))
        total_entry = ctk.CTkEntry(
            budget_content,
            textvariable=self.total_budget_var,
            width=300,
            height=40,
            font=("Arial", 16)
        )
        total_entry.pack(anchor="w", pady=(0, 30))
        
        # --- Category budgets ---
        ctk.CTkLabel(
            budget_content,
            text="📊 Category Budgets:",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 15))
        
        self.category_budget_vars = {}
        categories = [
            ("Groceries", "groceries", 600.0),
            ("Entertainment", "entertainment", 300.0),
            ("Electronics", "electronics", 500.0),
            ("Other", "other", 200.0)
        ]
        
        for display_name, key, default in categories:
            cat_frame = ctk.CTkFrame(budget_content, fg_color="transparent")
            cat_frame.pack(fill="x", pady=8)
            
            ctk.CTkLabel(
                cat_frame,
                text=f"{display_name}:",
                font=("Arial", 14),
                text_color=self.colors["text"],
                width=150
            ).pack(side="left")
            
            var = tk.StringVar(value=str(current.get(key, default)))
            self.category_budget_vars[key] = var
            
            ctk.CTkEntry(
                cat_frame,
                textvariable=var,
                width=200,
                height=35,
                font=("Arial", 14)
            ).pack(side="left", padx=(20, 0))
        
        # --- Info ---
        ctk.CTkLabel(
            budget_content,
            text="💡 Tip: Set 0 to disable budget limit for a category",
            font=("Arial", 12),
            text_color=self.colors["text_secondary"]
        ).pack(anchor="w", pady=(20, 30))
        
        # --- Save button ---
        save_budget_btn = ctk.CTkButton(
            budget_content,
            text="💾 Save Budget Settings",
            width=250,
            height=50,
            command=self._save_budget_settings,
            fg_color=self.colors["success"],
            hover_color="#059669",
            font=("Arial", 16, "bold")
        )
        save_budget_btn.pack(anchor="w")

    # ──────── Create currency tab ────────
    def _create_currency_tab(self):
        """Create currency converter tab content"""
        # --- Title ---
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="💱 Currency Converter",
            font=("Arial", 28, "bold"),
            text_color=self.colors["text"]
        ).pack(side="left")
        
        # --- Converter card ---
        converter_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.colors["card"],
            corner_radius=12
        )
        converter_card.pack(fill="x", padx=30, pady=20)
        
        # --- Converter content ---
        content = ctk.CTkFrame(converter_card, fg_color="transparent")
        content.pack(padx=50, pady=50)
        
        # --- Amount input ---
        ctk.CTkLabel(
            content,
            text="💰 Amount to convert:",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 10))
        
        self.amount_var = tk.StringVar(value="1.0")
        amount_entry = ctk.CTkEntry(
            content,
            textvariable=self.amount_var,
            width=400,
            height=50,
            font=("Arial", 18)
        )
        amount_entry.pack(anchor="w", pady=(0, 30))
        amount_entry.bind("<KeyRelease>", lambda *_: self._update_conversion())
        
        # --- Currency selection ---
        ctk.CTkLabel(
            content,
            text="🌍 Select currencies:",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 15))
        
        currency_frame = ctk.CTkFrame(content, fg_color="transparent")
        currency_frame.pack(anchor="w", pady=(0, 30))
        
        currs = ["USD", "EUR", "GBP", "MXN", "JPY", "CAD"]
        self.from_var = tk.StringVar(value="USD")
        self.to_var = tk.StringVar(value="EUR")
        
        # --- From currency ---
        from_frame = ctk.CTkFrame(currency_frame, fg_color="transparent")
        from_frame.pack(side="left", padx=(0, 30))
        
        ctk.CTkLabel(from_frame, text="From:", font=("Arial", 14), text_color=self.colors["text"]).pack()
        ctk.CTkOptionMenu(
            from_frame,
            variable=self.from_var,
            values=currs,
            width=150,
            height=40,
            fg_color=self.colors["accent"],
            font=("Arial", 16),
            command=lambda *_: self._update_conversion()
        ).pack(pady=(5, 0))
        
        # --- To currency ---
        to_frame = ctk.CTkFrame(currency_frame, fg_color="transparent")
        to_frame.pack(side="left")
        
        ctk.CTkLabel(to_frame, text="To:", font=("Arial", 14), text_color=self.colors["text"]).pack()
        ctk.CTkOptionMenu(
            to_frame,
            variable=self.to_var,
            values=currs,
            width=150,
            height=40,
            fg_color=self.colors["accent"],
            font=("Arial", 16),
            command=lambda *_: self._update_conversion()
        ).pack(pady=(5, 0))
        
        # --- Results ---
        results_frame = ctk.CTkFrame(content, fg_color=self.colors["bg"], corner_radius=12)
        results_frame.pack(fill="x", pady=20)
        
        self.result_lbl = ctk.CTkLabel(
            results_frame,
            text="",
            font=("Arial", 24, "bold"),
            text_color=self.colors["text"]
        )
        self.result_lbl.pack(pady=(20, 10))
        
        self.rate_lbl = ctk.CTkLabel(
            results_frame,
            text="",
            font=("Arial", 14),
            text_color=self.colors["text_secondary"]
        )
        self.rate_lbl.pack(pady=(0, 20))
        
        # --- Initial conversion ---
        self._update_conversion()

    # ──────── Create AI assistant tab ────────
    def _create_ai_assistant_tab(self):
        """Create AI assistant tab content"""
        # --- Title ---
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="🤖 AI Budget Assistant",
            font=("Arial", 28, "bold"),
            text_color=self.colors["text"]
        ).pack(side="left")
        
        # --- Chat card ---
        chat_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.colors["card"],
            corner_radius=12
        )
        chat_card.pack(fill="both", expand=True, padx=30, pady=20)
        
        # --- Chat display ---
        self.chatbox = tk.Text(
            chat_card,
            height=25,
            state="disabled",
            bg=self.colors["card"],
            fg=self.colors["text"],
            font=("Arial", 12),
            wrap="word",
            borderwidth=0,
            highlightthickness=0
        )
        self.chatbox.pack(padx=20, pady=(20, 10), fill="both", expand=True)
        
        # --- Configure text tags ---
        self.chatbox.tag_config("user_header", foreground="#a78bfa", font=("Arial", 11, "bold"))
        self.chatbox.tag_config("user", foreground="#c4b5fd")
        self.chatbox.tag_config("assistant_header", foreground="#60a5fa", font=("Arial", 11, "bold"))
        self.chatbox.tag_config("assistant", foreground=self.colors["text"])
        
        # --- Input area ---
        input_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # --- Import button ---
        import_btn = ctk.CTkButton(
            input_frame,
            text="📂",
            width=50,
            height=40,
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"],
            command=self._import_bank_statement,
            font=("Arial", 16)
        )
        import_btn.pack(side="left", padx=(0, 10))
        
        # --- Message input ---
        self.msg_var = tk.StringVar()
        entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.msg_var,
            height=40,
            placeholder_text="Type your message...",
            font=("Arial", 12)
        )
        entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        entry.bind("<Return>", lambda e: self._send_message())
        entry.focus()
        
        # --- Send button ---
        self.send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            width=80,
            height=40,
            fg_color=self.colors["accent"],
            hover_color=self.colors["hover"],
            command=self._send_message,
            font=("Arial", 12, "bold")
        )
        self.send_btn.pack(side="right")
        
        # --- Initialize chat history and welcome message ---
        self.chat_history = []
        self._append_chat_message("assistant", 
                                 "Hello! I'm your AI budget assistant. I can help you:\n"
                                 "• Record expenses (e.g., 'Add $50 for groceries')\n"
                                 "• Check spending (e.g., 'How much did I spend on entertainment?')\n"
                                 "• Import bank statements (click 📂)\n\n"
                                 "How can I help you today?")

    # ──────── Create content tab ────────
    def _create_contact_tab(self):
        """Create contact information tab content"""
        # --- Title ---
        title_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(
            title_frame,
            text="📧 Contact & About",
            font=("Arial", 28, "bold"),
            text_color=self.colors["text"]
        ).pack(side="left")
        
        # --- Contact card ---
        contact_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.colors["card"],
            corner_radius=12
        )
        contact_card.pack(fill="x", padx=30, pady=20)
        
        contact_content = ctk.CTkFrame(contact_card, fg_color="transparent")
        contact_content.pack(padx=50, pady=50)
        
        # --- App info ---
        ctk.CTkLabel(
            contact_content,
            text="💰 AI Budget Tracker",
            font=("Arial", 24, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(
            contact_content,
            text="Modern budget management application with AI integration.",
            font=("Arial", 16),
            text_color=self.colors["text_secondary"]
        ).pack(anchor="w", pady=(0, 30))
        
        # --- Features ---
        ctk.CTkLabel(
            contact_content,
            text="🚀 Features:",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(0, 10))
        
        features = [
            "• Modern sidebar navigation interface",
            "• Interactive financial dashboard",
            "• AI-powered expense insights",
            "• Real-time currency conversion",
            "• Visual analytics and charts",
            "• Bank statement import (CSV/PDF)",
            "• Natural language AI assistant",
            "• Budget tracking and management"
        ]
        
        for feature in features:
            ctk.CTkLabel(
                contact_content,
                text=feature,
                font=("Arial", 14),
                text_color=self.colors["text_secondary"]
            ).pack(anchor="w", pady=2)
        
        # --- Contact info ---
        ctk.CTkLabel(
            contact_content,
            text="👨‍💻 Developer:",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=(30, 10))
        
        ctk.CTkLabel(
            contact_content,
            text="Created by: Angel Jaen",
            font=("Arial", 14),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=2)
        
        ctk.CTkLabel(
            contact_content,
            text="Email: anlujaen@gmail.com",
            font=("Arial", 14),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=2)
        
        ctk.CTkLabel(
            contact_content,
            text="GitHub: github.com/yourusername/ai-budget-tracker",
            font=("Arial", 14),
            text_color=self.colors["text"]
        ).pack(anchor="w", pady=2)

    # ──────────────────────── DASHBOARD CHART METHODS ────────────────────────

    # ──────── Create charts sections ────────
    def _create_charts_section(self):
        """Create charts section for dashboard"""
        charts_frame = ctk.CTkFrame(
            self.content_frame, 
            fg_color=self.colors["card"], 
            corner_radius=12
        )
        charts_frame.pack(fill="x", padx=30, pady=20)
        
        # --- Charts title ---
        title_row = ctk.CTkFrame(charts_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            title_row, 
            text="📈 Expense Charts", 
            font=("Arial", 18, "bold"), 
            text_color=self.colors["text"]
        ).pack(side="left")

        ctk.CTkLabel(
            title_row, 
            text="Category Breakdown", 
            font=("Arial", 18, "bold"), 
            text_color=self.colors["text"]
        ).pack(side="right")
        
        # --- Charts row ---
        charts_row = ctk.CTkFrame(charts_frame, fg_color="transparent")
        charts_row.pack(fill="x", padx=20, pady=(0, 20))

        left_chart = ctk.CTkFrame(charts_row, fg_color=self.colors["bg"], corner_radius=8)
        left_chart.pack(side="left", expand=True, fill="both", padx=(0, 10))

        right_chart = ctk.CTkFrame(charts_row, fg_color=self.colors["bg"], corner_radius=8)
        right_chart.pack(side="right", expand=True, fill="both", padx=(10, 0))

        # --- Draw charts ---
        self.show_line_chart(left_chart)
        self.show_donut_chart(right_chart)

    # ──────── Get expenses by month ────────
    def get_expenses_by_month(self):
        """Get expense totals for each month of the current year"""
        try:
            with get_db_session() as session:
                exps = session.query(Expense).all()
                session.expunge_all()

            current_year = datetime.now().year
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            totals = [0] * len(months)
            
            for e in exps:
                if e.date and e.date.year == current_year:
                    month_abbr = e.date.strftime('%b')
                    if month_abbr in months:
                        idx = months.index(month_abbr)
                        totals[idx] += e.amount        
            return totals
        except Exception as e:
            print(f"Error getting expenses by month: {e}")
            return [0] * 6

    # ──────── Get expenses by category ────────
    def get_expenses_by_category(self):
        """Get expense totals for each category"""
        try:
            with get_db_session() as session:
                exps = session.query(Expense).all()
                session.expunge_all()

            cats = ["Groceries", "Electronics", "Entertainment", "Other"]
            totals = [0] * len(cats)
            
            for e in exps:
                cat = e.category.capitalize() if e.category else "Other"
                if cat in cats:
                    totals[cats.index(cat)] += e.amount
                else:
                    totals[cats.index("Other")] += e.amount
                    
            return totals
        except Exception as e:
            print(f"Error getting expenses by category: {e}")
            return [0] * 4

    # ──────── Show line Chart ────────
    def show_line_chart(self, parent):
        """Display line chart showing expenses by month"""
        try:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            data = self.get_expenses_by_month()
            x = np.arange(len(months))
            
            max_val = max(data) if any(data) else 1
            y_top = max(100, round(max_val * 1.25))

            fig, ax = plt.subplots(figsize=(6, 3.5), dpi=100)
            fig.patch.set_facecolor(self.colors["bg"])
            ax.set_facecolor(self.colors["bg"])

            if len(set(data)) > 1 and sum(data) > 0:
                x_smooth = np.linspace(x.min(), x.max(), 300)
                y_smooth = PchipInterpolator(x, data)(x_smooth)
                ax.plot(x_smooth, y_smooth, color=self.colors["accent"], linewidth=3, zorder=1)
            else:
                ax.plot(x, data, color=self.colors["accent"], linewidth=3, marker="o", 
                       markersize=8, markerfacecolor=self.colors["accent"], 
                       markeredgewidth=2, markeredgecolor='white', zorder=1)

            for xi, val in zip(x, data):
                if val > 0:
                    ax.scatter(xi, val, color=self.colors["accent"], edgecolors='white', 
                             s=80, linewidth=2, zorder=3)
                    ax.text(xi, val + y_top * 0.03, f"${val:,.0f}", fontsize=10, 
                           color=self.colors["text"], ha='center', va='bottom', fontweight='bold')

            ax.set_xlim(-0.4, len(months) - 0.6)
            ax.set_ylim(0, y_top)
            ax.set_xticks(x)
            ax.set_xticklabels(months, color=self.colors["text"], fontsize=11, fontweight="bold")
            ax.tick_params(axis='y', colors=self.colors["text"], labelsize=10)
            ax.grid(axis='y', linestyle='--', linewidth=0.5, color='#4a4a4a', alpha=0.5)
            
            for spine in ax.spines.values():
                spine.set_visible(False)

            fig.tight_layout(pad=1)
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=15, pady=15, fill="both", expand=True)
            plt.close(fig)

        except Exception as e:
            print(f"Error creating line chart: {e}")
            error_label = ctk.CTkLabel(parent, text="Error loading chart", 
                                     font=("Arial", 14), text_color=self.colors["error"])
            error_label.pack(expand=True)

    # ────────  Show donut Chart ────────
    def show_donut_chart(self, parent):
        """Display donut chart showing expenses by category"""
        try:
            categories = ["Groceries", "Electronics", "Entertainment", "Other"]
            vals = self.get_expenses_by_category()
            vals = [max(0, v) for v in vals]
            total = sum(vals)

            if total == 0:
                no_data_frame = ctk.CTkFrame(parent, fg_color="transparent")
                no_data_frame.pack(expand=True)
                ctk.CTkLabel(no_data_frame, text="No expenses to display", 
                           text_color=self.colors["text"], font=("Arial", 16)).pack()
                ctk.CTkLabel(no_data_frame, text="Add some expenses to see the breakdown", 
                           text_color=self.colors["text_secondary"], font=("Arial", 12)).pack(pady=(5, 0))
                return

            colors = ["#7c3aed", "#8b5cf6", "#a78bfa", "#ddd6fe"][:len(vals)]

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5.5, 4), dpi=100, 
                                         gridspec_kw={'height_ratios': [3, 1.2]})
            fig.patch.set_facecolor(self.colors["bg"])
            ax1.set_facecolor(self.colors["bg"])
            ax2.set_facecolor(self.colors["bg"])

            wedges, texts = ax1.pie(vals, wedgeprops=dict(width=0.5), startangle=90, colors=colors)
            centre_circle = plt.Circle((0, 0), 0.45, fc=self.colors["bg"])
            ax1.add_artist(centre_circle)
            ax1.axis("equal")
            ax1.axis("off")

            # --- Legend ---
            ax2.axis("off")
            ax2.set_xlim(0, 1)
            ax2.set_ylim(0, 1)
            
            for i, (cat, val, color) in enumerate(zip(categories, vals, colors)):
                percent = (val / total * 100) if total else 0
                y_pos = 0.8 - i * 0.2
                
                ax2.text(0.05, y_pos, f"● {cat}", fontsize=11, color=color, 
                        ha="left", va="center", fontweight="bold")
                ax2.text(0.95, y_pos, f"${val:,.0f} ({percent:.0f}%)", fontsize=10, 
                        color=self.colors["text"], ha="right", va="center", fontweight="bold")

            fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.1)
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=15, pady=15, fill="both", expand=True)
            plt.close(fig)
        
        except Exception as e:
            print(f"Error creating donut chart: {e}")
            error_label = ctk.CTkLabel(parent, text="Error loading chart", 
                                     font=("Arial", 14), text_color=self.colors["error"])
            error_label.pack(expand=True)

    # ──────────────────────── ACTION METHODS ────────────────────────

    # ──────── Save expense ────────
    def _save_expense(self):
        """Save expense from Add Expense tab"""
        try:
            raw = self.expense_amount_var.get().strip()
            if not raw:
                messagebox.showwarning("Invalid Amount", "Please enter an amount")
                return

            amount = float(raw.replace(',', '.'))
            if amount <= 0:
                messagebox.showwarning("Invalid Amount", "Amount must be positive")
                return
            if amount > 1_000_000:
                messagebox.showwarning("Invalid Amount", "Amount too large")
                return

            category = self.expense_cat_var.get()
            description = self.expense_desc_var.get().strip()[:200]
            
            add_expense(amount, category, description)
            messagebox.showinfo("Success", f"Expense of ${amount:.2f} recorded successfully!")
            self._clear_expense_form()
            
            # --- Refresh dashboard if it's visible ---
            if self.current_tab == "Dashboard":
                self.show_tab("Dashboard")

        except ValueError:
            messagebox.showwarning("Invalid Amount", "Please enter a valid number")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save expense: {str(e)}")

    # ──────── Clear expense form ────────
    def _clear_expense_form(self):
        """Clear the expense form"""
        self.expense_amount_var.set("")
        self.expense_cat_var.set("Groceries")
        self.expense_desc_var.set("")

    # ──────── Save budget settings ────────
    def _save_budget_settings(self):
        """Save budget settings from Budget tab"""
        try:
            data = {}
            
            # --- Validate total budget ---
            raw_total = self.total_budget_var.get().strip().replace(",", ".")
            total = float(raw_total) if raw_total else 0.0
            if total < 0:
                raise ValueError("Total budget cannot be negative")
            data["total"] = total

            # --- Validate categories ---
            for key, var in self.category_budget_vars.items():
                raw_val = var.get().strip().replace(",", ".")
                value = float(raw_val) if raw_val else 0.0
                if value < 0:
                    raise ValueError(f"{key} cannot be negative")
                data[key] = value

            save_budget(data)
            messagebox.showinfo("Success", "Budget limits updated successfully!")

        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save budget: {str(e)}")

    # ──────────────────────── CURRENCY METHODS ────────────────────────

    # ──────── Convert currency ────────
    def _convert_currency(self, amount: float, from_curr: str, to_curr: str):
        """Convert currency using API"""
        if from_curr == to_curr:
            return amount, 1.0
        try:
            rate = get_exchange_rate(from_curr, to_curr) 
            if rate is None:
                return 0.0, 0.0
            return amount * rate, rate
        except Exception as e:
            print(f"Currency conversion error: {e}")
            return 0.0, 0.0

    # ──────── Update currency ────────      
    def _update_conversion(self):
        """Update currency conversion display"""
        if not all([hasattr(self, attr) and getattr(self, attr) is not None 
                   for attr in ['amount_var', 'result_lbl', 'rate_lbl']]):
            return
        
        try:
            amount_str = self.amount_var.get().strip()
            if not amount_str:
                self.result_lbl.configure(text="Enter an amount")
                self.rate_lbl.configure(text="")
                return
            
            amount = float(amount_str.replace(',', ''))
            from_c = self.from_var.get()
            to_c = self.to_var.get()
            converted, rate = self._convert_currency(amount, from_c, to_c)

            if rate == 0.0:
                self.result_lbl.configure(text="Conversion unavailable")
                self.rate_lbl.configure(text="Check your internet connection")
                return

            self.result_lbl.configure(text=f"💰 {amount:.2f} {from_c} = {converted:.2f} {to_c}")
            self.rate_lbl.configure(text=f"📊 1 {from_c} = {rate:.4f} {to_c}")

        except ValueError:
            self.result_lbl.configure(text="❌ Invalid amount")
            self.rate_lbl.configure(text="Please enter a valid number")
        except Exception as e:
            self.result_lbl.configure(text="❌ Error")
            self.rate_lbl.configure(text="Please try again")
            print(f"Conversion error: {e}")

    # ──────────────────────── AI ASSISTANT METHODS ────────────────────────

    # ──────── Import bank statement ────────
    def _import_bank_statement(self):
        """Import bank statement from AI Assistant tab"""
        filetypes = [("CSV files", "*.csv")]
        if PDF_SUPPORT:
            filetypes.append(("PDF files", "*.pdf"))
        filetypes.append(("All files", "*.*"))
        
        file_path = filedialog.askopenfilename(
            title="Select Bank Statement", 
            filetypes=filetypes
        )
        if not file_path:
            return
        
        filename = os.path.basename(file_path)
        self._append_chat_message("user", f"Importing bank statement: {filename}")
        
        try:
            if file_path.lower().endswith(".csv"):
                result = load_bank_statement_csv(file_path, insert_payment)
                if isinstance(result, dict) and result.get("imported", 0) > 0:
                    self._append_chat_message("assistant", 
                                            f"✅ CSV imported successfully!\n"
                                            f"Imported: {result['imported']} expenses\n"
                                            f"Failed: {result.get('failed', 0)}")
                    if result.get("expenses"):
                        lines = ["📄 Imported expenses:"]
                        for e in result["expenses"][:5]:  
                            date = e.date.strftime("%Y-%m-%d") if e.date else "Unknown"
                            desc = f" | {e.description}" if e.description else ""
                            lines.append(f" • ${e.amount:.2f} | {e.category} | {date}{desc}")
                        if len(result["expenses"]) > 5:
                            lines.append(f" • ... and {len(result['expenses']) - 5} more")
                        self._append_chat_message("assistant", "\n".join(lines))
                else:
                    self._append_chat_message("assistant", "❌ No valid expenses found in CSV")
                
                # --- Refresh dashboard if it's visible ---
                if self.current_tab == "Dashboard":
                    self.show_tab("Dashboard")
            else:
                self._append_chat_message("assistant", "❌ Unsupported file format. Please use CSV files.")

        except Exception as e:
            self._append_chat_message("assistant", f"❌ Error importing file: {str(e)}")
            print(f"Import error: {e}")

    # ──────── Append chat message ────────
    def _append_chat_message(self, role: str, text: str):
        """Add message to chat display"""
        self.chatbox.configure(state="normal")
        tag = "user" if role == "user" else "assistant"
        prefix = "You: " if role == "user" else "Assistant: "
        timestamp = datetime.now().strftime("%H:%M")
        
        self.chatbox.insert("end", f"[{timestamp}] {prefix}\n", f"{tag}_header")
        self.chatbox.insert("end", f"{text}\n\n", tag)
        self.chatbox.configure(state="disabled")
        self.chatbox.see("end")

    # ──────── Send message ────────
    def _send_message(self):
        """Send message to AI assistant"""
        msg = self.msg_var.get().strip()
        if not msg:
            return
        
        self.msg_var.set("")
        self._append_chat_message("user", msg)
        self.chat_history.append(("user", msg))
        self.send_btn.configure(state="disabled", text="...")

        try:
            reply = chat_completion(self.chat_history)

            if reply["type"] == "text":
                self.chat_history.append(("assistant", reply["content"]))
                self._append_chat_message("assistant", reply["content"])
            elif reply["type"] == "function_call":
                name, args = reply["name"], reply["arguments"]
                result = self._execute_ai_function(name, args)
                self.chat_history.append(("assistant", result))
                self._append_chat_message("assistant", result)
        
        except Exception as e:
            err = f"❌ Sorry, I encountered an error: {e}"
            self.chat_history.append(("assistant", err))
            self._append_chat_message("assistant", err)

        finally:
            self.send_btn.configure(state="normal", text="Send")

    # ──────── Execute AI function ────────
    def _execute_ai_function(self, name: str, args: dict) -> str:
        """Execute AI function calls"""
        try:
            if name == "insert_payment":
                insert_payment(**args)
                # --- Refresh dashboard if it's visible ---
                if self.current_tab == "Dashboard":
                    self.show_tab("Dashboard")
                desc = f" ({args['description']})" if args.get("description") else ""
                return f"✅ Expense recorded: ${args['amount']} for {args['category']}{desc}"

            elif name == "delete_payment":
                from src.core.database import delete_payment
                success = delete_payment(**args)
                if success:
                    # --- Refresh dashboard if it's visible ---
                    if self.current_tab == "Dashboard":
                        self.show_tab("Dashboard")
                    return f"✅ Expense #{args['expense_id']} deleted successfully."
                else:
                    return f"❌ Could not find expense #{args['expense_id']}"

            elif name == "query_expenses_by_category":
                from src.core.database import query_expenses_by_category
                total = query_expenses_by_category(**args)
                return f"💰 Total spent on {args['category']}: ${total:.2f}"
            
            elif name == "list_expenses_by_category":
                from src.core.database import list_expenses_by_category
                expenses = list_expenses_by_category(args['category'])
                if not expenses:
                    return f"No expenses found for {args['category']}."
                lines = [f"💵 Expenses in {args['category'].capitalize()}:"]
                for e in expenses[:10]:  # Limit to 10 for readability
                    lines.append(f" • ID: {e['id']} | ${e['amount']:.2f} on {e['date']} | {e['description']}")
                if len(expenses) > 10:
                    lines.append(f" • ... and {len(expenses) - 10} more")
                return "\n".join(lines)
            
            else:
                return f"❌ Unknown function: {name}"
        except Exception as e:
            return f"❌ Error executing {name}: {e}"

if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()
