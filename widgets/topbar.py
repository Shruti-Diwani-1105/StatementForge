import os
from PyQt6.QtWidgets import QFrame, QHBoxLayout
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView

class ProfileWidgetBridge(QObject):
    """Bridge object maintaining compatibility with self.topbar.profile_widget.clicked."""
    clicked = pyqtSignal()

    def update_profile(self, full_name):
        pass


class TopBar(QFrame):
    """
    Top navigation bar containing search, notification system, and user profile metadata
    rendered via HTML + CSS.
    """
    search_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBarFrame")
        self.setFixedHeight(70)
        
        # Transparent border & background container
        self.setStyleSheet("QFrame#TopBarFrame { background: transparent; border: none; }")
        
        # Compatibility helper for topbar.profile_widget.clicked
        self.profile_widget = ProfileWidgetBridge(self)
        self.profile_name = "User"
        
        # Main Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # QWebEngineView hosting HTML/CSS topbar
        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        layout.addWidget(self.web_view)
        
        # Connect IPC document.title Listener
        self.web_view.titleChanged.connect(self._handle_title_changed)
        
        # Load TopBar HTML
        self._load_html()

    def _load_html(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, "web", "topbar.html")
        if os.path.exists(html_path):
            self.web_view.setUrl(QUrl.fromLocalFile(html_path))
            self.web_view.loadFinished.connect(self._on_load_finished)
        else:
            print(f"Error: TopBar HTML file not found at {html_path}")

    def _on_load_finished(self, success):
        if success:
            from utils.theme_manager import ThemeManager
            current_theme = ThemeManager.get_theme()
            self.update_theme_icon(current_theme)
            if hasattr(self, "profile_name") and self.profile_name:
                self.update_profile(self.profile_name)

    def _handle_title_changed(self, title: str):
        """Processes document.title IPC commands sent from HTML."""
        if not title or not title.startswith("app-cmd:"):
            return

        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        payload = parts[2] if len(parts) > 2 else ""

        if cmd == "topbar_profile":
            self.profile_widget.clicked.emit()
        elif cmd == "topbar_theme_toggle":
            self.toggle_theme()
        elif cmd == "topbar_search_submit":
            self.search_submitted.emit(payload)
        elif cmd == "topbar_notification":
            win = self.window()
            if hasattr(win, "show_coming_soon"):
                win.show_coming_soon("Notifications")

    def toggle_theme(self):
        """Toggles the current application theme and updates the HTML icon."""
        from utils.theme_manager import ThemeManager
        new_theme = ThemeManager.toggle_theme()
        self.update_theme_icon(new_theme)
        
        # Propagate theme change to the main controller window
        win = self.window()
        if win and hasattr(win, "sync_theme_styles"):
            win.sync_theme_styles(new_theme)

    def update_theme_icon(self, theme):
        """Updates the theme class and button representation in HTML."""
        script = f"""
        if ('{theme}' === 'dark') {{
            document.body.classList.add('dark-mode');
            var btn = document.getElementById('btn-theme-toggle');
            if (btn) btn.classList.add('dark-active');
        }} else {{
            document.body.classList.remove('dark-mode');
            var btn = document.getElementById('btn-theme-toggle');
            if (btn) btn.classList.remove('dark-active');
        }}
        """
        self.web_view.page().runJavaScript(script)

    def update_profile(self, full_name):
        """Updates the active user's avatar letter and name details in HTML."""
        self.profile_name = full_name
        name = full_name.strip() if full_name and full_name.strip() else "User"
        initial = name[0].upper() if name else "U"
        escaped_name = name.replace("'", "\\'")
        script = f"""
        var nameEl = document.getElementById('user-name');
        var avatarEl = document.getElementById('user-avatar');
        if (nameEl) nameEl.textContent = '{escaped_name}';
        if (avatarEl) avatarEl.textContent = '{initial}';
        """
        self.web_view.page().runJavaScript(script)
