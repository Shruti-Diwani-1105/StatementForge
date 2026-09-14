import os
import json
from PyQt6.QtWidgets import QApplication

class ThemeManager:
    """Manages application theme - permanently configured to clean light mode."""
    _current_theme = "light"

    @classmethod
    def initialize_theme(cls):
        """Always applies light theme on application startup."""
        cls._current_theme = "light"
        cls.apply_theme("light")

    @classmethod
    def get_theme(cls):
        """Returns permanent light theme."""
        return "light"

    @classmethod
    def toggle_theme(cls):
        """No-op theme toggle, maintains light theme."""
        cls._current_theme = "light"
        cls.apply_theme("light")
        return "light"

    @classmethod
    def apply_theme(cls, theme_name="light"):
        """Reads theme.qss light stylesheet and sets it as the QApplication style sheet."""
        app = QApplication.instance()
        if not app:
            return
            
        qss_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "styles", 
            "theme.qss"
        )
        
        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    stylesheet = f.read()
                    app.setStyleSheet(stylesheet)
            except Exception as e:
                print(f"ThemeManager: Error loading stylesheet theme.qss: {e}")
        else:
            print(f"ThemeManager: Stylesheet not found at {qss_path}")
