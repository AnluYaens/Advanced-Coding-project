import tkinter as tk
from tkinter import messagebox, filedialog
import os
from datetime import datetime, timedelta
from typing import Dict, List
import threading

import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
try:
    from scipy.interpolate import PchipInterpolator
except ImportError:
    PchipInterpolator = None

from src.core.database import (
    save_budget,
    get_budget,
    add_expense,
    insert_payment,
    get_all_expenses,
    get_expenses_by_month as db_get_expenses_by_month,
    get_db_session,
    update_expense,
    delete_payment,
    query_expenses_by_category,
    list_expenses_by_category
)
from src.core.models import Expense
from src.core.ai_engine import chat_completion
from src.services.currency_api import get_exchange_rate
from src.services.bank_statement_loader import load_bank_statement_csv

# --- PDF support toggle ---
PDF_SUPPORT = False
try:
    from src.services.bank_statement_loader_pdf import load_bank_statement_pdf
    PDF_SUPPORT = True
except ImportError:
    print("Warning: bank_statement_loader_pdf not available")


# ──────────────────────── COLOR SYSTEM ────────────────────────
PALETTE = {
    # --- Base backgrounds (dark to light) ---
    "bg":          "#0a0a0f",     # Main background
    "bg-elevated": "#12121a",     # Elevated
    "sidebar":     "#1a1a28",     # Sidebar
    "card":        "#242438",     # Cards
    "card-hover":  "#2a2a42",     # Card hover state
    "input":       "#1f1f33",     # Input backgrounds

    # --- Primary accent (purple) ---
    "accent":      "#8b5cf6",     # Main accent
    "accent-hover": "#a78bfa",    # Accent hover
    "accent-dark": "#6d28d9",     # Accent pressed
    "accent-glow": "#8b5cf620",   # Subtle glow effect

    # --- Text hierarchy ---
    "text":        "#ffffff",     # Primary text
    "text-secondary": "#94a3b8",  # Secondary text
    "text-tertiary": "#64748b",   # Tertiary text
    "text-muted":  "#475569",     # Very muted text

    # --- Semantic colors ---
    "success":     "#10b981",     # Success green
    "success-light": "#34d399",   # Success hover
    "warning":     "#f59e0b",     # Warning orange
    "warning-light": "#fbbf24",   # Warning hover
    "error":       "#ef4444",     # Error red
    "error-light": "#f87171",     # Error hover
    "info":        "#3b82f6",     # Info blue
    "info-light":  "#60a5fa",     # Info hover

    # --- Additional colors for variety ---
    "purple":      "#8b5cf6",
    "blue":        "#3b82f6",
    "green":       "#10b981",
    "orange":      "#f59e0b",
    "pink":        "#ec4899",
    "teal":        "#14b8a6",
    "red":         "#ef4444",
    "yellow":      "#eab308",
    "indigo":      "#6366f1",

    # --- UI elements ---
    "border":      "#2e3348",     # Default border
    "border-light": "#3f4461",    # Light border
    "shadow":      "#00000040",   # Shadow color

    # --- Gray scale for buttons ---
    "gray-700":    "#374151",
    "gray-600":    "#4b5563",
    "bg-hover":    "#2a2a42",
}

# ──────────────────────── TYPOGRAPHY SYSTEM ────────────────────────
class Typography:
    FONT_FAMILY = "Inter"  # Falls back to system font if not available

    @staticmethod
    def get_font(size, weight="normal"):
        """Get font tuple with proper style handling."""
        weights = {
            "normal": "normal",
            "medium": "normal",
            "semibold": "bold",
            "bold": "bold"
        }
        style = weights.get(weight, "normal")
        return (Typography.FONT_FAMILY, size, style)

    # --- Predefined styles ---
    DISPLAY = ("Inter", 28, "bold")
    HEADING_1 = ("Inter", 24, "bold")
    HEADING_2 = ("Inter", 20, "bold")
    HEADING_3 = ("Inter", 16, "bold")
    BODY_LARGE = ("Inter", 15, "normal")
    BODY = ("Inter", 14, "normal")
    CAPTION = ("Inter", 12, "normal")
    SMALL = ("Inter", 11, "normal")

# ──────────────────────── CUSTOM WIDGETS ────────────────────────

class AnimatedButton(ctk.CTkButton):
    """A CustomTkinter button with hover and press animations."""
    def __init__(self, *args, **kwargs):
        self.default_color = kwargs.get('fg_color', PALETTE["accent"])
        self.hover_color = kwargs.get('hover_color', PALETTE["accent-hover"])
        super().__init__(*args, **kwargs)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event=None):
        self.configure(fg_color=self.hover_color)

    def _on_leave(self, event=None):
        self.configure(fg_color=self.default_color)

    def _on_press(self, event=None):
        self.configure(fg_color=PALETTE["accent-dark"])

    def _on_release(self, event):
        if self.winfo_containing(event.x_root, event.y_root) == self:
            self.configure(fg_color=self.hover_color)
        else:
            self.configure(fg_color=self.default_color)

class GlassCard(ctk.CTkFrame):
    """A card with a semi-transparent 'glass' effect."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(
            fg_color=PALETTE["card"],
            corner_radius=12,
            border_width=1,
            border_color=PALETTE["border"]
        )

class LoadingIndicator(ctk.CTkLabel):
    """An animated loading indicator label."""
    def __init__(self, parent):
        super().__init__(parent, text="", font=Typography.BODY)
        self.dots = 0
        self.is_loading = False

    def start(self):
        self.is_loading = True
        self.animate()

    def stop(self):
        self.is_loading = False
        self.configure(text="")

    def animate(self):
        if not self.is_loading:
            return
        self.dots = (self.dots + 1) % 4
        self.configure(text="Thinking" + "." * self.dots)
        self.after(300, self.animate)

# ──────────────────────── UI WIDGETS ────────────────────────

class FinancialInsightsWidget(ctk.CTkFrame):
    """A widget to display AI-generated financial insights."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color=PALETTE["card"], corner_radius=12)

        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            header_frame,
            text="🤖 AI Financial Insights",
            font=Typography.get_font(14, "bold"),
            text_color=PALETTE["text"]
        ).pack(side="left")

        self.refresh_btn = AnimatedButton(
            header_frame,
            text="↻",
            width=24,
            height=24,
            fg_color=PALETTE["info"],
            hover_color=PALETTE["info-light"],
            command=self.refresh_insights,
            font=Typography.get_font(12, "bold"),
            corner_radius=4
        )
        self.refresh_btn.pack(side="right")

        # --- Insights container ---
        self.insights_frame = ctk.CTkFrame(
            self,
            fg_color=PALETTE["bg-elevated"],
            corner_radius=8
        )
        self.insights_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # --- Auto-load insights on a slight delay ---
        self.after(500, self.refresh_insights)

    def refresh_insights(self):
        """Generate insights with loading animation."""
        for widget in self.insights_frame.winfo_children():
            widget.destroy()

        loading = LoadingIndicator(self.insights_frame)
        loading.pack(pady=30)
        loading.start()

        # --- Simulate loading ---
        self.after(800, lambda: self._show_insights(loading))

    def _show_insights(self, loading_indicator):
        loading_indicator.stop()
        loading_indicator.destroy()

        # --- Get real data from database ---
        try:
            with get_db_session() as session:
                expenses = session.query(Expense).all()
                session.expunge_all()

            total_spent = sum(e.amount for e in expenses)
            monthly_budget = get_budget().get("total", 2000) if get_budget() else 2000
            budget_used = (total_spent / monthly_budget * 100) if monthly_budget > 0 else 0

            category_totals = {}
            for e in expenses:
                cat = e.category or "Other"
                category_totals[cat] = category_totals.get(cat, 0) + e.amount

            highest_cat = max(category_totals.items(), key=lambda x: x[1])[0] if category_totals else "None"

            insights = [
                ("💡", "Spending Status", f"You've used {budget_used:.0f}% of your monthly budget",
                 PALETTE["success"] if budget_used < 80 else PALETTE["warning"]),
                ("📊", "Top Category", f"Highest spending: {highest_cat} (${category_totals.get(highest_cat, 0):.0f})",
                 PALETTE["info"]),
                ("🎯", "Savings Tip", f"You have ${max(0, monthly_budget - total_spent):.0f} left in your budget",
                 PALETTE["purple"]),
                ("📈", "Transaction Count", f"Total transactions this month: {len(expenses)}",
                 PALETTE["blue"])
            ]
        except Exception as e:
            print(f"Error generating insights: {e}")
            insights = [
                ("💡", "Welcome", "Start tracking your expenses to see insights", PALETTE["info"])
            ]

        for emoji, category, text, color in insights:
            insight_card = GlassCard(self.insights_frame)
            insight_card.pack(fill="x", padx=10, pady=2)
            insight_card.configure(fg_color=PALETTE["bg-elevated"])

            content_frame = ctk.CTkFrame(insight_card, fg_color="transparent")
            content_frame.pack(fill="x", padx=12, pady=8)

            icon_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            icon_frame.pack(side="left", padx=(0, 8))

            ctk.CTkLabel(icon_frame, text=emoji, font=Typography.get_font(14)).pack()

            text_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(text_frame, text=category, font=Typography.get_font(10, "bold"), text_color=color, anchor="w").pack(anchor="w")

            ctk.CTkLabel(
                text_frame, text=text, font=Typography.get_font(9, "normal"),
                text_color=PALETTE["text-secondary"], anchor="w", wraplength=200
            ).pack(anchor="w", pady=(1, 0))

