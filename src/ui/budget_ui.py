import customtkinter as ctk
from tkinter import messagebox
from core.database import SessionLocal
from core.models import Budget


def show_budget_window(parent):
    # Extraer colores desde parent
    bg = parent.card_bg
    text = parent.text
    primary = parent.accent

    win = ctk.CTkToplevel(parent)
    win.title('Set Budget')
    win.geometry('400x300')
    win.configure(fg_color=bg)
    
    # Formulario
    ctk.CTkLabel(win, text='Category:', text_color=text).pack(pady=(20,5))
    entry_cat = ctk.CTkEntry(win, width=200)
    entry_cat.pack()

    ctk.CTkLabel(win, text='Limit ($):', text_color=text).pack(pady=(20,5))
    entry_lim = ctk.CTkEntry(win, width=200)
    entry_lim.pack()

    def save():
        cat = entry_cat.get().strip()
        lim_text = entry_lim.get().strip()
        if not cat or not lim_text:
            return messagebox.showerror('Error','Both fields required')
        try:
            lim = float(lim_text)
        except ValueError:
            return messagebox.showerror('Error','Limit must be number')
        db = SessionLocal()
        existing = db.query(Budget).filter_by(category=cat).first()
        if existing:
            existing.limit = lim
            db.commit()
            messagebox.showinfo('Updated', f"Budget '{cat}' updated to ${lim:.2f}")
        else:
            b = Budget(category=cat, limit=lim)
            db.add(b)
            db.commit()
            messagebox.showinfo('Saved', f"New budget for '{cat}' with limit ${lim:.2f}")
        db.close()
        win.destroy()

    ctk.CTkButton(win, text='Save Budget', command=save,
                 fg_color=primary, hover_color=parent.hover).pack(pady=20)