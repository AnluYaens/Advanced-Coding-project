import tkinter as tk
from tkinter import messagebox, filedialog
import os
import traceback

import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.interpolate import PchipInterpolator
from datetime import datetime

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

# Import bank statement loaders
from src.services.bank_statement_loader import load_bank_statement_csv

# PDF support toggle 
PDF_SUPPORT = False
try:
    from src.services.bank_statement_loader_pdf import load_bank_statement_pdf
    PDF_SUPPORT = True
except ImportError:
    print("Warning: bank_statement_loader_pdf not available")
    
# ───────────────────────────────── THEME HANDLING ─────────────────────────
# Define ALL hex colors in a single dictionary
PALETTE = {
    "bg": "#1e1b2e",      # general background (dark violet)
    "card": "#2d235f",    # card/frame background
    "accent": "#6d28d9",  # highlight color (buttons, lines)
    "hover": "#7c3aed",   # hover color
    "text": "#f9fafb",    # main text (almost white)
    "error": "#ef4444",   # error color
    "success": "#10b981", # success color
    "warning": "#f59e0b", # warning color
}

# Global CustomTkinter config
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BudgetApp(ctk.CTk):
    """Main budget application window."""

    def __init__(self):
        super().__init__()
        self.title("AI Budget Tracker")
        self.geometry("820x920")
        self.resizable(False, False)

        # ---- Palette accessible throughout the instance ----
        self.colors = PALETTE.copy()
        # Short aliases
        self.bg       = self.colors["bg"]
        self.card_bg  = self.colors["card"]
        self.accent   = self.colors["accent"]
        self.hover    = self.colors["hover"]
        self.text     = self.colors["text"]

        # Window background
        self.configure(fg_color=self.bg)
        
        # Save references to main sections
        self.main_sections = {}
        
        # Build UI
        self._create_top_tabs()
        self._create_header()
        self._create_charts_section()
        self._create_converter_section()

     # ─────────────────────────── DATABASE HELPERS ────────────────────────────
    def get_expenses_by_month(self):
        """Get expense totals for each month of the current year"""
        try:
            with get_db_session() as session:
                exps = session.query(Expense).all()
                session.expunge_all()  # Detach from session

            current_year = datetime.now().year
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            totals = [0] * len(months)
            
            for e in exps:
                if e.date:
                    # Filter by current year without using extract
                    if e.date.year == current_year:
                        month_abbr = e.date.strftime('%b')
                        if month_abbr in months:
                            idx = months.index(month_abbr)
                            totals[idx] += e.amount        
            return totals  # <- NO slicing aquí
        except Exception as e:
            print(f"Error getting expenses by month: {e}")
            return [0] * 6

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
                    # Put uncategorized in "Other"
                    totals[cats.index("Other")] += e.amount
                    
            return totals
        except Exception as e:
            print(f"Error getting expenses by category: {e}")
            return [0] * 4

    # ---- Top bar ----
    def _create_top_tabs(self):
        """Create the top navigation bar with buttons"""
        bar = ctk.CTkFrame(self, fg_color=self.card_bg, height=40)
        bar.pack(fill="x")
        
        self.main_sections['top_bar'] = bar

        contact_btn = ctk.CTkButton(
            bar, 
            text="📧 Contact",
            width=80,
            font=("Arial", 16, "bold"),
            fg_color=self.card_bg,
            hover_color=self.hover,
            text_color=self.text,
            command=self.show_contact,
        )
        contact_btn.place(relx=0.02, rely=0.5, anchor="w")

        ai_btn = ctk.CTkButton(
            bar,
            text="🤖 AI Assistant",
            width=110,
            font=("Arial", 16, "bold"),
            fg_color=self.card_bg,
            hover_color=self.hover,
            text_color=self.text,
            command=self.open_ai_assistant,
        )
        ai_btn.place(relx=0.98, rely=0.5, anchor="e")

    # ─────────────────────── HEADER + NAVIGATION ───────────────────────────────
    def _create_header(self):
        """Create the main header with title and action buttons"""
        header = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=12)
        header.pack(pady=20, padx=60, fill="x")
        
        self.main_sections['header'] = header

        ctk.CTkLabel(
            header, 
            text="📊 Budget Assistant", 
            font=("Arial",32,"bold"), 
            text_color=self.text
        ).pack(pady=(20,10))

        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(pady=(0,20))

        for i,(label,cmd) in enumerate([
            ("Add Expense", self.add_expense),
            ("Spending Analysis", self.view_summary),
            ("Set Budget", self.set_budget),
        ]):
            ctk.CTkButton(
                btns, text=label, command=cmd,
                width=200, height=50,
                fg_color=self.card_bg,
                hover_color=self.hover,
                text_color=self.text, 
                font=("Arial",16, "bold"), 
                corner_radius=12
            ).grid(row=0, column=i, padx=20)

    # ────────────────────── Charts Section ─────────────────────────
    def _create_charts_section(self):
        """Create (or recreate) the charts display area and keep it in place"""
        # --- Main container ---
        sec = ctk.CTkFrame(
            self, 
            fg_color=self.bg, 
            corner_radius=12, 
            border_width=2, 
            border_color=self.accent
        )

        # --- (Packing) -> always insert just before the 'coverter' frame ---
        converter = self.main_sections.get("converter")
        if converter and converter.winfo_exists():
            # Insert before converter so the visual order never change
            sec.pack(pady=10, padx=60, fill="x", before=converter)
        else:
            # Initial creation (converter doesnt exist yet)
            sec.pack(pady=10, padx=60, fill="x")
        
        # Store references in sections dictionary
        self.main_sections['charts'] = sec
        
        # --- Chart titles ---
        trow = ctk.CTkFrame(sec, fg_color="transparent")
        trow.pack(fill="x", padx=20, pady=(20,0))

        ctk.CTkLabel(
            trow, 
            text="Expense Chart", 
            font=("Arial",20,"bold"), 
            text_color=self.text
        ).pack(side="left")

        ctk.CTkLabel(
            trow, 
            text="By category", 
            font=("Arial",20,"bold"), 
            text_color=self.text
        ).pack(side="right")
        
       # ---- Charts row ----
        crow = ctk.CTkFrame(sec, fg_color="transparent")
        crow.pack(fill="x", padx=20, pady=20)

        left = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        left.pack(side="left", expand=True, fill="both", padx=10)

        right = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        right.pack(side="right", expand=True, fill="both", padx=10)

        # --- Draw the charts (helper functions) ---
        self.show_line_chart(left)
        self.show_donut_chart(right)


    # ───────────────────────── LINE CHART ───────────────────────────────
    def show_line_chart(self, parent):
        """Display line chart showing expenses by month"""
        try:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            data = self.get_expenses_by_month()
            x = np.arange(len(months))
            
            # --- Y axis range ---
            max_val = max(data) if any(data) else 1
            y_top = max(100, round(max_val * 1.25))  # Minimum 100 for better visualization


            # --- Prepare figure ---
            fig, ax = plt.subplots(figsize=(5, 3.2), dpi=100)
            fig.patch.set_facecolor(self.card_bg)
            ax.set_facecolor(self.card_bg)

            # --- Draw line/curve ---
            if len(set(data)) > 1 and sum(data) > 0:
                # Smooth curve if we have varying data
                x_smooth = np.linspace(x.min(), x.max(), 300)
                y_smooth = PchipInterpolator(x, data)(x_smooth)

                ax.plot(
                    x_smooth, y_smooth,
                    color=self.accent,
                    linewidth=2.5,
                    solid_capstyle='round',
                    zorder=1,
                )
            else:
                # Simple line if data is uniform or zero
                ax.plot(
                    x, data,
                    color=self.accent,
                    linewidth=2.5,
                    marker="o",
                    markersize=6,
                    markerfacecolor=self.accent,
                    markeredgewidth=1.5,
                    markeredgecolor='white',
                    zorder=1,
                )

            # Points & labels (only if > 0)
            for xi, val in zip(x, data):
                if val > 0:
                    # point
                    ax.scatter(
                        xi, val,
                        color=self.accent,
                        edgecolors='white',
                        s=60,
                        linewidth=1.5,
                        zorder=3
                    )
                    # label
                    ax.text(
                        xi, val + y_top * 0.03,
                        f"${val:,.0f}",
                        fontsize=9,
                        color=self.text,
                        ha='center',
                        va='bottom',
                        fontweight='bold'
                    )

            # Axes configuration
            ax.set_xlim(-0.4, len(months) - 0.6) 
            ax.set_ylim(0, y_top)
            ax.set_xticks(x)
            ax.set_xticklabels(
                months, 
                color=self.text, 
                fontsize=10, 
                fontweight="bold"
            )
            ax.tick_params(axis='y', colors=self.text, labelsize=10)

            # --- Grid ---
            ax.grid(
                axis='y', linestyle='--', linewidth=0.5, color='#43337a', alpha=0.5
            )
            for spine in ax.spines.values():
                spine.set_visible(False)

            # --- Layout ---
            ax.margins(x=0.02)          
            fig.tight_layout(pad=1) # prevents cutting inside the card

            # --- Insert into widget ---
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=10, pady=10)

            # --- Close figure to prevent memory leak --- (Important to remember)
            plt.close(fig)

        except Exception as e:
            print(f"Error creating line chart: {e}")
            # Show error message in the chart area
            error_label = ctk.CTkLabel(
                parent,
                text="Error loading chart",
                font=("Arial", 14),
                text_color=self.colors["error"]
            )
            error_label.pack(expand=True)      

    #  ───────────────────────── Donut CHART ───────────────────────────────
    def show_donut_chart(self, parent):
        """Display donut chart showing expenses by category"""
        try:
            categories = ["Groceries", "Electronics", "Entertainment", "Other"]
            vals = self.get_expenses_by_category()

            # --- Clean data ---
            vals = [max(0, v) for v in vals]  # Ensure no negative values
            total = sum(vals)

            if total == 0:
                # Show "no data" message
                no_data_frame = ctk.CTkFrame(parent, fg_color="transparent")
                no_data_frame.pack(expand=True)

                ctk.CTkLabel(
                    no_data_frame,
                    text="No expenses to display",
                    text_color=self.text,
                    font=("Arial", 16)
                ).pack()
                
                ctk.CTkLabel(
                    no_data_frame,
                    text="Add some expenses to see the breakdown",
                    text_color="#888",
                    font=("Arial", 12)
                ).pack(pady=(5, 0))
                return

            # --- Custom colors --- 
            colors = [
                "#7c3aed",  # strong purple
                "#8b5cf6",  # light violet
                "#a78bfa",  # lavender
                "#ddd6fe",  # pastel
            ][:len(vals)]

            # --- Create figure ---
            fig, (ax1, ax2) = plt.subplots(
                2, 1,
                figsize=(4.5, 4.3),
                dpi=100,
                gridspec_kw={'height_ratios': [3.2, 1.2]}
            )
            fig.patch.set_facecolor(self.card_bg)
            ax1.set_facecolor(self.card_bg)
            ax2.set_facecolor(self.card_bg)

            # --- Draw donut ---
            wedges, texts = ax1.pie(
                vals, 
                wedgeprops=dict(width=0.5), 
                startangle=90, 
                colors=colors
            )
            
            # Add center circle
            centre_circle = plt.Circle((0, 0), 0.45, fc=self.card_bg)
            ax1.add_artist(centre_circle)
            ax1.axis("equal")
            ax1.axis("off")

            # Legend
            ax2.axis("off")
            ax2.set_xlim(0, 1)
            ax2.set_ylim(0, 1)
            
            spacing = 0.25
            top_y = 1.0

            for i, (cat, val, color) in enumerate(zip(categories, vals, colors)):
                percent = (val / total * 100) if total else 0
                
                # --- Category with bullet ---
                ax2.text(
                    0.05, 
                    top_y - i * spacing,
                    f"● {cat}",
                    fontsize=11,
                    color=color,
                    ha="left",
                    va="center",
                    fontweight="bold"
                )

                # --- Amount and percentage --- 
                ax2.text(
                    0.95, 
                    top_y - i * spacing,
                    f"${val:,.0f} ({percent:.0f}%)",
                    fontsize=10,
                    color=self.text,
                    ha="right",
                    va="center",
                    fontweight="bold"
                )

            fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.2)

            # --- Display in app ---
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=10, pady=10)

            # --- Close figure ---
            plt.close(fig)
        
        except Exception as e:
            print(f"Error creating donut chart: {e}")
            traceback.print_exc()
            # Show error message
            error_label = ctk.CTkLabel(
                parent,
                text="Error loading chart",
                font=("Arial", 14),
                text_color=self.colors["error"]
            )
            error_label.pack(expand=True)

    #  ───────────────────────── Converter Section ───────────────────────────────
    def _create_converter_section(self):
        """Create currency converter section"""
        sec = ctk.CTkFrame(
            self, fg_color=self.card_bg, corner_radius=12
        )
        sec.pack(pady=25, padx=60, fill="x")
        
        self.main_sections['converter'] = sec

        ctk.CTkLabel(
            sec, text="Transfer Calculator", 
            font=("Arial",20,"bold"), 
            text_color=self.text
        ).pack(pady=(20,10))

        grid = ctk.CTkFrame(sec, fg_color="transparent")
        grid.pack(pady=10)

        # --- Amount entry ---
        ctk.CTkLabel(grid, text="Amount:", text_color=self.text).grid(
            row=0, column=0, sticky="e", padx=(0, 10)
        )
        self.amount_var = tk.StringVar(value="1.0")
        amt_entry = ctk.CTkEntry(grid, textvariable=self.amount_var, width=100)
        amt_entry.grid(row=0, column=1, sticky="w")
        amt_entry.bind("<KeyRelease>", lambda *_: self._update_conversion())

        # --- From / to currencies ---
        currs = ["USD", "EUR", "GBP", "MXN", "JPY", "CAD"]
        self.from_var = tk.StringVar(value="USD")
        self.to_var = tk.StringVar(value="EUR")

        def _trace(*_): 
            self._update_conversion()

        self.from_var.trace_add("write", _trace)
        self.to_var.trace_add("write", _trace)

        ctk.CTkLabel(grid, text="From", text_color=self.text).grid(
            row=0, column=2, padx=(20, 4)
        )
        ctk.CTkOptionMenu(
            grid, variable=self.from_var, values=currs,
            width=80,
            fg_color=self.accent,
            button_color=self.accent,
            text_color="white",
            dropdown_fg_color="#2d235f",      # dark dropdown menu
            dropdown_text_color="white"
        ).grid(row=0, column=3)

        ctk.CTkLabel(grid, text="To", text_color=self.text).grid(
            row=0, column=4, padx=(20, 4)
        )
        ctk.CTkOptionMenu(
            grid, variable=self.to_var, values=currs,
            width=80,
            fg_color=self.accent,
            button_color=self.accent,
            text_color="white",
            dropdown_fg_color="#2d235f",
            dropdown_text_color="white"
        ).grid(row=0, column=5)

        # --- Result labels ---
        self.result_lbl = ctk.CTkLabel(
            sec, text="", font=("Arial", 22, "bold"), text_color=self.text
        )
        self.rate_lbl = ctk.CTkLabel(
            sec, text="", font=("Arial", 14), text_color="#c0c0c0"
        )
        self.result_lbl.pack(pady=(12,0))
        self.rate_lbl.pack(pady=(0, 20))

        # --- Initial conversion ---
        self._update_conversion()

    def _convert_currency(self, amount: float, from_curr: str, to_curr: str):
        """Use service.currency_api.get_exchange_rate."""
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
        
    def _update_conversion(self):
        """Update the currency conversion display"""
        try:
            amount_str = self.amount_var.get().strip()

            if amount_str == "":
                self.result_lbl.configure(text="Enter an amount")
                self.rate_lbl.configure(text="")
                return
            
            try:
                amount = float(amount_str.replace(',', ''))
            except ValueError:
                self.result_lbl.configure(text="Invalid amount")
                self.rate_lbl.configure(text="Please enter a valid number")
                return
            
            from_c = self.from_var.get()
            to_c = self.to_var.get()
            converted, rate = self._convert_currency(amount, from_c, to_c)

            if rate == 0.0:
                self.result_lbl.configure(text="Conversion unavailable")
                self.rate_lbl.configure(text="check your internet connection")
                return

            self.result_lbl.configure(
                text=f"{amount:.2f} {from_c} = {converted:.2f} {to_c}"
            )
            self.rate_lbl.configure(text=f"1 {from_c} = {rate:.3f} {to_c}")

        except Exception as e:
            self.result_lbl.configure(text="Error")
            self.rate_lbl.configure(text="Please try again")
            print(f"Conversion error: {e}")

    #  ───────────────────────── More methods ───────────────────────────────
    # --- Add expense flow ---
    def add_expense(self):
        """Open add expense dialog"""
        AddExpenseDialog(self, on_saved=self._refresh_charts)

    # --- Summary popup ---
    def view_summary(self):
        """Show spending summary popup"""
        try:
            with get_db_session() as session:
                exps = session.query(Expense).order_by(Expense.date.desc()).all()
                session.expunge_all()

            if not exps: 
                messagebox.showinfo("Summary","No expenses recorded yet.")
                return
            
            total = sum(e.amount for e in exps)
            
            # Group by category
            by_category = {}
            for e in exps:
                cat = e.category or "Other"
                by_category[cat] = by_category.get(cat, 0) + e.amount

            # Build summary text
            summary_lines = [f"Total Expenses: ${total:.2f}\n"]
            summary_lines.append("By Category:")
            for cat, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total * 100) if total > 0 else 0
                summary_lines.append(f" • {cat}: ${amount:.2f} ({percentage:.1f}%)")

            summary_lines.append(f"\nRecent Expenses (last 5):")
            for e in exps[:5]:
                date_str = e.date.strftime("%m/%d") if e.date else "Unknown"
                summary_lines.append(f"  {date_str} - {e.category}: ${e.amount:.2f}")

            messagebox.showinfo("Spending Summary", "\n".join(summary_lines))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load summary: {str(e)}")

    # --- Budget Dialog ---
    def set_budget(self):
        """Open budget setting dialog"""
        BudgetDialog(self)

    # --- Contact popup ---
    def show_contact(self):
        """Show contact information popup"""
        messagebox.showinfo(
            "Contact",
            "AI Budget Tracker\n\n"
            "An advanced budget management application with AI integration.\n\n"
            "Features:\n"
            "• AI-powered expense recording\n"
            "• Visual spending analytics\n"
            "• Currency conversion\n"
            "• Bank statement import\n\n"
            "Created by: Angel Jaen\n"
            "Email: anlujaen@gmail.com\n"
            "GitHub: github.com/yourusername/budget-tracker",
        )

    # --- AI Assistant ---
    def open_ai_assistant(self):
        """Open AI chat assistant window"""
        ChatWindow(self)

    # --- Refresh Charts ---
    def _refresh_charts(self):
        """Safely refresh only the charts section"""
        try:
            # --- close all the figures before recreate ---
            plt.close('all')

            # Only destroy and recreate the charts section
            if 'charts' in self.main_sections and self.main_sections["charts"].winfo_exists():
                self.main_sections['charts'].destroy()
                del self.main_sections['charts']
            
            # Recreate only the charts
            import gc
            self._create_charts_section()
            
        except Exception as e:
            print(f"Error refreshing charts: {e}")
            traceback.print_exc()
            messagebox.showerror("Error", "Unable to refresh. Please restart.")