class QuickStatsWidget(ctk.CTkFrame):
    """A widget to display quick statistics cards."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color="transparent")

        # --- Title ---
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            title_frame, text="📊 Quick Statistics", font=Typography.get_font(14, "bold"),
            text_color=PALETTE["text"]
        ).pack(side="left")

        # --- Stats grid ---
        stats_container = ctk.CTkFrame(self, fg_color="transparent")
        stats_container.pack(fill="both", expand=True)
        stats_container.grid_columnconfigure((0, 1), weight=1)
        stats_container.grid_rowconfigure((0, 1), weight=1)
        self.create_stats_cards(stats_container)

    def create_stats_cards(self, parent):
        """Creates and places the individual stat cards."""
        stats = self.calculate_stats()
        cards_info = [
            ("💰", "Total Spent", f"${stats['total_spent']:.0f}", f"↗ +{stats['spent_change']}%", PALETTE["blue"]),
            ("📊", "Daily Average", f"${stats['daily_avg']:.0f}", f"{'↘' if stats['avg_change'] < 0 else '↗'} {stats['avg_change']:+.0f}%", PALETTE["green"]),
            ("🎯", "Budget Used", f"{stats['budget_used']}%", "On Track" if stats['budget_used'] < 80 else "⚠️ High", PALETTE["purple"]),
            ("💳", "Transactions", str(stats['transaction_count']), "Total this month", PALETTE["orange"]),
        ]
        for i, (icon, label, value, change, color) in enumerate(cards_info):
            card = self.create_single_stat_card(parent, icon, label, value, change, color)
            card.grid(row=i//2, column=i%2, padx=3, pady=3, sticky="ew")

    def create_single_stat_card(self, parent, icon, label, value, change, color):
        """Creates a single stat card."""
        card = GlassCard(parent)
        card.configure(border_color=PALETTE["border-light"])

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text=icon, font=Typography.get_font(14, "normal")).pack(side="left")
        ctk.CTkLabel(header, text=label, font=Typography.get_font(10, "normal"), text_color=PALETTE["text-secondary"]).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(content, text=value, font=Typography.get_font(18, "bold"), text_color=PALETTE["text"]).pack(pady=(6, 3))

        change_frame = ctk.CTkFrame(content, fg_color="transparent")
        change_frame.pack()
        change_color = PALETTE["success"] if "+" in change or "On Track" in change else PALETTE["error"] if "↘" in change or "High" in change else PALETTE["text-tertiary"]
        ctk.CTkLabel(change_frame, text=change, font=Typography.get_font(9, "normal"), text_color=change_color).pack()

        return card

    def calculate_stats(self):
        """Calculates statistics from the database."""
        try:
            with get_db_session() as session:
                now = datetime.now()
                month_start = datetime(now.year, now.month, 1)
                current_expenses = session.query(Expense).filter(Expense.date >= month_start).all()

                if now.month == 1:
                    last_month_start, last_month_end = datetime(now.year - 1, 12, 1), datetime(now.year - 1, 12, 31)
                else:
                    last_month_start, last_month_end = datetime(now.year, now.month - 1, 1), month_start - timedelta(days=1)
                
                last_month_expenses = session.query(Expense).filter(Expense.date.between(last_month_start, last_month_end)).all()
                session.expunge_all()

                total_spent = sum(e.amount for e in current_expenses)
                days_passed = (now - month_start).days + 1
                daily_avg = total_spent / days_passed if days_passed > 0 else 0

                monthly_budget = (get_budget() or {}).get("total", 2000)
                budget_used = (total_spent / monthly_budget * 100) if monthly_budget > 0 else 0
                
                last_month_total = sum(e.amount for e in last_month_expenses)
                spent_change = ((total_spent - last_month_total) / last_month_total * 100) if last_month_total > 0 else 0

                last_month_daily_avg = last_month_total / ((last_month_end - last_month_start).days + 1) if last_month_total > 0 else 0
                avg_change = ((daily_avg - last_month_daily_avg) / last_month_daily_avg * 100) if last_month_daily_avg > 0 else 0

                return {
                    'total_spent': total_spent, 'spent_change': int(spent_change),
                    'daily_avg': daily_avg, 'avg_change': int(avg_change),
                    'budget_used': int(budget_used), 'transaction_count': len(current_expenses)
                }
        except Exception as e:
            print(f"Error calculating stats: {e}")
            return {'total_spent': 0, 'spent_change': 0, 'daily_avg': 0, 'avg_change': 0, 'budget_used': 0, 'transaction_count': 0}

# ──────────────────────── Global `customtkinter` config ────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ──────────────────────── Main Application ────────────────────────
class BudgetApp(ctk.CTk):
    """The main class for the AI Budget Tracker application."""

    def __init__(self):
        super().__init__()
        self.title("AI Budget Tracker")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.minsize(1000, 600)

        # --- Center window on screen ---
        self.update_idletasks()
        width, height = 1200, 700
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2) - 40
        self.geometry(f"{width}x{height}+{x}+{y}")

        # --- Colors and Configuration ---
        self.colors = PALETTE.copy()
        self.configure(fg_color=self.colors["bg"])

        # --- State management ---
        self.current_tab = "Dashboard"
        self.main_sections = {}
        self.dashboard_chat_history = []

        # --- Initialize all instance variables ---
        self.expense_amount_var, self.expense_cat_var, self.expense_desc_var = None, None, None
        self.amount_var, self.from_var, self.to_var = None, None, None
        self.result_lbl, self.rate_lbl = None, None
        self.total_budget_var, self.category_budget_vars = None, {}
        self.dashboard_chatbox, self.dashboard_msg_var, self.dashboard_send_btn = None, None, None
        self.transaction_list_frame, self.filter_category_var, self.filter_month_var = None, None, None
        self._chart_canvas, self._chart_canvas_donut = None, None
        
        # --- Load icons ---
        def load_icon(path, size=(24, 24)):
            try:
                return CTkImage(
                    light_image=Image.open(path).resize(size, Image.Resampling.LANCZOS),
                    dark_image=Image.open(path).resize(size, Image.Resampling.LANCZOS),
                    size=size
                )
            except Exception as e:
                print(f"Error loading icon {path}: {e}")
                return None

        self.emoji_icons = {
            "Dashboard": load_icon("src/assets/icons/dashboard.png"),
            "Add Expense": load_icon("src/assets/icons/add_expense.png"),
            "All Transactions": load_icon("src/assets/icons/all_transactions.png"),
            "Analytics": load_icon("src/assets/icons/analytics.png"),
            "AI Insights": load_icon("src/assets/icons/ai_insights.png"),
            "Set Budget": load_icon("src/assets/icons/set_budget.png"),
            "Currency": load_icon("src/assets/icons/currency.png"),
            "Contact": load_icon("src/assets/icons/contact.png"),
        }

        # --- Build UI ---
        self.nav_buttons = {}
        self._create_layout()

    def _create_layout(self):
        """Creates the main application layout."""
        # --- Main container ---
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=0, pady=0)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        # --- Create sidebar ---
        self._create_sidebar(main_container)

        # --- Create main content area ---
        self._create_content_area(main_container)

        # --- Show dashboard by default ---
        self.show_tab("Dashboard")

    def _create_sidebar(self, parent):
        """Creates the sidebar navigation."""
        sidebar = ctk.CTkFrame(parent, fg_color=self.colors["sidebar"], width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        sidebar.grid_propagate(False)

        # --- Logo/Header ---
        header = ctk.CTkFrame(sidebar, fg_color="transparent", height=80)
        header.pack(fill="x", padx=16, pady=(20, 30))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="Budget", font=Typography.HEADING_1, text_color=self.colors["text"]).pack(anchor="w")
        ctk.CTkLabel(header, text="Tracker Pro", font=Typography.get_font(14, "normal"), text_color=self.colors["text-secondary"]).pack(anchor="w")

        # --- Navigation tabs ---
        tabs_config = ["Dashboard", "Add Expense", "All Transactions", "Analytics", "AI Insights", "Set Budget", "Currency", "Contact"]
        for tab in tabs_config:
            btn = AnimatedButton(
                sidebar, text=f"  {tab}", anchor="w", height=48, fg_color="transparent",
                hover_color=self.colors["bg-hover"], text_color=self.colors["text-secondary"],
                font=Typography.get_font(15, "medium"), command=lambda t=tab: self.show_tab(t),
                image=self.emoji_icons.get(tab), compound="left", corner_radius=8
            )
            btn.pack(fill="x", padx=16, pady=2)
            self.nav_buttons[tab] = btn

    def _create_content_area(self, parent):
        """Creates the main content area."""
        self.content_frame = ctk.CTkFrame(parent, fg_color=self.colors["bg"], corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

    def set_active_tab(self, tab_name):
        """Updates the visual state of the navigation buttons."""
        for name, btn in self.nav_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=self.colors["accent"], text_color=self.colors["text"])
            else:
                btn.configure(fg_color="transparent", text_color=self.colors["text-secondary"])

    def clear_content(self):
        """Clears all widgets from the content frame and performs cleanup."""
        # --- Clean up chart references to prevent memory leaks ---
        if hasattr(self, '_chart_canvas') and self._chart_canvas:
            self._chart_canvas.get_tk_widget().destroy()
            self._chart_canvas = None
        if hasattr(self, '_chart_canvas_donut') and self._chart_canvas_donut:
            self._chart_canvas_donut.get_tk_widget().destroy()
            self._chart_canvas_donut = None
        plt.close('all')

        # --- Destroy all widgets in content frame ---
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # --- Reset grid configuration ---
        for i in range(self.content_frame.grid_size()[0]):
            self.content_frame.grid_columnconfigure(i, weight=0)
        for i in range(self.content_frame.grid_size()[1]):
            self.content_frame.grid_rowconfigure(i, weight=0)


    def show_tab(self, tab_name):
        """Shows the content for a specific tab."""
        self.clear_content()
        self.set_active_tab(tab_name)
        self.current_tab = tab_name

        # --- Route to appropriate tab content ---
        tab_methods = {
            "Dashboard": self._create_dashboard_tab,
            "Add Expense": self._create_add_expense_tab,
            "All Transactions": self._create_all_transactions_tab,
            "Analytics": self._create_analytics_tab,
            "Set Budget": self._create_budget_tab,
            "Currency": self._create_currency_tab,
            "AI Insights": self._create_ai_insights_tab,
            "Contact": self._create_contact_tab
        }
        
        if tab_name == "Dashboard":
            self.dashboard_chat_history = []
        
        if method := tab_methods.get(tab_name):
            method()

    # ──────────────────────── DASHBOARD TAB ────────────────────────

    def _create_dashboard_tab(self):
        """Creates the dashboard tab."""
        # --- Dashboard header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(header_frame, text="Financial Dashboard", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")
        ctk.CTkLabel(header_frame, text=datetime.now().strftime("%B %Y"), font=Typography.BODY, text_color=self.colors["text-secondary"]).pack(side="right", pady=(8,0))

        # --- Visual separator ---
        separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=self.colors["border"])
        separator.pack(fill="x", padx=20, pady=(5, 15))

        # --- Main dashboard container ---
        main_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- Configure responsive grid ---
        main_container.grid_columnconfigure(0, weight=4, minsize=350)
        main_container.grid_columnconfigure(1, weight=3, minsize=280)
        main_container.grid_columnconfigure(2, weight=6, minsize=420)
        main_container.grid_rowconfigure(0, weight=1)

        # --- Create columns ---
        self._create_charts_column(main_container)
        self._create_chat_column(main_container)
        self._create_widgets_column(main_container)

    def _create_charts_column(self, parent):
        """Creates the charts column for the dashboard."""
        left_column = ctk.CTkFrame(parent, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        # --- Monthly trend chart ---
        trend_card = GlassCard(left_column)
        trend_card.pack(fill="both", expand=True, pady=(0, 8))
        ctk.CTkLabel(trend_card, text="Monthly Spending Trend", font=Typography.HEADING_3, text_color=self.colors["text"]).pack(padx=16, pady=(16, 0), anchor="w")
        self.show_line_chart(trend_card)

        # --- Category breakdown ---
        category_card = GlassCard(left_column)
        category_card.pack(fill="both", expand=True)
        ctk.CTkLabel(category_card, text="Category Breakdown", font=Typography.HEADING_3, text_color=self.colors["text"]).pack(padx=16, pady=(16, 0), anchor="w")
        self.show_donut_chart(category_card)

    def _create_chat_column(self, parent):
        """Creates the AI chat column for the dashboard."""
        chat_card = GlassCard(parent)
        chat_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=0)

        # --- Chat header ---
        chat_header = ctk.CTkFrame(chat_card, fg_color="transparent")
        chat_header.pack(fill="x", padx=12, pady=(12, 8))
        ctk.CTkLabel(chat_header, text="AI Assistant", font=Typography.get_font(14, "bold"), text_color=self.colors["text"]).pack(side="left")
        import_btn = AnimatedButton(
            chat_header, text="📂", width=32, height=26, fg_color=self.colors["accent"],
            hover_color=self.colors["accent-hover"], command=self._import_bank_statement,
            font=Typography.get_font(11, "medium"), corner_radius=6
        )
        import_btn.pack(side="right")

        # --- Chat display ---
        chat_display = ctk.CTkFrame(chat_card, fg_color=self.colors["bg-elevated"], corner_radius=8)
        chat_display.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.dashboard_chatbox = tk.Text(
            chat_display, state="disabled", bg=self.colors["bg-elevated"], fg=self.colors["text"],
            font=Typography.get_font(12, "normal"), wrap="word", borderwidth=0, highlightthickness=0,
            insertbackground=self.colors["accent"]
        )
        self.dashboard_chatbox.pack(padx=8, pady=8, fill="both", expand=True)
        self.dashboard_chatbox.tag_config("user_header", foreground=self.colors["accent"], font=Typography.get_font(11, "bold"))
        self.dashboard_chatbox.tag_config("user", foreground=self.colors["text"], font=Typography.get_font(12, "normal"))
        self.dashboard_chatbox.tag_config("assistant_header", foreground=self.colors["info"], font=Typography.get_font(11, "bold"))
        self.dashboard_chatbox.tag_config("assistant", foreground=self.colors["text-secondary"], font=Typography.get_font(12, "normal"))

        # --- Chat input ---
        input_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        input_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.dashboard_msg_var = tk.StringVar()
        msg_entry = ctk.CTkEntry(
            input_frame, textvariable=self.dashboard_msg_var, height=32, placeholder_text="Ask me...",
            font=Typography.get_font(11, "normal"), fg_color=self.colors["input"],
            border_color=self.colors["border"], corner_radius=6
        )
        msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        msg_entry.bind("<Return>", lambda e: self._send_dashboard_message())
        msg_entry.focus()
        self.dashboard_send_btn = AnimatedButton(
            input_frame, text="Send", width=50, height=32, fg_color=self.colors["accent"],
            hover_color=self.colors["accent-hover"], command=self._send_dashboard_message,
            font=Typography.get_font(10, "semibold"), corner_radius=6
        )
        self.dashboard_send_btn.pack(side="right")

        # --- Welcome message ---
        if not self.dashboard_chat_history:
            self._append_dashboard_chat("assistant",
                "Hello! I'm your AI budget assistant. I can help you:\n"
                "• Record expenses (e.g., 'Add $50 for groceries')\n"
                "• Check spending (e.g., 'How much on entertainment?')\n"
                "• Import bank statements (click 📂)\n\n"
                "How can I help you today?")

    def _create_widgets_column(self, parent):
        """Creates the widgets column for the dashboard."""
        right_column = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color=self.colors["accent"],
            scrollbar_button_hover_color=self.colors["accent-hover"], scrollbar_fg_color=self.colors["bg-elevated"]
        )
        right_column.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=0)
        
        # --- Add widgets to the column ---
        QuickStatsWidget(right_column).pack(fill="x", pady=(0, 8))
        self._create_budget_status(right_column)
        self._create_recent_transactions(right_column)

    def _create_recent_transactions(self, parent):
        """Creates the recent transactions widget."""
        trans_card = GlassCard(parent)
        trans_card.pack(fill="x", pady=(8, 0))
        
        header = ctk.CTkFrame(trans_card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(header, text="Recent Transactions", font=Typography.get_font(14, "bold"), text_color=self.colors["text"]).pack(side="left")
        view_all_label = ctk.CTkLabel(header, text="View all →", font=Typography.get_font(10, "normal"), text_color=self.colors["accent"], cursor="hand2")
        view_all_label.pack(side="right")
        view_all_label.bind("<Button-1>", lambda e: self.show_tab("All Transactions"))

        try:
            with get_db_session() as session:
                recent = session.query(Expense).order_by(Expense.date.desc()).limit(5).all()
                session.expunge_all()
            
            if not recent:
                ctk.CTkLabel(trans_card, text="No transactions yet.", font=Typography.BODY, text_color=self.colors["text-tertiary"]).pack(pady=20)
            else:
                for exp in recent:
                    trans_frame = ctk.CTkFrame(trans_card, fg_color="transparent", corner_radius=6)
                    trans_frame.pack(fill="x", padx=16, pady=2)
                    
                    content = ctk.CTkFrame(trans_frame, fg_color="transparent")
                    content.pack(fill="x", padx=12, pady=8)

                    left_frame = ctk.CTkFrame(content, fg_color="transparent")
                    left_frame.pack(side="left", fill="x", expand=True)

                    category_colors = {"Groceries": self.colors["green"], "Entertainment": self.colors["pink"], "Electronics": self.colors["blue"], "Other": self.colors["orange"]}
                    color = category_colors.get(exp.category, self.colors["text-tertiary"])
                    
                    ctk.CTkLabel(left_frame, text=exp.category, font=Typography.get_font(11, "medium"), text_color=color, anchor="w").pack(anchor="w")

                    date_str = exp.date.strftime("%b %d") if exp.date else "Unknown"
                    desc = (exp.description[:20] + "..." if exp.description and len(exp.description) > 20 else exp.description) or ""
                    
                    ctk.CTkLabel(left_frame, text=f"{date_str} • {desc}" if desc else date_str, font=Typography.get_font(9, "normal"), text_color=self.colors["text-tertiary"], anchor="w").pack(anchor="w")
                    
                    ctk.CTkLabel(content, text=f"${exp.amount:.2f}", font=Typography.get_font(12, "bold"), text_color=self.colors["text"]).pack(side="right")
        except Exception as e:
            print(f"Error loading transactions: {e}")
        
        ctk.CTkFrame(trans_card, fg_color="transparent", height=12).pack()
    
    def _create_budget_status(self, parent):
        """Creates the budget status widget."""
        budget_card = GlassCard(parent)
        budget_card.pack(fill="x")
        
        ctk.CTkLabel(budget_card, text="Budget Status (Current Month)", font=Typography.get_font(14, "bold"), text_color=self.colors["text"]).pack(padx=16, pady=(12, 8), anchor="w")
        
        try:
            budget_data = get_budget() or {}
            now = datetime.now()
            expenses = db_get_expenses_by_month(now.month, now.year)
            
            category_spending = {"groceries": 0, "entertainment": 0, "electronics": 0, "other": 0}
            for exp in expenses:
                cat_key = exp.category.lower() if exp.category else "other"
                category_spending[cat_key] = category_spending.get(cat_key, 0) + exp.amount

            categories = [
                ("Groceries", "groceries", budget_data.get("groceries", 600), self.colors["green"]),
                ("Entertainment", "entertainment", budget_data.get("entertainment", 300), self.colors["pink"]),
                ("Electronics", "electronics", budget_data.get("electronics", 500), self.colors["blue"]),
                ("Other", "other", budget_data.get("other", 200), self.colors["orange"])
            ]
            
            for display_name, key, budget_amount, color in categories:
                spent = category_spending.get(key, 0)
                progress = min(spent / budget_amount, 1.0) if budget_amount > 0 else 0
                
                cat_frame = ctk.CTkFrame(budget_card, fg_color="transparent")
                cat_frame.pack(fill="x", padx=16, pady=4)
                
                header = ctk.CTkFrame(cat_frame, fg_color="transparent")
                header.pack(fill="x", pady=(0, 3))
                ctk.CTkLabel(header, text=display_name, font=Typography.get_font(11, "medium"), text_color=self.colors["text"]).pack(side="left")
                ctk.CTkLabel(header, text=f"${spent:.0f} / ${budget_amount:.0f}", font=Typography.get_font(10, "normal"), text_color=color).pack(side="right")
                
                progress_bg = ctk.CTkFrame(cat_frame, height=4, fg_color=self.colors["bg-elevated"], corner_radius=2)
                progress_bg.pack(fill="x")
                if progress > 0:
                    fill_color = self.colors["warning"] if progress >= 0.9 else color
                    progress_fill = ctk.CTkFrame(progress_bg, height=4, fg_color=fill_color, corner_radius=2)
                    progress_fill.place(relwidth=progress, relheight=1)

        except Exception as e:
            print(f"Error loading budget status: {e}")
        
        ctk.CTkFrame(budget_card, fg_color="transparent", height=12).pack()
        
    # ──────────────────────── CHARTS ────────────────────────

    def _create_empty_data_placeholder(self, parent, icon, title, subtitle):
        """Creates a standardized placeholder for when there is no data."""
        placeholder_frame = ctk.CTkFrame(parent, fg_color="transparent")
        placeholder_frame.pack(expand=True, fill="both", padx=10, pady=20)
        
        center_frame = ctk.CTkFrame(placeholder_frame, fg_color="transparent")
        center_frame.pack(expand=True)
        ctk.CTkLabel(center_frame, text=icon, font=Typography.get_font(40), text_color=self.colors["text-tertiary"]).pack(pady=(0,10))
        ctk.CTkLabel(center_frame, text=title, font=Typography.HEADING_2, text_color=self.colors["text"]).pack()
        ctk.CTkLabel(center_frame, text=subtitle, font=Typography.BODY, text_color=self.colors["text-secondary"], wraplength=210).pack(pady=(4,0))
        
    def show_line_chart(self, parent):
        """Displays the monthly spending line chart."""
        try:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            data = self.get_expenses_by_month_for_chart()
            x = np.arange(len(months))

            if sum(data) == 0:
                self._create_empty_data_placeholder(parent, "📈", "No Expense Data", "Add expenses to see your monthly trend.")
                return

            fig, ax = plt.subplots(figsize=(6.5, 4), dpi=80)
            fig.patch.set_facecolor(self.colors["card"])
            ax.set_facecolor(self.colors["card"])

            if len(set(data)) > 1 and sum(data) > 0 and PchipInterpolator:
                x_smooth = np.linspace(x.min(), x.max(), 300)
                y_smooth = PchipInterpolator(x, data)(x_smooth)
                ax.fill_between(x_smooth, 0, y_smooth, alpha=0.15, color=self.colors["accent"])
                ax.plot(x_smooth, y_smooth, color=self.colors["accent"], linewidth=2.5, zorder=2)
            else:
                ax.plot(x, data, color=self.colors["accent"], linewidth=2.5, marker="o", zorder=2)

            for xi, val in enumerate(data):
                if val > 0:
                    ax.scatter(xi, val, color=self.colors["accent"], s=100, alpha=0.2, zorder=1)
                    ax.scatter(xi, val, color=self.colors["accent"], edgecolor='white', s=40, linewidth=1.5, zorder=3)
                    ax.text(xi, val + max(data) * 0.05, f"${val:,.0f}", fontsize=9, color=self.colors["text"], ha='center', va='bottom', fontweight='medium')

            ax.set_ylim(bottom=0)
            ax.set_xticks(x)
            ax.set_xticklabels(months, color=self.colors["text-secondary"], fontsize=9)
            ax.tick_params(axis='y', colors=self.colors["text-tertiary"], labelsize=8)
            ax.grid(axis='y', linestyle='-', linewidth=0.5, color=self.colors["border"], alpha=0.3)
            [spine.set_visible(False) for spine in ax.spines.values()]
            fig.tight_layout(pad=1.5)

            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=16, pady=(8, 16), fill="both", expand=True)
            self._chart_canvas = canvas
            plt.close(fig)

        except Exception as e:
            print(f"Error creating line chart: {e}")
            self._create_empty_data_placeholder(parent, "❌", "Chart Error", "Could not load the line chart data.")

    def show_donut_chart(self, parent):
        """Displays the category breakdown donut chart."""
        try:
            categories = ["Groceries", "Electronics", "Entertainment", "Other"]
            vals = self.get_expenses_by_category_for_chart()
            total = sum(vals)

            if total == 0:
                self._create_empty_data_placeholder(parent, "🍩", "No Category Data", "Add expenses to see the category breakdown.")
                return

            colors = [self.colors["green"], self.colors["blue"], self.colors["pink"], self.colors["orange"]]
            fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=80)
            fig.patch.set_facecolor(self.colors["card"])
            ax.set_facecolor(self.colors["card"])

            ax.pie(vals, colors=colors, wedgeprops=dict(width=0.4, edgecolor=self.colors["card"], linewidth=2), startangle=90)
            ax.add_artist(plt.Circle((0, 0), 0.60, fc=self.colors["card"]))
            
            ax.text(0, 0, f"${total:,.0f}", ha='center', va='center', fontsize=18, fontweight='bold', color=self.colors["text"])
            ax.text(0, -0.15, "Total", ha='center', va='center', fontsize=11, color=self.colors["text-secondary"])
            ax.axis("equal")

            legend_elements = [
                plt.Rectangle((0, 0), 1, 1, fc=color, label=f"{cat}: ${val:,.0f} ({val/total*100:.0f}%)")
                for cat, val, color in zip(categories, vals, colors) if val > 0
            ]
            ax.legend(
                handles=legend_elements, loc='center', bbox_to_anchor=(0.5, -0.15),
                ncol=2, frameon=False, fontsize=9, labelcolor=self.colors["text-secondary"],
                handlelength=0.8, handletextpad=0.5, columnspacing=1.0
            )
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=16, pady=(8, 16), fill="both", expand=True)
            self._chart_canvas_donut = canvas
            plt.close(fig)
            
        except Exception as e:
            print(f"Error creating donut chart: {e}")
            self._create_empty_data_placeholder(parent, "❌", "Chart Error", "Could not load the donut chart data.")

    # ──────────────────────── UI TABS ────────────────────────

    def _create_add_expense_tab(self):
        """Creates the 'Add Expense' tab."""
        # --- Header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text="Add New Expense", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")

        # --- Separator ---
        separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=self.colors["border"])
        separator.pack(fill="x", padx=30, pady=(5, 16))

        # --- Form card ---
        form_card = GlassCard(self.content_frame)
        form_card.pack(fill="x", padx=30, pady=16)
        form_content = ctk.CTkFrame(form_card, fg_color="transparent")
        form_content.pack(padx=40, pady=40)

        # --- Amount input ---
        ctk.CTkLabel(form_content, text="Amount", font=Typography.get_font(14, "semibold"), text_color=self.colors["text"]).pack(anchor="w", pady=(0, 6))
        self.expense_amount_var = tk.StringVar(value="")
        amount_entry = ctk.CTkEntry(
            form_content, textvariable=self.expense_amount_var, width=350, height=44,
            placeholder_text="0.00", font=Typography.get_font(16, "normal"), fg_color=self.colors["input"],
            border_color=self.colors["border"], corner_radius=8
        )
        amount_entry.pack(anchor="w", pady=(0, 20))
        amount_entry.focus()

        # --- Category selection ---
        ctk.CTkLabel(form_content, text="Category", font=Typography.get_font(14, "semibold"), text_color=self.colors["text"]).pack(anchor="w", pady=(0, 6))
        self.expense_cat_var = tk.StringVar(value="Groceries")
        category_menu = ctk.CTkOptionMenu(
            form_content, variable=self.expense_cat_var, values=["Groceries", "Electronics", "Entertainment", "Other"],
            width=350, height=44, fg_color=self.colors["accent"], font=Typography.get_font(14, "normal"),
            dropdown_font=Typography.BODY, corner_radius=8
        )
        category_menu.pack(anchor="w", pady=(0, 20))

        # --- Description ---
        ctk.CTkLabel(form_content, text="Description (optional)", font=Typography.get_font(14, "semibold"), text_color=self.colors["text"]).pack(anchor="w", pady=(0, 6))
        self.expense_desc_var = tk.StringVar()
        desc_entry = ctk.CTkEntry(
            form_content, textvariable=self.expense_desc_var, width=350, height=44,
            placeholder_text="What did you buy?", font=Typography.get_font(14, "normal"),
            fg_color=self.colors["input"], border_color=self.colors["border"], corner_radius=8
        )
        desc_entry.pack(anchor="w", pady=(0, 32))

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(form_content, fg_color="transparent")
        btn_frame.pack(anchor="w")
        save_btn = AnimatedButton(
            btn_frame, text="💾 Save Expense", width=180, height=44, command=self._save_expense,
            fg_color=self.colors["success"], hover_color=self.colors["success-light"],
            font=Typography.get_font(14, "bold"), corner_radius=8
        )
        save_btn.pack(side="left", padx=(0, 12))
        clear_btn = AnimatedButton(
            btn_frame, text="🗑️ Clear Form", width=140, height=44, command=self._clear_expense_form,
            fg_color=self.colors["gray-700"], hover_color=self.colors["gray-600"],
            font=Typography.get_font(14, "normal"), corner_radius=8
        )
        clear_btn.pack(side="left")

    def _create_all_transactions_tab(self):
        """Creates the 'All Transactions' tab with filters."""
        # --- Configure grid for this specific tab ---
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(2, weight=1)

        # --- Header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text="All Transactions", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")

        # --- Filter Panel ---
        filter_card = GlassCard(self.content_frame)
        filter_card.grid(row=1, column=0, sticky="ew", padx=30, pady=(15, 10))
        filter_frame = ctk.CTkFrame(filter_card, fg_color="transparent")
        filter_frame.pack(padx=16, pady=10, fill="x")

        ctk.CTkLabel(filter_frame, text="Category:", font=Typography.BODY).pack(side="left", padx=(0, 8))
        self.filter_category_var = tk.StringVar(value="All")
        categories = ["All", "Groceries", "Entertainment", "Electronics", "Other"]
        ctk.CTkOptionMenu(filter_frame, variable=self.filter_category_var, values=categories, width=150, font=Typography.BODY, fg_color=PALETTE["input"]).pack(side="left")

        ctk.CTkLabel(filter_frame, text="Month:", font=Typography.BODY).pack(side="left", padx=(24, 8))
        self.filter_month_var = tk.StringVar(value="All")
        months = ["All"] + [datetime(2000, i, 1).strftime('%B') for i in range(1, 13)]
        ctk.CTkOptionMenu(filter_frame, variable=self.filter_month_var, values=months, width=150, font=Typography.BODY, fg_color=PALETTE["input"]).pack(side="left")

        apply_btn = AnimatedButton(filter_frame, text="Apply Filters", height=30, command=self._refresh_transaction_list)
        apply_btn.pack(side="left", padx=24)

        # --- Transaction List Frame ---
        list_container = GlassCard(self.content_frame)
        list_container.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 10))
        self.transaction_list_frame = ctk.CTkScrollableFrame(list_container, fg_color="transparent")
        self.transaction_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Initial data load ---
        self._refresh_transaction_list()

    def _refresh_transaction_list(self):
        """Clears and reloads the transaction list based on filters."""
        for widget in self.transaction_list_frame.winfo_children():
            widget.destroy()

        loading_label = ctk.CTkLabel(self.transaction_list_frame, text="🔄 Loading transactions...", font=Typography.BODY, text_color=PALETTE["text-secondary"])
        loading_label.pack(expand=True)

        self.after(50, lambda: self._load_and_display_transactions(loading_label))

    def _load_and_display_transactions(self, loading_label: ctk.CTkLabel):
        """Fetches and displays filtered transactions."""
        loading_label.destroy()
        
        category = self.filter_category_var.get()
        months_map = {name: i for i, name in enumerate(["All"] + [datetime(2000, i, 1).strftime('%B') for i in range(1, 13)])}
        month = months_map[self.filter_month_var.get()]
        current_year = datetime.now().year

        all_expenses = get_all_expenses(limit=100, category=category, month=month, year=current_year)

        if not all_expenses:
            self._create_empty_data_placeholder(self.transaction_list_frame, "📂", "No Transactions Found", "Try adjusting your filters or add a new expense.")
            return

        for expense in all_expenses:
            self._create_transaction_row_widget(self.transaction_list_frame, expense)

    def _create_transaction_row_widget(self, parent, expense: Expense):
        """Creates a single row widget for the transaction list."""
        main_row_container = ctk.CTkFrame(parent, fg_color="transparent")
        main_row_container.pack(fill="x")

        content_frame = ctk.CTkFrame(main_row_container, fg_color="transparent", height=55)
        content_frame.pack(fill="x", padx=10, pady=5)
        content_frame.grid_columnconfigure(1, weight=1)

        # --- Category and Icon ---
        category_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        category_frame.grid(row=0, column=0, sticky="w", padx=(0, 15))
        category_colors = {"Groceries": self.colors["green"], "Entertainment": self.colors["pink"], "Electronics": self.colors["blue"], "Other": self.colors["orange"]}
        color = category_colors.get(expense.category, self.colors["text-tertiary"])
        ctk.CTkLabel(category_frame, text="●", font=Typography.get_font(18), text_color=color).pack(side="left", padx=(0,10))
        ctk.CTkLabel(category_frame, text=expense.category, font=Typography.BODY).pack(side="left")

        # --- Description and Date ---
        desc_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        desc_frame.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(desc_frame, text=expense.description or "No description", font=Typography.BODY, anchor="w").pack(anchor="w")
        ctk.CTkLabel(desc_frame, text=expense.date.strftime('%B %d, %Y'), font=Typography.CAPTION, text_color=self.colors["text-secondary"], anchor="w").pack(anchor="w")

        # --- Amount and Buttons ---
        actions_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=2, sticky="e", padx=(15, 5))
        ctk.CTkLabel(actions_frame, text=f"${expense.amount:.2f}", font=Typography.get_font(16, "bold"), width=90, anchor="e").pack(side="left", padx=(0,10))
        
        edit_btn = AnimatedButton(actions_frame, text="✏️", width=30, height=30, fg_color="transparent", hover_color=self.colors["warning-light"], command=lambda exp=expense: self._open_edit_window(exp))
        edit_btn.pack(side="left", padx=(4,0))
        delete_btn = AnimatedButton(actions_frame, text="🗑️", width=30, height=30, fg_color="transparent", hover_color=self.colors["error-light"], command=lambda exp_id=expense.id: self._delete_expense(exp_id))
        delete_btn.pack(side="left")
        
        # --- Separator Line ---
        ctk.CTkFrame(main_row_container, fg_color=PALETTE["border"], height=1).pack(fill="x", padx=10)

    def _open_edit_window(self, expense: Expense):
        """Opens a Toplevel window to edit an expense."""
        edit_window = ctk.CTkToplevel(self)
        edit_window.title(f"Edit Expense ID: {expense.id}")
        edit_window.geometry("400x450")
        edit_window.resizable(False, False)
        edit_window.transient(self)
        edit_window.grab_set()
        edit_window.configure(fg_color=PALETTE["bg-elevated"])

        form_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        form_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(form_frame, text="Amount", font=Typography.BODY).pack(anchor="w")
        amount_var = tk.StringVar(value=f"{expense.amount:.2f}")
        ctk.CTkEntry(form_frame, textvariable=amount_var, font=Typography.BODY).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form_frame, text="Category", font=Typography.BODY).pack(anchor="w")
        cat_var = tk.StringVar(value=expense.category)
        categories = ["Groceries", "Entertainment", "Electronics", "Other"]
        ctk.CTkOptionMenu(form_frame, variable=cat_var, values=categories).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form_frame, text="Description", font=Typography.BODY).pack(anchor="w")
        desc_var = tk.StringVar(value=expense.description or "")
        ctk.CTkEntry(form_frame, textvariable=desc_var, font=Typography.BODY).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form_frame, text="Date (YYYY-MM-DD)", font=Typography.BODY).pack(anchor="w")
        date_var = tk.StringVar(value=expense.date.strftime('%Y-%m-%d'))
        ctk.CTkEntry(form_frame, textvariable=date_var, font=Typography.BODY).pack(fill="x", pady=(0, 20))

        save_btn = AnimatedButton(form_frame, text="Save Changes", command=lambda: self._save_expense_changes(expense.id, amount_var, cat_var, desc_var, date_var, edit_window))
        save_btn.pack(pady=10)

    def _save_expense_changes(self, expense_id, amount_var, cat_var, desc_var, date_var, window):
        """Saves changes from the edit window."""
        try:
            new_data = {
                "amount": float(amount_var.get()),
                "category": cat_var.get(),
                "description": desc_var.get(),
                "date": datetime.strptime(date_var.get(), '%Y-%m-%d').date()
            }
            update_expense(expense_id, new_data)
            messagebox.showinfo("Success", "Expense updated successfully.")
            window.destroy()
            self._refresh_transaction_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update expense: {e}", parent=window)

    def _delete_expense(self, expense_id: int):
        """Confirms and deletes an expense."""
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete expense ID: {expense_id}?", icon='warning'):
            try:
                if delete_payment(expense_id):
                    messagebox.showinfo("Success", f"Expense ID {expense_id} has been deleted.")
                    self._refresh_transaction_list()
                else:
                    messagebox.showerror("Error", f"Could not find expense with ID {expense_id}.")
            except Exception as e:
                messagebox.showerror("Database Error", f"An error occurred: {e}")


    def _create_analytics_tab(self):
        """Creates the 'Analytics' tab."""
        # --- Header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text="Spending Analytics", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")

        # --- Separator ---
        separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=self.colors["border"])
        separator.pack(fill="x", padx=30, pady=(5, 16))

        # --- Analytics content ---
        try:
            with get_db_session() as session:
                exps = session.query(Expense).order_by(Expense.date.desc()).all()
                session.expunge_all()

            if not exps:
                self._create_empty_data_placeholder(self.content_frame, "📊", "No Expenses Recorded", "Add some expenses to see your analytics.")
                return

            total = sum(e.amount for e in exps)

            # --- Summary cards ---
            summary_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            summary_frame.pack(fill="x", padx=30, pady=16)
            for i in range(3):
                summary_frame.grid_columnconfigure(i, weight=1)

            self._create_summary_card(summary_frame, "💰", "Total Expenses", f"${total:.2f}", self.colors["purple"], 0)
            self._create_summary_card(summary_frame, "📊", "Average Transaction", f"${total/len(exps):.2f}", self.colors["blue"], 1)
            self._create_summary_card(summary_frame, "💳", "Total Transactions", str(len(exps)), self.colors["green"], 2)

            # --- Detailed analytics ---
            detail_card = GlassCard(self.content_frame)
            detail_card.pack(fill="x", padx=30, pady=(16, 0))
            detail_content = ctk.CTkFrame(detail_card, fg_color="transparent")
            detail_content.pack(padx=30, pady=30, fill="x")

            ctk.CTkLabel(detail_content, text="Spending by Category", font=Typography.HEADING_2, text_color=self.colors["text"]).pack(anchor="w", pady=(0, 16))
                
            by_category = {}
            for e in exps:
                by_category[e.category or "Other"] = by_category.get(e.category or "Other", 0) + e.amount
            
            category_colors = {"Groceries": self.colors["green"], "Electronics": self.colors["blue"], "Entertainment": self.colors["pink"], "Other": self.colors["orange"]}
            for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total * 100) if total > 0 else 0
                color = category_colors.get(cat, self.colors["text-tertiary"])
                
                cat_frame = ctk.CTkFrame(detail_content, fg_color=self.colors["bg-elevated"], corner_radius=8)
                cat_frame.pack(fill="x", pady=4)
                cat_content = ctk.CTkFrame(cat_frame, fg_color="transparent")
                cat_content.pack(fill="x", padx=16, pady=12)
                
                info_frame = ctk.CTkFrame(cat_content, fg_color="transparent")
                info_frame.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(info_frame, text=cat, font=Typography.get_font(14, "semibold"), text_color=color, anchor="w").pack(anchor="w")
                ctk.CTkLabel(info_frame, text=f"{percentage:.1f}% of total", font=Typography.CAPTION, text_color=self.colors["text-tertiary"], anchor="w").pack(anchor="w")
                
                ctk.CTkLabel(cat_content, text=f"${amount:.2f}", font=Typography.get_font(16, "bold"), text_color=self.colors["text"]).pack(side="right")

        except Exception as e:
            self._create_empty_data_placeholder(self.content_frame, "❌", "Error Loading Analytics", str(e))

    def _create_summary_card(self, parent, icon, title, value, color, column):
        """Creates a summary card for the analytics tab."""
        card = GlassCard(parent)
        card.grid(row=0, column=column, padx=6, sticky="ew")
        card.configure(border_color=PALETTE["border-light"])
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(padx=20, pady=20)

        icon_bg = ctk.CTkFrame(content, width=40, height=40, fg_color=PALETTE["bg-elevated"], corner_radius=8)
        icon_bg.pack(pady=(0, 8))
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text=icon, font=Typography.get_font(20, "normal")).pack(expand=True)
        
        ctk.CTkLabel(content, text=title, font=Typography.CAPTION, text_color=self.colors["text-secondary"]).pack()
        ctk.CTkLabel(content, text=value, font=Typography.get_font(20, "bold"), text_color=self.colors["text"]).pack(pady=(4, 0))

    def _create_ai_insights_tab(self):
        """Creates the 'AI Insights' tab."""
        # --- Header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text="AI Financial Insights", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")

        # --- Separator ---
        separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=self.colors["border"])
        separator.pack(fill="x", padx=30, pady=(5, 16))

        # --- Main container ---
        main_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=30)
        main_container.grid_columnconfigure((0, 1), weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        # --- Left column: Primary insights ---
        left_card = GlassCard(main_container)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        FinancialInsightsWidget(left_card).pack(fill="both", expand=True, padx=16, pady=16)

        # --- Right column: Additional analytics ---
        right_card = GlassCard(main_container)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        ctk.CTkLabel(right_card, text="Monthly Spending Trends", font=Typography.HEADING_2, text_color=self.colors["text"]).pack(padx=20, pady=(20, 16), anchor="w")
        self._create_spending_prediction(right_card)
        self._create_category_recommendations(right_card)
    
    def _create_spending_prediction(self, parent):
        """Creates the spending prediction widget."""
        pred_frame = ctk.CTkFrame(parent, fg_color=self.colors["bg-elevated"], corner_radius=12)
        pred_frame.pack(fill="x", padx=20, pady=(0, 16))
        content = ctk.CTkFrame(pred_frame, fg_color="transparent")
        content.pack(padx=20, pady=20, fill="x")
        ctk.CTkLabel(content, text="📈 Spending Forecast", font=Typography.HEADING_3, text_color=self.colors["text"]).pack(anchor="w", pady=(0, 12))
        
        try:
            with get_db_session() as session:
                now = datetime.now()
                month_start = datetime(now.year, now.month, 1)
                expenses = session.query(Expense).filter(Expense.date >= month_start).all()
                session.expunge_all()
            
            total_spent = sum(e.amount for e in expenses)
            days_passed = (now - month_start).days + 1
            
            if days_passed > 0 and total_spent > 0:
                daily_avg = total_spent / days_passed
                projected = daily_avg * 30
                ctk.CTkLabel(content, text=f"Current daily average: ${daily_avg:.2f}", font=Typography.BODY, text_color=self.colors["text-secondary"]).pack(anchor="w", pady=2)
                ctk.CTkLabel(content, text=f"Projected monthly total: ${projected:.2f}", font=Typography.get_font(16, "bold"), text_color=self.colors["warning"] if projected > 2000 else self.colors["success"]).pack(anchor="w", pady=2)
            else:
                ctk.CTkLabel(content, text="No data yet this month.", font=Typography.BODY, text_color=self.colors["text-tertiary"]).pack(anchor="w")
        except Exception as e:
            print(f"Error calculating prediction: {e}")
    
    def _create_category_recommendations(self, parent):
        """Creates the category spending recommendations widget."""
        rec_frame = ctk.CTkFrame(parent, fg_color=self.colors["bg-elevated"], corner_radius=12)
        rec_frame.pack(fill="x", padx=20, pady=(0, 20))
        content = ctk.CTkFrame(rec_frame, fg_color="transparent")
        content.pack(padx=20, pady=20, fill="x")
        ctk.CTkLabel(content, text="💡 Recommendations", font=Typography.HEADING_3, text_color=self.colors["text"]).pack(anchor="w", pady=(0, 12))
        
        recommendations = [
            ("🛒", "Consider reducing grocery spending by 10%", self.colors["green"]),
            ("🎮", "Entertainment budget is on track", self.colors["pink"]),
            ("💾", "You're saving well this month!", self.colors["success"])
        ]
        for icon, text, color in recommendations:
            rec_item = ctk.CTkFrame(content, fg_color="transparent")
            rec_item.pack(fill="x", pady=4)
            ctk.CTkLabel(rec_item, text=icon, font=Typography.get_font(14)).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(rec_item, text=text, font=Typography.BODY, text_color=color, anchor="w").pack(side="left", fill="x", expand=True)

    def _create_budget_tab(self):
        """Creates the 'Budget Management' tab."""
        # --- Header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text="Budget Management", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")

        # --- Separator ---
        separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=self.colors["border"])
        separator.pack(fill="x", padx=30, pady=(5, 16))

        # --- Budget form ---
        budget_card = GlassCard(self.content_frame)
        budget_card.pack(fill="x", padx=30, pady=16)
        budget_content = ctk.CTkFrame(budget_card, fg_color="transparent")
        budget_content.pack(padx=40, pady=40, fill="x")

        current = get_budget() or {}

        # --- Total budget ---
        ctk.CTkLabel(budget_content, text="Total Monthly Budget", font=Typography.HEADING_2, text_color=self.colors["text"]).pack(anchor="w", pady=(0, 8))
        self.total_budget_var = tk.StringVar(value=str(current.get("total", 2000.0)))
        total_entry = ctk.CTkEntry(
            budget_content, textvariable=self.total_budget_var, width=300, height=44, font=Typography.get_font(16, "normal"),
            fg_color=self.colors["input"], border_color=self.colors["border"], corner_radius=8
        )
        total_entry.pack(anchor="w", pady=(0, 30))

        # --- Category budgets ---
        ctk.CTkLabel(budget_content, text="Category Budgets", font=Typography.HEADING_2, text_color=self.colors["text"]).pack(anchor="w", pady=(0, 16))
        self.category_budget_vars = {}
        categories = [
            ("Groceries", "groceries", 600.0, self.colors["green"]), ("Entertainment", "entertainment", 300.0, self.colors["pink"]),
            ("Electronics", "electronics", 500.0, self.colors["blue"]), ("Other", "other", 200.0, self.colors["orange"])
        ]
        for display_name, key, default, color in categories:
            cat_frame = ctk.CTkFrame(budget_content, fg_color="transparent")
            cat_frame.pack(fill="x", pady=6)
            
            label_frame = ctk.CTkFrame(cat_frame, fg_color="transparent")
            label_frame.pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(label_frame, width=10, height=10, fg_color=color, corner_radius=5).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(label_frame, text=display_name, font=Typography.get_font(13, "medium"), text_color=self.colors["text"]).pack(side="left")
            
            var = tk.StringVar(value=str(current.get(key, default)))
            self.category_budget_vars[key] = var
            entry = ctk.CTkEntry(
                cat_frame, textvariable=var, width=180, height=36, font=Typography.get_font(13, "normal"),
                fg_color=self.colors["input"], border_color=self.colors["border"], corner_radius=6
            )
            entry.pack(side="right")
        
        # --- Info Tip ---
        info_frame = ctk.CTkFrame(budget_content, fg_color=PALETTE["bg-elevated"], corner_radius=8)
        info_frame.pack(fill="x", pady=(24, 30))
        info_content = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_content.pack(padx=16, pady=12)
        ctk.CTkLabel(info_content, text="💡", font=Typography.get_font(16, "normal")).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(info_content, text="Tip: Set 0 to disable budget limit for a category", font=Typography.BODY, text_color=self.colors["info"]).pack(side="left")
        
        # --- Save button ---
        save_budget_btn = AnimatedButton(
            budget_content, text="💾 Save Budget Settings", width=240, height=44, command=self._save_budget_settings,
            fg_color=self.colors["success"], hover_color=self.colors["success-light"], font=Typography.get_font(14, "bold"), corner_radius=8
        )
        save_budget_btn.pack(anchor="w")

    def _create_currency_tab(self):
        """Creates the 'Currency Converter' tab."""
        # --- Header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text="Currency Converter", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")

        # --- Separator ---
        separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=self.colors["border"])
        separator.pack(fill="x", padx=30, pady=(5, 16))

        # --- Converter card ---
        converter_card = GlassCard(self.content_frame)
        converter_card.pack(fill="x", padx=30, pady=16)
        content = ctk.CTkFrame(converter_card, fg_color="transparent")
        content.pack(padx=40, pady=40)
        
        # --- Amount Input ---
        ctk.CTkLabel(content, text="Amount to convert", font=Typography.get_font(16, "semibold"), text_color=self.colors["text"]).pack(anchor="w", pady=(0, 8))
        self.amount_var = tk.StringVar(value="1.0")
        amount_entry = ctk.CTkEntry(content, textvariable=self.amount_var, width=350, height=44, font=Typography.get_font(16, "normal"), fg_color=self.colors["input"], border_color=self.colors["border"], corner_radius=8)
        amount_entry.pack(anchor="w", pady=(0, 24))
        amount_entry.bind("<KeyRelease>", lambda *_: self._update_conversion())
        
        # --- Currency Selection ---
        ctk.CTkLabel(content, text="Select currencies", font=Typography.get_font(16, "semibold"), text_color=self.colors["text"]).pack(anchor="w", pady=(0, 12))
        currency_frame = ctk.CTkFrame(content, fg_color="transparent")
        currency_frame.pack(anchor="w", pady=(0, 30))
        
        currencies = ["USD", "EUR", "GBP", "MXN", "JPY", "CAD"]
        self.from_var, self.to_var = tk.StringVar(value="USD"), tk.StringVar(value="EUR")
        
        from_frame = ctk.CTkFrame(currency_frame, fg_color="transparent")
        from_frame.pack(side="left", padx=(0, 24))
        ctk.CTkLabel(from_frame, text="From", font=Typography.get_font(12, "medium"), text_color=self.colors["text-secondary"]).pack(pady=(0, 6))
        ctk.CTkOptionMenu(from_frame, variable=self.from_var, values=currencies, width=150, height=40, fg_color=self.colors["accent"], font=Typography.get_font(14, "medium"), dropdown_font=Typography.BODY, command=lambda *_: self._update_conversion(), corner_radius=8).pack()
        
        swap_btn = AnimatedButton(currency_frame, text="⇄", width=40, height=40, fg_color=self.colors["gray-700"], hover_color=self.colors["gray-600"], font=Typography.get_font(18, "normal"), command=self._swap_currencies, corner_radius=20)
        swap_btn.pack(side="left", padx=12, pady=(16, 0))
        
        to_frame = ctk.CTkFrame(currency_frame, fg_color="transparent")
        to_frame.pack(side="left")
        ctk.CTkLabel(to_frame, text="To", font=Typography.get_font(12, "medium"), text_color=self.colors["text-secondary"]).pack(pady=(0, 6))
        ctk.CTkOptionMenu(to_frame, variable=self.to_var, values=currencies, width=150, height=40, fg_color=self.colors["accent"], font=Typography.get_font(14, "medium"), dropdown_font=Typography.BODY, command=lambda *_: self._update_conversion(), corner_radius=8).pack()
        
        # --- Results ---
        results_frame = ctk.CTkFrame(content, fg_color=self.colors["bg-elevated"], corner_radius=12)
        results_frame.pack(fill="x", pady=24)
        results_content = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_content.pack(padx=24, pady=24)
        self.result_lbl = ctk.CTkLabel(results_content, text="", font=Typography.get_font(22, "bold"), text_color=self.colors["text"])
        self.result_lbl.pack()
        self.rate_lbl = ctk.CTkLabel(results_content, text="", font=Typography.BODY, text_color=self.colors["text-secondary"])
        self.rate_lbl.pack(pady=(6, 0))
        
        # --- Initial conversion ---
        self._update_conversion()

    def _create_contact_tab(self):
        """Creates the 'About & Contact' tab."""
        # --- Header ---
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(20, 5))
        ctk.CTkLabel(header_frame, text="About & Contact", font=Typography.DISPLAY, text_color=self.colors["text"]).pack(side="left")

        # --- Separator ---
        separator = ctk.CTkFrame(self.content_frame, height=1, fg_color=self.colors["border"])
        separator.pack(fill="x", padx=30, pady=(5, 16))
        
        # --- Main scrollable frame ---
        scroll_frame = ctk.CTkScrollableFrame(
            self.content_frame, fg_color="transparent",
            scrollbar_button_color=self.colors["accent"],
            scrollbar_button_hover_color=self.colors["accent-hover"]
        )
        scroll_frame.pack(fill="both", expand=True, padx=10)

        # --- About Card ---
        about_card = GlassCard(scroll_frame)
        about_card.pack(fill="x", padx=20, pady=(16, 12))
        about_content = ctk.CTkFrame(about_card, fg_color="transparent")
        about_content.pack(padx=40, pady=40)
        
        title_frame = ctk.CTkFrame(about_content, fg_color="transparent")
        title_frame.pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(title_frame, text="💰", font=Typography.get_font(30, "normal")).pack(side="left", padx=(0, 12))
        title_text_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_text_frame.pack(side="left")
        ctk.CTkLabel(title_text_frame, text="AI Budget Tracker", font=Typography.HEADING_1, text_color=self.colors["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_text_frame, text="Version 2.5", font=Typography.BODY, text_color=self.colors["text-secondary"], anchor="w").pack(anchor="w")
        
        ctk.CTkLabel(about_content, text="A modern budget management application with AI integration and a visual design.", font=Typography.BODY_LARGE, text_color=self.colors["text-secondary"], wraplength=500, anchor="w").pack(anchor="w", pady=(20, 24))
        
        # --- Features Grid ---
        features_frame = ctk.CTkFrame(about_content, fg_color="transparent")
        features_frame.pack(fill="x")
        features = [("🎨", "Modern Design", "Dark theme with animations"), ("🤖", "AI Assistant", "Natural language expense tracking"), ("📊", "Analytics", "Visual insights into spending"), ("💱", "Currency", "Real-time conversion"), ("📂", "Import", "Bank statement support"), ("🎯", "Budgeting", "Category management")]
        for i in range(2): features_frame.grid_columnconfigure(i, weight=1)
        for idx, (icon, title, desc) in enumerate(features):
            feature_card = ctk.CTkFrame(features_frame, fg_color=self.colors["bg-elevated"], corner_radius=8)
            feature_card.grid(row=idx//2, column=idx%2, padx=6, pady=6, sticky="ew")
            feature_content = ctk.CTkFrame(feature_card, fg_color="transparent")
            feature_content.pack(padx=16, pady=16)
            ctk.CTkLabel(feature_content, text=f"{icon} {title}", font=Typography.get_font(13, "semibold"), text_color=self.colors["text"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(feature_content, text=desc, font=Typography.CAPTION, text_color=self.colors["text-tertiary"], anchor="w", wraplength=200).pack(anchor="w", pady=(3, 0))
        
        # --- Developer Info Card ---
        dev_card = GlassCard(scroll_frame)
        dev_card.pack(fill="x", padx=20, pady=12)
        dev_content = ctk.CTkFrame(dev_card, fg_color="transparent")
        dev_content.pack(padx=40, pady=30)
        ctk.CTkLabel(dev_content, text="👨‍💻 Developer Information", font=Typography.HEADING_2, text_color=self.colors["text"]).pack(anchor="w", pady=(0, 16))
        contact_info = [("Created by:", "Angel Jaen"), ("Email:", "anlujaen@gmail.com"), ("GitHub:", "github.com/anlujaen/ai-budget-tracker"), ("License:", "MIT License")]
        for label, value in contact_info:
            info_frame = ctk.CTkFrame(dev_content, fg_color="transparent")
            info_frame.pack(fill="x", pady=3)
            ctk.CTkLabel(info_frame, text=label, font=Typography.get_font(12, "medium"), text_color=self.colors["text-secondary"], width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(info_frame, text=value, font=Typography.BODY, text_color=self.colors["text"], anchor="w").pack(side="left", padx=(12, 0))

    # ──────────────────────── HELPER METHODS ────────────────────────

    def _prompt_dashboard_refresh(self):
        """Asks the user if they want to refresh the dashboard after a database update."""
        if messagebox.askyesno("Refresh Dashboard?", "The database has been updated. Would you like to refresh the dashboard to see the changes?\n\n(Note: The current AI chat session will be cleared.)"):
            self.show_tab("Dashboard")

    def get_expenses_by_month_for_chart(self):
        """Gets expense totals for the first 6 months of the current year for charts."""
        try:
            with get_db_session() as session:
                exps = session.query(Expense).all()
                session.expunge_all()

            totals = [0] * 6
            for e in exps:
                if e.date and e.date.year == datetime.now().year and e.date.month <= 6:
                    totals[e.date.month - 1] += e.amount
            return totals
        except Exception as e:
            print(f"Error getting expenses by month: {e}")
            return [0] * 6

    def get_expenses_by_category_for_chart(self):
        """Gets expense totals for each category for charts."""
        try:
            with get_db_session() as session:
                exps = session.query(Expense).all()
                session.expunge_all()

            totals = {"Groceries": 0, "Electronics": 0, "Entertainment": 0, "Other": 0}
            for e in exps:
                cat = e.category.capitalize() if e.category in totals else "Other"
                totals[cat] += e.amount
            return list(totals.values())
        except Exception as e:
            print(f"Error getting expenses by category: {e}")
            return [0] * 4

    def _append_dashboard_chat(self, role: str, text: str):
        """Adds a message to the dashboard chat display."""
        if not self.dashboard_chatbox or not self.dashboard_chatbox.winfo_exists(): return

        self.dashboard_chatbox.configure(state="normal")
        if self.dashboard_chatbox.get("1.0", "end-1c").strip():
            self.dashboard_chatbox.insert("end", "\n\n")

        prefix = "You" if role == "user" else "AI"
        self.dashboard_chatbox.insert("end", f"[{datetime.now().strftime('%H:%M')}] {prefix}\n", f"{role}_header")
        self.dashboard_chatbox.insert("end", text, role)
        self.dashboard_chatbox.configure(state="disabled")
        self.dashboard_chatbox.see("end")

    def _send_dashboard_message(self):
        """Sends a message from the dashboard chat input."""
        msg = self.dashboard_msg_var.get().strip()
        if not msg:
            return

        self.dashboard_msg_var.set("")
        self._append_dashboard_chat("user", msg)
        self.dashboard_chat_history.append(("user", msg))
        
        self.dashboard_send_btn.configure(state="disabled", text="...")

        def process():
            try:
                reply = chat_completion(self.dashboard_chat_history)
                self.dashboard_chat_history.append(("assistant", reply.get("content", "Done.")))

                if reply["type"] == "function_call":
                    result = self._execute_ai_function(reply["name"], reply["arguments"])
                    self.after(10, self._append_dashboard_chat, "assistant", result)
                else:
                    self.after(10, self._append_dashboard_chat, "assistant", reply["content"])
            except Exception as e:
                err_msg = f"❌ Sorry, I encountered an error: {e}"
                self.after(10, self._append_dashboard_chat, "assistant", err_msg)
            finally:
                self.after(100, self.dashboard_send_btn.configure, {"state": "normal", "text": "Send"})
        
        threading.Thread(target=process, daemon=True).start()

    def _save_expense(self):
        """Saves an expense from the 'Add Expense' tab."""
        try:
            raw = self.expense_amount_var.get().strip()
            if not raw:
                messagebox.showwarning("Invalid Input", "Please enter an amount.")
                return
            amount = float(raw.replace(',', '.'))
            if not (0 < amount <= 1_000_000):
                raise ValueError("Amount must be positive and not excessively large.")
            
            add_expense(amount, self.expense_cat_var.get(), self.expense_desc_var.get().strip()[:200])
            messagebox.showinfo("Success", f"Expense of ${amount:.2f} recorded successfully!")
            self._clear_expense_form()
            self._prompt_dashboard_refresh()
            
        except ValueError as e:
            messagebox.showwarning("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save expense: {str(e)}")

    def _clear_expense_form(self):
        """Clears the fields in the 'Add Expense' form."""
        if self.expense_amount_var: self.expense_amount_var.set("")
        if self.expense_cat_var: self.expense_cat_var.set("Groceries")
        if self.expense_desc_var: self.expense_desc_var.set("")

    def _save_budget_settings(self):
        """Saves the budget settings from the 'Set Budget' tab."""
        try:
            data = {"total": float(self.total_budget_var.get().strip().replace(",", ".") or 0.0)}
            if data["total"] < 0: raise ValueError("Total budget cannot be negative.")
            
            for key, var in self.category_budget_vars.items():
                data[key] = float(var.get().strip().replace(",", ".") or 0.0)
                if data[key] < 0: raise ValueError(f"Budget for {key} cannot be negative.")
            
            save_budget(data)
            messagebox.showinfo("Success", "Budget limits updated successfully!")

        except ValueError as e: messagebox.showerror("Invalid Input", str(e))
        except Exception as e: messagebox.showerror("Error", f"Failed to save budget: {str(e)}")

    def _update_conversion(self):
        """Updates the currency conversion display."""
        if not all([hasattr(self, attr) and getattr(self, attr) for attr in ['amount_var', 'result_lbl', 'rate_lbl']]):
            return
        try:
            amount_str = self.amount_var.get().strip()
            if not amount_str:
                self.result_lbl.configure(text="Enter an amount")
                self.rate_lbl.configure(text="")
                return

            amount, from_c, to_c = float(amount_str.replace(',', '')), self.from_var.get(), self.to_var.get()
            
            if from_c == to_c:
                converted, rate = amount, 1.0
            else:
                rate = get_exchange_rate(from_c, to_c)
                converted = (amount * rate) if rate is not None else None
            
            if converted is None:
                self.result_lbl.configure(text="Conversion unavailable", text_color=PALETTE["error"])
                self.rate_lbl.configure(text="Check internet or API key")
            else:
                self.result_lbl.configure(text=f"{amount:,.2f} {from_c} = {converted:,.2f} {to_c}", text_color=PALETTE["text"])
                self.rate_lbl.configure(text=f"1 {from_c} = {rate:.4f} {to_c}")

        except ValueError:
            self.result_lbl.configure(text="❌ Invalid amount", text_color=PALETTE["error"])
            self.rate_lbl.configure(text="Please enter a valid number.")
        except Exception as e:
            print(f"Conversion error: {e}")
            self.result_lbl.configure(text="❌ Error", text_color=PALETTE["error"])
            self.rate_lbl.configure(text="An unexpected error occurred.")

    def _swap_currencies(self):
        """Swaps the 'from' and 'to' currencies and updates the conversion."""
        old_from = self.from_var.get()
        self.from_var.set(self.to_var.get())
        self.to_var.set(old_from)
        self._update_conversion()

    def _import_bank_statement(self):
        """Opens a file dialog to import a bank statement."""
        filetypes = [("CSV files", "*.csv")]
        if PDF_SUPPORT: filetypes.append(("PDF files", "*.pdf"))
        filetypes.append(("All files", "*.*"))
        
        file_path = filedialog.askopenfilename(title="Select Bank Statement", filetypes=filetypes)
        if not file_path: return

        self._append_dashboard_chat("user", f"Importing: {os.path.basename(file_path)}")
        try:
            if file_path.lower().endswith(".csv"):
                result = load_bank_statement_csv(file_path)
            elif file_path.lower().endswith(".pdf") and PDF_SUPPORT:
                result = load_bank_statement_pdf(file_path)
            else:
                raise ValueError("Unsupported file format. Please use CSV or PDF.")
            
            if result.get("imported", 0) > 0:
                self._append_dashboard_chat("assistant", f"✅ Import successful!\nImported: {result['imported']} | Failed: {result.get('failed', 0)}")
                self._prompt_dashboard_refresh()
            else:
                error_list = result.get('errors', ['N/A'])
                self._append_dashboard_chat("assistant", f"❌ No valid expenses found in the file.\nErrors: {error_list[0]}")

        except Exception as e:
            self._append_dashboard_chat("assistant", f"❌ Import error: {e}")

    def _execute_ai_function(self, name: str, args: dict) -> str:
        """Executes a function call made by the AI."""
        try:
            if name == "insert_payment":
                insert_payment(**args)
                self.after(100, self._prompt_dashboard_refresh)
                desc = f" ({args['description']})" if args.get("description") else ""
                return f"✅ Expense recorded: ${args['amount']} for {args['category']}{desc}"
            
            elif name == "delete_payment":
                if delete_payment(**args):
                    self.after(100, self._prompt_dashboard_refresh)
                    return f"✅ Expense #{args['expense_id']} deleted."
                return f"❌ Expense #{args['expense_id']} not found."

            elif name == "query_expenses_by_category":
                total = query_expenses_by_category(**args)
                return f"💰 Total spent on {args['category']}: ${total:.2f}"

            elif name == "list_expenses_by_category":
                expenses = list_expenses_by_category(args['category'])
                if not expenses: return f"No expenses found for {args['category']}."
                lines = [f"💵 Expenses in {args['category'].capitalize()}:"] + [f" • ID: {e['id']} | ${e['amount']:.2f} on {e['date']} | {e['description']}" for e in expenses[:10]]
                if len(expenses) > 10: lines.append(f" • ... and {len(expenses) - 10} more.")
                return "\n".join(lines)
            
            return f"❌ Unknown function: {name}"
        except Exception as e:
            return f"❌ Error executing {name}: {e}"

if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()