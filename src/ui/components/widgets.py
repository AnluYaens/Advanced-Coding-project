"""
Complex widget components for the dashboard.
"""

import customtkinter as ctk
from datetime import datetime, timedelta
from src.ui.config.theme import PALETTE, ICON_MAP, CATEGORY_COLORS
from src.ui.config.typography import Typography
from src.ui.components.buttons import AnimatedButton
from src.ui.components.cards import GlassCard
from src.ui.components.indicators import LoadingIndicator
from src.core.database import get_db_session, get_budget
from src.core.models import Expense


class FinancialInsightsWidget(GlassCard):
    """AI insights widget for financial recommendations."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # --- Main frame ---
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(pady=10, padx=15, fill="both", expand=True)

        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure((0, 1, 2), weight=1)

        # --- Create de visual pannels ---
        self._create_budget_gauge(content_frame)
        self._create_top_category_card(content_frame)
        self._create_monthly_comparison_card(content_frame)

    def _create_budget_gauge(self, parent):
        """Create a visual gauge for the monthly budget status."""
        gauge_card = ctk.CTkFrame(
            parent,
            fg_color=PALETTE["bg-elevated"],
            corner_radius=8
        )
        gauge_card.grid(row=0, column=0, sticky="nsew", pady=(0, 7))

        content = ctk.CTkFrame(gauge_card, fg_color="transparent")
        content.pack(expand=True, fill="both", pady=5)

        ctk.CTkLabel(
            content,
            text="Monthly Budget Status", 
            font=Typography.BODY
        ).pack()

        try:
            # --- Obtain data ---
            total_budget = get_budget().get("total", 0)
            with get_db_session() as session:
                now = datetime.now()
                expenses = session.query(Expense).filter(datetime(now.year, now.month, 1) <= Expense.date).all()
                total_spent = sum(e.amount for e in expenses)

            usage_percent = (total_spent / total_budget) * 100 if total_budget > 0 else 0
            usage_fraction = min(total_spent / total_budget, 1.0) if total_budget > 0 else 0

            # --- Determine color ---
            if usage_percent > 100: 
                progress_color = PALETTE["error"]
            elif usage_percent > 80:
                progress_color = PALETTE["warning"]
            else: 
                progress_color = PALETTE["success"]
            
            # --- Create the widgets ---
            ctk.CTkLabel(
                content, 
                text=f"{usage_percent:.0f}%", 
                font=Typography.get_font(32, "bold"), 
                text_color=progress_color
            ).pack(pady=(2,0))
            
            progress_bar = ctk.CTkProgressBar(
                content, 
                progress_color=progress_color, 
                fg_color=PALETTE["input"]
            )
            progress_bar.set(usage_fraction)
            progress_bar.pack(fill="x", padx=40, pady=5)
            
            ctk.CTkLabel(
                content, 
                text=f"${total_spent:,.0f} spent of ${total_budget:,.0f}", 
                font=Typography.CAPTION, 
                text_color=PALETTE["text-secondary"]
            ).pack()

        except Exception as e:
            ctk.CTkLabel(
                content, 
                text="Could not load budget status.", 
                font=Typography.BODY, 
                text_color=PALETTE["error"]
            ).pack()
        
        original_color = PALETTE["bg-elevated"]
        hover_color = PALETTE["sidebar"] 

        def on_enter(event): gauge_card.configure(fg_color=hover_color)
        def on_leave(event): gauge_card.configure(fg_color=original_color)

        # --- We atach the evemt to the card and all of it widgets to avoid conflicts ---
        for widget in [gauge_card] + gauge_card.winfo_children() + content.winfo_children():
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _create_top_category_card(self, parent):
        """Creates a card highlighting the top spending category."""
        top_cat_card = ctk.CTkFrame(parent, fg_color=PALETTE["bg-elevated"], corner_radius=8)
        top_cat_card.grid(row=1, column=0, sticky="nsew", pady=7)

        content = ctk.CTkFrame(top_cat_card, fg_color="transparent")
        content.pack(expand=True, fill="both", pady=5)

        ctk.CTkLabel(
            content, 
            text="Top Spending Area", 
            font=Typography.BODY
        ).pack()
        
        try:
            # --- Obtain and process data ---
            category_spending = {}
            total_spent = 0
            with get_db_session() as session:
                now = datetime.now()
                expenses = session.query(Expense).filter(datetime(now.year, now.month, 1) <= Expense.date).all()
                for exp in expenses:
                    category_spending[exp.category] = category_spending.get(exp.category, 0) + exp.amount
                    total_spent += exp.amount
            
            if not category_spending:
                ctk.CTkLabel(
                    content, 
                    text="No spending this month.", 
                    font=Typography.BODY, 
                    text_color=PALETTE["text-secondary"]
                ).pack(pady=10)
                return

            top_category_name = max(category_spending, key=category_spending.get)
            top_category_amount = category_spending[top_category_name]
            
            # --- Mapping of icons ---
            icon_map = {"Groceries": "🛒", "Electronics": "💻", "Entertainment": "🎮", "Other": "🏷️"}
            icon = icon_map.get(top_category_name, "💰")
            
            # --- Create Widgets ---
            grid_frame = ctk.CTkFrame(content, fg_color="transparent")
            grid_frame.pack(fill="x", padx=20, pady=5, expand=True)
            grid_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                grid_frame, 
                text=icon, 
                font=Typography.get_font(36)
            ).grid(row=0, column=0, rowspan=2, padx=(0, 15))
            
            ctk.CTkLabel(
                grid_frame, 
                text=top_category_name, 
                font=Typography.HEADING_3, 
                text_color=CATEGORY_COLORS.get(top_category_name, PALETTE["text"])
            ).grid(row=0, column=1, sticky="sw")
            
            ctk.CTkLabel(
                grid_frame, 
                text=f"${top_category_amount:,.2f} spent", 
                font=Typography.BODY, 
                text_color=PALETTE["text-secondary"]
            ).grid(row=1, column=1, sticky="nw")

        except Exception as e:
            ctk.CTkLabel(
                content, 
                text="Could not load top category.", 
                font=Typography.BODY, 
                text_color=PALETTE["error"]
            ).pack()

        original_color = PALETTE["bg-elevated"]
        hover_color = PALETTE["sidebar"]
        
        def on_enter(event): top_cat_card.configure(fg_color=hover_color)
        def on_leave(event): top_cat_card.configure(fg_color=original_color)

        all_widgets = [top_cat_card] + top_cat_card.winfo_children() + content.winfo_children()
        if 'grid_frame' in locals():
            all_widgets += grid_frame.winfo_children()

        for widget in all_widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _create_monthly_comparison_card(self, parent):
        """Creates a card comparing current spending pace to last month."""
        pace_card = ctk.CTkFrame(parent, fg_color=PALETTE["bg-elevated"], corner_radius=8)
        pace_card.grid(row=2, column=0, sticky="nsew", pady=(7, 0))
        
        content = ctk.CTkFrame(pace_card, fg_color="transparent")
        content.pack(expand=True, fill="both", pady=5)

        ctk.CTkLabel(
            content, 
            text="Monthly Pace", 
            font=Typography.BODY
        ).pack(pady=(5,0))
        
        try:
            current_month_spent = 0
            last_month_spent = 0
            
            with get_db_session() as session:
                now = datetime.now()
                
                # --- Spent of the actual month until today ---
                current_month_expenses = session.query(Expense).filter(
                    Expense.date >= datetime(now.year, now.month, 1),
                    Expense.date <= now
                ).all()
                current_month_spent = sum(e.amount for e in current_month_expenses)

                # --- Expenses of the month before untill the same day ---
                last_month = (now.replace(day=1) - timedelta(days=1)).month
                last_month_year = (now.replace(day=1) - timedelta(days=1)).year
                
                last_month_expenses = session.query(Expense).filter(
                    Expense.date >= datetime(last_month_year, last_month, 1),
                    Expense.date <= datetime(last_month_year, last_month, now.day)
                ).all()
                last_month_spent = sum(e.amount for e in last_month_expenses)

            if last_month_spent > 0:
                pace_change = ((current_month_spent - last_month_spent) / last_month_spent) * 100
                is_positive_change = pace_change > 0
            else: # --- Avoid division by 0 if the month before doesnt have expenses ---
                pace_change = current_month_spent 
                is_positive_change = True

            # --- Create widgets ---
            grid_frame = ctk.CTkFrame(content, fg_color="transparent")
            grid_frame.pack(fill="x", padx=20, pady=5, expand=True)
            grid_frame.grid_columnconfigure(1, weight=1)
            
            icon = "📈" if is_positive_change else "📉"
            color = PALETTE["error"] if is_positive_change else PALETTE["success"]
            
            ctk.CTkLabel(
                grid_frame, 
                text=icon, 
                font=Typography.get_font(36), 
                text_color=color
            ).grid(row=0, column=0, rowspan=2, padx=(0, 15))
            
            # --- Configure text ---
            if last_month_spent > 0:
                change_text = f"{pace_change:+.0f}%"
                subtitle_text = "vs. same period last month"
            else:
                change_text = f"${current_month_spent:,.0f}"
                subtitle_text = "spent this month (no data for last month)"

            ctk.CTkLabel(
                grid_frame, 
                text=change_text, 
                font=Typography.HEADING_2, 
                text_color=color
            ).grid(row=0, column=1, sticky="sw")
            ctk.CTkLabel(
                grid_frame, 
                text=subtitle_text, 
                font=Typography.BODY, 
                text_color=PALETTE["text-secondary"]
            ).grid(row=1, column=1, sticky="nw")

        except Exception as e:
            ctk.CTkLabel(
                content, 
                text=f"Could not load spending pace: {e}", 
                font=Typography.BODY, 
                text_color=PALETTE["error"]
            ).pack()

        original_color = PALETTE["bg-elevated"]
        hover_color = PALETTE["sidebar"]
        
        def on_enter(event): pace_card.configure(fg_color=hover_color)
        def on_leave(event): pace_card.configure(fg_color=original_color)

        all_widgets = [pace_card] + pace_card.winfo_children() + content.winfo_children()
        if 'grid_frame' in locals():
            all_widgets += grid_frame.winfo_children()

        for widget in all_widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

class QuickStatsWidget(ctk.CTkFrame):
    """Quick statistics cards widget."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color="transparent")

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            title_frame, 
            text="📊 Quick Statistics", 
            font=Typography.get_font(16, "bold"), 
            text_color=PALETTE["text"]
        ).pack(side="left")

        stats_container = ctk.CTkFrame(self, fg_color="transparent")
        stats_container.pack(fill="both", expand=True)
        stats_container.grid_columnconfigure((0, 1), weight=1)
        self.create_stats_cards(stats_container)

    def create_stats_cards(self, parent):
        """Create stat cards."""
        stats = self.calculate_stats()
        cards_info = [
            ("💰", "Total Spent", f"${stats['total_spent']:.0f}", 
             f"↗ +{stats['spent_change']}%", PALETTE["blue"]),
            ("📊", "Daily Average", f"${stats['daily_avg']:.0f}", 
             f"{'↘' if stats['avg_change'] < 0 else '↗'} {stats['avg_change']:+.0f}%", 
             PALETTE["green"]),
            ("🎯", "Budget Used", f"{stats['budget_used']}%", 
             "⚠️ High" if stats['budget_used'] > 80 else "On Track", 
             PALETTE["purple"]),
            ("💳", "Transactions", str(stats['transaction_count']), 
             "Total this month", PALETTE["orange"]),
        ]
        for i, (icon, label, value, change, color) in enumerate(cards_info):
            card = self.create_single_stat_card(parent, icon, label, value, change, color)
            card.grid(row=i//2, column=i%2, padx=4, pady=4, sticky="nsew")

    def create_single_stat_card(self, parent, icon, label, value, change, color):
        """Creates a single stat card."""
        card = GlassCard(parent)
        card.configure(fg_color=PALETTE["bg-elevated"], height=120)
        card.pack_propagate(False)

        accent_bar = ctk.CTkFrame(card, width=5, fg_color=color, corner_radius=0)
        accent_bar.pack(side="left", fill="y")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)

        # --- Header ---
        ctk.CTkLabel(
            content,
            text=label.upper(),
            font=Typography.get_font(10, "bold"),
            text_color=PALETTE["text-secondary"]
        ).pack(side="top", anchor="w")

        # --- Footer Area ---
        footer_frame = ctk.CTkFrame(content, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x")

        # --- Spacer ---
        ctk.CTkFrame(content, fg_color="transparent").pack(expand=True, fill="both")

        # --- Populate Footer ---
        ctk.CTkLabel(
            footer_frame,
            text=value,
            font=Typography.get_font(26, "bold"),
            text_color=PALETTE["text"]
        ).pack(side="top", anchor="w")

        sub_footer = ctk.CTkFrame(footer_frame, fg_color="transparent")
        sub_footer.pack(side="top", fill="x", anchor="w", pady=(2, 0))

        safe_icon = ICON_MAP.get(icon, icon)

        is_bad = "↘" in change or "High" in change
        change_color = PALETTE["error"] if is_bad else PALETTE["success"]
        final_change_text = change.replace("On Track", "").replace("Total this month", "").strip()

        ctk.CTkLabel(
            sub_footer,
            text=safe_icon,
            font=Typography.get_font(16),
            text_color=color
        ).pack(side="left", anchor="center")

        if final_change_text:
            ctk.CTkLabel(
                sub_footer,
                text=final_change_text,
                font=Typography.get_font(11, "medium"),
                text_color=change_color
            ).pack(side="left", anchor="center", padx=6)

        return card

    def calculate_stats(self):
        """Calculate statistics from database."""
        try:
            with get_db_session() as session:
                now = datetime.now()
                month_start = datetime(now.year, now.month, 1)
                current_expenses = session.query(Expense).filter(
                    Expense.date >= month_start
                ).all()
                
                if now.month == 1:
                    last_month_start = datetime(now.year - 1, 12, 1)
                    last_month_end = datetime(now.year - 1, 12, 31)
                else:
                    last_month_start = datetime(now.year, now.month - 1, 1)
                    last_month_end = month_start - timedelta(days=1)
                    
                last_month_expenses = session.query(Expense).filter(
                    Expense.date.between(last_month_start, last_month_end)
                ).all()
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
                    'total_spent': total_spent, 
                    'spent_change': int(spent_change),
                    'daily_avg': daily_avg, 
                    'avg_change': int(avg_change),
                    'budget_used': int(budget_used), 
                    'transaction_count': len(current_expenses)
                }
        except Exception as e:
            print(f"Error calculating stats: {e}")
            return {
                'total_spent': 0, 'spent_change': 0, 
                'daily_avg': 0, 'avg_change': 0, 
                'budget_used': 0, 'transaction_count': 0
            }