#  ───────────────────────── AddExpenseDialog Class ─────────────────────────────── 
class AddExpenseDialog(ctk.CTkToplevel):
    """Dialog window for adding new expenses"""
    def __init__(self, parent: BudgetApp, on_saved):
        super().__init__(parent)
        self.title("Add Expense")
        self.geometry("340x320")
        self.grab_set()
        self.resizable(False, False)
        self.on_saved = on_saved

        # --- Use parent colors ---
        self.configure(fg_color=parent.card_bg)

        # --- Amount ---
        ctk.CTkLabel(
            self, 
            text="Amount", 
            font=("Arial", 14, "bold"),
            text_color=parent.text
            ).pack(pady=(20,6))
        
        self.amount_var = tk.StringVar(value="")
        amount_entry = ctk.CTkEntry(
            self, 
            textvariable=self.amount_var, 
            width=120,
            placeholder_text="0.00"
        )
        amount_entry.pack()
        amount_entry.focus() # Auto-focus on amount

        # --- Category ---
        ctk.CTkLabel(
            self, 
            text="Category",
            text_color=parent.text
        ).pack(pady=(16, 6))

        self.cat_var = tk.StringVar(value="Groceries")
        ctk.CTkOptionMenu(
            self,
            variable=self.cat_var,
            values=["Groceries", "Electronics", "Entertainment", "Other"],
            width=200,
            fg_color=parent.accent,
            button_color=parent.accent,
        ).pack()

        # --- Description ---
        ctk.CTkLabel(
            self, 
            text="Description (optional)",
            text_color=parent.text
        ).pack(pady=(16, 6))

        self.desc_var = tk.StringVar()
        ctk.CTkEntry(
            self, 
            textvariable=self.desc_var, 
            width=220,
            placeholder_text="What did you buy?"
        ).pack()

        # --- Buttons ---
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=24)

        ctk.CTkButton(
            row, 
            text="Save", 
            width=100, 
            command=self._save,
            fg_color=parent.colors["success"],
            hover_color="#059669"
            ).grid(row=0, column=0, padx=10)
        
        ctk.CTkButton(
            row,
            text="Cancel",
            width=100,
            fg_color="#444",
            hover_color="#555",
            command=self.destroy,
            ).grid(row=0, column=1, padx=10)
        
        # Bind Enter key to save 
        self.bind('<Return>', lambda e: self._save())

    # --- Save Expenses Method---
    def _save(self):
        """Save the expense to database"""
        try:
            raw = self.amount_var.get().strip()
            
            if not raw:
                messagebox.showwarning(
                "Invalid Amount", 
                "Please enter an amount",
                parent=self
                )
                return
            # Allow input with commas and decimal points
            # E.g.: "1,234.56" -> 1234.56
            cleaned = raw.replace(',', '.')

            try:
                amount = float(cleaned)
                if amount <= 0:
                    messagebox.showwarning(
                        "Invalid Amount",
                        "Amount must be a positive number.",
                        parent=self,
                    )
                    return
                if amount > 1_000_000: 
                    messagebox.showwarning(
                        "Invalid Amount",
                        "Amount seems too large. Please verify.",
                        parent=self
                    )
                    return
            except ValueError:
                messagebox.showwarning(
                    "Invalid Amount",
                    "Please enter a valid number (e.g., 123.45)",
                    parent=self
                )
                return

            category = self.cat_var.get()
            description = self.desc_var.get().strip()

            if len(description) > 200:
                description = description[:200]
            
            # Save expense 
            add_expense(amount, category, description)

            messagebox.showinfo(
                "Saved", 
                f"Expense of ${amount:.2f} recorded successfully!",
                parent=self
            )

            self.destroy()
            self.on_saved()

        except Exception as e:
            messagebox.showerror(
                "Error", 
                f"Failed to save expense: {str(e)}",
                parent=self
            )    

