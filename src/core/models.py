from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Expense(id={self.id}, amount={self.amount}, category='{self.category}', date={self.date})>"

class Budget(Base):
    __tablename__ = 'budgets'

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, unique=True)
    limit = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Budget(category='{self.category}', limit={self.limit})>"

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    categories = relationship('Category', back_populates='user')

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String, nullable=False)
    user = relationship('User', back_populates='categories')

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship('Category')