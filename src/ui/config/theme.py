"""
Theme configuration for the AI Budget Tracker application.
Contains color palette and theme-related constants.
"""

# --- Enhanced color system ---
PALETTE = {
    # --- Base backgrounds (dark to light) ---
    "bg":          "#0a0a0f",     # Main background
    "bg-elevated": "#12121a",     # Elevated
    "sidebar":     "#1a1a28",     # Sidebar
    "card":        "#242438",     # Cards
    "card-hover":  "#2a2a42",     # Card hover state
    "input":       "#1f1f33",     # Input backgrounds

    # --- Primary accent (purple) ---
    "accent":      "#8b5cf6",     # Main accent
    "accent-hover": "#a78bfa",    # Accent hover
    "accent-dark": "#6d28d9",     # Accent pressed
    "accent-glow": "#8b5cf620",   # Subtle glow effect

    # --- Text hierarchy ---
    "text":        "#ffffff",     # Primary text
    "text-secondary": "#94a3b8",  # Secondary text
    "text-tertiary": "#64748b",   # Tertiary text
    "text-muted":  "#475569",     # Very muted text

    # --- Semantic colors ---
    "success":     "#10b981",     # Success green
    "success-light": "#34d399",   # Success hover
    "warning":     "#f59e0b",     # Warning orange
    "warning-light": "#fbbf24",   # Warning hover
    "error":       "#ef4444",     # Error red
    "error-light": "#f87171",     # Error hover
    "info":        "#3b82f6",     # Info blue
    "info-light":  "#60a5fa",     # Info hover

    # --- Additional colors for variety ---
    "purple":      "#8b5cf6",
    "blue":        "#3b82f6",
    "green":       "#10b981",
    "orange":      "#f59e0b",
    "pink":        "#ec4899",
    "teal":        "#14b8a6",
    "red":         "#ef4444",
    "yellow":      "#eab308",
    "indigo":      "#6366f1",

    # --- UI elements ---
    "border":      "#2e3348",     # Default border
    "border-light": "#3f4461",    # Light border
    "shadow":      "#00000040",   # Shadow color

    # --- Gray scale for buttons ---
    "gray-700":    "#374151",
    "gray-600":    "#4b5563",
    "bg-hover":    "#2a2a42",
}

# --- Category color mapping ---
CATEGORY_COLORS = {
    "Groceries": PALETTE["green"],
    "Entertainment": PALETTE["pink"],
    "Electronics": PALETTE["blue"],
    "Other": PALETTE["orange"]
}

# --- Icon mapping for safe display ---
ICON_MAP = {
    "💰": "💲",
    "📊": "📈",
    "🎯": "◎",
    "💳": "#"
}