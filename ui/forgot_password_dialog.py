import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QCursor

from widgets.custom_button import PrimaryButton, SecondaryButton
from ui.register import PremiumInputGroup, PasswordRequirementsWidget, ToastNotification
from utils.auth_db import AuthDB
from services.otp_service import OTPService, SendOTPWorker

class ForgotPasswordDialog(QDialog):
    """
    Polished multi-step wizard dialog for resetting password.
    Step 1: Enter email
    Step 2: Enter verification code (mock: 123456)
    Step 3: Enter new password (checked against standard criteria)
    Step 4: Success confirmation
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password")
        self.setFixedSize(480, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
        """)

        self.email_address = ""
        self.otp_worker = None
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.main_layout.setSpacing(0)

        # Wizard stacked widget
        self.stack = QStackedWidget(self)
        self.main_layout.addWidget(self.stack)

        self.init_pages()

    def init_pages(self):
        # ------------------ PAGE 0: EMAIL INPUT ------------------
        self.page_email = QFrame()
        layout_email = QVBoxLayout(self.page_email)
        layout_email.setContentsMargins(0, 0, 0, 0)
        layout_email.setSpacing(20)

        title_email = QLabel("Forgot Password")
        title_email.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")
        desc_email = QLabel("Enter your registered email address below, and we'll send you a password reset code.")
        desc_email.setWordWrap(True)
        desc_email.setStyleSheet("font-size: 13px; color: #64748B; line-height: 18px;")
        
        self.email_input = PremiumInputGroup("Email Address", "xyz@gmail.com", "assets/icons/email.png", is_password=False, parent=self)
        self.email_input.textChanged.connect(self.clear_email_errors)

        btn_layout_email = QHBoxLayout()
        btn_layout_email.setSpacing(12)
        self.btn_email_cancel = SecondaryButton("Cancel")
        self.btn_email_cancel.clicked.connect(self.reject)
        self.btn_email_next = PrimaryButton("Send Code")
        self.btn_email_next.clicked.connect(self.process_email)
        
        btn_layout_email.addWidget(self.btn_email_cancel)
        btn_layout_email.addWidget(self.btn_email_next)

        layout_email.addWidget(title_email)
        layout_email.addWidget(desc_email)
        layout_email.addWidget(self.email_input)
        layout_email.addStretch()
        layout_email.addLayout(btn_layout_email)
        self.stack.addWidget(self.page_email)

        # ------------------ PAGE 1: VERIFICATION CODE ------------------
        self.page_code = QFrame()
        layout_code = QVBoxLayout(self.page_code)
        layout_code.setContentsMargins(0, 0, 0, 0)
        layout_code.setSpacing(20)

        title_code = QLabel("Verify Identity")
        title_code.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")
        
        self.desc_code = QLabel("")
        self.desc_code.setWordWrap(True)
        self.desc_code.setStyleSheet("font-size: 13px; color: #64748B; line-height: 18px;")

        self.code_input = PremiumInputGroup("Verification Code", "Enter 6-digit code", "assets/icons/lock.png", is_password=False, parent=self)
        self.code_input.textChanged.connect(self.clear_code_errors)

        btn_layout_code = QHBoxLayout()
        btn_layout_code.setSpacing(12)
        self.btn_code_back = SecondaryButton("Back")
        self.btn_code_back.clicked.connect(self.go_back_to_email)
        self.btn_code_next = PrimaryButton("Verify")
        self.btn_code_next.clicked.connect(self.process_code)

        btn_layout_code.addWidget(self.btn_code_back)
        btn_layout_code.addWidget(self.btn_code_next)

        layout_code.addWidget(title_code)
        layout_code.addWidget(self.desc_code)
        layout_code.addWidget(self.code_input)
        layout_code.addStretch()
        layout_code.addLayout(btn_layout_code)
        self.stack.addWidget(self.page_code)

        # ------------------ PAGE 2: RESET PASSWORD ------------------
        self.page_reset = QFrame()
        layout_reset = QVBoxLayout(self.page_reset)
        layout_reset.setContentsMargins(0, 0, 0, 0)
        layout_reset.setSpacing(14)

        title_reset = QLabel("Create New Password")
        title_reset.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")
        desc_reset = QLabel("Your password must meet security requirements below.")
        desc_reset.setStyleSheet("font-size: 13px; color: #64748B;")

        self.pass_input = PremiumInputGroup("New Password", "••••••••", "assets/icons/lock.png", is_password=True, parent=self)
        self.pass_input.textChanged.connect(self.on_pass_changed)

        self.req_widget = PasswordRequirementsWidget(self)

        self.confirm_input = PremiumInputGroup("Confirm Password", "••••••••", "assets/icons/lock.png", is_password=True, parent=self)
        self.confirm_input.textChanged.connect(self.clear_confirm_errors)

        btn_layout_reset = QHBoxLayout()
        btn_layout_reset.setSpacing(12)
        self.btn_reset_back = SecondaryButton("Back")
        self.btn_reset_back.clicked.connect(self.go_back_to_code)
        self.btn_reset_save = PrimaryButton("Reset Password")
        self.btn_reset_save.clicked.connect(self.process_reset)

        btn_layout_reset.addWidget(self.btn_reset_back)
        btn_layout_reset.addWidget(self.btn_reset_save)

        layout_reset.addWidget(title_reset)
        layout_reset.addWidget(desc_reset)
        layout_reset.addWidget(self.pass_input)
        layout_reset.addWidget(self.req_widget)
        layout_reset.addWidget(self.confirm_input)
        layout_reset.addStretch()
        layout_reset.addLayout(btn_layout_reset)
        self.stack.addWidget(self.page_reset)

        # ------------------ PAGE 3: SUCCESS ------------------
        self.page_success = QFrame()
        layout_success = QVBoxLayout(self.page_success)
        layout_success.setContentsMargins(0, 0, 0, 0)
        layout_success.setSpacing(24)
        layout_success.setAlignment(Qt.AlignmentFlag.AlignCenter)

        success_icon = QLabel("✓")
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_icon.setFixedSize(64, 64)
        success_icon.setStyleSheet("""
            background-color: #EFF6FF;
            color: #2563EB;
            font-size: 32px;
            font-weight: bold;
            border-radius: 32px;
        """)

        success_title = QLabel("✓ Password Reset Complete")
        success_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #10B981;")

        success_desc = QLabel("Your account password has been updated. You can now login with your new password.")
        success_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_desc.setWordWrap(True)
        success_desc.setStyleSheet("font-size: 13px; color: #64748B; line-height: 18px;")

        self.btn_success_done = PrimaryButton("Back to Login")
        self.btn_success_done.setFixedHeight(48)
        self.btn_success_done.setFixedWidth(200)
        self.btn_success_done.clicked.connect(self.accept)

        layout_success.addStretch()
        layout_success.addWidget(success_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_success.addWidget(success_title)
        layout_success.addWidget(success_desc)
        layout_success.addStretch()
        layout_success.addWidget(self.btn_success_done, alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.page_success)

    # --- Verification & Transition Logic ---

    def clear_email_errors(self):
        self.email_input.set_error(None)

    def clear_code_errors(self):
        self.code_input.set_error(None)

    def clear_confirm_errors(self):
        self.confirm_input.set_error(None)

    def go_back_to_email(self):
        self.stack.setCurrentIndex(0)

    def go_back_to_code(self):
        self.stack.setCurrentIndex(1)

    def process_email(self):
        email = self.email_input.text().strip()
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        
        if not email:
            self.email_input.set_error("❌ Email address is required.")
            return
        if not re.match(email_regex, email):
            self.email_input.set_error("❌ Please enter a valid email address.")
            return

        # Check if user exists in database
        if not AuthDB.user_exists(email):
            self.email_input.set_error("❌ This email address is not registered.")
            return

        self.email_address = email
        
        # Disable inputs and show loading state
        self.email_input.setEnabled(False)
        self.btn_email_cancel.setEnabled(False)
        self.btn_email_next.setEnabled(False)
        self.btn_email_next.setText("Sending...")
        
        # Generate OTP
        otp = OTPService.generate_otp(email)
        
        # Start background worker to send OTP
        self.otp_worker = SendOTPWorker(email, otp)
        self.otp_worker.finished.connect(self.on_otp_sent)
        self.otp_worker.start()

    def on_otp_sent(self, success: bool, message: str):
        # Re-enable inputs
        self.email_input.setEnabled(True)
        self.btn_email_cancel.setEnabled(True)
        self.btn_email_next.setEnabled(True)
        self.btn_email_next.setText("Send Code")
        
        if success:
            self.code_input.set_error(None)  # Clear any previous error
            self.desc_code.setText(
                f"We have sent a 6-digit verification code to <b>{self.email_address}</b>.<br><br>"
                "Please check your inbox."
            )
            toast = ToastNotification(self, "Verification code sent")
            toast.show_toast()
            self.stack.setCurrentIndex(1)
        else:
            self.email_input.set_error(f"❌ Failed to send code: {message}")

    def process_code(self):
        code = self.code_input.text().strip()
        if not code:
            self.code_input.set_error("❌ Verification code is required.")
            return
        
        # Verify using OTPService
        success, message = OTPService.verify_otp(self.email_address, code)
        if not success:
            self.code_input.set_error(f"❌ {message}")
            return

        self.stack.setCurrentIndex(2)

    def on_pass_changed(self):
        pwd = self.pass_input.text()
        self.req_widget.update_requirements(pwd)
        self.pass_input.set_error(None)

    def process_reset(self):
        password = self.pass_input.text()
        confirm = self.confirm_input.text()

        # Check password rules
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        pass_err = None
        
        if not password:
            pass_err = "❌ Password is required"
        elif len(password) < 8:
            pass_err = "❌ Password must contain at least 8 characters"
        elif not any(c.isupper() for c in password):
            pass_err = "❌ Password must contain at least one uppercase letter"
        elif not any(c.islower() for c in password):
            pass_err = "❌ Password must contain at least one lowercase letter"
        elif not any(c.isdigit() for c in password):
            pass_err = "❌ Password must contain at least one number"
        elif not any(c in special_chars for c in password):
            pass_err = "❌ Password must contain one special character"

        if pass_err:
            self.pass_input.set_error(pass_err)
            return

        if confirm != password:
            self.confirm_input.set_error("❌ Passwords do not match")
            return

        # Perform update
        success, message = AuthDB.reset_password(self.email_address, password)
        if not success:
            self.pass_input.set_error(f"❌ {message}")
            return

        # Show success screen
        self.stack.setCurrentIndex(3)
