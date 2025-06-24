"""
Main application file for the AI Budget Tracker.
This is the refactored version with modular architecture.
"""

import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

from src.ui.config.theme import PALETTE
from src.ui.components.sidebar import Sidebar
from src.ui.views.dashboard import DashboardView
from src.ui.views.add_expense import AddExpenseView
from src.ui.views.all_transactions import AllTransactionsView
from src.ui.views.analytics import AnalyticsView
from src.ui.views.insights import AIInsightsView
from src.ui.views.budget import BudgetView
from src.ui.views.currency import CurrencyView
from src.ui.views.contact import ContactView


class BudgetApp(ctk.CTk):
    """
    Main application class for the AI Budget Tracker.
    Refactored version with modular architecture.
    """
    
    def __init__(self):
        super().__init__()
        self.title("AI Budget Tracker")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.minsize(1000, 600)
        
        # --- Center window on screen ---
        self.update_idletasks()
        width, height = 1200, 700
        x = (self.winfo_screenwidth() // 2) - width // 2
        y = (self.winfo_screenheight() // 2) - height // 2 - 40
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # --- Configure appearance ---
        self.configure(fg_color=PALETTE["bg"])
        
        # --- Initialize state ---
        self.current_tab = "Dashboard"
        self.current_view = None
        
        # --- Create layout ---
        self._create_layout()
        
        # --- Show initial tab ---
        self.show_tab("Dashboard")
        
    def _create_layout(self):
        """Create the main application layout."""
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # --- Create sidebar ---
        self.sidebar = Sidebar(main_container, self.show_tab)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # --- Create content area ---
        self.content_frame = ctk.CTkFrame(
            main_container, 
            fg_color=PALETTE["bg"], 
            corner_radius=0
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
    def clear_content(self):
        """Clear all widgets from content frame."""
        # --- Clean up current view if it has a cleanup method ---
        if self.current_view and hasattr(self.current_view, 'cleanup'):
            self.current_view.cleanup()
            
        # --- Close any matplotlib figures ---
        plt.close('all')
        
        # --- Destroy all widgets ---
        for widget in self.content_frame.winfo_children():
            try:
                widget.destroy()
            except:
                pass
                
    def show_tab(self, tab_name):
        """Show the specified tab."""
        self.clear_content()
        self.sidebar.set_active_tab(tab_name)
        self.current_tab = tab_name
        
        # --- Create view based on tab ---
        view_map = {
            "Dashboard": DashboardView,
            "Add Expense": AddExpenseView,
            "All Transactions": AllTransactionsView,
            "Analytics": AnalyticsView,
            "AI Insights": AIInsightsView,
            "Set Budget": BudgetView,
            "Currency": CurrencyView,
            "Contact": ContactView
        }
        
        view_class = view_map.get(tab_name)
        if view_class:
            # --- Create view instance ---
            if tab_name in ["Dashboard", "Add Expense"]:
                # --- Views that need refresh callback ---
                self.current_view = view_class(self.content_frame, self.show_tab)
            else:
                self.current_view = view_class(self.content_frame)
            
            # --- Create the view ---
            self.current_view.create()
            
            
def main():
    """Main entry point for the application."""
    app = BudgetApp()
    app.mainloop()


if __name__ == "__main__":
    main()