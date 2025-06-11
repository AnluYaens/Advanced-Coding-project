import os
from typing import Dict
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Crea base antes de tocar los modelos - evita el import circular
Base = declarative_base()


# SQlite setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Subir dos niveles para llegar a la raiz del proyecto
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir, os.pardir))
DB_FILE = os.path.join(ROOT_DIR, 'budget_tracker.db')


DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Soporte multihilo de SQLite
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# importa modelos despues de base - ya no hay ciclo
from .models import Budget, Expense

# Crear tablas si no existen
def init_db() -> None:
    """create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


# New helper functions for the budget dialog

def save_budget(budget_dict: Dict[str, float]) -> None:
    """Insert or update budget limits."""
    session= SessionLocal()
    try:
        for category, limit in budget_dict.items():
            obj = (
                session.query(Budget)
                .filter(Budget.category == category.lower())
                .first()
            )
            if obj:
                obj.limit = limit
            else:
                obj = Budget(category=category.lower(), limit=limit)
                session.add(obj)
        session.commit()
    finally:
        session.close()


def get_budget() -> Dict[str, float]:
    """Return budgets as a dict {category: limit}."""
    session = SessionLocal()
    try:
        return {b.category: b.limit for b in session.query(Budget).all()}
    finally:
        session.close()

# ──  Expense helpers  ─────────────────────────────────────────────────
def add_expense(amount: float, category: str, description: str = "") -> None:
    """Persist a new expense row."""
    session = SessionLocal()
    try:
        exp = Expense(
            amount=amount,
            category=category.capitalize(),
            description=description,
            date=datetime.utcnow(),
        )
        session.add(exp)
        session.commit()
    finally:
        session.close()

# Funciones del chatbot

def insert_payment(amount, category, description, date_str):
    from datetime import datetime
    session = SessionLocal()
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        exp = Expense(
            amount=amount,
            category=category.capitalize(),
            description=description,
            date=date,
        )
        session.add(exp)
        session.commit()
    finally:
        session.close()

def delete_payment(expense_id):
    session = SessionLocal()
    try:
        exp = session.query(Expense).filter(Expense.id == expense_id).first()
        if exp:
            session.delete(exp)
            session.commit()
    finally:
        session.close()

def query_expenses_by_category(category):
    session = SessionLocal()
    try:
        exps = session.query(Expense).filter(Expense.category == category.capitalize()).all()
        total = sum(e.amount for e in exps)
        return total
    finally:
        session.close()