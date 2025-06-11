import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.interpolate import PchipInterpolator
import math

from src.core.database_anterior import (
    SessionLocal, 
    save_budget, 
    get_budget, 
    add_expense
)
from src.core.models import Expense
from src.core.ai_engine import chat_completion
from src.services.currency_api import get_exchange_rate


# tratar de buscar una manera en la cual alguien suba una foto o algo de su bank statement
#  y la app la agregue automaticamente con ayuda de la AI o algo
# y asi la persona no tenga que meter todo manual sino solo cambios puntuales 

# ───────────────────────────────── THEME HANDLING ─────────────────────────
# Definimos TODOS los colores hex en un único diccionario.  A partir de aquí
# no deberíamos volver a escribir un literal "#rrggbb" en el código para mantener
# la coherencia y poder cambiar de tema en un solo lugar.

PALETTE = {
    "bg": "#1e1b2e",      # fondo general (dark violet)
    "card": "#2d235f",    # fondo de tarjetas / frames
    "accent": "#6d28d9",  # color destacado (botones, líneas)
    "hover": "#7c3aed",   # color al pasar el ratón
    "text": "#f9fafb",    # texto principal (casi blanco)
}

# Si mañana quieres un tema claro sólo cambias las 5 líneas de arriba o cargas
# otro diccionario desde un JSON.

