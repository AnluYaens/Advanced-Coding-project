"""
Main entry point for the AI Budget Tracker application.

This script initializes the database and launches the main graphical user interface.
"""
from src.ui.app import BudgetApp
from src.core.database import init_db
from src.core.seeder import seed_database_if_empty


if __name__ == '__main__':
    # --- Initialize the database ---
    init_db()

    # --- Populate the database with sample data (Only if it is empty) ---
    seed_database_if_empty() 
    
    # --- Launch the app ---
    app = BudgetApp()
    app.mainloop()