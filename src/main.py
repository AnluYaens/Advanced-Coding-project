

from src.core.database_anterior import init_db
from src.ui.interface_ctk_2 import BudgetApp

if __name__ == '__main__':
    init_db()
    app = BudgetApp()
    app.mainloop()
    