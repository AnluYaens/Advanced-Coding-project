import tkinter as tk
import customtkinter as ctk
from tkcalendar import Calendar
from datetime import datetime
from tkinter import messagebox

from core.models import Expense
from core.database import SessionLocal
from services.currency_api import get_exchange_rate 

import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ctkchart

# Configuración de apariencia
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BudgetApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Budget Tracker")
        self.geometry("820x920")
        self.configure(fg_color="#1e1b2e")

        # Colores del tema
        self.bg = "#1e1b2e"
        self.card_bg = "#2d235f"
        self.accent = "#6d28d9"
        self.hover = "#7c3aed"
        self.text = "#f9fafb"

        # Construcción de la interfaz
        self._create_top_tabs()
        self._create_header()
        self._create_charts_section()
        self._create_converter_section()

    # Data fetching
    def get_expenses_by_month(self):
        db = SessionLocal()
        exps = db.query(Expense).all()
        db.close()
        months = ["Jan","Feb","Mar","Apr","May","Jun"]
        totals = [0]*len(months)
        for e in exps:
            if e.date and e.date.strftime('%b') in months:
                idx = months.index(e.date.strftime('%b'))
                totals[idx] += e.amount
        return totals

    def get_expenses_by_category(self):
        db = SessionLocal()
        exps = db.query(Expense).all()
        db.close()
        cats = ["Groceries","Electronics","Entertainment","Other"]
        totals = [0]*len(cats)
        for e in exps:
            cat = e.category.capitalize()
            if cat in cats:
                totals[cats.index(cat)] += e.amount
        return totals

    # UI sections
    def _create_top_tabs(self):
        bar = ctk.CTkFrame(self, fg_color=self.card_bg, height=40)
        bar.pack(fill="x")
        ctk.CTkLabel(bar, text="Contact", text_color=self.text, font=("Arial",14)).place(relx=0.02, rely=0.5, anchor="w")
        ctk.CTkLabel(bar, text="AI Assistant", text_color=self.text, font=("Arial",14)).place(relx=0.98, rely=0.5, anchor="e")

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=12)
        header.pack(pady=20, padx=60, fill="x")
        ctk.CTkLabel(header, text="Budget Assistant", font=("Arial",32,"bold"), text_color=self.text).pack(pady=(20,10))
        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(pady=(0,20))
        for i,(label,cmd) in enumerate([
            ("Add Expense", self.add_expense),
            ("Spending Analysis", self.view_summary),
            ("Set Budget", lambda: messagebox.showinfo("Set Budget","Not implemented yet"))
        ]):
            ctk.CTkButton(
                btns, text=label, command=cmd,
                width=200, height=50,
                fg_color=self.card_bg, hover_color=self.hover,
                text_color=self.text, font=("Arial",16), corner_radius=12
            ).grid(row=0, column=i, padx=20)

    def _create_charts_section(self):
        sec = ctk.CTkFrame(self, fg_color=self.bg, corner_radius=12, border_width=2, border_color=self.accent)
        sec.pack(pady=10, padx=60, fill="x")
        # Titles
        trow = ctk.CTkFrame(sec, fg_color="transparent")
        trow.pack(fill="x", padx=20, pady=(20,0))
        ctk.CTkLabel(trow, text="Expense Chart", font=("Arial",20,"bold"), text_color=self.text).pack(side="left")
        ctk.CTkLabel(trow, text="By category", font=("Arial",20,"bold"), text_color=self.text).pack(side="right")
        # Charts
        crow = ctk.CTkFrame(sec, fg_color="transparent")
        crow.pack(fill="x", padx=20, pady=20)
        left = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        left.pack(side="left", expand=True, fill="both", padx=10)
        right = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        right.pack(side="right", expand=True, fill="both", padx=10)
        self.show_line_chart(left)
        self.show_donut_chart(right)

    def show_line_chart(self, parent):
        # Etiquetas del eje X
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun")
        data = self.get_expenses_by_month()

        # Evitar eje Y plano
        max_val = max(data) if any(data) else 1
        y_top = round(max_val * 1.2, 2)

        # mathpolib personalizado
        fig, ax = plt.subplots(figsize=(4, 2.5), dpi=100)
        # Fondo oscuro del figura y del eje
        fig.patch.set_facecolor(self.card_bg)
        ax.set_facecolor(self.card_bg)

        # Lineas y marcadores
        ax.plot(
            months,
            data,
            color=self.accent,
            linewidth=2.5,
            marker="o",
            markersize=6,
            markerfacecolor=self.accent,
            markeredgewidth=0
        )

        # Ejes
        ax.set_ylim(0, y_top)
        ax.set_xlim(-0.3, len(months) - 0.7)

        # Ticks personalizados
        ax.set_xticks(months)
        ax.tick_params(axis="x", colors=self.text, labelsize=9)
        ax.tick_params(axis="y", colors=self.text, labelsize=9)
        ax.set_yticks(ax.get_yticks())
        ax.set_yticklabels([int(v) for v in ax.get_yticks()])

        # Cuadricula suave
        ax.grid(
            True,
            which="major",
            axis="y",
            linestyle="--",
            linewidth=0.5,
            color="#43337a",
            alpha=0.7
        )
        # Ocultar spines (bordes del gráfico)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Empaquetar en Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=10)
        
    def show_donut_chart(self, parent):
        cats = ["Groceries","Electronics","Entertainment","Other"]
        vals = self.get_expenses_by_category()
        # Saneamos None/NaN --> 0
        vals = [
            0 if (v is None or (isinstance(v, float) and math.isnan(v))) 
              else v for v in vals
        ]

        if sum(vals) == 0:
            ctk.CTkLabel(
                parent,
                text="No data to display",
                text_color=self.text,
                font=("Arial", 14, "bold")
            ).pack(expand=True, pady=50)
            return
        
        colors = [self.accent, self.hover, "#43337a", self.card_bg][:len(vals)]

        fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
        fig.patch.set_facecolor(self.card_bg)
        ax.set_facecolor(self.card_bg)

        wedges, texts, autotexts = ax.pie(
            vals,
            wedgeprops=dict(width=0.5),
            startangle=90,
            colors=colors,
            autopct="%1.1f%%",
            pctdistance=0.82,
            textprops=dict(color=self.text, fontsize=9),
        )
        centre = plt.Circle((0, 0), 0.55, fc=self.card_bg)
        ax.add_artist(centre)

        ax.set(aspect="equal") 

        ax.legend(
            wedges,
            cats,
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            frameon=False,
            labelcolor=self.text,
            fontsize=9
        )

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=10)

    def _create_converter_section(self):
        frm = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=12)
        frm.pack(pady=20, padx=60, fill="x")
        ctk.CTkLabel(frm, text="Transfer Calculator", font=("Arial",20,"bold"), text_color=self.text).pack(pady=(20,10))
        form = ctk.CTkFrame(frm, fg_color="transparent")
        form.pack(pady=10)
        ctk.CTkLabel(form, text="Amount:", text_color=self.text).grid(row=0, column=0, padx=5)
        self.amount_entry = ctk.CTkEntry(form, width=100); self.amount_entry.insert(0, "1")
        self.amount_entry.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(form, text="From", text_color=self.text).grid(row=0, column=2, padx=5)
        self.from_currency = tk.StringVar(value="USD")
        ctk.CTkOptionMenu(form, values=["USD","EUR","COP","GBP","JPY"], variable=self.from_currency).grid(row=0, column=3, padx=5)
        ctk.CTkLabel(form, text="To", text_color=self.text).grid(row=1, column=2, padx=5)
        self.to_currency = tk.StringVar(value="EUR")
        ctk.CTkOptionMenu(form, values=["USD","EUR","COP","GBP","JPY"], variable=self.to_currency).grid(row=1, column=3, padx=5)
        self.result_label = ctk.CTkLabel(frm, text="", font=("Arial",24,"bold"), text_color=self.text)
        self.result_label.pack(pady=(10,0))
        self.exchange_rate_label = ctk.CTkLabel(frm, text="", font=("Arial",12), text_color=self.text)
        self.exchange_rate_label.pack(pady=(0,20))
        self.amount_entry.bind("<KeyRelease>", lambda e: self.update_conversion())
        self.from_currency.trace("w", lambda *args: self.update_conversion())
        self.to_currency.trace("w", lambda *args: self.update_conversion())
        self.update_conversion()

    def add_expense(self):
        win = ctk.CTkToplevel(self)
        win.transient(self); win.grab_set(); win.lift(); win.focus_force()
        win.title("Add New Expense"); win.geometry("420x550"); win.configure(fg_color=self.card_bg)
        cont = ctk.CTkFrame(win, fg_color=self.card_bg); cont.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(cont, text="Add New Expense", font=("Arial",18,"bold"), text_color=self.text).pack(pady=(0,10))
        amt = ctk.CTkEntry(cont, placeholder_text="e.g. 25.00")
        ctk.CTkLabel(cont, text="Amount ($):", text_color=self.text).pack(anchor="w")
        amt.pack(fill="x", pady=(0,10))
        cat = ctk.CTkEntry(cont, placeholder_text="e.g. Food")
        ctk.CTkLabel(cont, text="Category:", text_color=self.text).pack(anchor="w")
        cat.pack(fill="x", pady=(0,10))
        desc = ctk.CTkEntry(cont, placeholder_text="Optional")
        ctk.CTkLabel(cont, text="Description:", text_color=self.text).pack(anchor="w")
        desc.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(cont, text="Select Date:", text_color=self.text).pack(anchor="w")
        cal = Calendar(cont, selectmode='day', year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                       background=self.text, foreground=self.card_bg, selectbackground=self.accent, selectforeground=self.text)
        cal.pack(fill="x", pady=(0,15))
        ctk.CTkButton(cont, text="Save Expense", command=lambda: self._save_expense(amt, cat, desc, cal),
                      width=180, height=40, fg_color=self.accent, hover_color=self.hover,
                      text_color=self.text, corner_radius=12).pack(pady=(10,0))

    def _save_expense(self, amt_entry, cat_entry, desc_entry, cal):
        a = amt_entry.get().strip(); c = cat_entry.get().strip(); d = desc_entry.get().strip()
        date_val = cal.selection_get()
        if not a or not c: return messagebox.showerror("Error","Amount and category required.")
        try: val = float(a); assert val>0
        except: return messagebox.showerror("Error","Enter a positive number.")
        db = SessionLocal()
        exp = Expense(amount=val, category=c, description=d, date=datetime.combine(date_val, datetime.min.time()))
        db.add(exp); db.commit(); db.close()
        messagebox.showinfo("Saved", f"{c} - ${val:.2f} on {date_val}")
        win = amt_entry.master.master; win.destroy()

    def view_summary(self):
        db = SessionLocal(); exps = db.query(Expense).all(); db.close()
        if not exps: return messagebox.showinfo("Summary","No expenses recorded yet.")
        total = sum(e.amount for e in exps)
        lines = [f"{e.date.date()} - {e.category}: ${e.amount:.2f}" for e in exps]
        messagebox.showinfo("Summary", f"Total: ${total:.2f}\n\n" + "\n".join(lines))

    def update_conversion(self):
        txt = self.amount_entry.get().strip()
        try: val = float(txt)
        except: return self.result_label.configure(text="Invalid amount", text_color="#ef4444")
        fr = self.from_currency.get(); to = self.to_currency.get()
        rate = 1 if fr==to else get_exchange_rate(fr,to)
        if not rate: return self.result_label.configure(text="Rate unavailable", text_color="#ef4444")
        conv = val*rate
        self.result_label.configure(text=f"{val:,.2f} {fr} = {conv:,.2f} {to}")
        self.exchange_rate_label.configure(text=f"1 {fr} = {rate:.3f} {to}")

if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()
