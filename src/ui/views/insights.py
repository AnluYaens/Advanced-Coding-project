"""
AI Insights view for financial recommendations and predictions.
"""

import customtkinter as ctk
from datetime import datetime
from src.ui.config.theme import PALETTE, CATEGORY_COLORS
from src.ui.config.typography import Typography
from src.ui.components.cards import GlassCard
from src.ui.components.widgets import FinancialInsightsWidget
from src.ui.utils.helpers import create_header
from src.core.database import get_db_session, get_budget
from src.core.models import Expense


class AIInsightsView:
    """AI-powered financial insights and recommendations."""
    
    def __init__(self, parent):
        self.parent = parent
        
    def create(self):
        """Create the AI insights view."""
        create_header(self.parent, "AI Financial Insights")
        
        main_container = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=30)
        main_container.grid_columnconfigure((0, 1), weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        # --- Left column - AI insights widget ---
        left_card = GlassCard(main_container)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        
        insights_widget = FinancialInsightsWidget(left_card)
        insights_widget.pack(fill="both", expand=True, padx=16, pady=16)

        # --- Right column - Trends and recommendations ---
        right_card = GlassCard(main_container)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        
        ctk.CTkLabel(
            right_card, 
            text="Monthly Spending Trends", 
            font=Typography.HEADING_2, 
            text_color=PALETTE["text"]
        ).pack(padx=20, pady=(20, 16), anchor="w")
        
        self._create_spending_prediction(right_card)
        self._create_budget_analysis(right_card)
    
    def _create_spending_prediction(self, parent):
        """Create spending prediction widget with budget comparison."""
        pred_frame = ctk.CTkFrame(
            parent, 
            fg_color=PALETTE["bg-elevated"], 
            corner_radius=12
        )
        pred_frame.pack(fill="x", padx=20, pady=(0, 16))
        
        content = ctk.CTkFrame(pred_frame, fg_color="transparent")
        content.pack(padx=20, pady=20)
        
        ctk.CTkLabel(
            content, 
            text="📈 Spending Forecast", 
            font=Typography.HEADING_3, 
            text_color=PALETTE["text"]
        ).pack(anchor="w", pady=(0, 12))
        
        try:
            now = datetime.now()
            month_start = datetime(now.year, now.month, 1)
            total_spent = 0

            with get_db_session() as session:
                expenses = session.query(Expense).filter(
                    Expense.date >= month_start
                ).all()
                total_spent = sum(e.amount for e in expenses)

            total_budget = get_budget().get("total", 0)
            days_in_month = (datetime(now.year, now.month % 12 + 1, 1) - month_start).days if now.month != 12 else 31
            days_passed = (now - month_start).days + 1
            
            if days_passed > 0:
                daily_avg = total_spent / days_passed
                projected = daily_avg * days_in_month 
                
                ctk.CTkLabel(
                    content, 
                    text=f"Current daily average: ${daily_avg:.2f}", 
                    font=Typography.BODY, 
                    text_color=PALETTE["text-secondary"]
                ).pack(anchor="w", pady=2)
                
                ctk.CTkLabel(
                    content, 
                    text=f"Projected monthly total: ${projected:.2f}", 
                    font=Typography.get_font(16, "bold"), 
                    text_color=PALETTE["warning"] if projected > total_budget else PALETTE["success"]
                ).pack(anchor="w", pady=2)

                if total_budget > 0:
                    difference = total_budget - projected
                    status_text = f"On track to be ${difference:.2f} under budget." if difference >= 0 else f"Projected to be ${abs(difference):.2f} over budget."
                    status_color = PALETTE["success"] if difference >= 0 else PALETTE["error"]
                    ctk.CTkLabel(content, text=status_text, font=Typography.BODY, text_color=status_color).pack(anchor="w", pady=(8, 2))
            else:
                ctk.CTkLabel(
                    content, 
                    text="No data yet this month.", 
                    font=Typography.BODY, 
                    text_color=PALETTE["text-tertiary"]
                ).pack(anchor="w")

        except Exception as e:
            ctk.CTkLabel(content, text=f"Error calculating prediction: {e}", font=Typography.BODY, text_color=PALETTE["error"]).pack(anchor="w")
    
    def _create_budget_analysis(self, parent):
        """Create dynamic, data-driven recomendations based on budget usage."""
        rec_frame = ctk.CTkFrame(parent, fg_color=PALETTE["bg-elevated"], corner_radius=12)
        rec_frame.pack(fill="x", padx=20, pady=(0, 20))

        content = ctk.CTkFrame(rec_frame, fg_color="transparent")
        content.pack(padx=20, pady=20)

        ctk.CTkLabel(
            content, 
            text="💡 Budget Hotspots", 
            font=Typography.HEADING_3, 
            text_color=PALETTE["text"]
        ).pack(anchor="w", pady=(0, 16))

        try:
            budgets = get_budget()
            category_spending = {}

            with get_db_session() as session:
                now = datetime.now()
                expenses = session.query(Expense).filter(datetime(now.year, now.month, 1) <= Expense.date).all()

                # --- Cluster expenses per category ---
                for exp in expenses:
                    cat_key = exp.category.lower()
                    category_spending[cat_key] = category_spending.get(cat_key, 0) + exp.amount

            relevant_budgets = {k: v for k, v in budgets.items() if k != "total" and v > 0}

            if not relevant_budgets:
                ctk.CTkLabel(content, text="No category budgets set. Set them to see your progress!", font=Typography.BODY, text_color=PALETTE["info"]).pack(anchor="w")
                return
            
            for cat, limit in relevant_budgets.items():
                spent = category_spending.get(cat, 0)
                usage_fraction = (spent / limit) if limit > 0 else 0

                # --- Generate recommendations based on used ---
                if usage_fraction > 0.9:
                    progress_color = PALETTE["error"]
                elif usage_fraction > 0.7:
                    progress_color = PALETTE["warning"]
                else:
                    progress_color = CATEGORY_COLORS.get(cat.capitalize(), PALETTE["success"])

                cat_row_frame = ctk.CTkFrame(content, fg_color="transparent")
                cat_row_frame.pack(fill="x", pady=6)
                cat_row_frame.grid_columnconfigure(1, weight=1)

                # --- Name of the category ---
                ctk.CTkLabel(
                    cat_row_frame,
                    text=cat.capitalize(),
                    font=Typography.get_font(13, "medium"),
                    text_color=PALETTE["text"]
                ).grid(row=0, column=0, sticky="w")

                # --- Text with expense and limit ---
                ctk.CTkLabel(
                    cat_row_frame,
                    text=f"${spent:,.0f} / ${limit:,.0f}",
                    font=Typography.CAPTION,
                    text_color=PALETTE["text-secondary"]
                ).grid(row=0, column=2, sticky="e", padx=(10, 0))

                # --- Progress bar ----
                progress_bar = ctk.CTkProgressBar(
                    cat_row_frame,
                    progress_color=progress_color,
                    fg_color=PALETTE["input"]
                )
                progress_bar.set(min(usage_fraction, 1.0))
                progress_bar.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))


        except Exception as e:
            ctk.CTkLabel(
                content, 
                text=f"Could not generate budget analysis: {e}", 
                text_color=PALETTE["error"]
            ).pack(anchor="w")