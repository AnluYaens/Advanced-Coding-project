import os
import logging
from typing import Dict, List
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# --- Configure logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Create base ---
Base = declarative_base()

# --- SQLite setup with absolute paths ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir, os.pardir))
DB_FILE = os.path.join(ROOT_DIR, 'budget_tracker.db')

# --- Create directory if it doesn't exist ---
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_FILE}"

# --- Engine with optimized configuration ---
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    echo=False,  # --- Change to True for SQL debug ---
    pool_pre_ping=True,
    pool_recycle=3600,
)

# --- Enable WAL mode for SQLite (better concurrency) ---
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# --- Import models after Base and engine creation ---
from .models import Budget, Expense

@contextmanager
def get_db_session():
    """Context manager for safe database session handling."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        session.close()

def init_db() -> None:
    """Create all database tables if they don't exist."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")
        raise


# ──────────────────────── BUDGET FUNCTIONS ────────────────────────

def save_budget(budget_dict: Dict[str, float]) -> None:
    """Insert or update budget limits."""
    try:
        with get_db_session() as session:
            for category, limit in budget_dict.items():
                if limit < 0:
                    raise ValueError(f"Limit for {category} cannot be negative")
                
                if not category or not category.strip():
                    raise ValueError("Category cannot be empty")
                
                obj = (
                    session.query(Budget)
                    .filter(Budget.category == category.lower().strip())
                    .first()
                )
                if obj:
                    obj.limit = limit
                else:
                    obj = Budget(category=category.lower().strip(), limit=limit)
                    session.add(obj)
        
        logger.info(f"Budget saved: {budget_dict}")
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving budget: {e}")
        raise

def get_budget() -> Dict[str, float]:
    """Return budgets as dictionary {category: limit}."""
    try:
        with get_db_session() as session:
            budgets = session.query(Budget).all()
            return {b.category: b.limit for b in budgets}
            
    except Exception as e:
        logger.error(f"Error getting budget: {e}")
        return {}

# ──────────────────────── EXPENSE FUNCTIONS ────────────────────────────

def add_expense(amount: float, category: str, description: str = "") -> None:
    """Save a new expense record."""
    try:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        if not category:
            raise ValueError("Category cannot be empty")
        
        with get_db_session() as session:
            exp = Expense(
                amount=amount,
                category=category.capitalize(),
                description=description.strip(),
                date=datetime.now(),  
            )
            session.add(exp)
        
        logger.info(f"Expense added: ${amount} in {category}")
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error adding expense: {e}")
        raise

