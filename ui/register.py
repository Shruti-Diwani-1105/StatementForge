from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from ui.html_screen_wrapper import HtmlScreenWrapper
from widgets.auth_widgets import ToastNotification, PasswordRequirementsWidget, PremiumInputGroup

class RegisterScreen(QWidget):
    """
    Registration screen rendered via HTML, CSS, and JS with Python backend integration.
    """
    gotoWelcome = pyqtSignal()
    gotoLogin = pyqtSignal()
    registerSuccess = pyqtSignal()
    loginSuccess = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.html_wrapper = HtmlScreenWrapper("web/register.html", self)
        layout.addWidget(self.html_wrapper)
        
        # Connect bridge signals
        self.html_wrapper.bridge.gotoWelcome.connect(self.gotoWelcome.emit)
        self.html_wrapper.bridge.gotoLogin.connect(self.gotoLogin.emit)
        self.html_wrapper.bridge.registerSuccess.connect(self.registerSuccess.emit)
        self.html_wrapper.bridge.triggerGoogleLogin.connect(self.handle_google_login)

    def clear_fields(self):
        """Resets HTML form and errors."""
        self.html_wrapper.clear_fields()

    def handle_google_login(self):
        from services.google_auth_service import GoogleAuthWorker
        self.google_worker = GoogleAuthWorker()
        self.google_worker.finished.connect(self.on_google_auth_finished)
        self.google_worker.start()

    def on_google_auth_finished(self, success, result):
        if not success:
            error_msg = result.get("error", "Failed to authenticate with Google.")
            if "cancelled" not in error_msg.lower():
                self.html_wrapper.display_register_error(error_msg)
            return

        from utils.auth_db import AuthDB
        email = result.get("email")
        name = result.get("name", "Google User")
        
        login_success, message, user_details = AuthDB.get_or_create_google_user(email, name)
        
        if not login_success:
            self.html_wrapper.display_register_error(message)
            return
            
        self.loginSuccess.emit(user_details)
