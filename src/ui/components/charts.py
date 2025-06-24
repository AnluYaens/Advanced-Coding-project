"""
Chart components for data visualization.
"""

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
try:
    from scipy.interpolate import PchipInterpolator
except ImportError:
    PchipInterpolator = None
    
import customtkinter as ctk
from src.ui.config.theme import PALETTE, CATEGORY_COLORS
from src.ui.config.typography import Typography
from src.ui.utils.helpers import create_empty_placeholder


class LineChart:
    """Enhanced line chart for spending trends."""
    
    @staticmethod
    def create(parent, data, colors):
        """Create and display a line chart."""
        if sum(data) == 0:
            create_empty_placeholder(
                parent, 
                "📈", 
                "No Expense Data", 
                "Add some expenses to see your monthly trend."
            )
            return None
            
        fig, ax = plt.subplots(figsize=(6.5, 4), dpi=80)
        fig.patch.set_facecolor(colors["card"])
        ax.set_facecolor(colors["card"])
        
        x = np.arange(len(data))
        
        # --- Smooth line if we have varied data and interpolator available ---
        if len(set(data)) > 1 and PchipInterpolator:
            x_smooth = np.linspace(x.min(), x.max(), 300)
            y_smooth = PchipInterpolator(x, data)(x_smooth)
            ax.fill_between(x_smooth, 0, y_smooth, alpha=0.15, color=colors["accent"])
            ax.plot(x_smooth, y_smooth, color=colors["accent"], linewidth=2.5, zorder=2)
        else:
            ax.plot(x, data, color=colors["accent"], linewidth=2.5, marker="o", zorder=2)
            
        # --- Add data points ---
        for xi, val in enumerate(data):
            if val > 0:
                ax.scatter(xi, val, color=colors["accent"], s=100, alpha=0.2, zorder=1)
                ax.scatter(xi, val, color=colors["accent"], edgecolor='white', 
                          s=40, linewidth=1.5, zorder=3)
                ax.text(xi, val + max(data) * 0.05, f"${val:,.0f}", 
                       fontsize=9, color=colors["text"], 
                       ha='center', va='bottom', fontweight='medium')
        
        # --- Styling ---
        ax.set_ylim(bottom=0)
        ax.set_xticks(x)
        ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun"], 
                          color=colors["text-secondary"], fontsize=9)
        ax.tick_params(axis='y', colors=colors["text-tertiary"], labelsize=8)
        ax.grid(axis='y', linestyle='-', linewidth=0.5, 
               color=colors["border"], alpha=0.3)
        
        # --- Remove spines ---
        for spine in ax.spines.values():
            spine.set_visible(False)
            
        fig.tight_layout(pad=1.5)
        
        # --- Create canvas ---
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=16, pady=(8, 16), fill="both", expand=True)
        
        plt.close(fig)
        return canvas


class DonutChart:
    """Enhanced donut chart for category breakdown."""
    
    @staticmethod
    def create(parent, values, categories, colors_dict):
        """Create and display a donut chart."""
        if sum(values) == 0:
            create_empty_placeholder(
                parent, 
                "🍩", 
                "No Category Data", 
                "Add expenses to see the category breakdown."
            )
            return None
            
        total = sum(values)
        colors = [colors_dict[cat] for cat in categories]
        
        fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=80)
        fig.patch.set_facecolor(PALETTE["card"])
        ax.set_facecolor(PALETTE["card"])
        
        # --- Create donut ---
        ax.pie(values, colors=colors, 
              wedgeprops=dict(width=0.4, edgecolor=PALETTE["card"], linewidth=2), 
              startangle=90)
        ax.add_artist(plt.Circle((0, 0), 0.60, fc=PALETTE["card"]))
        
        # --- Center text ---
        ax.text(0, 0, f"${total:,.0f}", ha='center', va='center', 
               fontsize=18, fontweight='bold', color=PALETTE["text"])
        ax.text(0, -0.15, "Total", ha='center', va='center', 
               fontsize=11, color=PALETTE["text-secondary"])
        ax.axis("equal")
        
        # --- Legend ---
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, fc=color, 
                         label=f"{cat}: ${val:,.0f} ({val/total*100:.0f}%)")
            for cat, val, color in zip(categories, values, colors) if val > 0
        ]
        
        ax.legend(
            handles=legend_elements,
            loc='center',
            bbox_to_anchor=(0.5, -0.15),
            ncol=2,
            frameon=False,
            fontsize=9,
            labelcolor=PALETTE["text-secondary"],
            handlelength=0.8,
            handletextpad=0.5,
            columnspacing=1.0
        )
        
        fig.tight_layout()
        
        # --- Create canvas ---
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=16, pady=(8, 16), fill="both", expand=True)
        
        plt.close(fig)
        return canvas