# Config global CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BudgetApp(ctk.CTk):
    """Ventana principal de la aplicación de presupuesto."""

    def __init__(self):
        super().__init__()
        self.title("AI Budget Tracker")
        self.geometry("820x920")
        self.resizable(False, False)

        # ---- Paleta accesible en toda la instancia ----
        self.colors = PALETTE.copy()  # por si quieres mutar en caliente (theme switch)
        # Alias cortos para no refactorizar todo el código antiguo
        self.bg       = self.colors["bg"]
        self.card_bg  = self.colors["card"]
        self.accent   = self.colors["accent"]
        self.hover    = self.colors["hover"]
        self.text     = self.colors["text"]

        # Fondo de la ventana
        self.configure(fg_color=self.bg)
        
        # ✅ MEJORA: Guardar referencias a secciones principales
        self.main_sections = {}
        
        # Build UI
        self._create_top_tabs()
        self._create_header()
        self._create_charts_section()
        self._create_converter_section()

     # ─────────────────────────── HELPERS BD ────────────────────────────
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

    # Top bar
    def _create_top_tabs(self):
        bar = ctk.CTkFrame(self, fg_color=self.card_bg, height=40)
        bar.pack(fill="x")
        
        # ✅ MEJORA: Guardar referencia
        self.main_sections['top_bar'] = bar

        contact_btn = ctk.CTkButton(
            bar, 
            text="Contact",
            width=80,
            fg_color=self.card_bg,
            hover_color=self.hover,
            text_color=self.text,
            command=self.show_contact,
        )
        contact_btn.place(relx=0.02, rely=0.5, anchor="w")

        ai_btn = ctk.CTkButton(
            bar,
            text="AI Assistant",
            width=110,
            fg_color=self.card_bg,
            hover_color=self.hover,
            text_color=self.text,
            command=self.open_ai_assistant,
        )
        ai_btn.place(relx=0.98, rely=0.5, anchor="e")

     # ─────────────────────── HEADER + NAV ───────────────────────────────
    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=12)
        header.pack(pady=20, padx=60, fill="x")
        
        # ✅ MEJORA: Guardar referencia
        self.main_sections['header'] = header

        ctk.CTkLabel(
            header, 
            text="Budget Assistant", 
            font=("Arial",32,"bold"), 
            text_color=self.text
        ).pack(pady=(20,10))

        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(pady=(0,20))

        for i,(label,cmd) in enumerate(
            [
                ("Add Expense", self.add_expense),
                ("Spending Analysis", self.view_summary),
                ("Set Budget", self.set_budget),
            ]
        ):
            ctk.CTkButton(
                btns, text=label, command=cmd,
                width=200, height=50,
                fg_color=self.card_bg,
                hover_color=self.hover,
                text_color=self.text, 
                font=("Arial",16), 
                corner_radius=12
            ).grid(row=0, column=i, padx=20)

    # ────────────────────── Charts Section ─────────────────────────
    def _create_charts_section(self):
        sec = ctk.CTkFrame(
            self, 
            fg_color=self.bg, 
            corner_radius=12, 
            border_width=2, 
            border_color=self.accent
        )
        sec.pack(pady=10, padx=60, fill="x")
        
        # ✅ MEJORA: Guardar referencia
        self.main_sections['charts'] = sec
        
        # Titles
        trow = ctk.CTkFrame(sec, fg_color="transparent")
        trow.pack(fill="x", padx=20, pady=(20,0))
        ctk.CTkLabel(
            trow, text="Expense Chart", font=("Arial",20,"bold"), 
            text_color=self.text).pack(side="left")
        ctk.CTkLabel(
            trow, text="By category", font=("Arial",20,"bold"), 
            text_color=self.text).pack(side="right")
        
       # ───────────────────────── Charts rows ───────────────────────────────
        crow = ctk.CTkFrame(sec, fg_color="transparent")
        crow.pack(fill="x", padx=20, pady=20)

        left = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        left.pack(side="left", expand=True, fill="both", padx=10)

        right = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        right.pack(side="right", expand=True, fill="both", padx=10)

        self.show_line_chart(left)
        self.show_donut_chart(right)


    # ───────────────────────── LINE CHART ───────────────────────────────
    def show_line_chart(self, parent):
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        data = self.get_expenses_by_month()
        x = np.arange(len(months))
        
        # --- Rango Y ---
        max_val = max(data) if any(data) else 1
        y_top = round(max_val * 1.25)

        # --- Preparar figura ---
        fig, ax = plt.subplots(figsize=(5, 3.2), dpi=100)
        fig.patch.set_facecolor(self.card_bg)
        ax.set_facecolor(self.card_bg)

        # --- Curva suave siempre que haya al menos 2 puntos distintos ---
        if len(set(data)) > 1:
            x_smooth = np.linspace(x.min(), x.max(), 300)
            y_smooth = PchipInterpolator(x, data)(x_smooth)

            ax.plot(
                x_smooth, y_smooth,
                color=self.accent,
                linewidth=2.5,
                solid_capstyle='round',
                zorder=1,
            )
        else:
            # Si todo es igual (o casi), trazamos línea recta
            ax.plot(
                x, data,
                color=self.accent,
                linewidth=2.5,
                marker="o",
                markersize=6,
                markerfacecolor=self.accent,
                markeredgewidth=1.5,
                markeredgecolor='white',
                zorder=1,
            )

        #Puntos & etiquetas (sólo si > 1)
        for xi, val in zip(x, data):
            if val > 1:
                # punto
                ax.scatter(
                    xi, val,
                    color=self.accent,
                    edgecolors='white',
                    s=60,
                    linewidth=1.5,
                    zorder=3
                )
                # etiqueta
                ax.text(
                    xi, val + y_top * 0.03,
                    f"${val:,.0f}",
                    fontsize=9,
                    color=self.text,
                    ha='center',
                    va='bottom',
                    fontweight='bold'
                )

        # Ejes y límites apariencia
        ax.set_xlim(-0.4, len(months) - 0.6) # mejor distribuicion horizontal
        ax.set_ylim(0, y_top)
        ax.set_xticks(x)
        ax.set_xticklabels(
            months, 
            color=self.text, 
            fontsize=10, 
            fontname="Segoe UI", 
            fontweight="bold"
        )
        ax.tick_params(axis='y', colors=self.text, labelsize=10)

        # — Cuadrícula y bordes —
        ax.grid(
            axis='y', linestyle='--', linewidth=0.5, color='#43337a', alpha=0.5
        )
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Margen horizontal minimo + ajuste global
 
        ax.margins(x=0.02)          # ocupa mejor el ancho 
        fig.tight_layout(pad=1)     # evita que se corte dentro del card

        # insertar en el widget ctk
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=10)
        

    # Donut Chart
    def show_donut_chart(self, parent):
        categories = ["Groceries", "Electronics", "Entertainment", "Other"]
        vals = [
            0 if (v is None or (isinstance(v, float) and math.isnan(v)))
            else v
            for v in self.get_expenses_by_category()
        ]

        if sum(vals) == 0:
            ctk.CTkLabel(
                parent,
                text="No data to display",
                text_color=self.text,
                font=("Arial", 14, "bold")
            ).pack(expand=True, pady=50)
            return

        # Colores personalizados (en tono violeta azulado)
        colors = [
            "#7c3aed",  # morado fuerte
            "#8b5cf6",  # violeta claro
            "#a78bfa",  # lavanda
            "#ddd6fe",  # pastel
        ][:len(vals)]

        total = sum(vals)

        # --- Figura en dos partes (gráfico + leyenda) ---
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(4.5, 4.3),
            dpi=100,
            gridspec_kw={'height_ratios': [3.2, 1.2]}
        )
        fig.patch.set_facecolor(self.card_bg)
        ax1.set_facecolor(self.card_bg)
        ax2.set_facecolor(self.card_bg)

        ax1.pie(vals, wedgeprops=dict(width=0.5), startangle=90, colors=colors)
        ax1.add_artist(plt.Circle((0, 0), 0.45, fc=self.card_bg))
        ax1.axis("off")

        ax2.axis("off")
        ax2.set_xlim(0, 1)
        spacing = 0.25
        top_y = 1.0

        for i, (cat, val, color) in enumerate(zip(categories, vals, colors)):
            percent = (val / total * 100) if total else 0
            # Usamos dos columnas: ● + categoría, luego monto y porcentaje alineado a la derecha
            ax2.text(
                0.05, 
                top_y - i * spacing,
                f"● {cat}",
                fontsize=11,
                color=color,
                ha="left",
                va="center",
                fontweight="bold"
            )
            ax2.text(
                0.95, 
                top_y - i * spacing,
                f"${val:,.0f} ({percent:.0f}%)",
                fontsize=10,
                color=self.text,
                ha="right",
                va="center",
                fontweight="bold"
            )

        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.2)

        # --- Mostrar en la app ---
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=10)


    # Converter Section
    def _create_converter_section(self):
        sec = ctk.CTkFrame(
            self, fg_color=self.card_bg, corner_radius=12
        )
        sec.pack(pady=25, padx=60, fill="x")
        
        # ✅ MEJORA: Guardar referencia
        self.main_sections['converter'] = sec

        ctk.CTkLabel(
            sec, text="Transfer Calculator", 
            font=("Arial",20,"bold"), 
            text_color=self.text
        ).pack(pady=(20,10))

        grid = ctk.CTkFrame(sec, fg_color="transparent")
        grid.pack(pady=10)

        # amount
        ctk.CTkLabel(grid, text="Amount:", text_color=self.text).grid(
            row=0, column=0, sticky="e", padx=(0, 10)
        )
        self.amount_var = tk.DoubleVar(value=1.0)
        amt_entry = ctk.CTkEntry(grid, textvariable=self.amount_var, width=100)
        amt_entry.grid(row=0, column=1, sticky="w")
        amt_entry.bind("<KeyRelease>", lambda *_: self._update_conversion())

        # --- From / To currencies --------------------------------------------
        currs = ["USD", "EUR", "GBP", "MXN", "JPY", "CAD"]
        self.from_var = tk.StringVar(value="USD")
        self.to_var = tk.StringVar(value="EUR")

        def _trace(*_): self._update_conversion()
        self.from_var.trace_add("write", _trace)
        self.to_var.trace_add("write", _trace)

        ctk.CTkLabel(grid, text="From", text_color=self.text).grid(
            row=0, column=2, padx=(20, 4)
        )
        ctk.CTkOptionMenu(
            grid, variable=self.from_var, values=currs,
            width=80,
            fg_color=self.accent,
            button_color=self.accent,
            text_color="white",
            dropdown_fg_color="#2d235f",      # menú desplegable oscuro
            dropdown_text_color="white"
        ).grid(row=0, column=3)

        ctk.CTkLabel(grid, text="To", text_color=self.text).grid(
            row=0, column=4, padx=(20, 4)
        )
        ctk.CTkOptionMenu(
            grid, variable=self.to_var, values=currs,
            width=80,
            fg_color=self.accent,
            button_color=self.accent,
            text_color="white",
            dropdown_fg_color="#2d235f",
            dropdown_text_color="white"
        ).grid(row=0, column=5)

        # --- Result labels ----------------------------------------------------
        self.result_lbl = ctk.CTkLabel(
            sec, text="", font=("Arial", 22, "bold"), text_color=self.text
        )
        self.rate_lbl = ctk.CTkLabel(
            sec, text="", font=("Arial", 14), text_color="#c0c0c0"
        )
        self.result_lbl.pack(pady=(12,0))
        self.rate_lbl.pack(pady=(0, 20))

        # Primera conversión inicial
        self._update_conversion()

    def _convert_currency(self, amount: float, from_curr: str, to_curr: str):
        """
        Usa service.currency_api.get_exchange_rate.
        Devuelve (importe_convertido, tipo_cambio).
        """
        if from_curr == to_curr:
            return amount, 1.0

        try:
            rate = get_exchange_rate(from_curr, to_curr)   # puede ser None
        except Exception:
            rate = None

        if rate is None:
            return 0.0, 0.0

        return amount * rate, rate
        
    def _update_conversion(self):
        # ✅ MEJORA: Manejo de errores mejorado
        try:
            amount = self.amount_var.get()
            from_c = self.from_var.get()
            to_c = self.to_var.get()
            converted, rate = self._convert_currency(amount, from_c, to_c)

            if rate == 0.0:
                self.result_lbl.configure(text="Conversion error")
                self.rate_lbl.configure(text="Unable to fetch exchange rate")
                return

            self.result_lbl.configure(
                text=f"{amount:.2f} {from_c} = {converted:.2f} {to_c}"
            )
            self.rate_lbl.configure(text=f"1 {from_c} = {rate:.3f} {to_c}")
        except Exception as e:
            self.result_lbl.configure(text="Error")
            self.rate_lbl.configure(text="Please check your input")

    # Add expense flow
    def add_expense(self):
        AddExpenseDialog(self, on_saved=self._refresh_charts)

    # Summary popup
    def view_summary(self):
        db = SessionLocal()
        exps = db.query(Expense).all()
        db.close()

        if not exps: 
            return messagebox.showinfo("Summary","No expenses recorded yet.")
        total = sum(e.amount for e in exps)
        lines = [f"{e.date.date()} - {e.category}: ${e.amount:.2f}" for e in exps]
        messagebox.showinfo("Summary", f"Total: ${total:.2f}\n\n" + "\n".join(lines))

    # Budget Dialog
    def set_budget(self):
        BudgetDialog(self)

    # Contact popup
    def show_contact(self):
        messagebox.showinfo(
            "Contact",
            "Proyecto: Advanced Coding\nAutor: Tu Nombre\n"
            "Email: tu@email.com\nGitHub: https://github.com/tuusuario",
        )

    # AI Assistant
    def open_ai_assistant(self):
        ChatWindow(self)

    # ✅ CORRECCIÓN CRÍTICA: Método _refresh_charts mejorado
    def _refresh_charts(self):
        """Método corregido para refrescar solo los gráficos de manera segura"""
        try:
            # Solo destruir y recrear la sección de gráficos
            if 'charts' in self.main_sections:
                self.main_sections['charts'].destroy()
                del self.main_sections['charts']
            
            # Recrear solo los gráficos
            self._create_charts_section()
            
        except Exception as e:
            print(f"Error refreshing charts: {e}")
            # En caso de error, mostrar mensaje al usuario
            messagebox.showerror("Error", "Unable to refresh charts. Please restart the application.")

