import os
from PyQt6.QtWidgets import QApplication

class AppearanceService:
    """
    Manages live updates to the application appearance, including
    theme loading, custom accent color mapping, and font size adjustment.
    """
    
    @staticmethod
    def apply_appearance(theme_name, accent_color="blue", font_size="Medium"):
        """
        Loads the theme QSS, performs string replacement for accent colors and font sizes,
        and applies the modified QSS to the QApplication instance.
        """
        app = QApplication.instance()
        if not app:
            return False
            
        # Determine theme filename
        filename = "theme.qss" if theme_name == "light" else "theme_dark.qss"
        
        # Get path to styles folder (two levels up from settings/appearance_service.py)
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qss_path = os.path.join(project_dir, "styles", filename)
        
        if not os.path.exists(qss_path):
            print(f"AppearanceService: Stylesheet not found at {qss_path}")
            return False
            
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                qss_content = f.read()
                
            # Perform accent color mapping replacements
            qss_content = AppearanceService._replace_accents(qss_content, theme_name, accent_color)
            
            # Perform font size replacements
            qss_content = AppearanceService._replace_font_size(qss_content, font_size)
            
            # Set the stylesheet application-wide
            app.setStyleSheet(qss_content)
            return True
        except Exception as e:
            print(f"AppearanceService: Error applying stylesheet: {e}")
            return False

    @staticmethod
    def _replace_accents(qss_content, theme, accent):
        """Replaces standard blue hex values in QSS with selected accent color hex values."""
        accent = accent.lower()
        if accent == "blue":
            return qss_content # Blue is the default, no replacement needed
            
        # Standard Blue values to locate and replace
        # Light mode defaults: Blue is #2563EB, Hover is #1D4ED8, Pressed is #1E40AF, Selected BG is #EFF6FF, checkbox checked is #2563EB
        # Dark mode defaults: Blue is #3B82F6, Hover is #2563EB, Pressed is #1D4ED8, Selected BG is #1E293B, checkbox checked is #3B82F6
        
        replacements = []
        
        if theme == "light":
            if accent == "green":
                replacements = [
                    ("#2563EB", "#16A34A"), # Primary
                    ("#1D4ED8", "#15803D"), # Hover
                    ("#1E40AF", "#166534"), # Pressed
                    ("#EFF6FF", "#F0FDF4"), # Selected BG
                    ("#93C5FD", "#86EFAC"), # Disabled BG
                ]
            elif accent == "purple":
                replacements = [
                    ("#2563EB", "#7C3AED"),
                    ("#1D4ED8", "#6D28D9"),
                    ("#1E40AF", "#5B21B6"),
                    ("#EFF6FF", "#F5F3FF"),
                    ("#93C5FD", "#C084FC"),
                ]
            elif accent == "orange":
                replacements = [
                    ("#2563EB", "#EA580C"),
                    ("#1D4ED8", "#C2410C"),
                    ("#1E40AF", "#9A3412"),
                    ("#EFF6FF", "#FFF7ED"),
                    ("#93C5FD", "#FDBA74"),
                ]
        else: # dark theme
            if accent == "green":
                replacements = [
                    ("#3B82F6", "#10B981"), # Primary
                    ("#2563EB", "#059669"), # Hover
                    ("#1D4ED8", "#047857"), # Pressed
                    ("#EFF6FF", "#064E3B"), # Selected
                    ("#1E3A8A", "#064E3B"), # Disabled BG
                    ("#60A5FA", "#34D399"), # Progress chunk
                ]
            elif accent == "purple":
                replacements = [
                    ("#3B82F6", "#8B5CF6"),
                    ("#2563EB", "#7C3AED"),
                    ("#1D4ED8", "#6D28D9"),
                    ("#EFF6FF", "#4C1D95"),
                    ("#1E3A8A", "#4C1D95"),
                    ("#60A5FA", "#A78BFA"),
                ]
            elif accent == "orange":
                replacements = [
                    ("#3B82F6", "#F97316"),
                    ("#2563EB", "#EA580C"),
                    ("#1D4ED8", "#C2410C"),
                    ("#EFF6FF", "#7C2D12"),
                    ("#1E3A8A", "#7C2D12"),
                    ("#60A5FA", "#FB923C"),
                ]
                
        for target, replacement in replacements:
            qss_content = qss_content.replace(target, replacement)
            # Support lowercase matching just in case
            qss_content = qss_content.replace(target.lower(), replacement)
            
        return qss_content

    @staticmethod
    def _replace_font_size(qss_content, size_name):
        """Replaces base font sizing inside the QSS file."""
        # Baseline is font-size: 14px in both theme files under QWidget
        if size_name == "Small":
            return qss_content.replace("font-size: 14px;", "font-size: 12px;")
        elif size_name == "Large":
            return qss_content.replace("font-size: 14px;", "font-size: 16px;")
        return qss_content # Medium (14px) is default
