from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from .database import Base
from datetime import datetime

class Expense(Base):
    """Model for storing expense records"""
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<Expense(id={self.id}, amount={self.amount}, category='{self.category}', date={self.date})>"

    def to_dict(self):
        """convert to dictionary for JSON serialization"""
        return{
            'id': self.id,
            'amount': self.amount,
            'category': self.category,
            'description': self.description,
            'date': self.date.isoformat() if self.date else None
        }

class Budget(Base):
    """Model for storing budget limits by category"""
    __tablename__ = 'budgets'

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, unique=True)
    limit = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Budget(category='{self.category}', limit={self.limit})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'category': self.category,
            'limit': self.limit
        }

# --- Index for performance on common queries ---
Index('idx_expense_category_date', Expense.category, Expense.date)