class AddExpenseDialog(ctk.CTkToplevel):
    def __init__(self, parent: BudgetApp, on_saved):
        super().__init__(parent)
        self.title("Add Expense")
        self.geometry("340x300")
        self.grab_set()
        self.resizable(False, False)
        self.on_saved = on_saved

        # Amount
        ctk.CTkLabel(self, text="Amount", font=("Segoe UI", 14, "bold")).pack(
            pady=(20,6)
        )
        self.amount_var = tk.DoubleVar(value=0.0)
        ctk.CTkEntry(self, textvariable=self.amount_var, width=120).pack()

        # Category
        ctk.CTkLabel(self, text="Category").pack(pady=(16, 6))
        self.cat_var = tk.StringVar(value="Groceries")
        ctk.CTkOptionMenu(
            self,
            variable=self.cat_var,
            values=["Groceries", "Electronics", "Entertainment", "Other"],
        ).pack()

         # Description
        ctk.CTkLabel(self, text="Description").pack(pady=(16, 6))
        self.desc_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.desc_var, width=220).pack()

        # Buttons
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=24)
        ctk.CTkButton(
            row, 
            text="Save", 
            width=80, 
            command=self._save
            ).grid(row=0, column=0, padx=10
        )
        ctk.CTkButton(
            row,
            text="Cancel",
            width=80,
            fg_color="#444",
            hover_color="#555",
            command=self.destroy,
            ).grid(row=0, column=1, padx=10
        )

    def _save(self):
        amount = self.amount_var.get()
        if amount <= 0:
            return messagebox.showwarning("Invalid", "Amount must be > 0")

        # ✅ MEJORA: Mejor manejo de errores
        try:
            add_expense(amount, self.cat_var.get(), self.desc_var.get())
            messagebox.showinfo("Saved", "Expense recorded!")
            self.destroy()
            self.on_saved()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save expense: {str(e)}")


