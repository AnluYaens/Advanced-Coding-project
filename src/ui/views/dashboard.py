"""
Dashboard view with charts, AI chat, and financial widgets.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from datetime import datetime
import os
import threading

from src.ui.config.theme import PALETTE, CATEGORY_COLORS
from src.ui.config.typography import Typography
from src.ui.components.buttons import AnimatedButton
from src.ui.components.cards import GlassCard
from src.ui.components.charts import LineChart, DonutChart
from src.ui.components.widgets import QuickStatsWidget
from src.ui.components.indicators import LoadingIndicator
from src.ui.utils.helpers import create_header, truncate_text
from src.core.database import (
    get_db_session, get_budget, get_expenses_by_month,
    insert_payment, delete_payment, query_expenses_by_category,
    list_expenses_by_category
)
from src.core.models import Expense
from src.core.ai_engine import chat_completion
from src.services.bank_statement_loader import load_bank_statement_csv

# --- PDF support toggle ---
PDF_SUPPORT = False
try:
    from src.services.bank_statement_loader_pdf import load_bank_statement_pdf
    PDF_SUPPORT = True
except ImportError:
    print("Warning: bank_statement_loader_pdf not available")


class DashboardView:
    """Dashboard view with financial overview."""
    
    def __init__(self, parent, refresh_callback):
        self.parent = parent
        self.refresh_callback = refresh_callback
        self.dashboard_chat_history = []
        
        # --- Widget references ---
        self.dashboard_chatbox = None
        self.dashboard_msg_var = None
        self.dashboard_send_btn = None
        self._ai_thinking_indicator = None
        
        # --- Chart references ---
        self._chart_canvas = None
        self._chart_canvas_donut = None
        
    def create(self):
        """Create the dashboard view."""
        create_header(self.parent, "Financial Dashboard", show_date=True)
        
        main_container = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- Configure grid weights ---
        main_container.grid_columnconfigure(0, weight=4, minsize=350)  # --- Charts ---
        main_container.grid_columnconfigure(1, weight=3, minsize=280)  # --- AI Chat ---
        main_container.grid_columnconfigure(2, weight=6, minsize=420)  # --- Widgets ---
        main_container.grid_rowconfigure(0, weight=1)
        
        self._create_charts_column(main_container)
        self._create_chat_column(main_container)
        self._create_widgets_column(main_container)
        
    def _create_charts_column(self, parent):
        """Create charts column."""
        left_column = ctk.CTkFrame(parent, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        
        # --- Trend chart ---
        trend_card = GlassCard(left_column)
        trend_card.pack(fill="both", expand=True, pady=(0, 8))
        ctk.CTkLabel(
            trend_card, 
            text="Monthly Spending Trend", 
            font=Typography.HEADING_3, 
            text_color=PALETTE["text"]
        ).pack(padx=16, pady=(16, 0), anchor="w")
        
        data = self._get_expenses_by_month()
        self._chart_canvas = LineChart.create(trend_card, data, PALETTE)

        # --- Category chart ---
        category_card = GlassCard(left_column)
        category_card.pack(fill="both", expand=True)
        ctk.CTkLabel(
            category_card, 
            text="Category Breakdown", 
            font=Typography.HEADING_3, 
            text_color=PALETTE["text"]
        ).pack(padx=16, pady=(16, 0), anchor="w")
        
        values = self._get_expenses_by_category()
        categories = ["Groceries", "Electronics", "Entertainment", "Other"]
        self._chart_canvas_donut = DonutChart.create(
            category_card, values, categories, CATEGORY_COLORS
        )
        
    def _create_chat_column(self, parent):
        """Create AI chat column."""
        chat_card = GlassCard(parent)
        chat_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=0)
        
        # --- Header ---
        chat_header = ctk.CTkFrame(chat_card, fg_color="transparent")
        chat_header.pack(fill="x", padx=12, pady=(12, 8))
        ctk.CTkLabel(
            chat_header, 
            text="AI Assistant", 
            font=Typography.get_font(14, "bold"), 
            text_color=PALETTE["text"]
        ).pack(side="left")
        
        import_btn = AnimatedButton(
            chat_header, 
            text="📂", 
            width=32, 
            height=26, 
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent-hover"], 
            command=self._import_bank_statement,
            font=Typography.get_font(11, "medium"), 
            corner_radius=6
        )
        import_btn.pack(side="right")

        # --- Chat display ---
        chat_display = ctk.CTkFrame(chat_card, fg_color=PALETTE["bg-elevated"], corner_radius=8)
        chat_display.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        
        self.dashboard_chatbox = tk.Text(
            chat_display, 
            state="disabled", 
            bg=PALETTE["bg-elevated"], 
            fg=PALETTE["text"],
            font=Typography.get_font(14, "normal"), 
            wrap="word", 
            borderwidth=0, 
            highlightthickness=0,
            insertbackground=PALETTE["accent"],
        )
        self.dashboard_chatbox.pack(padx=8, pady=8, fill="both", expand=True)

        # --- Configure text tags ---
        self.dashboard_chatbox.tag_config(
            "user_header", 
            foreground=PALETTE["accent"], 
            font=Typography.get_font(11, "bold"),
            spacing1=5
        )
        self.dashboard_chatbox.tag_config(
            "user", 
            foreground=PALETTE["text"], 
            font=Typography.get_font(14, "normal")
        )
        self.dashboard_chatbox.tag_config(
            "assistant_header", 
            foreground=PALETTE["info"], 
            font=Typography.get_font(11, "bold"),
            spacing1=5
        )
        self.dashboard_chatbox.tag_config(
            "assistant", 
            foreground=PALETTE["text-secondary"], 
            font=Typography.get_font(14, "normal")
        )

        # --- Input frame ---
        input_frame = ctk.CTkFrame(chat_card, fg_color="transparent")
        input_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        self.dashboard_msg_var = tk.StringVar()
        msg_entry = ctk.CTkEntry(
            input_frame, 
            textvariable=self.dashboard_msg_var, 
            height=32, 
            placeholder_text="Ask me...",
            font=Typography.get_font(14, "normal"), 
            fg_color=PALETTE["input"],
            border_color=PALETTE["border"], 
            corner_radius=6
        )
        msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        msg_entry.bind("<Return>", lambda e: self._send_dashboard_message())
        msg_entry.focus()
        
        self.dashboard_send_btn = AnimatedButton(
            input_frame, 
            text="Send", 
            width=50, 
            height=32, 
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent-hover"], 
            command=self._send_dashboard_message,
            font=Typography.get_font(10, "semibold"), 
            corner_radius=6
        )
        self.dashboard_send_btn.pack(side="right")

        # --- Initial message ---
        if not self.dashboard_chat_history:
            self._append_dashboard_chat("assistant",
                "Hello! I'm your AI budget assistant. I can help you:\n"
                "• Record expenses (e.g., 'Add $50 for groceries')\n"
                "• Check spending (e.g., 'How much on entertainment?')\n"
                "• Import bank statements (click 📂)\n"
                "• Refresh the dashboard\n\n"
                "How can I help you today?")
            
    def _create_widgets_column(self, parent):
        """Create widgets column."""
        right_column = ctk.CTkScrollableFrame(
            parent, 
            fg_color="transparent", 
            scrollbar_button_color=PALETTE["accent"],
            scrollbar_button_hover_color=PALETTE["accent-hover"], 
            scrollbar_fg_color=PALETTE["bg-elevated"]
        )
        right_column.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=0)
        
        # --- Quick stats ---
        QuickStatsWidget(right_column).pack(fill="x", pady=(0, 8))
        
        # --- Budget status ---
        self._create_budget_status(right_column)
        
        # --- Recent transactions ---
        self._create_recent_transactions(right_column)
        
    def _create_budget_status(self, parent):
        """Create budget status widget."""
        budget_card = GlassCard(parent)
        budget_card.pack(fill="x")
        
        ctk.CTkLabel(
            budget_card, 
            text="Budget Status (Current Month)", 
            font=Typography.get_font(14, "bold"), 
            text_color=PALETTE["text"]
        ).pack(padx=16, pady=(12, 8), anchor="w")
        
        try:
            budget_data = get_budget() or {}
            
            # --- Get current month expenses ---
            now = datetime.now()
            expenses = get_expenses_by_month(now.month, now.year)
            
            category_spending = {"groceries": 0, "entertainment": 0, "electronics": 0, "other": 0}
            for exp in expenses:
                cat_key = exp.category.lower() if exp.category else "other"
                category_spending[cat_key] = category_spending.get(cat_key, 0) + exp.amount

            categories = [
                ("Groceries", "groceries", budget_data.get("groceries", 600), PALETTE["green"]),
                ("Entertainment", "entertainment", budget_data.get("entertainment", 300), PALETTE["pink"]),
                ("Electronics", "electronics", budget_data.get("electronics", 500), PALETTE["blue"]),
                ("Other", "other", budget_data.get("other", 200), PALETTE["orange"])
            ]
            
            for display_name, key, budget_amount, color in categories:
                spent = category_spending.get(key, 0)
                progress = min(spent / budget_amount, 1.0) if budget_amount > 0 else 0
                
                cat_frame = ctk.CTkFrame(budget_card, fg_color="transparent")
                cat_frame.pack(fill="x", padx=16, pady=4)
                
                header = ctk.CTkFrame(cat_frame, fg_color="transparent")
                header.pack(fill="x", pady=(0, 3))
                ctk.CTkLabel(
                    header, 
                    text=display_name, 
                    font=Typography.get_font(11, "medium"), 
                    text_color=PALETTE["text"]
                ).pack(side="left")
                ctk.CTkLabel(
                    header, 
                    text=f"${spent:.0f} / ${budget_amount:.0f}", 
                    font=Typography.get_font(10, "normal"), 
                    text_color=color
                ).pack(side="right")
                
                progress_bg = ctk.CTkFrame(
                    cat_frame, 
                    height=4, 
                    fg_color=PALETTE["bg-elevated"], 
                    corner_radius=2
                )
                progress_bg.pack(fill="x")
                
                if progress > 0:
                    progress_fill = ctk.CTkFrame(
                        progress_bg, 
                        height=4, 
                        fg_color=color if progress < 0.9 else PALETTE["warning"], 
                        corner_radius=2
                    )
                    progress_fill.place(relwidth=progress, relheight=1)
        except Exception as e:
            print(f"Error loading budget status: {e}")
        
        ctk.CTkFrame(budget_card, fg_color="transparent", height=12).pack()
        
    def _create_recent_transactions(self, parent):
        """Create recent transactions widget."""
        trans_card = GlassCard(parent)
        trans_card.pack(fill="x", pady=(8, 0))
        
        header = ctk.CTkFrame(trans_card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            header, 
            text="Recent Transactions", 
            font=Typography.get_font(14, "bold"), 
            text_color=PALETTE["text"]
        ).pack(side="left")

        view_all_label = ctk.CTkLabel(
            header, 
            text="View all →", 
            font=Typography.get_font(10, "normal"), 
            text_color=PALETTE["accent"], 
            cursor="hand2"
        )
        view_all_label.pack(side="right")
        view_all_label.bind("<Button-1>", lambda e: self.refresh_callback("All Transactions"))

        try:
            with get_db_session() as session:
                recent = session.query(Expense).order_by(Expense.date.desc()).limit(5).all()
                session.expunge_all()
            
            if not recent:
                ctk.CTkLabel(
                    trans_card, 
                    text="No transactions yet.", 
                    font=Typography.BODY, 
                    text_color=PALETTE["text-tertiary"]
                ).pack(pady=20)
            else:
                for exp in recent:
                    trans_frame = ctk.CTkFrame(trans_card, fg_color=PALETTE["card"], corner_radius=6)
                    trans_frame.pack(fill="x", padx=16, pady=2)
                    
                    def on_enter(e, widget=trans_frame): 
                        widget.configure(fg_color=PALETTE["card-hover"])
                    def on_leave(e, widget=trans_frame): 
                        widget.configure(fg_color=PALETTE["card"])
                    trans_frame.bind("<Enter>", on_enter)
                    trans_frame.bind("<Leave>", on_leave)

                    content = ctk.CTkFrame(trans_frame, fg_color="transparent")
                    content.pack(fill="x", padx=12, pady=8)
                    
                    color = CATEGORY_COLORS.get(exp.category, PALETTE["text-tertiary"])
                    left_frame = ctk.CTkFrame(content, fg_color="transparent")
                    left_frame.pack(side="left", fill="x", expand=True)
                    
                    ctk.CTkLabel(
                        left_frame, 
                        text=exp.category, 
                        font=Typography.get_font(11, "medium"), 
                        text_color=color, 
                        anchor="w"
                    ).pack(anchor="w")
                    
                    date_str = exp.date.strftime("%b %d") if exp.date else "Unknown"
                    desc = truncate_text(exp.description)
                    
                    ctk.CTkLabel(
                        left_frame, 
                        text=f"{date_str} • {desc}" if desc else date_str, 
                        font=Typography.get_font(9, "normal"), 
                        text_color=PALETTE["text-tertiary"], 
                        anchor="w"
                    ).pack(anchor="w")
                    
                    ctk.CTkLabel(
                        content, 
                        text=f"${exp.amount:.2f}", 
                        font=Typography.get_font(12, "bold"), 
                        text_color=PALETTE["text"]
                    ).pack(side="right")
        except Exception as e:
            print(f"Error loading transactions: {e}")
            
        ctk.CTkFrame(trans_card, fg_color="transparent", height=12).pack()
        
    def _get_expenses_by_month(self):
        """Get expenses aggregated by month."""
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

    def _get_expenses_by_category(self):
        """Get expenses aggregated by category."""
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
            
    def _show_ai_thinking_indicator(self, show: bool):
        """Show or hide AI thinking indicator."""
        if hasattr(self, "_ai_thinking_indicator") and self._ai_thinking_indicator and self._ai_thinking_indicator.winfo_exists():
            self._ai_thinking_indicator.destroy()

        if show:
            self._ai_thinking_indicator = ctk.CTkFrame(self.dashboard_chatbox, fg_color="transparent")
            
            icon = ctk.CTkLabel(
                self._ai_thinking_indicator, 
                text="AI", 
                font=Typography.get_font(11, "bold"), 
                text_color=PALETTE["info"]
            )
            icon.pack(side="left", padx=(0, 4))
            
            loading_label = LoadingIndicator(self._ai_thinking_indicator)
            loading_label.configure(
                font=Typography.get_font(12, "normal"), 
                text_color=PALETTE["text-secondary"]
            )
            loading_label.pack(side="left")
            loading_label.start()
            
            # --- Insert the frame in the Text widget ---
            self.dashboard_chatbox.configure(state="normal")
            self.dashboard_chatbox.insert("end", "\n\n")
            self.dashboard_chatbox.window_create("end", window=self._ai_thinking_indicator)
            self.dashboard_chatbox.configure(state="disabled")
            self.dashboard_chatbox.see("end")

    def _append_dashboard_chat(self, role: str, text: str):
        """Append message to chat."""
        if not self.dashboard_chatbox: 
            return
            
        self.dashboard_chatbox.configure(state="normal")
        if self.dashboard_chatbox.get("1.0", "end-1c").strip(): 
            self.dashboard_chatbox.insert("end", "\n")
            
        prefix = "You" if role == "user" else "AI"
        self.dashboard_chatbox.insert(
            "end", 
            f"[{datetime.now().strftime('%H:%M')}] {prefix}\n", 
            f"{role}_header"
        )
        self.dashboard_chatbox.insert("end", text, role)
        self.dashboard_chatbox.configure(state="disabled")
        self.dashboard_chatbox.see("end")

    def _send_dashboard_message(self):
        """Send message to AI assistant."""
        msg = self.dashboard_msg_var.get().strip()
        if not msg:
            return
            
        self.dashboard_msg_var.set("")
        self._append_dashboard_chat("user", msg)
        self.dashboard_chat_history.append(("user", msg))
        self.dashboard_send_btn.configure(state="disabled")
        
        # --- Show thinking indicator ---
        self._show_ai_thinking_indicator(True)
        
        def process():
            refresh_has_been_triggered = False

            try:
                reply = chat_completion(self.dashboard_chat_history)
                self.dashboard_chat_history.append(("assistant", reply.get("content", "Done.")))
                
                # --- Hide indicator before showing response ---
                if self.parent.winfo_exists():
                    self.parent.after(0, self._show_ai_thinking_indicator, False)
                
                if reply["type"] == "function_call":
                    if reply["name"] == "refresh_dashboard_ui":
                        refresh_has_been_triggered = True
                        self._execute_ai_function(reply["name"], reply["arguments"])
                        return
                    # --- For all the other functions, continue ---
                    result = self._execute_ai_function(reply["name"], reply["arguments"])
                    if self.parent.winfo_exists():
                        self.parent.after(10, self._append_dashboard_chat, "assistant", result)
                else:
                    if self.parent.winfo_exists():
                        self.parent.after(10, self._append_dashboard_chat, "assistant", reply["content"])
            except Exception as e:
                if self.parent.winfo_exists():
                    self.parent.after(0, self._show_ai_thinking_indicator, False)
                    self.parent.after(10, self._append_dashboard_chat, "assistant", f"❌ Sorry, I encountered an error: {e}")
            finally:
                if not refresh_has_been_triggered:
                    if self.dashboard_send_btn and self.dashboard_send_btn.winfo_exists():
                        self.dashboard_send_btn.configure(state="normal")
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
        
    def _import_bank_statement(self):
        """Import bank statement."""
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
            
        self._append_dashboard_chat("user", f"Importing: {os.path.basename(file_path)}")
        
        try:
            if file_path.lower().endswith(".csv"):
                result = load_bank_statement_csv(file_path)
            elif file_path.lower().endswith(".pdf") and PDF_SUPPORT:
                result = load_bank_statement_pdf(file_path)
            else:
                raise ValueError("Unsupported file format. Please use CSV or PDF.")
                
            if result.get("imported", 0) > 0:
                success_message = (
                    f"✅ Import successful!\n"
                    f"Imported: {result['imported']} | Failed: {result.get('failed', 0)}\n\n"
                    f"Say 'refresh' to see the changes on the dashboard."
                )
                self._append_dashboard_chat("assistant", success_message)
            else:
                self._append_dashboard_chat(
                    "assistant", 
                    f"❌ No valid expenses found in the file.\nErrors: {result.get('errors', ['N/A'])}"
                )
        except Exception as e:
            self._append_dashboard_chat("assistant", f"❌ Import error: {e}")
            
    def _execute_ai_function(self, name: str, args: dict) -> str:
        """Execute AI function calls."""
        try:
            if name == "insert_payment":
                insert_payment(**args)
                return f"✅ Expense recorded: ${args['amount']} for {args['category']}.\n\nSay 'refresh' to see the update."
            
            elif name == "delete_payment":
                if delete_payment(**args):
                    return f"✅ Expense #{args['expense_id']} deleted.\n\nSay 'refresh' to see the update."
                else:
                    return f"❌ Expense #{args['expense_id']} not found."
                
            elif name == "refresh_dashboard_ui":
                self.parent.after(0, self.refresh_callback, "Dashboard")
                return ""
            
            elif name == "query_expenses_by_category":
                total = query_expenses_by_category(**args)
                return f"💰 Total spent on {args['category']}: ${total:.2f}"
            
            elif name == "list_expenses_by_category":
                expenses = list_expenses_by_category(args['category'])
                if not expenses:
                    return f"No expenses found for {args['category']}."
                lines = [f"💵 Expenses in {args['category'].capitalize()}:"]
                for e in expenses[:10]:
                    lines.append(f" • ID: {e['id']} | ${e['amount']:.2f} on {e['date']} | {e['description']}")
                if len(expenses) > 10:
                    lines.append(f" • ... and {len(expenses) - 10} more.")
                return "\n".join(lines)
            return f"❌ Unknown function: {name}"
        except Exception as e:
            return f"❌ Error executing {name}: {e}"
            
    def cleanup(self):
        """Clean up resources."""
        # --- Clean up matplotlib figures ---
        if self._chart_canvas:
            try:
                self._chart_canvas.get_tk_widget().destroy()
            except:
                pass
            self._chart_canvas = None
            
        if self._chart_canvas_donut:
            try:
                self._chart_canvas_donut.get_tk_widget().destroy()
            except:
                pass
            self._chart_canvas_donut = None