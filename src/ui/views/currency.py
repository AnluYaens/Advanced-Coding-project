"""
Currency converter view for exchange rate calculations.
"""

import tkinter as tk
import customtkinter as ctk
from src.ui.config.theme import PALETTE
from src.ui.config.typography import Typography
from src.ui.components.buttons import AnimatedButton
from src.ui.components.cards import GlassCard
from src.ui.utils.helpers import create_header
from src.services.currency_api import get_exchange_rate


class CurrencyView:
    """Currency converter view."""
    
    def __init__(self, parent):
        self.parent = parent
        self.amount_var = None
        self.from_var = None
        self.to_var = None
        self.result_lbl = None
        self.rate_lbl = None
        
    def create(self):
        """Create the currency converter view."""
        create_header(self.parent, "Currency Converter")
        
        converter_card = GlassCard(self.parent)
        converter_card.pack(fill="x", padx=30, pady=16)
        
        content = ctk.CTkFrame(converter_card, fg_color="transparent")
        content.pack(padx=40, pady=40)
        
        # --- Amount input ---
        ctk.CTkLabel(
            content, 
            text="Amount to convert", 
            font=Typography.get_font(16, "semibold"), 
            text_color=PALETTE["text"]
        ).pack(anchor="w", pady=(0, 8))
        
        self.amount_var = tk.StringVar(value="1.0")
        amount_entry = ctk.CTkEntry(
            content, 
            textvariable=self.amount_var, 
            width=350, 
            height=44, 
            font=Typography.get_font(16, "normal"), 
            fg_color=PALETTE["input"], 
            border_color=PALETTE["border"], 
            corner_radius=8
        )
        amount_entry.pack(anchor="w", pady=(0, 24))
        amount_entry.bind("<KeyRelease>", lambda *_: self._update_conversion())
        
        # --- Currency selection ---
        ctk.CTkLabel(
            content, 
            text="Select currencies", 
            font=Typography.get_font(16, "semibold"), 
            text_color=PALETTE["text"]
        ).pack(anchor="w", pady=(0, 12))
        
        currency_frame = ctk.CTkFrame(content, fg_color="transparent")
        currency_frame.pack(anchor="w", pady=(0, 30))
        
        currencies = ["USD", "EUR", "GBP", "MXN", "JPY", "CAD"]
        self.from_var = tk.StringVar(value="USD")
        self.to_var = tk.StringVar(value="EUR")
        
        # --- From currency ---
        from_frame = ctk.CTkFrame(currency_frame, fg_color="transparent")
        from_frame.pack(side="left", padx=(0, 24))
        
        ctk.CTkLabel(
            from_frame, 
            text="From", 
            font=Typography.get_font(12, "medium"), 
            text_color=PALETTE["text-secondary"]
        ).pack(pady=(0, 6))
        
        ctk.CTkOptionMenu(
            from_frame, 
            variable=self.from_var, 
            values=currencies, 
            width=150, 
            height=40, 
            fg_color=PALETTE["accent"], 
            font=Typography.get_font(14, "medium"), 
            dropdown_font=Typography.BODY, 
            command=lambda *_: self._update_conversion(), 
            corner_radius=8
        ).pack()
        
        # --- Swap button ---
        swap_btn = AnimatedButton(
            currency_frame, 
            text="⇄", 
            width=40, 
            height=40, 
            fg_color=PALETTE["gray-700"], 
            hover_color=PALETTE["gray-600"], 
            font=Typography.get_font(18, "normal"), 
            command=self._swap_currencies, 
            corner_radius=20
        )
        swap_btn.pack(side="left", padx=12, pady=(16, 0))
        
        # --- To currency ---
        to_frame = ctk.CTkFrame(currency_frame, fg_color="transparent")
        to_frame.pack(side="left")
        
        ctk.CTkLabel(
            to_frame, 
            text="To", 
            font=Typography.get_font(12, "medium"), 
            text_color=PALETTE["text-secondary"]
        ).pack(pady=(0, 6))
        
        ctk.CTkOptionMenu(
            to_frame, 
            variable=self.to_var, 
            values=currencies, 
            width=150, 
            height=40, 
            fg_color=PALETTE["accent"], 
            font=Typography.get_font(14, "medium"), 
            dropdown_font=Typography.BODY, 
            command=lambda *_: self._update_conversion(), 
            corner_radius=8
        ).pack()
        
        # --- Results ---
        results_frame = ctk.CTkFrame(
            content, 
            fg_color=PALETTE["bg-elevated"], 
            corner_radius=12
        )
        results_frame.pack(fill="x", pady=24)
        
        results_content = ctk.CTkFrame(results_frame, fg_color="transparent")
        results_content.pack(padx=24, pady=24)
        
        self.result_lbl = ctk.CTkLabel(
            results_content, 
            text="", 
            font=Typography.get_font(22, "bold"), 
            text_color=PALETTE["text"]
        )
        self.result_lbl.pack()
        
        self.rate_lbl = ctk.CTkLabel(
            results_content, 
            text="", 
            font=Typography.BODY, 
            text_color=PALETTE["text-secondary"]
        )
        self.rate_lbl.pack(pady=(6, 0))
        
        self._update_conversion()

    def _update_conversion(self):
        """Update the currency conversion."""
        if not all([self.amount_var, self.result_lbl, self.rate_lbl]):
            return
            
        try:
            amount_str = self.amount_var.get().strip()
            if not amount_str:
                self.result_lbl.configure(text="Enter an amount")
                self.rate_lbl.configure(text="")
                return
                
            amount = float(amount_str.replace(',', ''))
            from_c = self.from_var.get()
            to_c = self.to_var.get()
            
            if from_c == to_c:
                converted = amount
                rate = 1.0
            else:
                rate = get_exchange_rate(from_c, to_c)
                converted = (amount * rate) if rate else 0.0
                
            if not rate:
                self.result_lbl.configure(text="Conversion unavailable")
                self.rate_lbl.configure(text="Check internet connection or API key")
            else:
                self.result_lbl.configure(
                    text=f"{amount:,.2f} {from_c} = {converted:,.2f} {to_c}"
                )
                self.rate_lbl.configure(text=f"1 {from_c} = {rate:.4f} {to_c}")
        except ValueError:
            self.result_lbl.configure(
                text="❌ Invalid amount", 
                text_color=PALETTE["error"]
            )
            self.rate_lbl.configure(text="Please enter a valid number.")

    def _swap_currencies(self):
        """Swap from and to currencies."""
        old_from = self.from_var.get()
        self.from_var.set(self.to_var.get())
        self.to_var.set(old_from)
        self._update_conversion()