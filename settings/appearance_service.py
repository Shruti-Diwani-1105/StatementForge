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
            
        theme_clean = theme_name.lower().strip() if isinstance(theme_name, str) else "light"
        # Determine theme filename
        filename = "theme.qss" if theme_clean in ["light", "system"] else "theme_dark.qss"
        
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
            qss_content = AppearanceService._replace_accents(qss_content, theme_clean, accent_color)
            
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
        accent = str(accent).lower().strip() if accent else "blue"
        if accent in ["blue", "royal blue"]:
            return qss_content
            
        replacements = []
        if theme == "light":
            if accent in ["indigo"]:
                replacements = [
                    ("#2563EB", "#4F46E5"),
                    ("#1D4ED8", "#3730A3"),
                    ("#1E40AF", "#312E81"),
                    ("#EFF6FF", "#EEF2FF"),
                    ("#93C5FD", "#A5B4FC"),
                ]
            elif accent in ["purple"]:
                replacements = [
                    ("#2563EB", "#8B5CF6"),
                    ("#1D4ED8", "#7C3AED"),
                    ("#1E40AF", "#6D28D9"),
                    ("#EFF6FF", "#F5F3FF"),
                    ("#93C5FD", "#DDD6FE"),
                ]
            elif accent in ["emerald", "green"]:
                replacements = [
                    ("#2563EB", "#10B981"),
                    ("#1D4ED8", "#059669"),
                    ("#1E40AF", "#047857"),
                    ("#EFF6FF", "#ECFDF5"),
                    ("#93C5FD", "#A7F3D0"),
                ]
            elif accent in ["amber", "orange"]:
                replacements = [
                    ("#2563EB", "#F59E0B"),
                    ("#1D4ED8", "#D97706"),
                    ("#1E40AF", "#B45309"),
                    ("#EFF6FF", "#FFFBEB"),
                    ("#93C5FD", "#FDE68A"),
                ]
        else:  # Dark mode
            if accent in ["indigo"]:
                replacements = [
                    ("#3B82F6", "#6366F1"),
                    ("#2563EB", "#4F46E5"),
                    ("#1D4ED8", "#3730A3"),
                    ("#EFF6FF", "#1E1B4B"),
                    ("#1E3A8A", "#312E81"),
                    ("#60A5FA", "#818CF8"),
                ]
            elif accent in ["purple"]:
                replacements = [
                    ("#3B82F6", "#A855F7"),
                    ("#2563EB", "#8B5CF6"),
                    ("#1D4ED8", "#7C3AED"),
                    ("#EFF6FF", "#3B0764"),
                    ("#1E3A8A", "#581C87"),
                    ("#60A5FA", "#C084FC"),
                ]
            elif accent in ["emerald", "green"]:
                replacements = [
                    ("#3B82F6", "#10B981"),
                    ("#2563EB", "#059669"),
                    ("#1D4ED8", "#047857"),
                    ("#EFF6FF", "#064E3B"),
                    ("#1E3A8A", "#065F46"),
                    ("#60A5FA", "#34D399"),
                ]
            elif accent in ["amber", "orange"]:
                replacements = [
                    ("#3B82F6", "#F59E0B"),
                    ("#2563EB", "#D97706"),
                    ("#1D4ED8", "#B45309"),
                    ("#EFF6FF", "#78350F"),
                    ("#1E3A8A", "#92400E"),
                    ("#60A5FA", "#FBBF24"),
                ]
                
        for target, replacement in replacements:
            qss_content = qss_content.replace(target, replacement)
            qss_content = qss_content.replace(target.lower(), replacement)
            
        return qss_content

    @staticmethod
    def _replace_font_size(qss_content, size_name):
        """Replaces base font sizing inside the QSS file."""
        if size_name == "Small":
            return qss_content.replace("font-size: 14px;", "font-size: 12px;")
        elif size_name == "Large":
            return qss_content.replace("font-size: 14px;", "font-size: 16px;")
        return qss_content