# ───────────────────────────── CHAT WINDOW ───────────────────────────────────
class ChatWindow(ctk.CTkToplevel):
    def __init__(self, parent: BudgetApp):
        super().__init__(parent)
        self.title("AI Assistant")
        self.geometry("480x620")
        self.grab_set()
        
        # ✅ CORRECCIÓN: Acceder a los colores del parent
        self.parent_app = parent

        self.history = []  # [(role, content), ...]

        self.chatbox = ctk.CTkTextbox(
            self, width=450, height=500, 
            state="disabled",
            fg_color="#1f1b2e", # mismo fondo que la app
            text_color="white",
            font=("Segoe UI", 13, "bold")
        )
        self.chatbox.pack(padx=15, pady=15)

        entry_row = ctk.CTkFrame(self, fg_color="transparent")
        entry_row.pack(pady=(0, 15), fill="x")

        self.msg_var = tk.StringVar()
        entry = ctk.CTkEntry(entry_row, textvariable=self.msg_var)
        entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        entry.bind("<Return>", lambda e: self._send())

        send_btn = ctk.CTkButton(
            entry_row,
            text="Send", 
            width=70,
            fg_color=self.parent_app.accent,  # ✅ CORRECCIÓN: Usar parent.accent
            hover_color=self.parent_app.hover,  # ✅ CORRECCIÓN: Usar parent.hover
            text_color="white", 
            command=self._send
        )
        send_btn.pack(side="right")

    def _append(self, role: str, text: str):
        self.chatbox.configure(state="normal")

        if role == "user":
            prefix = "You: "
            tag = "user"
        else:
            prefix = "Assistant: "
            tag = "assistant"

        self.chatbox.insert("end", f"{prefix} {text}\n\n", tag)
        self.chatbox.tag_config("user", foreground="#7c3aed", justify="right")      # azul claro
        self.chatbox.tag_config("assistant", foreground="#fefefe", justify="left")  # blanco
        self.chatbox.configure(state="disabled")
        self.chatbox.yview_moveto(1.0)

    def _send(self):
        msg = self.msg_var.get().strip()
        if not msg:
            return
        self.msg_var.set("")
        self._append("user", msg)
        self.history.append(("user", msg))

        try:
            reply = chat_completion(self.history)
        except Exception as e:
            reply = {"type": "text", "content": f"(Error contacting OpenAI API: {e})"}

        if reply["type"] == "text":
            # Respuesta normal
            self.history.append(("assistant", reply["content"]))
            self._append("assistant", reply["content"])

        elif reply["type"] == "function_call":
            # Ejecutar función
            name = reply["name"]
            args = reply["arguments"]

            try:
                if name == "insert_payment":
                    from src.core.database_anterior import insert_payment
                    insert_payment(**args)
                    result = f"Gasto registrado correctamente."
                    self.parent_app._refresh_charts()

                elif name == "delete_payment":
                    from src.core.database_anterior import delete_payment
                    delete_payment(**args)
                    result = f"Gasto eliminado correctamente."
                    self.parent_app._refresh_charts()

                elif name == "query_expenses_by_category":
                    from src.core.database_anterior import query_expenses_by_category
                    total = query_expenses_by_category(**args)
                    result = f"Total gastado en {args['category']}: ${total:.2f}"

                else:
                    result = f"(Función desconocida: {name})"

            except Exception as e:
                result = f"(Error ejecutando función {name}: {e})"

            self.history.append(("assistant", result))
            self._append("assistant", result)