# ───────────────────────────── CHAT WINDOW ───────────────────────────────────
class ChatWindow(ctk.CTkToplevel):
    """AI Assistant chat window"""
    def __init__(self, parent: BudgetApp):
        super().__init__(parent)
        self.title("AI Assistant")
        self.geometry("500x650")
        self.grab_set()
        
        # Access parent colors
        self.parent_app = parent
        self.configure(fg_color=parent.bg)

        self.history = []  # [(role, content), ...]

        # --- Header ---
        header = ctk.CTkFrame(self, fg_color=parent.card_bg, height=50)
        header.pack(fill="x", padx=10, pady=(10,0))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="🤖 AI Budget Assistant",
            font=("Arial", 18, "bold"),
            text_color=parent.text
        ).pack(expand=True)

        # --- Chat display using standard Text widget instead of CTkTextbox ---
        # This is because CTkTextbox doesn't support font in tag_config
        chat_frame = ctk.CTkFrame(self, fg_color=parent.card_bg, corner_radius=10)
        chat_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.chatbox = tk.Text(
            chat_frame,
            width=50,
            height=20,
            state="disabled",
            bg=parent.card_bg,
            fg=parent.text,
            font=("Arial", 14, "bold"),
            wrap="word",
            borderwidth=0,
            highlightthickness=0
        )
        self.chatbox.pack(padx=10, pady=10, fill="both", expand=True)

        # Configure text tags for standard Text widget
        self.chatbox.tag_config("user_header", 
                              foreground="#a78bfa",
                              font=("Arial", 12, "bold"))
        self.chatbox.tag_config("user", 
                              foreground="#c4b5fd")
        self.chatbox.tag_config("assistant_header", 
                              foreground="#60a5fa",
                              font=("Arial", 12, "bold"))
        self.chatbox.tag_config("assistant", 
                              foreground=self.parent_app.text)

        # --- Input area ---
        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.pack(pady=(0,10), fill="x", padx=10)

        # --- Import button ---
        import_btn = ctk.CTkButton(
            entry_row,
            text="📂",
            width=40,
            height=40,
            corner_radius=20,
            fg_color=parent.accent,
            hover_color=parent.hover,
            text_color="white",
            command=self._import_bank_statement,
            font=("Arial", 16, "bold")
        )
        import_btn.pack(side="left", padx=(0, 10))

        # --- Message Input ---
        self.msg_var = tk.StringVar()
        entry = ctk.CTkEntry(
            entry_row, 
            textvariable=self.msg_var,
            placeholder_text="Type your message...",
            height=40,
            corner_radius=20
        )
        entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        entry.bind("<Return>", lambda e: self._send())
        entry.focus()

        # --- Send button ---
        self.send_btn = ctk.CTkButton(
            entry_row,
            text="Send", 
            width=70,
            height=40,
            corner_radius=20,
            font=("Arial", 16, "bold"),
            fg_color=parent.accent,  
            hover_color=parent.hover, 
            text_color="white", 
            command=self._send
        )
        self.send_btn.pack(side="right")

        # Welcome message
        self._append(
            "assistant", 
            "Hello! I'm your AI budget assistant. I can help you:\n"
            "• Record expenses (e.g., 'Add $50 for groceries')\n"
            "• Check spending (e.g., 'How much did I spend on entertainment?')\n"
            "• Import bank statements (click 📎)\n\n"
            "How can I help you today?"
        )

    # --- Import Bank Statement Method ---
    def _import_bank_statement(self):
        """Import bank statement from CSV or PDF file"""
        filetypes = [("CSV files", "*.csv")]
        if PDF_SUPPORT:
            filetypes.append(("PDF files", "*.pdf"))
        filetypes.append(("All files", "*.*"))
        
        file_path = filedialog.askopenfilename(
            title="Select Bank Statement",
            filetypes=filetypes,
            parent=self
        )
        if not file_path:
            return
        
        filename = os.path.basename(file_path)
        self._append("user", f"Importing bank statement: {filename}")
        
        try:
            if file_path.lower().endswith(".csv"):
                result = load_bank_statement_csv(file_path, insert_payment)
                if isinstance(result, dict) and result.get("imported", 0) > 0:
                    self._append(
                        "assistant", 
                        f"✅ CSV imported successfully!\n"
                        f"Imported: {result['imported']} expenses\n"
                        f"Failed: {result.get('failed', 0)}"
                    )
                else:    
                    self._append("assistant", "❌ No valid expenses found in CSV")
                self.parent_app._refresh_charts()

            elif file_path.lower().endswith(".pdf"):
                if PDF_SUPPORT:
                    result = load_bank_statement_pdf(file_path, insert_payment)
                    
                    if isinstance(result, dict) and result.get("imported", 0) > 0:
                        self._append(
                            "assistant", 
                            f"✅ PDF imported successfully!\n"
                            f"Imported: {result['imported']} expenses\n"
                            f"Failed: {result.get('failed', 0)}"
                        )
                    
                    if result.get("expenses"):
                        lines = ["📄 Imported expenses:"]
                        for e in result["expenses"]:
                            date = e.date.strftime("%Y-%m-%d") if e.date else "Unknown"
                            desc = f" | {e.description}" if e.description else ""
                            lines.append(f" • ID {e.id} | ${e.amount:.2f} | {e.category} | {date}{desc}")
                        self._append("assistant", "\n".join(lines))
                        
                    else:
                        self._append("assistant", "❌ No valid expenses found in PDF")
                    
                    self.parent_app._refresh_charts()
                else:
                    self._append(
                        "assistant", 
                        "❌ PDF support is not available." 
                        "Please install pdfplumber:\n"
                        "pip install pdfplumber"
                    )
            else:
                self._append("assistant", "❌ Unsupported file format. Please use CSV or PDF files.")

        except Exception as e:
            self._append("assistant", f"❌ Error importing file: {str(e)}")
            print(f"Import error: {e}")
            traceback.print_exc()

    # --- Append Method ---
    def _append(self, role: str, text: str):
        """Add message to chat display"""
        self.chatbox.configure(state="normal")

        tag = "user" if role == "user" else "assistant"
        prefix = "You: " if role == "user" else "Assistant: "
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M")
        
        # Insert text with tags
        self.chatbox.insert("end", f"[{timestamp}] {prefix}\n", f"{tag}_header")
        self.chatbox.insert("end", f"{text}\n\n", tag)

        self.chatbox.configure(state="disabled")
        self.chatbox.see("end") # Scroll to bottom

    # --- Send Method ---
    def _send(self):
        """Send message to AI and get response"""
        msg = self.msg_var.get().strip()
        if not msg:
            return
        
        self.msg_var.set("")
        self._append("user", msg)
        self.history.append(("user", msg))

        # Disable send button while procesing
        self.send_btn.configure(state="disabled", text="...")

        try:
            reply = chat_completion(self.history)

            if reply["type"] == "text":
                # Normal response
                self.history.append(("assistant", reply["content"]))
                self._append("assistant", reply["content"])

            elif reply["type"] == "function_call":
                # Execute function
                name, args = reply["name"], reply["arguments"]
                result = self._execute_functions(name, args)
                self.history.append(("assistant", result))
                self._append("assistant", result)
        
        except Exception as e:
            err = f"❌ Sorry, I encountered an error: {e}"
            self.history.append(("assistant", err))
            self._append("assistant", err)
            traceback.print_exc()

        finally:
            # Re-enable send button
            self.send_btn.configure(state="normal", text="Send")

    # --- Execute the functions requested ---
    def _execute_functions(self, name: str, args: dict) -> str:
        """Wrapper to call domain functions safely and return a user-friendly message"""
        try:
            if name ==  "insert_payment":
                insert_payment(**args)
                self.parent_app._refresh_charts()
                desc = f" ({args['description']})" if args.get("description") else ""
                return f"✅ Expense recorded: ${args['amount']} for {args['category']}{desc}"

            elif name == "delete_payment":
                from src.core.database import delete_payment
                success = delete_payment(**args)
                if success:
                    self.parent_app._refresh_charts()
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
                for e in expenses:
                    lines.append(f" • ID: {e['id']} | ${e['amount']:.2f} on {e['date']} | {e['description']}")
                return "\n".join(lines)
            
            else:
                return f"❌ Unknown function: {name}"
        except Exception as e:
            return f"❌ Error executing {name}: {e}"

