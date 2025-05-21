import os
import sys

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.database import init_db
from ui.interface_ctk import BudgetApp

if __name__ == '__main__':
    init_db()
    app = BudgetApp()
    app.mainloop()
    