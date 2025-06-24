import json
import os
import logging
from datetime import datetime

from src.core.database import get_db_session, ROOT_DIR
from src.core.models import Budget, Expense

logger = logging.getLogger(__name__)

def seed_database_if_empty():
    """
    Checks if the database is empty and, if so, populates it with sample
    data from sample_data.json.
    """
    with get_db_session() as session:
        # --- Check if the database is empty ---
        if session.query(Budget).count() > 0 or session.query(Expense).count() > 0:
            logger.info("Database already contains data. Skipping seeding")
            return
        
        logger.info("Database is empty. Seeding with sample data...")

        # --- Build the path to the JSON file ---
        json_path =  os.path.join(ROOT_DIR, 'sample_data.json')
        if not os.path.exists(json_path):
            logger.error(f"Sample data file not found at: {json_path}")
            return
    
        # --- Load the data ---
        with open(json_path, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)

        try:
            # --- Insert the budgets ---
            for budget_data in sample_data.get("budgets", []):
                budget = Budget(**budget_data)
                session.add(budget)
            logger.info(f"Seeded {len(sample_data.get('budgets', []))} budget records.")

            # --- Insert the expenses ---
            for expense_data in sample_data.get("expenses", []):
                # --- Convert the date string to a datetime object ---
                expense_data['date'] = datetime.strptime(expense_data['date'], '%Y-%m-%d')
                expense = Expense(**expense_data)
                session.add(expense)
            logger.info(f"Seeded {len(sample_data.get('expenses', []))} expense records.")

            session.commit() # --- Commit all changes ---
            logger.info("Sample data successfully seeded to the database.")

        except Exception as e:
            logger.error(f"An error occurred during seeding: {e}")
            session.rollback()
            raise