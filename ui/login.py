from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QSpacerItem, QSizePolicy, QMessageBox, QFrame, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QCursor, QAction, QIcon
from widgets.custom_button import PrimaryButton, SecondaryButton, LinkButton

class LoginScreen(QWidget):
    """
    Login screen with email, password fields, validation logic,
    and redirection anchors to Register and Forgot Password.
    """
    loginSuccess = pyqtSignal(dict)
    gotoRegister = pyqtSignal()
    gotoWelcome = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("LoginBackground")
        self.setStyleSheet("background-color: #f7f9fb;")
        
        # Outer layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(0)
        
        # 1. Back button in top-left
        top_bar_layout = QHBoxLayout()
        self.back_btn = SecondaryButton("←  Back")
        self.back_btn.setFixedWidth(100)
        self.back_btn.setFixedHeight(36)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #4B5563;
                border: 1px solid #c4c5d7;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover {
                background-color: #f2f4f6;
            }
        """)
        self.back_btn.clicked.connect(self.gotoWelcome.emit)
        top_bar_layout.addWidget(self.back_btn)
        top_bar_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        outer_layout.addLayout(top_bar_layout)
        
        outer_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Centered Login Card Container
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        self.card.setFixedWidth(440)
        self.card.setStyleSheet("""
            QFrame#LoginCard {
                background-color: #FFFFFF;
                border: 1px solid #c4c5d7;
                border-top: 4px solid #0037b0;
                border-radius: 12px;
            }
        """)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)
        
        # Logo & Heading
        logo_container = QLabel()
        logo_container.setFixedSize(64, 64)
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_container.setStyleSheet("""
            background-color: rgba(0, 55, 176, 0.1);
            border-radius: 16px;
        """)
        logo_pixmap = QPixmap("assets/logo.png")
        if not logo_pixmap.isNull():
            logo_container.setPixmap(logo_pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            
        logo_wrapper = QHBoxLayout()
        logo_wrapper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_wrapper.addWidget(logo_container)
        card_layout.addLayout(logo_wrapper)
        
        title_label = QLabel("Welcome Back")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #191c1e; font-family: 'Times New Roman'; border: none;")
        card_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Login to manage and parse your statements.")
        subtitle_label.setObjectName("ScreenSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 13px; color: #434655; font-family: 'Times New Roman'; border: none;")
        card_layout.addWidget(subtitle_label)
        
        card_layout.addSpacing(10)
        
        # Form layout
        form_layout = QVBoxLayout()
        form_layout.setSpacing(14)
        
        # Email Input Group
        email_label = QLabel("Email Address")
        email_label.setObjectName("FormLabel")
        email_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #191c1e; font-family: 'Times New Roman'; border: none;")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setFixedHeight(36)
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #c4c5d7;
                border-radius: 6px;
                background-color: #f7f9fb;
                color: #191c1e;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QLineEdit:focus {
                border: 2px solid #0037b0;
                background-color: #ffffff;
            }
        """)
        
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        
        # Password Input Group
        pass_layout = QHBoxLayout()
        pass_label = QLabel("Password")
        pass_label.setObjectName("FormLabel")
        pass_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #191c1e; font-family: 'Times New Roman'; border: none;")
        pass_layout.addWidget(pass_label)
        
        pass_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.forgot_btn = LinkButton("Forgot Password?")
        self.forgot_btn.setStyleSheet("font-size: 13px; color: #0037b0; font-weight: 500; border: none; padding: 0px; font-family: 'Times New Roman'; background: transparent;")
        self.forgot_btn.clicked.connect(self.show_forgot_password_dialog)
        pass_layout.addWidget(self.forgot_btn)
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Enter your password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setFixedHeight(36)
        self.pass_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #c4c5d7;
                border-radius: 6px;
                background-color: #f7f9fb;
                color: #191c1e;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QLineEdit:focus {
                border: 2px solid #0037b0;
                background-color: #ffffff;
            }
        """)
        
        # Add show/hide password toggle action
        self.show_pass_action = QAction(self.pass_input)
        self.eye_closed_icon = QIcon("assets/icons/eye_closed.png")
        self.eye_open_icon = QIcon("assets/icons/eye.png")
        self.show_pass_action.setIcon(self.eye_closed_icon)
        self.pass_input.addAction(self.show_pass_action, QLineEdit.ActionPosition.TrailingPosition)
        self.show_pass_action.triggered.connect(self.toggle_password_visibility)
        
        form_layout.addLayout(pass_layout)
        form_layout.addWidget(self.pass_input)
        card_layout.addLayout(form_layout)
        
        # Inline error display
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ba1a1a; font-size: 12px; font-weight: 500; font-family: 'Times New Roman';")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)
        
        # Remember Me checkbox
        self.remember_cb = QCheckBox("Remember this device")
        self.remember_cb.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                color: #434655;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
        """)
        card_layout.addWidget(self.remember_cb)
        
        # Login Trigger Button
        self.login_btn = PrimaryButton("Login to Account")
        self.login_btn.setFixedHeight(40)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(self.login_btn)
        
        # Or separator line
        or_layout = QHBoxLayout()
        or_layout.setContentsMargins(0, 5, 0, 5)
        or_line1 = QFrame()
        or_line1.setFrameShape(QFrame.Shape.HLine)
        or_line1.setFrameShadow(QFrame.Shadow.Sunken)
        or_line1.setStyleSheet("background-color: #c4c5d7; max-height: 1px; border: none;")
        or_lbl = QLabel("or")
        or_lbl.setObjectName("OrLabel")
        or_lbl.setStyleSheet("font-size: 13px; font-weight: 500; padding: 0 8px; color: #434655; font-family: 'Times New Roman'; border: none;")
        or_line2 = QFrame()
        or_line2.setFrameShape(QFrame.Shape.HLine)
        or_line2.setFrameShadow(QFrame.Shadow.Sunken)
        or_line2.setStyleSheet("background-color: #c4c5d7; max-height: 1px; border: none;")
        or_layout.addWidget(or_line1)
        or_layout.addWidget(or_lbl)
        or_layout.addWidget(or_line2)
        card_layout.addLayout(or_layout)

        # Continue with Google button
        self.google_btn = SecondaryButton("Continue with Google")
        self.google_btn.setFixedHeight(40)
        self.google_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #191c1e;
                border: 1px solid #c4c5d7;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
                font-family: 'Times New Roman';
            }
            QPushButton:hover {
                background-color: #f2f4f6;
            }
        """)
        google_pixmap = QPixmap("assets/icons/google.png")
        if not google_pixmap.isNull():
            self.google_btn.setIcon(QIcon(google_pixmap.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
        self.google_btn.setIconSize(QSize(18, 18))
        self.google_btn.clicked.connect(self.handle_google_login)
        card_layout.addWidget(self.google_btn)
        
        # Register redirect link
        register_link_layout = QHBoxLayout()
        register_link_layout.setSpacing(4)
        register_link_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        register_lbl = QLabel("Don't have an account?")
        register_lbl.setObjectName("ScreenSubtitle")
        register_lbl.setStyleSheet("font-size: 13px; color: #434655; font-family: 'Times New Roman'; border: none;")
        
        self.register_btn = LinkButton("Register Now")
        self.register_btn.setStyleSheet("font-weight: bold; border: none; padding: 0px; color: #0037b0; font-family: 'Times New Roman'; background: transparent; font-size: 13px;")
        self.register_btn.clicked.connect(self.gotoRegister.emit)
        
        register_link_layout.addWidget(register_lbl)
        register_link_layout.addWidget(self.register_btn)
        card_layout.addLayout(register_link_layout)
        
        # Center card layout
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        horizontal_layout.addWidget(self.card)
        horizontal_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        outer_layout.addLayout(horizontal_layout)
        outer_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def handle_login(self):
        """Validates credentials against local memory database."""
        email = self.email_input.text().strip()
        password = self.pass_input.text().strip()
        
        from utils.auth_db import AuthDB
        success, message, user_details = AuthDB.validate_user(email, password)
        
        if not success:
            self.error_label.setText(message)
            self.error_label.setVisible(True)
            return
            
        self.error_label.setVisible(False)
        self.loginSuccess.emit(user_details)

    def show_forgot_password_dialog(self):
        from ui.forgot_password_dialog import ForgotPasswordDialog
        dialog = ForgotPasswordDialog(self)
        dialog.exec()

    def toggle_password_visibility(self):
        """Toggles the password field between hidden and visible text."""
        if self.pass_input.echoMode() == QLineEdit.EchoMode.Password:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_pass_action.setIcon(self.eye_open_icon)
        else:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_pass_action.setIcon(self.eye_closed_icon)

    def clear_fields(self):
        """Resets credentials and error alerts when displaying the page anew."""
        self.email_input.clear()
        self.pass_input.clear()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_pass_action.setIcon(self.eye_closed_icon)
        self.error_label.setVisible(False)

    def handle_google_login(self):
        # If currently running and user requested cancel, treat this click as cancel
        if self.google_btn.text() == "Cancel Sign-In":
            if hasattr(self, 'google_worker') and self.google_worker and self.google_worker.isRunning():
                self.google_worker.cancel()
            self.on_google_auth_finished(False, {"error": "Google Sign-In was cancelled by the user."})
            return

        self.error_label.setVisible(False)
        self.google_btn.setText("Cancel Sign-In")
        self.login_btn.setEnabled(False)

        # If a previous worker is still running in the background, disconnect it and cancel it
        if hasattr(self, 'google_worker') and self.google_worker and self.google_worker.isRunning():
            try:
                self.google_worker.finished.disconnect(self.on_google_auth_finished)
            except TypeError:
                pass
            self.google_worker.cancel()
            if not hasattr(self, '_active_google_workers'):
                self._active_google_workers = set()
            old_worker = self.google_worker
            self._active_google_workers.add(old_worker)
            old_worker.finished.connect(lambda: self._active_google_workers.discard(old_worker))

        from services.google_auth_service import GoogleAuthWorker
        self.google_worker = GoogleAuthWorker()
        self.google_worker.finished.connect(self.on_google_auth_finished)
        self.google_worker.start()

    def on_google_auth_finished(self, success, result):
        self.google_btn.setEnabled(True)
        self.google_btn.setText("Continue with Google")
        self.login_btn.setEnabled(True)

        if not success:
            error_msg = result.get("error", "Failed to authenticate with Google.")
            if "cancelled" in error_msg.lower():
                self.error_label.setVisible(False)
                return
            self.error_label.setText(f"❌ {error_msg}")
            self.error_label.setVisible(True)
            return

        # Authenticate / Auto-register Google user in AuthDB
        from utils.auth_db import AuthDB
        email = result.get("email")
        name = result.get("name", "Google User")
        
        login_success, message, user_details = AuthDB.get_or_create_google_user(email, name)
        
        if not login_success:
            self.error_label.setText(f"❌ {message}")
            self.error_label.setVisible(True)
            return
            
        self.error_label.setVisible(False)
        self.loginSuccess.emit(user_details)
