import os
import json
import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from utils.user_session import UserSession
from utils.profile_service import ProfileService
from utils.theme_manager import ThemeManager

class ProfileWindow(QWidget):
    """
    Dedicated Profile & Edit Profile window rendering native web/profile.html.
    Supports real-time bidirectional communication with Python backend services.
    """
    save_requested = pyqtSignal(str, str, str)  # name, phone, username
    password_change_requested = pyqtSignal(str, str)  # old_password, new_password
    logout_requested = pyqtSignal()
    back_to_dashboard = pyqtSignal()
    profile_updated = pyqtSignal(dict)  # Emitted on successful profile save

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProfileWindow")
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # WebEngine View
        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        # IPC listener
        self.web_view.titleChanged.connect(self.handle_title_changed)
        
        # Load profile.html
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_dir, "web", "profile.html")
        if os.path.exists(html_path):
            self.web_view.setUrl(QUrl.fromLocalFile(html_path))
            self.web_view.loadFinished.connect(self._on_html_loaded)
        else:
            print(f"Error: Profile HTML file not found at {html_path}")

        self.layout.addWidget(self.web_view)

    def _on_html_loaded(self, success):
        if success:
            user = UserSession.get_current_user()
            if user:
                self.load_user_data(user)
            self.update_theme_style(ThemeManager.get_theme())

    def load_user_data(self, user):
        """Fetches real user profile from database and populates HTML view."""
        email = user.get("email", "") if user else ""
        profile_data = ProfileService.get_profile(email)
        
        # Datetime serializer for JSON
        def dt_converter(o):
            if isinstance(o, datetime.datetime):
                return o.isoformat()
            return str(o)

        json_str = json.dumps(profile_data, default=dt_converter)
        script = f"if (typeof loadUserProfileData === 'function') {{ loadUserProfileData({json_str}); }}"
        self.web_view.page().runJavaScript(script)

    def handle_title_changed(self, title: str):
        """Processes document.title IPC commands sent from JavaScript inside Profile HTML."""
        if not title or not title.startswith("app-cmd:"):
            return
        
        parts = title.split(":", 2)
        cmd = parts[1] if len(parts) > 1 else ""
        payload_str = parts[2] if len(parts) > 2 else ""

        payload = None
        if payload_str:
            try:
                payload = json.loads(payload_str)
            except Exception:
                payload = payload_str

        if cmd == "profile_back":
            self.back_to_dashboard.emit()

        elif cmd == "profile_request_data":
            user = UserSession.get_current_user()
            if user:
                self.load_user_data(user)

        elif cmd == "profile_save":
            if isinstance(payload, dict):
                name = payload.get("name", "")
                phone = payload.get("phone", "")
                job_title = payload.get("job_title", "")
                department = payload.get("department", "")
                timezone = payload.get("timezone", "")
                bio = payload.get("bio", "")
                profile_color = payload.get("profile_color", "#0037b0")

                user = UserSession.get_current_user()
                if not user:
                    self.show_toast("No active user session found.", is_error=True)
                    return

                username = user.get("username", user.get("email", "").split('@')[0])
                success, msg = ProfileService.update_profile(
                    user["email"], name, phone, username,
                    job_title=job_title, department=department, bio=bio,
                    profile_color=profile_color, timezone=timezone
                )

                if success:
                    updated = ProfileService.get_profile(user["email"])
                    self.load_user_data(updated)
                    self.profile_updated.emit(updated)
                    self.show_toast("Profile updated successfully!", is_error=False)
                    # Switch view back to view mode in JS
                    self.web_view.page().runJavaScript("if (typeof toggleEditView === 'function') toggleEditView(false);")
                else:
                    self.show_toast(msg, is_error=True)

        elif cmd in ["profile_reset_password", "profile_forgot_password", "forgot_password"]:
            from PyQt6.QtWidgets import QDialog
            from ui.forgot_password_dialog import ForgotPasswordDialog
            user = UserSession.get_current_user()
            email = user.get("email", "") if user else ""
            dialog = ForgotPasswordDialog(self)
            if email:
                dialog.email_input.setText(email)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.show_toast("Password reset completed successfully!", is_error=False)
                if email:
                    updated = ProfileService.get_profile(email)
                    self.load_user_data(updated)

        elif cmd == "profile_change_password":
            if isinstance(payload, dict):
                old_pwd = payload.get("old_password", "")
                new_pwd = payload.get("new_password", "")
                user = UserSession.get_current_user()
                if not user:
                    self.show_toast("No active session.", is_error=True)
                    return

                success, msg = ProfileService.change_password(user["email"], old_pwd, new_pwd)
                if success:
                    self.show_toast(msg, is_error=False)
                    self.web_view.page().runJavaScript("if (typeof closePasswordModal === 'function') closePasswordModal();")
                    updated = ProfileService.get_profile(user["email"])
                    self.load_user_data(updated)
                else:
                    self.show_toast(msg, is_error=True)

        elif cmd == "profile_set_password":
            if isinstance(payload, dict):
                new_pwd = payload.get("new_password", "")
                user = UserSession.get_current_user()
                if not user:
                    self.show_toast("No active session.", is_error=True)
                    return

                success, msg = ProfileService.set_password(user["email"], new_pwd)
                if success:
                    self.show_toast(msg, is_error=False)
                    self.web_view.page().runJavaScript("if (typeof closePasswordModal === 'function') closePasswordModal();")
                    updated = ProfileService.get_profile(user["email"])
                    self.load_user_data(updated)
                else:
                    self.show_toast(msg, is_error=True)

        elif cmd == "profile_update_notifications":
            if isinstance(payload, dict):
                user = UserSession.get_current_user()
                if not user:
                    return
                email_n = payload.get("email_notifications", True)
                desktop_n = payload.get("desktop_notifications", True)
                stmt_n = payload.get("statement_notifications", True)

                success, msg = ProfileService.update_notifications(user["email"], email_n, desktop_n, stmt_n)
                if success:
                    self.show_toast(msg, is_error=False)
                    updated = ProfileService.get_profile(user["email"])
                    self.load_user_data(updated)

        elif cmd == "profile_disconnect_google":
            user = UserSession.get_current_user()
            if user:
                success, msg = ProfileService.disconnect_google(user["email"])
                if success:
                    self.show_toast(msg, is_error=False)
                    updated = ProfileService.get_profile(user["email"])
                    self.load_user_data(updated)
                else:
                    self.show_toast(msg, is_error=True)

        elif cmd == "profile_connect_google":
            self.show_toast("Google connect feature uses Google sign in from login page.", is_error=False)

    def show_toast(self, message: str, is_error: bool = False):
        """Calls JavaScript showToast() function inside Profile HTML."""
        safe_msg = message.replace("'", "\\'").replace("\n", " ")
        err_bool = "true" if is_error else "false"
        script = f"if (typeof showToast === 'function') showToast('{safe_msg}', {err_bool});"
        self.web_view.page().runJavaScript(script)

    def show_error(self, message: str):
        self.show_toast(message, is_error=True)

    def show_success_toast(self, message: str):
        self.show_toast(message, is_error=False)

    def clear_password_fields(self):
        self.web_view.page().runJavaScript("if (typeof closePasswordModal === 'function') closePasswordModal();")

    def update_theme_style(self, theme: str):
        """Updates Light/Dark mode styling dynamically based on system theme."""
        if theme == "dark":
            script = "document.body.classList.add('dark-mode');"
        else:
            script = "document.body.classList.remove('dark-mode');"
        self.web_view.page().runJavaScript(script)
