from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal

class WebBridge(QObject):
    """
    Bi-directional communication bridge between JavaScript running in 
    QWebEngineView and Python backend logic.
    """
    # Navigation signals
    gotoWelcome = pyqtSignal()
    gotoLogin = pyqtSignal()
    gotoRegister = pyqtSignal()

    # Auth signals
    loginSuccess = pyqtSignal(dict)
    registerSuccess = pyqtSignal()

    # Web UI Feedback signals (Python -> JS)
    loginFailed = pyqtSignal(str)
    registerFailed = pyqtSignal(str)

    # Dialog signals
    openForgotPasswordDialog = pyqtSignal()
    triggerGoogleLogin = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(str)
    def navigateTo(self, page_name):
        """Called from JavaScript to switch pages."""
        page_name = page_name.lower().strip()
        if page_name in ["welcome", "landing", "home"]:
            self.gotoWelcome.emit()
        elif page_name == "login":
            self.gotoLogin.emit()
        elif page_name in ["register", "signup"]:
            self.gotoRegister.emit()

    @pyqtSlot(str, str, bool)
    def login(self, email, password, remember):
        """Called from JavaScript when user submits login form."""
        from utils.auth_db import AuthDB
        success, message, user_details = AuthDB.validate_user(email, password)
        
        if success:
            self.loginSuccess.emit(user_details)
        else:
            self.loginFailed.emit(message)

    @pyqtSlot(str, str, str, str)
    def register(self, full_name, email, password, confirm_password):
        """Called from JavaScript when user submits register form."""
        if password != confirm_password:
            self.registerFailed.emit("Passwords do not match.")
            return

        from utils.auth_db import AuthDB
        success = AuthDB.register_user(full_name, email, "", password)
        
        if success:
            self.registerSuccess.emit()
        else:
            self.registerFailed.emit("An account with this email address already exists.")


    @pyqtSlot()
    def googleAuth(self):
        """Called from JavaScript when Google button is clicked."""
        self.triggerGoogleLogin.emit()

    @pyqtSlot()
    def forgotPassword(self):
        """Called from JavaScript when Forgot Password link is clicked."""
        self.openForgotPasswordDialog.emit()