def update_expense(expense_id: int, new_data: Dict) -> bool:
    """Updates an existing expense record by its ID."""
    try:
        with get_db_session() as session:
            expense = session.query(Expense).filter(Expense.id == expense_id).first()
            if not expense:
                return False
            
            # --- refresh with new data ---
            for key, value in new_data.items():
                if hasattr(expense, key):
                    setattr(expense, key, value)
            
            # --- if date == string --> special configuration ---
            if 'date' in new_data and isinstance(new_data['date'], str):
                try:
                    expense.date = datetime.strptime(new_data['date'], '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Invalid date format for update: {new_data['date']}. Keeping original.")

            logger.info(f"Expense updated: ID {expense_id}")
            return True 
            
    except Exception as e:
        logger.error(f"Error updating expense: {e}")
        raise

def get_all_expenses(limit: int = None, category: str = None, month: int = None, year: int = None) -> List[Expense]:
    """
    Get all expenses with optional filters for category, month, and year.
    """
    try:
        with get_db_session() as session:
            from sqlalchemy import extract
            query = session.query(Expense).order_by(Expense.date.desc())

            # --- Aplied filters if necesary ---
            if category and category.lower() != 'all':
                query = query.filter(Expense.category == category)
            
            if month and month != 0:
                query = query.filter(extract('month', Expense.date) == month)

            if year and year != 0:
                query = query.filter(extract('year', Expense.date) == year)

            if limit:
                query = query.limit(limit)
            
            expenses = query.all()
            session.expunge_all()
            return expenses
            
    except Exception as e:
        logger.error(f"Error getting expenses: {e}")
        return []

def get_expenses_by_month(month: int, year: int) -> List[Expense]:
    """Get expenses for a specific month."""
    try:
        if not (1 <= month <= 12):
            raise ValueError("Month must be between 1 and 12")
        
        if year < 1900 or year > datetime.now().year + 1:
            raise ValueError("Year must be reasonable")
        
        with get_db_session() as session:
            from sqlalchemy import extract
            
            expenses = (
                session.query(Expense)
                .filter(
                    extract('month', Expense.date) == month,
                    extract('year', Expense.date) == year
                )
                .order_by(Expense.date.desc())
                .all()
            )
            session.expunge_all()
            return expenses
            
    except Exception as e:
        logger.error(f"Error getting expenses for month {month}/{year}: {e}")
        return []

def list_expenses_by_category(category: str) -> list[dict]:
    """Return all expenses for a category with id, amount and date"""
    with get_db_session() as session:
        results = (
            session.query(Expense)
            .filter(Expense.category.ilike(category))
            .order_by(Expense.date.desc())
            .all()
        )
        return [
            {
                "id": e.id,
                "amount": e.amount,
                "date": e.date.strftime("%Y-%m-%d") if e.date else "Unknown",
                "description": e.description or ""
            }
            for e in results
        ]

# ──────────────────────── CHATBOT FUNCTIONS ────────────────────────────

def insert_payment(amount: float, category: str, description: str, date: str) -> None:
    """Insert payment from chatbot."""
    try:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        
        if not category or not category.strip():
            raise ValueError("Category cannot be empty")
        
        # --- Parse date ---
        if isinstance(date, str):
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                # --- Other common formats ---
                try:
                    date_obj = datetime.strptime(date, "%d/%m/%Y")
                except ValueError:
                    date_obj = datetime.now()
        else:
            date_obj = date
        
        with get_db_session() as session:
            exp = Expense(
                amount=amount,
                category=category.capitalize(),
                description=description.strip(),
                date=date_obj,
            )
            session.add(exp)
        
        logger.info(f"Payment inserted by AI: ${amount} in {category}")
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inserting payment: {e}")
        raise

def insert_payment_safe(amount: float, category: str, description: str, date_str: str) -> None:
    """
    Safe wrapper for insert_payment that handles multiple date formats.
    
    Args:
        amount: Expense amount
        category: Expense category
        description: Expense description
        date_str: Date as string (supports various formats) or datetime object
    """
    from datetime import datetime
    
    # --- Validate date ---
    try:
        if isinstance(date_str, str):
            # --- Try multiple common formats ---
            date_formats = [
                "%Y-%m-%d",      # 2025-01-15
                "%d/%m/%Y",      # 15/01/2025
                "%m/%d/%Y",      # 01/15/2025
                "%Y/%m/%d",      # 2025/01/15
                "%d-%m-%Y",      # 15-01-2025
                "%m-%d-%Y",      # 01-15-2025
            ]
            
            date_obj = None
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str.strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if date_obj is None:
                # --- If no format worked, use current date ---
                logger.warning(f"Could not parse date '{date_str}', using current date")
                date_obj = datetime.utcnow()
        else:
            date_obj = date_str
            
        with get_db_session() as session:
            exp = Expense(
                amount=amount,
                category=category.capitalize(),
                description=description.strip(),
                date=date_obj,
            )
            session.add(exp)
            session.flush()  # --- Forces ID creation ---
            session.expunge(exp)  # --- Detach from session before return ---
            return exp
        
    except Exception as e:
        logger.error(f"Error in insert_payment_safe: {e}")
        raise

def delete_payment(expense_id: int) -> bool:
    """Delete payment by ID."""
    try:
        if expense_id <= 0:
            raise ValueError("Expense ID must be positive")
        
        with get_db_session() as session:
            exp = session.query(Expense).filter(Expense.id == expense_id).first()
            if exp:
                session.delete(exp)
                logger.info(f"Expense deleted: ID {expense_id}")
                return True
            else:
                logger.warning(f"Expense not found: ID {expense_id}")
                return False
                
    except Exception as e:
        logger.error(f"Error deleting payment: {e}")
        raise

def query_expenses_by_category(category: str) -> float:
    """Query total expenses by category."""
    try:
        with get_db_session() as session:
            expenses = (
                session.query(Expense)
                .filter(Expense.category == category.capitalize())
                .all()
            )
            total = sum(e.amount for e in expenses)
            
        logger.info(f"Query by category {category}: ${total}")
        return total
        
    except Exception as e:
        logger.error(f"Error querying expenses by category: {e}")
        return 0.0

def get_expense_summary() -> Dict[str, float]:
    """Get expense summary by category."""
    try:
        with get_db_session() as session:
            expenses = session.query(Expense).all()
            
        summary = {}
        for expense in expenses:
            category = expense.category
            if category in summary:
                summary[category] += expense.amount
            else:
                summary[category] = expense.amount
                
        return summary
        
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return {}

# ──────────────────────── UTILITY FUNCTIONS ────────────────────────────

def reset_database() -> None:
    """Reset database (for testing only)."""
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Database reset")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise

def check_database_health() -> bool:
    """Check that database is working properly."""
    try:
        with get_db_session() as session:
            # --- Simple query to verify connectivity ---
            session.execute("SELECT 1")
        return True
        
    except Exception as e:
        logger.error(f"Database health error: {e}")
        return False

if __name__ == "__main__":
    # --- Basic test ---
    try:
        init_db()
        if check_database_health():
            print("✅ Database working correctly")
            
            # --- Show statistics ---
            with get_db_session() as session:
                expense_count = session.query(Expense).count()
                budget_count = session.query(Budget).count()
                print(f"📊 Expenses: {expense_count}, Budgets: {budget_count}")
        else:
            print("❌ Database error")
            
    except Exception as e:
        print(f"❌ Error: {e}")