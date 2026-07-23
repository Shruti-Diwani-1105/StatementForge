from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from ui.html_screen_wrapper import HtmlScreenWrapper

class LoginScreen(QWidget):
    """
    Login screen rendered via HTML, CSS, and JS with Python backend integration.
    """
    loginSuccess = pyqtSignal(dict)
    gotoRegister = pyqtSignal()
    gotoWelcome = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.html_wrapper = HtmlScreenWrapper("web/login.html", self)
        layout.addWidget(self.html_wrapper)
        
        # Connect bridge signals
        self.html_wrapper.bridge.gotoWelcome.connect(self.gotoWelcome.emit)
        self.html_wrapper.bridge.gotoRegister.connect(self.gotoRegister.emit)
        self.html_wrapper.bridge.loginSuccess.connect(self.loginSuccess.emit)
        self.html_wrapper.bridge.openForgotPasswordDialog.connect(self.show_forgot_password_dialog)
        self.html_wrapper.bridge.triggerGoogleLogin.connect(self.handle_google_login)

    def clear_fields(self):
        """Resets HTML form and errors."""
        self.html_wrapper.clear_fields()

    def show_forgot_password_dialog(self):
        from ui.forgot_password_dialog import ForgotPasswordDialog
        dialog = ForgotPasswordDialog(self)
        dialog.exec()

    def handle_google_login(self):
        from services.google_auth_service import GoogleAuthWorker
        self.google_worker = GoogleAuthWorker()
        self.google_worker.finished.connect(self.on_google_auth_finished)
        self.google_worker.start()

    def on_google_auth_finished(self, success, result):
        if not success:
            error_msg = result.get("error", "Failed to authenticate with Google.")
            if "cancelled" not in error_msg.lower():
                self.html_wrapper.display_login_error(error_msg)
            return

        from utils.auth_db import AuthDB
        email = result.get("email")
        name = result.get("name", "Google User")
        
        login_success, message, user_details = AuthDB.get_or_create_google_user(email, name)
        
        if not login_success:
            self.html_wrapper.display_login_error(message)
            return
            
        self.loginSuccess.emit(user_details)
