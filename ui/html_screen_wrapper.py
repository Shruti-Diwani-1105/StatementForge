import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from controllers.web_bridge import WebBridge

class HtmlScreenWrapper(QWidget):
    """
    Generic QWebEngineView wrapper that hosts local HTML/CSS pages
    and sets up QWebChannel bridge + document.title IPC listener for Python interaction.
    """
    def __init__(self, html_relative_path, parent=None):
        super().__init__(parent)
        self.html_relative_path = html_relative_path
        
        # Instantiate layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Instantiate WebEngineView
        self.web_view = QWebEngineView(self)
        layout.addWidget(self.web_view)
        
        # Instantiate WebChannel & Bridge
        self.bridge = WebBridge(self)
        self.channel = QWebChannel(self)
        self.channel.registerObject("pybridge", self.bridge)
        
        self.web_view.page().setWebChannel(self.channel)
        
        # Connect Title Change IPC Listener (guarantees zero OS popups and fast execution)
        self.web_view.titleChanged.connect(self.handle_title_changed)
        
        # Connect bridge error signals to JS error handler
        self.bridge.loginFailed.connect(self.display_login_error)
        self.bridge.registerFailed.connect(self.display_register_error)
        
        # Load local HTML file
        self.load_html()

    def load_html(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, self.html_relative_path)
        if os.path.exists(file_path):
            self.web_view.setUrl(QUrl.fromLocalFile(file_path))
        else:
            print(f"Error: HTML file not found at {file_path}")

    def handle_title_changed(self, title: str):
        """Processes document.title IPC commands sent from JavaScript."""
        if not title or not title.startswith("app-cmd:"):
            return

        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        raw_payload = parts[2] if len(parts) > 2 else ""

        if cmd == "navigate":
            target = raw_payload.strip().lower()
            self.bridge.navigateTo(target)
        elif cmd == "google_auth":
            self.bridge.googleAuth()
        elif cmd == "forgot_password":
            self.bridge.forgotPassword()
        elif cmd == "login_submit":
            try:
                data = json.loads(raw_payload)
                self.bridge.login(
                    data.get("email", ""),
                    data.get("password", ""),
                    data.get("remember", False)
                )
            except Exception as e:
                print(f"Error parsing login payload: {e}")
        elif cmd == "register_submit":
            try:
                data = json.loads(raw_payload)
                self.bridge.register(
                    data.get("fullName", ""),
                    data.get("email", ""),
                    data.get("password", ""),
                    data.get("confirmPassword", "")
                )
            except Exception as e:
                print(f"Error parsing register payload: {e}")

    def eval_js(self, script):
        """Executes JavaScript inside the WebEngineView."""
        self.web_view.page().runJavaScript(script)

    def display_login_error(self, message):
        """Pushes error message to JavaScript in login.html."""
        escaped_msg = message.replace("'", "\\'").replace("\n", " ")
        self.eval_js(f"if (typeof showError === 'function') showError('{escaped_msg}');")

    def display_register_error(self, message):
        """Pushes error message to JavaScript in register.html."""
        escaped_msg = message.replace("'", "\\'").replace("\n", " ")
        self.eval_js(f"if (typeof showError === 'function') showError('{escaped_msg}');")

    def clear_fields(self):
        """Resets HTML forms and errors."""
        self.eval_js("if (typeof hideError === 'function') hideError();")
        self.eval_js("var f = document.querySelector('form'); if (f) f.reset();")

