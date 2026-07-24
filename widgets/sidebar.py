import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView

class Sidebar(QFrame):
    """
    Left-hand sidebar menu for application navigation rendered with HTML + CSS.
    Exposes signals when items are clicked to switch pages.
    """
    nav_changed = pyqtSignal(str)  # Emits the page key, e.g. "dashboard", "upload", etc.
    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        self.setFixedWidth(260)
        
        # Transparent border & background container
        self.setStyleSheet("QFrame#SidebarFrame { background: transparent; border: none; }")
        
        # Main Vertical Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # QWebEngineView hosting HTML/CSS sidebar
        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        layout.addWidget(self.web_view)
        
        # Connect IPC document.title Listener
        self.web_view.titleChanged.connect(self._handle_title_changed)
        
        # Compatibility dict for any legacy code querying buttons
        self.buttons = {}
        self.current_key = "dashboard"
        
        # Load Sidebar HTML
        self._load_html()

    def _load_html(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, "web", "sidebar.html")
        if os.path.exists(html_path):
            self.web_view.setUrl(QUrl.fromLocalFile(html_path))
            self.web_view.loadFinished.connect(self._on_load_finished)
        else:
            print(f"Error: Sidebar HTML file not found at {html_path}")

    def _on_load_finished(self, success):
        if success:
            self.set_active_page(self.current_key)
            from utils.theme_manager import ThemeManager
            self.update_theme_styles(ThemeManager.get_theme())

    def _handle_title_changed(self, title: str):
        """Processes document.title IPC commands sent from HTML."""
        if not title or not title.startswith("app-cmd:"):
            return

        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        payload = parts[2] if len(parts) > 2 else ""

        if cmd == "nav":
            key = payload.strip().lower()
            self.current_key = key
            self.nav_changed.emit(key)
        elif cmd == "logout":
            self.logout_clicked.emit()

    def set_active_page(self, key):
        """Sets a specific sidebar button as checked programmatically in HTML."""
        self.current_key = key
        script = f"document.querySelectorAll('.nav-button').forEach(b => b.classList.remove('active')); var el = document.getElementById('nav-{key}'); if (el) el.classList.add('active');"
        self.web_view.page().runJavaScript(script)

    def update_theme_styles(self, theme):
        """Propagates theme changes (light/dark) to the sidebar HTML container."""
        script = f"if ('{theme}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode');"
        self.web_view.page().runJavaScript(script)
