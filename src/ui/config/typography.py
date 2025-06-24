"""
Typography system for consistent font usage across the application.
"""

class Typography:
    """Typography configuration and helper methods."""
    
    FONT_FAMILY = "Inter"  # --- Falls back to system font if not available ---
 
    @staticmethod
    def get_font(size, weight="normal"):
        """
        Get font tuple with proper style handling.
        
        Args:
            size (int): Font size
            weight (str): Font weight - "normal", "medium", "semibold", or "bold"
            
        Returns:
            tuple: Font configuration tuple for tkinter/customtkinter
        """
        weights = {
            "normal": "normal",
            "medium": "normal",
            "semibold": "bold",
            "bold": "bold"
        }
        style = weights.get(weight, "normal")
        return (Typography.FONT_FAMILY, size, style)

    # --- Predefined styles ---
    DISPLAY = ("Inter", 28, "bold")
    HEADING_1 = ("Inter", 24, "bold")
    HEADING_2 = ("Inter", 20, "bold")
    HEADING_3 = ("Inter", 16, "bold")
    BODY_LARGE = ("Inter", 15, "normal")
    BODY = ("Inter", 14, "normal")
    CAPTION = ("Inter", 12, "normal")
    SMALL = ("Inter", 11, "normal")