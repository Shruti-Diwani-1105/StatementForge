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

    # Profile signals
    profileUpdated = pyqtSignal(dict)
    backToDashboardRequested = pyqtSignal()

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
            from ui.login_otp_dialog import LoginOTPDialog
            from PyQt6.QtWidgets import QDialog
            
            dialog = LoginOTPDialog(email, self.parent())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.loginSuccess.emit(user_details)
            else:
                self.loginFailed.emit("Login verification cancelled or failed.")
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

    @pyqtSlot(result=dict)
    def getProfileData(self):
        """Returns the active authenticated user profile dictionary from ProfileService."""
        from utils.user_session import UserSession
        from utils.profile_service import ProfileService
        user = UserSession.get_current_user()
        email = user.get("email", "") if user else ""
        return ProfileService.get_profile(email)

    @pyqtSlot(str, str, str, str, str, str, str, result=bool)
    def saveProfileData(self, name, phone, job_title, department, timezone, bio, color):
        """Saves updated profile fields in DB, updates session, and emits signal."""
        from utils.user_session import UserSession
        from utils.profile_service import ProfileService
        user = UserSession.get_current_user()
        if not user:
            return False

        success, msg = ProfileService.update_profile(
            user["email"], name, phone, user.get("username", user["email"].split('@')[0]),
            job_title=job_title, department=department, bio=bio,
            profile_picture="", profile_color=color, timezone=timezone
        )
        if success:
            updated_profile = ProfileService.get_profile(user["email"])
            self.profileUpdated.emit(updated_profile)
            return True
        return False