# ────────────────────────── BUDGET DIALOG ────────────────────────────────────
class BudgetDialog(ctk.CTkToplevel):
    """Dialog window for setting budget limits"""
    def __init__(self, parent: BudgetApp):
        super().__init__(parent)
        self.title("Set Budget Limits")
        self.geometry("360x450")
        self.grab_set()
        self.resizable(False, False)

        self.parent_app = parent
        self.configure(fg_color=parent.card_bg)
        
        # Get to current budgets
        current = get_budget() or {}

        # --- Title ---
        ctk.CTkLabel(
            self, 
            text="Monthly Budget Limits",
            font=("Arial", 18, "bold"),
            text_color=parent.text
        ).pack(pady=(20, 20))

        # --- Budget inputs frame ---
        inputs_frame = ctk.CTkFrame(self, fg_color="transparent")
        inputs_frame.pack(padx=20, pady=10)

        # --- Total budget ----
        ctk.CTkLabel(
            inputs_frame,
            text="Total Budget:",
            text_color=parent.text,
            font=("Arial", 14)
        ).grid(row=0, column=0, sticky="e", padx=(0,10), pady=10)

        self.total_var = tk.StringVar(value=str(current.get("total", 2000.0)))
        total_entry = ctk.CTkEntry(
            inputs_frame,
            textvariable=self.total_var,
            width=120,
            placeholder_text="0.00"
        )
        total_entry.grid(row=0, column=1, pady=10)

        # --- Category budgets ---
        self.category_vars = {}
        categories = [
            ("Groceries", "groceries", 600.0),
            ("Entertainment", "entertainment", 300.0),
            ("Electronics", "electronics", 500.0),
            ("Other", "other", 200.0)
        ]

        for i, (display_name, key, default) in enumerate(categories, start=1):
            ctk.CTkLabel(
                inputs_frame,
                text=f"{display_name}:",
                text_color=parent.text
            ).grid(row=i, column=0, sticky="e", padx=(0,10), pady=8)

            var = tk.StringVar(value=str(current.get(key, default)))
            self.category_vars[key] = var

            ctk.CTkEntry(
                inputs_frame,
                textvariable=var,
                width=120,
                placeholder_text="0.00"
            ).grid(row=i, column=1, pady=8)

        # --- Info Label ---
        info_label = ctk.CTkLabel(
            self,
            text="Set 0 to disable budget limit for a category",
            text_color="#888",
            font=("Arial", 11)
        )
        info_label.pack(pady=10)

        # --- Buttons ---
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=20)

        ctk.CTkButton(
            btn_row,
            text="Save",
            width=100,
            command=self._save,
            fg_color=parent.colors["success"],
            hover_color="#059669"
        ).grid(row=0, column=0, padx=10)

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100,
            fg_color="#444",
            hover_color="#555",
            command=self.destroy,
        ).grid(row=0, column=1, padx=10)

    # --- Save budget Method ---
    def _save(self):
        """Save budget settings to database"""
        try:
            # Collect all budget values
            data = {}

            # --- Validate total budget ---
            try:
                raw_total = self.total_var.get().strip().replace(",", ".")
                if raw_total== "":
                    total = 0.0
                else:
                    total = float(raw_total)
                
                if total < 0:
                    raise ValueError("Cannot be negative")
                
                data["total"] = total
            except ValueError as e:
                messagebox.showerror(
                    "Invalid Total Budget",
                    "Please enter a valid positive number",
                    parent=self
                )
                return

            # --- Validate categories ---
            for key, var in self.category_vars.items():
                try:
                    raw_val= var.get().strip().replace(",", ".")
                    if raw_val == "":
                        value = 0.0
                    else:
                        value = float(raw_val)
                    
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    
                    data[key] = value
                except ValueError:
                    messagebox.showerror(
                        "Invalid Value",
                        f"Please enter a valid number for {key}",
                        parent=self
                    )
                    return

            # Save to database
            save_budget(data)

            messagebox.showinfo(
                "Saved", 
                "Budget limits updated successfully!",
                parent=self
            )
            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error", 
                f"Failed to save budget: {str(e)}",
                parent=self
            )


if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()