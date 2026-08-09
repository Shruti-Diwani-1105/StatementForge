import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from widgets.auth_widgets import ToastNotification, PremiumInputGroup
from services.otp_service import OTPService, SendOTPWorker

class LoginOTPDialog(QDialog):
    """
    Dialog asking for an OTP code when the user logs in for the first time.
    Sends code to email immediately on construction.
    """
    def __init__(self, email, parent=None):
        super().__init__(parent)
        self.email_address = email.strip().lower()
        self.setWindowTitle("Verify Your Email")
        self.setFixedSize(480, 420)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; }")
        
        # Resend timer setup
        self.resend_seconds_left = 0
        self.resend_timer = QTimer(self)
        self.resend_timer.setInterval(1000)
        self.resend_timer.timeout.connect(self.update_resend_countdown)
        
        self.init_ui()
        self.send_verification_code()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(20)

        title = QLabel("Login Verification")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0037b0; font-family: 'Manrope', sans-serif;")
        
        self.desc = QLabel(
            f"We have sent a 6-digit verification code to <b>{self.email_address}</b>.<br><br>"
            "Please check your inbox and enter the code below to complete your login."
        )
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("font-size: 13px; color: #64748B; line-height: 18px; font-family: 'Inter', sans-serif;")

        self.code_input = PremiumInputGroup("Verification Code", "Enter 6-digit code", "assets/icons/lock.png", is_password=False, parent=self)
        self.code_input.textChanged.connect(self.clear_errors)

        # Resend Option Row
        resend_layout = QHBoxLayout()
        resend_layout.setContentsMargins(0, 0, 0, 0)
        resend_layout.setSpacing(6)
        resend_lbl = QLabel("Didn't receive the code?")
        resend_lbl.setStyleSheet("font-size: 13px; color: #64748B; font-family: 'Inter', sans-serif;")
        
        self.resend_btn = QPushButton("Resend Code")
        self.resend_btn.setStyleSheet("font-weight: bold; border: none; padding: 0px; color: #0037b0; font-family: 'Inter', sans-serif; background: transparent; font-size: 13px;")
        self.resend_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resend_btn.clicked.connect(self.send_verification_code)
        
        resend_layout.addWidget(resend_lbl)
        resend_layout.addWidget(self.resend_btn)
        resend_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        from widgets.custom_button import PrimaryButton, SecondaryButton
        self.btn_cancel = SecondaryButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_verify = PrimaryButton("Verify")
        self.btn_verify.clicked.connect(self.verify_code)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_verify)

        main_layout.addWidget(title)
        main_layout.addWidget(self.desc)
        main_layout.addWidget(self.code_input)
        main_layout.addLayout(resend_layout)
        main_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def clear_errors(self):
        self.code_input.set_error(None)

    def send_verification_code(self):
        """Sends OTP verification code to the email address."""
        if self.resend_seconds_left > 0:
            return

        self.resend_btn.setEnabled(False)
        self.resend_btn.setText("Sending code...")
        
        # Generate OTP code using OTPService
        otp = OTPService.generate_otp(self.email_address)
        
        # Send OTP in background using worker thread with action_type="login"
        self.otp_worker = SendOTPWorker(self.email_address, otp, action_type="login")
        self.otp_worker.finished.connect(self.on_otp_sent)
        self.otp_worker.start()

    def on_otp_sent(self, success: bool, message: str):
        if success:
            self.code_input.set_error(None)
            toast = ToastNotification(self, "Verification code sent!")
            toast.show_toast()
            self.start_resend_countdown(30)
        else:
            self.code_input.set_error(f"❌ Failed to send code: {message}")
            self.resend_btn.setEnabled(True)
            self.resend_btn.setText("Resend Code")

    def start_resend_countdown(self, seconds=30):
        self.resend_seconds_left = seconds
        self.resend_btn.setEnabled(False)
        self.resend_btn.setText(f"Resend in {self.resend_seconds_left}s")
        self.resend_timer.start()

    def update_resend_countdown(self):
        self.resend_seconds_left -= 1
        if self.resend_seconds_left <= 0:
            self.resend_timer.stop()
            self.resend_btn.setEnabled(True)
            self.resend_btn.setText("Resend Code")
        else:
            self.resend_btn.setText(f"Resend in {self.resend_seconds_left}s")

    def verify_code(self):
        code = self.code_input.text().strip()
        if not code:
            self.code_input.set_error("❌ Verification code is required.")
            return
            
        success, message = OTPService.verify_otp(self.email_address, code)
        if not success:
            self.code_input.set_error(f"❌ {message}")
            return
            
        self.resend_timer.stop()
        self.accept()
