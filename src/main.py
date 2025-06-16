"""
Main entry point for the AI Budget Tracker application.

This script initializes the database and launches the main graphical user interface.
"""
from src.core.database import init_db
from src.ui.interface_ctk import BudgetApp

if __name__ == '__main__':
    # --- Initialize the database ---
    init_db()
    # init_db(create_sample_data=True)  # Uncomment this line to populate database with demo data (only if empty)
    
    # --- Launch the budget tracker GUI ---
    app = BudgetApp()
    app.mainloop()
