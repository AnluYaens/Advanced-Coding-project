import tkinter as tk
from tkinter import messagebox
from core.models import Expense
from core.database import SessionLocal
from services.currency_api import get_exchange_rate

# Clase principal de la aplicación
class BudgetApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # 🖥️ Configuración de la ventana principal
        self.title("AI Budget Tracker")
        self.geometry("1000x700")  # Pantalla más grande
        self.configure(bg="#f0f0f0")  # Fondo claro (opcional)

        self.expenses = []

        # 🔵 Título principal
        self.label = tk.Label(self, text="Welcome to your Budget Assistant!", font=("Arial", 24, "bold"), bg="#f0f0f0")
        self.label.pack(pady=20)

        # 🔵 Botones principales
        self.add_expense_button = tk.Button(self, text="Add Expense", command=self.add_expense, width=20, height=2)
        self.add_expense_button.pack(pady=20)

        self.view_summary_button = tk.Button(self, text="View Summary", command=self.view_summary, width=20, height=2)
        self.view_summary_button.pack(pady=20)

        # 🔵 Campo de selección de moneda (movido aquí al final)
        self.selected_currency = tk.StringVar()
        self.selected_currency.set("USD")  # Moneda base por defecto

        tk.Label(self, text="Select currency:", font=("Arial", 14), bg="#f0f0f0").pack(pady=15)
        currency_options = ["USD", "EUR", "COP", "GBP", "JPY"]  # Puedes agregar más
        self.currency_menu = tk.OptionMenu(self, self.selected_currency, *currency_options)
        self.currency_menu.config(width=15)
        self.currency_menu.pack(pady=10)

    def add_expense(self):
        # Ventana nueva para ingresar gasto
        expense_window = tk.Toplevel(self)
        expense_window.title("Add New Expense")
        expense_window.geometry("400x400")

        # Campos de entrada
        tk.Label(expense_window, text="Amount ($):", font=("Arial", 12)).pack(pady=10)
        amount_entry = tk.Entry(expense_window)
        amount_entry.pack(pady=5)

        tk.Label(expense_window, text="Category:", font=("Arial", 12)).pack(pady=10)
        category_entry = tk.Entry(expense_window)
        category_entry.pack(pady=5)

        tk.Label(expense_window, text="Description:", font=("Arial", 12)).pack(pady=10)
        description_entry = tk.Entry(expense_window)
        description_entry.pack(pady=5)

        def save_expense():
            amount = amount_entry.get()
            category = category_entry.get()
            description = description_entry.get()

            if not amount or not category:
                messagebox.showerror("Error", "Amount and category are required!")
                return

            try:
                amount = float(amount)
            except ValueError:
                messagebox.showerror("Error", "Amount must be a number!")
                return

            self.expenses.append({
                "amount": amount,
                "category": category,
                "description": description
            })

            # Guardar en la base de datos
            db = SessionLocal()
            new_expense = Expense(amount=amount, category=category, description=description)
            db.add(new_expense)
            db.commit()
            db.close()

            messagebox.showinfo("Expense Saved", f"Amount: ${amount}\nCategory: {category}\nDescription: {description}")
            expense_window.destroy()

        save_button = tk.Button(expense_window, text="Save Expense", command=save_expense, width=15, height=2)
        save_button.pack(pady=20)

    def view_summary(self):
        db = SessionLocal()
        expenses = db.query(Expense).all()
        db.close()

        if not expenses:
            messagebox.showinfo("Summary", "No expenses recorded yet.")
            return

        total_usd = sum(expense.amount for expense in expenses)

        selected_currency = self.selected_currency.get()
        exchange_rate = 1  # Por defecto si es USD

        if selected_currency != "USD":
            exchange_rate = get_exchange_rate("USD", selected_currency)
            if not exchange_rate:
                messagebox.showerror("Error", "Could not fetch exchange rate.")
                return

        total_converted = total_usd * exchange_rate

        #construir el mensaje con cada gasto convertido también
        summary_message = f"Total Expenses: {total_converted:.2f} {selected_currency}\n\nDetails:\n"

        for expense in expenses:
            converted_amount = expense.amount * exchange_rate
            summary_message += f"- {expense.category}: {converted_amount:.2f} {selected_currency}\n"

        messagebox.showinfo("Summary", summary_message)


# Punto de entrada
if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()
