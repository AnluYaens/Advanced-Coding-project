import tkinter as tk  # Importa la librería estándar de Tkinter para construir interfaces gráficas
import customtkinter as ctk  # Extensión de Tkinter con estilos y widgets modernos
from tkcalendar import Calendar  # Widget de calendario para seleccionar fechas
from datetime import datetime  # Para trabajar con fechas y horas
from tkinter import messagebox  # Cuadros de diálogo emergentes

from core.models import Expense  # Modelo ORM para gastos
from core.database import SessionLocal  # Sesión de base de datos configurada
from services.currency_api import get_exchange_rate  # Función para obtener tipos de cambio

import math  # Operaciones matemáticas (p.ej. isnan)
import matplotlib.pyplot as plt  # Para generar gráficos
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Integración Matplotlib con Tkinter
import ctkchart  # Librería adicional para gráficos en CTk (si se usa)

# Configuración global de apariencia de CustomTkinter
ctk.set_appearance_mode("dark")  # Modo oscuro
ctk.set_default_color_theme("blue")  # Tema de color predeterminado

class BudgetApp(ctk.CTk):
    """
    Ventana principal de la aplicación: muestra pestañas, gráficos, conversor de divisas
    y permite agregar / visualizar gastos.
    """
    def __init__(self):
        super().__init__()
        # Configuración básica de la ventana
        self.title("AI Budget Tracker")
        self.geometry("820x920")
        self.configure(fg_color="#1e1b2e")  # Color de fondo principal

        # Variables de color del tema para reutilizar
        self.bg = "#1e1b2e"
        self.card_bg = "#2d235f"
        self.accent = "#6d28d9"
        self.hover = "#7c3aed"
        self.text = "#f9fafb"

        # Construcción de secciones de la interfaz
        self._create_top_tabs()
        self._create_header()
        self._create_charts_section()
        self._create_converter_section()

    # ----- MÉTODOS DE DATOS -----
    def get_expenses_by_month(self):
        """
        Consulta todos los gastos y devuelve una lista con totales mensuales
        para los meses de Ene a Jun.
        """
        db = SessionLocal()  # Inicializa sesión de BD
        exps = db.query(Expense).all()  # Trae todos los registros de gastos
        db.close()

        months = ["Jan","Feb","Mar","Apr","May","Jun"]
        totals = [0] * len(months)  # Inicializa totales a cero
        for e in exps:
            if e.date and e.date.strftime('%b') in months:
                idx = months.index(e.date.strftime('%b'))
                totals[idx] += e.amount  # Suma el monto al mes correspondiente
        return totals

    def get_expenses_by_category(self):
        """
        Consulta todos los gastos y devuelve totales agrupados
        por categoría: Grocery, Electronics, Entertainment, Other.
        """
        db = SessionLocal()
        exps = db.query(Expense).all()
        db.close()

        cats = ["Groceries","Electronics","Entertainment","Other"]
        totals = [0] * len(cats)
        for e in exps:
            cat = e.category.capitalize()
            if cat in cats:
                totals[cats.index(cat)] += e.amount  # Suma por categoría
        return totals

    # ----- SECCIONES DE INTERFAZ (UI) -----
    def _create_top_tabs(self):
        """
        Crea una barra superior con labels de Contacto y AI Assistant.
        """
        bar = ctk.CTkFrame(self, fg_color=self.card_bg, height=40)
        bar.pack(fill="x")
        # Etiquetas alineadas a izquierda y derecha
        ctk.CTkLabel(bar, text="Contact", text_color=self.text, font=("Arial",14)) \
            .place(relx=0.02, rely=0.5, anchor="w")
        ctk.CTkLabel(bar, text="AI Assistant", text_color=self.text, font=("Arial",14)) \
            .place(relx=0.98, rely=0.5, anchor="e")

    def _create_header(self):
        """
        Sección de encabezado con título y botones de acción.
        """
        header = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=12)
        header.pack(pady=20, padx=60, fill="x")
        ctk.CTkLabel(
            header,
            text="Budget Assistant",
            font=("Arial",32,"bold"),
            text_color=self.text
        ).pack(pady=(20,10))

        # Botones: Agregar gasto, Análisis de gasto, Establecer presupuesto
        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(pady=(0,20))
        acciones = [
            ("Add Expense", self.add_expense),
            ("Spending Analysis", self.view_summary),
            ("Set Budget", lambda: messagebox.showinfo("Set Budget","Not implemented yet"))
        ]
        for i, (label, cmd) in enumerate(acciones):
            ctk.CTkButton(
                btns,
                text=label,
                command=cmd,
                width=200,
                height=50,
                fg_color=self.card_bg,
                hover_color=self.hover,
                text_color=self.text,
                font=("Arial",16),
                corner_radius=12
            ).grid(row=0, column=i, padx=20)

    def _create_charts_section(self):
        """
        Construye la sección de gráficos de líneas y dona para mostrar gastos.
        """
        sec = ctk.CTkFrame(
            self,
            fg_color=self.bg,
            corner_radius=12,
            border_width=2,
            border_color=self.accent
        )
        sec.pack(pady=10, padx=60, fill="x")

        # Títulos de sección
        trow = ctk.CTkFrame(sec, fg_color="transparent")
        trow.pack(fill="x", padx=20, pady=(20,0))
        ctk.CTkLabel(
            trow,
            text="Expense Chart",
            font=("Arial",20,"bold"),
            text_color=self.text
        ).pack(side="left")
        ctk.CTkLabel(
            trow,
            text="By category",
            font=("Arial",20,"bold"),
            text_color=self.text
        ).pack(side="right")

        # Contenedor de ambos gráficos lado a lado
        crow = ctk.CTkFrame(sec, fg_color="transparent")
        crow.pack(fill="x", padx=20, pady=20)
        left = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        left.pack(side="left", expand=True, fill="both", padx=10)
        right = ctk.CTkFrame(crow, fg_color=self.card_bg, corner_radius=12)
        right.pack(side="right", expand=True, fill="both", padx=10)

        # Dibujar gráficos
        self.show_line_chart(left)
        self.show_donut_chart(right)

    def show_line_chart(self, parent):
        """
        Dibuja un gráfico de líneas con gastos por mes.
        """
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun")
        data = self.get_expenses_by_month()  # Obtiene valores

        # Ajusta el límite superior del eje Y para evitar línea plana
        max_val = max(data) if any(data) else 1
        y_top = round(max_val * 1.2, 2)

        # Configuración de Matplotlib
        fig, ax = plt.subplots(figsize=(4, 2.5), dpi=100)
        fig.patch.set_facecolor(self.card_bg)
        ax.set_facecolor(self.card_bg)

        # Línea con marcadores
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

        # Configuración de ejes y límites
        ax.set_ylim(0, y_top)
        ax.set_xlim(-0.3, len(months) - 0.7)
        ax.set_xticks(months)
        ax.tick_params(axis="x", colors=self.text, labelsize=9)
        ax.tick_params(axis="y", colors=self.text, labelsize=9)
        ax.set_yticks(ax.get_yticks())
        ax.set_yticklabels([int(v) for v in ax.get_yticks()])

        # Cuadrícula horizontal suave y sin bordes
        ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, color="#43337a", alpha=0.7)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Inserta el gráfico en el widget padre
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=10)

    def show_donut_chart(self, parent):
        """
        Dibuja un gráfico de dona con gastos por categoría.
        """
        cats = ["Groceries","Electronics","Entertainment","Other"]
        vals = self.get_expenses_by_category()
        # Sustituye valores None o NaN por cero
        vals = [0 if (v is None or (isinstance(v, float) and math.isnan(v))) else v for v in vals]

        if sum(vals) == 0:
            # Si no hay datos, muestra mensaje
            ctk.CTkLabel(
                parent,
                text="No data to display",
                text_color=self.text,
                font=("Arial", 14, "bold")
            ).pack(expand=True, pady=50)
            return

        # Asigna colores de acuerdo al tema
        colors = [self.accent, self.hover, "#43337a", self.card_bg][:len(vals)]

        fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
        fig.patch.set_facecolor(self.card_bg)
        ax.set_facecolor(self.card_bg)

        # Dibuja pastel con grosor para crear efecto de dona
        wedges, texts, autotexts = ax.pie(
            vals,
            wedgeprops=dict(width=0.5),
            startangle=90,
            colors=colors,
            autopct="%1.1f%%",
            pctdistance=0.82,
            textprops=dict(color=self.text, fontsize=9),
        )
        # Círculo interior para "hueco"
        centre = plt.Circle((0, 0), 0.55, fc=self.card_bg)
        ax.add_artist(centre)
        ax.set(aspect="equal")  # Asegura que sea un círculo perfecto

        # Leyenda lateral sin marco
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
        """
        Sección para convertir montos entre distintas monedas.
        """
        frm = ctk.CTkFrame(self, fg_color=self.card_bg, corner_radius=12)
        frm.pack(pady=20, padx=60, fill="x")
        ctk.CTkLabel(
            frm,
            text="Transfer Calculator",
            font=("Arial",20,"bold"),
            text_color=self.text
        ).pack(pady=(20,10))

        # Formulario básico: cantidad, de moneda origen, a moneda destino
        form = ctk.CTkFrame(frm, fg_color="transparent")
        form.pack(pady=10)
        ctk.CTkLabel(form, text="Amount:", text_color=self.text).grid(row=0, column=0, padx=5)
        self.amount_entry = ctk.CTkEntry(form, width=100)
        self.amount_entry.insert(0, "1")
        self.amount_entry.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(form, text="From", text_color=self.text).grid(row=0, column=2, padx=5)
        self.from_currency = tk.StringVar(value="USD")
        ctk.CTkOptionMenu(form, values=["USD","EUR","COP","GBP","JPY"], variable=self.from_currency).grid(row=0, column=3, padx=5)
        ctk.CTkLabel(form, text="To", text_color=self.text).grid(row=1, column=2, padx=5)
        self.to_currency = tk.StringVar(value="EUR")
        ctk.CTkOptionMenu(form, values=["USD","EUR","COP","GBP","JPY"], variable=self.to_currency).grid(row=1, column=3, padx=5)

        # Labels para mostrar el resultado de la conversión
        self.result_label = ctk.CTkLabel(frm, text="", font=("Arial",24,"bold"), text_color=self.text)
        self.result_label.pack(pady=(10,0))
        self.exchange_rate_label = ctk.CTkLabel(frm, text="", font=("Arial",12), text_color=self.text)
        self.exchange_rate_label.pack(pady=(0,20))

        # Eventos para actualizar al cambiar valor o divisa
        self.amount_entry.bind("<KeyRelease>", lambda e: self.update_conversion())
        self.from_currency.trace("w", lambda *args: self.update_conversion())
        self.to_currency.trace("w", lambda *args: self.update_conversion())
        self.update_conversion()  # Conversión inicial

    def add_expense(self):
        """
        Abre una ventana emergente para ingresar un nuevo gasto:
        monto, categoría, descripción y fecha.
        """
        win = ctk.CTkToplevel(self)  # Ventana secundaria
        win.transient(self); win.grab_set(); win.lift(); win.focus_force()
        win.title("Add New Expense"); win.geometry("420x550"); win.configure(fg_color=self.card_bg)

        cont = ctk.CTkFrame(win, fg_color=self.card_bg)
        cont.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(
            cont,
            text="Add New Expense",
            font=("Arial",18,"bold"),
            text_color=self.text
        ).pack(pady=(0,10))

        # Campo Monto
        amt = ctk.CTkEntry(cont, placeholder_text="e.g. 25.00")
        ctk.CTkLabel(cont, text="Amount ($):", text_color=self.text).pack(anchor="w")
        amt.pack(fill="x", pady=(0,10))

        # Campo Categoría
        cat = ctk.CTkEntry(cont, placeholder_text="e.g. Food")
        ctk.CTkLabel(cont, text="Category:", text_color=self.text).pack(anchor="w")
        cat.pack(fill="x", pady=(0,10))

        # Campo Descripción opcional
        desc = ctk.CTkEntry(cont, placeholder_text="Optional")
        ctk.CTkLabel(cont, text="Description:", text_color=self.text).pack(anchor="w")
        desc.pack(fill="x", pady=(0,10))

        # Selector de fecha con calendario
        ctk.CTkLabel(cont, text="Select Date:", text_color=self.text).pack(anchor="w")
        cal = Calendar(
            cont,
            selectmode='day',
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day,
            background=self.text,
            foreground=self.card_bg,
            selectbackground=self.accent,
            selectforeground=self.text
        )
        cal.pack(fill="x", pady=(0,15))

        # Botón para guardar
        ctk.CTkButton(
            cont,
            text="Save Expense",
            command=lambda: self._save_expense(amt, cat, desc, cal),
            width=180,
            height=40,
            fg_color=self.accent,
            hover_color=self.hover,
            text_color=self.text,
            corner_radius=12
        ).pack(pady=(10,0))

    def _save_expense(self, amt_entry, cat_entry, desc_entry, cal):
        """
        Valida inputs, crea un registro Expense y lo guarda en la base de datos.
        """
        a = amt_entry.get().strip(); c = cat_entry.get().strip(); d = desc_entry.get().strip()
        date_val = cal.selection_get()
        # Validaciones básicas
        if not a or not c:
            return messagebox.showerror("Error","Amount and category required.")
        try:
            val = float(a)
            assert val > 0
        except:
            return messagebox.showerror("Error","Enter a positive number.")

        # Inserta en la BD
        db = SessionLocal()
        exp = Expense(
            amount=val,
            category=c,
            description=d,
            date=datetime.combine(date_val, datetime.min.time())
        )
        db.add(exp); db.commit(); db.close()

        # Mensaje de confirmación y cierre de ventana
        messagebox.showinfo("Saved", f"{c} - ${val:.2f} on {date_val}")
        win = amt_entry.master.master; win.destroy()

    def view_summary(self):
        """
        Muestra un resumen de todos los gastos en un cuadro de diálogo:
        total y lista detalle.
        """
        db = SessionLocal(); exps = db.query(Expense).all(); db.close()
        if not exps:
            return messagebox.showinfo("Summary","No expenses recorded yet.")

        total = sum(e.amount for e in exps)
        lines = [f"{e.date.date()} - {e.category}: ${e.amount:.2f}" for e in exps]
        messagebox.showinfo("Summary", f"Total: ${total:.2f}\n\n" + "\n".join(lines))

    def update_conversion(self):
        """
        Obtiene tipo de cambio y actualiza los labels según monto y monedas seleccionadas.
        """
        txt = self.amount_entry.get().strip()
        try:
            val = float(txt)
        except:
            return self.result_label.configure(text="Invalid amount", text_color="#ef4444")

        fr = self.from_currency.get(); to = self.to_currency.get()
        rate = 1 if fr == to else get_exchange_rate(fr, to)
        if not rate:
            return self.result_label.configure(text="Rate unavailable", text_color="#ef4444")

        # Cálculo y despliegue
        conv = val * rate
        self.result_label.configure(text=f"{val:,.2f} {fr} = {conv:,.2f} {to}")
        self.exchange_rate_label.configure(text=f"1 {fr} = {rate:.3f} {to}")

if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()  # Inicia el bucle principal de la interfaz gráfica
