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
        
        # Enable drag & drop support
        self.setAcceptDrops(True)
        
        # Instantiate WebEngineView
        self.web_view = QWebEngineView(self)
        self.web_view.setAcceptDrops(True)
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
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._process_title_changed(title))

    def _process_title_changed(self, title: str):
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
        elif cmd == "get_admin_data":
            from services.admin_service import AdminService
            users = AdminService.get_all_users()
            stats = AdminService.get_system_stats()
            statements = AdminService.get_all_statements()
            logs = AdminService.get_audit_logs()
            
            users_json = json.dumps(users)
            stats_json = json.dumps(stats)
            stmts_json = json.dumps(statements)
            logs_json = json.dumps(logs)
            
            js_code = (
                f"if (typeof renderAdminUsersData === 'function') renderAdminUsersData({users_json}); "
                f"if (typeof renderAdminStatsData === 'function') renderAdminStatsData({stats_json}); "
                f"if (typeof renderAdminStatementsData === 'function') renderAdminStatementsData({stmts_json}); "
                f"if (typeof renderAdminLogsData === 'function') renderAdminLogsData({logs_json});"
            )
            self.eval_js(js_code)
        elif cmd == "create_admin_user":
            try:
                data = json.loads(raw_payload)
                from services.admin_service import AdminService
                success, msg = AdminService.create_user(
                    data.get("name", ""), data.get("email", ""), data.get("phone", ""),
                    data.get("password", ""), data.get("role", "user"), data.get("status", "active")
                )
                escaped_msg = msg.replace("'", "\\'").replace("\n", " ")
                self.eval_js(f"if (typeof onAdminActionComplete === 'function') onAdminActionComplete('add_user', {json.dumps(success)}, '{escaped_msg}');")
            except Exception as e:
                print(f"Error handling create_admin_user: {e}")
        elif cmd == "update_admin_user":
            try:
                data = json.loads(raw_payload)
                from services.admin_service import AdminService
                success, msg = AdminService.update_user(
                    data.get("email", ""), data.get("name", ""), data.get("phone", ""),
                    data.get("role", "user"), data.get("status", "active")
                )
                escaped_msg = msg.replace("'", "\\'").replace("\n", " ")
                self.eval_js(f"if (typeof onAdminActionComplete === 'function') onAdminActionComplete('edit_user', {json.dumps(success)}, '{escaped_msg}');")
            except Exception as e:
                print(f"Error handling update_admin_user: {e}")
        elif cmd == "reset_admin_password":
            try:
                data = json.loads(raw_payload)
                from services.admin_service import AdminService
                success, msg = AdminService.reset_user_password(data.get("email", ""), data.get("new_password", ""))
                escaped_msg = msg.replace("'", "\\'").replace("\n", " ")
                self.eval_js(f"if (typeof onAdminActionComplete === 'function') onAdminActionComplete('reset_pwd', {json.dumps(success)}, '{escaped_msg}');")
            except Exception as e:
                print(f"Error handling reset_admin_password: {e}")
        elif cmd == "update_user_role":
            try:
                data = json.loads(raw_payload)
                from services.admin_service import AdminService
                success, msg = AdminService.update_user_role(data.get("email", ""), data.get("role", "user"))
                escaped_msg = msg.replace("'", "\\'").replace("\n", " ")
                self.eval_js(f"if (typeof onAdminActionComplete === 'function') onAdminActionComplete('role', {json.dumps(success)}, '{escaped_msg}');")
            except Exception as e:
                print(f"Error handling update_user_role: {e}")
        elif cmd == "update_user_status":
            try:
                data = json.loads(raw_payload)
                from services.admin_service import AdminService
                success, msg = AdminService.update_user_status(data.get("email", ""), data.get("status", "active"))
                escaped_msg = msg.replace("'", "\\'").replace("\n", " ")
                self.eval_js(f"if (typeof onAdminActionComplete === 'function') onAdminActionComplete('status', {json.dumps(success)}, '{escaped_msg}');")
            except Exception as e:
                print(f"Error handling update_user_status: {e}")
        elif cmd == "delete_user_account":
            try:
                data = json.loads(raw_payload)
                from services.admin_service import AdminService
                success, msg = AdminService.delete_user(data.get("email", ""))
                escaped_msg = msg.replace("'", "\\'").replace("\n", " ")
                self.eval_js(f"if (typeof onAdminActionComplete === 'function') onAdminActionComplete('delete', {json.dumps(success)}, '{escaped_msg}');")
            except Exception as e:
                print(f"Error handling delete_user_account: {e}")

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

