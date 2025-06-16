from src.core.database import init_db
from src.ui.interface_ctk import BudgetApp

if __name__ == '__main__':
    init_db()
    app = BudgetApp()
    app.mainloop()
