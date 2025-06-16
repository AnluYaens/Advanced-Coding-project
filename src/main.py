from src.core.database import init_db
from src.ui.interface_ctk import BudgetApp

if __name__ == '__main__':
    init_db()
    # init_db(create_sample_data=True) ---> use this if you want to use the sample_data for the database
    #                                       ( This will only work if the database is empty if not is not going to work )
    app = BudgetApp()
    app.mainloop()
