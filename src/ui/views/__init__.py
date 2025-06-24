"""
Application views for different features.
"""

from src.ui.views.dashboard import DashboardView
from src.ui.views.add_expense import AddExpenseView
from src.ui.views.analytics import AnalyticsView
from src.ui.views.insights import AIInsightsView
from src.ui.views.budget import BudgetView
from src.ui.views.currency import CurrencyView
from src.ui.views.contact import ContactView
from src.ui.views.all_transactions import AllTransactionsView

__all__ = [
    'DashboardView',
    'AddExpenseView',
    'AllTransactionsView',
    'AnalyticsView',
    'AIInsightsView',
    'BudgetView',
    'CurrencyView',
    'ContactView'
]