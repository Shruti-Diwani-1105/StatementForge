import os
import json
from PyQt6.QtWidgets import QApplication

class ThemeManager:
    """Manages application-wide theme switching (Light vs Dark mode) and persistence."""
    _current_theme = "light"
    _theme_file = os.path.join(os.path.expanduser("~"), ".statementforge_theme.json")

    @classmethod
    def initialize_theme(cls):
        """Always defaults to light theme on application startup."""
        cls._current_theme = "light"
        try:
            with open(cls._theme_file, "w", encoding="utf-8") as f:
                json.dump({"theme": "light"}, f)
        except Exception:
            pass
        cls.apply_theme("light")

    @classmethod
    def get_theme(cls):
        """Returns the current theme string ('light' or 'dark')."""
        return cls._current_theme

    @classmethod
    def toggle_theme(cls):
        """Toggles the theme, saves the selection, and applies the stylesheet."""
        new_theme = "dark" if cls._current_theme == "light" else "light"
        cls._current_theme = new_theme
        
        try:
            with open(cls._theme_file, "w", encoding="utf-8") as f:
                json.dump({"theme": new_theme}, f)
        except Exception as e:
            print(f"ThemeManager: Error saving theme setting: {e}")
            
        cls.apply_theme(new_theme)
        return new_theme

    @classmethod
    def apply_theme(cls, theme_name):
        """Reads QSS file content and sets it as the QApplication style sheet."""
        app = QApplication.instance()
        if not app:
            return
            
        filename = "theme.qss" if theme_name == "light" else "theme_dark.qss"
        qss_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "styles", 
            filename
        )
        
        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    stylesheet = f.read()
                    app.setStyleSheet(stylesheet)
            except Exception as e:
                print(f"ThemeManager: Error loading stylesheet {filename}: {e}")
        else:
            print(f"ThemeManager: Stylesheet not found at {qss_path}")