# ────────────────────────── BUDGET DIALOG ────────────────────────────────────
class BudgetDialog(ctk.CTkToplevel):
    def __init__(self, parent: BudgetApp):
        super().__init__(parent)
        self.title("Set Budget")
        self.geometry("340x260")
        self.grab_set()
        self.resizable(False, False)

        current = get_budget() or {} 

        ctk.CTkLabel(
            self, text="Monthly Budget (total)", font=("Segoe UI", 14, "bold")
        ).pack(pady=(20, 8))
        self.total_var = tk.DoubleVar(value=current.get("total", 0.0))
        ctk.CTkEntry(self, textvariable=self.total_var, width=120).pack()

        ctk.CTkLabel(self, text="Groceries").pack(pady=(12, 4))
        self.gro_var = tk.DoubleVar(value=current.get("groceries", 0.0))
        ctk.CTkEntry(self, textvariable=self.gro_var, width=120).pack()

        ctk.CTkLabel(self, text="Entertainment").pack(pady=(8, 4))
        self.ent_var = tk.DoubleVar(value=current.get("entertainment", 0.0))
        ctk.CTkEntry(self, textvariable=self.ent_var, width=120).pack()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=20)
        ctk.CTkButton(btn_row, text="Save", width=80, command=self._save).grid(
            row=0, column=0, padx=10
        )
        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=80,
            fg_color="#444",
            hover_color="#555",
            command=self.destroy,
        ).grid(row=0, column=1, padx=10)

    def _save(self):
        # ✅ MEJORA: Validación básica
        try:
            data = {
                "total": self.total_var.get(),
                "groceries": self.gro_var.get(),
                "entertainment": self.ent_var.get(),
            }
            
            # Validar que los valores sean positivos
            for key, value in data.items():
                if value < 0:
                    messagebox.showerror("Error", f"{key.title()} cannot be negative")
                    return
            
            save_budget(data)
            messagebox.showinfo("Saved", "Budget updated!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save budget: {str(e)}")


if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()