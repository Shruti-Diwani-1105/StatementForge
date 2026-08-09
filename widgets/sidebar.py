import os
import json
from PyQt6.QtWidgets import QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QPropertyAnimation
from PyQt6.QtWebEngineWidgets import QWebEngineView

class Sidebar(QFrame):
    """
    Left-hand sidebar menu for application navigation rendered with HTML + CSS.
    Supports a global collapsible state (expanded: 260px, collapsed: 80px),
    tooltips, preference persistence, and smooth layout transitions.
    """
    nav_changed = pyqtSignal(str)  # Emits the page key, e.g. "dashboard", "upload", etc.
    logout_clicked = pyqtSignal()
    collapsed_changed = pyqtSignal(bool)  # Emits True when collapsed, False when expanded

    PREF_FILE = os.path.join(os.path.expanduser("~"), ".statementforge_sidebar.json")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        
        # Load stored preference
        self.is_collapsed = self._load_collapsed_preference()
        initial_width = 80 if self.is_collapsed else 260
        self.setFixedWidth(initial_width)
        
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

    def _load_collapsed_preference(self) -> bool:
        try:
            if os.path.exists(self.PREF_FILE):
                with open(self.PREF_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return bool(data.get("collapsed", False))
        except Exception:
            pass
        return False

    def _save_collapsed_preference(self, collapsed: bool):
        try:
            with open(self.PREF_FILE, "w", encoding="utf-8") as f:
                json.dump({"collapsed": collapsed}, f)
        except Exception as e:
            print(f"Sidebar: Error saving sidebar preference: {e}")

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
            self.apply_collapsed_state(self.is_collapsed, animate=False)

    def _handle_title_changed(self, title: str):
        """Processes document.title IPC commands sent from HTML."""
        if not title or not title.startswith("app-cmd:"):
            return
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._process_title_changed(title))

    def _process_title_changed(self, title: str):
        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        payload = parts[2] if len(parts) > 2 else ""

        if cmd == "nav":
            key = payload.strip().lower()
            self.current_key = key
            self.nav_changed.emit(key)
        elif cmd == "logout":
            self.logout_clicked.emit()
        elif cmd == "toggle_sidebar":
            new_state = (payload.strip().lower() == "collapsed")
            self.set_collapsed(new_state, animate=True)

    def set_collapsed(self, collapsed: bool, animate=True):
        """Programmatically collapses or expands the sidebar with smooth animation."""
        if self.is_collapsed == collapsed and self.width() == (80 if collapsed else 260):
            return
            
        self.is_collapsed = collapsed
        self._save_collapsed_preference(collapsed)
        self.apply_collapsed_state(collapsed, animate=animate)
        self.collapsed_changed.emit(collapsed)

    def toggle_collapsed(self):
        """Toggles current collapsed state."""
        self.set_collapsed(not self.is_collapsed, animate=True)

    def apply_collapsed_state(self, collapsed: bool, animate=True):
        """Adjusts PyQT container width and propagates state script to webview."""
        target_width = 80 if collapsed else 260
        
        if animate:
            self.anim_min = QPropertyAnimation(self, b"minimumWidth")
            self.anim_min.setDuration(220)
            self.anim_min.setEndValue(target_width)
            
            self.anim_max = QPropertyAnimation(self, b"maximumWidth")
            self.anim_max.setDuration(220)
            self.anim_max.setEndValue(target_width)
            
            self.anim_min.start()
            self.anim_max.start()
        else:
            self.setFixedWidth(target_width)
            
        script = f"if (typeof setCollapsedState === 'function') setCollapsedState({'true' if collapsed else 'false'});"
        self.web_view.page().runJavaScript(script)

    def set_active_page(self, key):
        """Sets a specific sidebar button as checked programmatically in HTML."""
        self.current_key = key
        script = f"document.querySelectorAll('.nav-button').forEach(b => b.classList.remove('active')); var el = document.getElementById('nav-{key}'); if (el) el.classList.add('active');"
        self.web_view.page().runJavaScript(script)

    def update_theme_styles(self, theme):
        """Propagates theme changes (light/dark) to the sidebar HTML container."""
        script = f"if ('{theme}' === 'dark') document.body.classList.add('dark-mode'); else document.body.classList.remove('dark-mode');"
        self.web_view.page().runJavaScript(script)
