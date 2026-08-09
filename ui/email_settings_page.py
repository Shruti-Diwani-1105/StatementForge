import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QGridLayout, QMessageBox,
    QProgressBar, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont

from services.email_service import PROVIDER_PRESETS, EmailService
from services.credential_manager import CredentialManager
from settings.settings_service import SettingsService
from settings.widgets.setting_card import SettingCard
from settings.widgets.password_input import PasswordInput
from utils.user_session import UserSession
from workers.email_worker import EmailTestWorker

class EmailSettingsPage(QWidget):
    """
    Dedicated Email Configuration tab view for StatementForge settings.
    Configures SMTP providers, sender details, and secure credentials stored in OS keychain.
    Uses a scroll area and explicit control heights to guarantee pristine layout rendering.
    """
    settingsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "light"
        self.init_ui()
        self.load_email_settings()

    def init_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Main Scroll Area
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        main_layout = QVBoxLayout(self.scroll_content)
        main_layout.setContentsMargins(0, 0, 16, 24)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Header Title
        title_lay = QVBoxLayout()
        title_lay.setSpacing(4)
        
        self.page_title = QLabel("Email Configuration")
        self.page_title.setObjectName("SettingsPageTitle")
        self.page_title.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A; font-family: 'Manrope', sans-serif;")
        
        self.page_sub = QLabel("Configure secure SMTP settings for sending financial reports directly via email.")
        self.page_sub.setObjectName("SettingsPageSubtitle")
        self.page_sub.setStyleSheet("font-size: 13px; color: #64748B; font-family: 'Inter', sans-serif;")
        
        title_lay.addWidget(self.page_title)
        title_lay.addWidget(self.page_sub)
        main_layout.addLayout(title_lay)

        # Card 1: SMTP Provider & Account Details
        self.card1 = SettingCard("Email Provider & Sender Account", "Select provider and enter your sender email address.")
        grid1 = QGridLayout()
        grid1.setSpacing(14)

        # Provider Selector
        lbl_p = QLabel("Email Provider:")
        lbl_p.setStyleSheet("font-weight: 600; font-size: 13px; color: #334155; font-family: 'Inter', sans-serif;")
        grid1.addWidget(lbl_p, 0, 0)

        self.provider_combo = QComboBox()
        self.provider_combo.setFixedHeight(40)
        self.provider_combo.addItems(["Gmail", "Outlook / Microsoft", "Yahoo", "Custom SMTP server"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        grid1.addWidget(self.provider_combo, 0, 1)

        # Sender Email
        lbl_s = QLabel("Sender Email Address:")
        lbl_s.setStyleSheet("font-weight: 600; font-size: 13px; color: #334155; font-family: 'Inter', sans-serif;")
        grid1.addWidget(lbl_s, 1, 0)

        self.sender_email_input = QLineEdit()
        self.sender_email_input.setFixedHeight(40)
        self.sender_email_input.setPlaceholderText("your-email@domain.com")
        self.sender_email_input.textChanged.connect(lambda: self.settingsChanged.emit())
        grid1.addWidget(self.sender_email_input, 1, 1)

        # Password / App Password
        lbl_pass = QLabel("App Password / SMTP Password:")
        lbl_pass.setStyleSheet("font-weight: 600; font-size: 13px; color: #334155; font-family: 'Inter', sans-serif;")
        grid1.addWidget(lbl_pass, 2, 0)

        self.password_input = PasswordInput()
        self.password_input.setFixedHeight(40)
        self.password_input.line_edit.setPlaceholderText("Enter App Password or SMTP Password")
        self.password_input.textChanged.connect(lambda p: self.settingsChanged.emit())
        grid1.addWidget(self.password_input, 2, 1)

        self.card1.add_layout(grid1)

        # Provider note box
        self.provider_note_card = QFrame()
        self.provider_note_card.setStyleSheet("background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px;")
        note_lay = QHBoxLayout(self.provider_note_card)
        note_lay.setContentsMargins(14, 10, 14, 10)
        
        self.note_lbl = QLabel("💡 Use an App Password instead of your normal Google account password.")
        self.note_lbl.setStyleSheet("font-size: 12.5px; color: #1E40AF; font-weight: 500; font-family: 'Inter', sans-serif;")
        self.note_lbl.setWordWrap(True)
        note_lay.addWidget(self.note_lbl)
        self.card1.add_widget(self.provider_note_card)

        main_layout.addWidget(self.card1)

        # Card 2: Server Technical Configuration
        self.card2 = SettingCard("SMTP Server Details", "Technical SMTP server configuration and encryption preferences.")
        grid2 = QGridLayout()
        grid2.setSpacing(14)

        # Host
        lbl_h = QLabel("SMTP Server Host:")
        lbl_h.setStyleSheet("font-weight: 600; font-size: 13px; color: #334155; font-family: 'Inter', sans-serif;")
        grid2.addWidget(lbl_h, 0, 0)

        self.host_input = QLineEdit()
        self.host_input.setFixedHeight(40)
        self.host_input.setPlaceholderText("e.g. smtp.gmail.com")
        self.host_input.textChanged.connect(lambda: self.settingsChanged.emit())
        grid2.addWidget(self.host_input, 0, 1)

        # Port
        lbl_prt = QLabel("SMTP Port:")
        lbl_prt.setStyleSheet("font-weight: 600; font-size: 13px; color: #334155; font-family: 'Inter', sans-serif;")
        grid2.addWidget(lbl_prt, 1, 0)

        self.port_input = QLineEdit()
        self.port_input.setFixedHeight(40)
        self.port_input.setPlaceholderText("587 or 465")
        self.port_input.textChanged.connect(lambda: self.settingsChanged.emit())
        grid2.addWidget(self.port_input, 1, 1)

        # Encryption Type
        lbl_enc = QLabel("Encryption Type:")
        lbl_enc.setStyleSheet("font-weight: 600; font-size: 13px; color: #334155; font-family: 'Inter', sans-serif;")
        grid2.addWidget(lbl_enc, 2, 0)

        self.encryption_combo = QComboBox()
        self.encryption_combo.setFixedHeight(40)
        self.encryption_combo.addItems(["STARTTLS", "SSL/TLS", "None"])
        self.encryption_combo.currentTextChanged.connect(lambda: self.settingsChanged.emit())
        grid2.addWidget(self.encryption_combo, 2, 1)

        self.card2.add_layout(grid2)
        main_layout.addWidget(self.card2)

        # Card 3: Test Connection Section
        self.card3 = SettingCard("Verify & Test Connection", "Test your SMTP settings before sending report dispatches.")
        test_lay = QVBoxLayout()
        test_lay.setSpacing(12)

        test_row = QHBoxLayout()
        test_row.setSpacing(10)

        self.test_recipient_input = QLineEdit()
        self.test_recipient_input.setFixedHeight(40)
        self.test_recipient_input.setPlaceholderText("Optional test recipient email to send a test message")
        test_row.addWidget(self.test_recipient_input, stretch=1)

        self.btn_test = QPushButton("Test Connection")
        self.btn_test.setFixedHeight(40)
        self.btn_test.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 8px;
                padding: 0 20px;
                border: none;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #CBD5E1; color: #94A3B8; }
        """)
        self.btn_test.clicked.connect(self.run_connection_test)
        test_row.addWidget(self.btn_test)

        test_lay.addLayout(test_row)

        self.test_progress = QProgressBar()
        self.test_progress.setRange(0, 0)
        self.test_progress.setTextVisible(False)
        self.test_progress.setFixedHeight(4)
        self.test_progress.hide()
        test_lay.addWidget(self.test_progress)

        self.test_status_lbl = QLabel("")
        self.test_status_lbl.setWordWrap(True)
        self.test_status_lbl.hide()
        test_lay.addWidget(self.test_status_lbl)

        self.card3.add_layout(test_lay)
        main_layout.addWidget(self.card3)

        self.scroll.setWidget(self.scroll_content)
        page_layout.addWidget(self.scroll)

        self.apply_inputs_style()

    def apply_inputs_style(self):
        if self.current_theme == "dark":
            input_qss = """
                QLineEdit, QComboBox {
                    background-color: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 0 12px;
                    font-size: 13px;
                    font-family: 'Inter', sans-serif;
                    color: #F8FAFC;
                }
                QLineEdit:focus, QComboBox:focus {
                    border-color: #3B82F6;
                }
            """
        else:
            input_qss = """
                QLineEdit, QComboBox {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 0 12px;
                    font-size: 13px;
                    font-family: 'Inter', sans-serif;
                    color: #0F172A;
                }
                QLineEdit:focus, QComboBox:focus {
                    border-color: #2563EB;
                }
            """
        self.provider_combo.setStyleSheet(input_qss)
        self.sender_email_input.setStyleSheet(input_qss)
        self.host_input.setStyleSheet(input_qss)
        self.port_input.setStyleSheet(input_qss)
        self.encryption_combo.setStyleSheet(input_qss)
        self.test_recipient_input.setStyleSheet(input_qss)

    def apply_theme(self, theme):
        self.current_theme = theme.lower().strip() if isinstance(theme, str) else "light"
        self.apply_inputs_style()
        if hasattr(self, "card1"): self.card1.update_theme_style(self.current_theme)
        if hasattr(self, "card2"): self.card2.update_theme_style(self.current_theme)
        if hasattr(self, "card3"): self.card3.update_theme_style(self.current_theme)

    def on_provider_changed(self, provider_name):
        preset = PROVIDER_PRESETS.get(provider_name)
        if preset:
            self.host_input.setText(preset["host"])
            self.port_input.setText(str(preset["port"]))
            self.encryption_combo.setCurrentText(preset["encryption"])
            self.note_lbl.setText(f"💡 {preset['note']}")
        self.settingsChanged.emit()

    def load_email_settings(self):
        settings = SettingsService.get_cached_settings()
        user = UserSession.get_current_user()

        provider = settings.get("email_provider", "Gmail")
        self.provider_combo.setCurrentText(provider)

        sender = settings.get("email_sender_address") or (user.get("email") if user else "")
        self.sender_email_input.setText(sender)

        preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["Custom SMTP server"])
        self.host_input.setText(settings.get("email_smtp_server", preset["host"]))
        self.port_input.setText(str(settings.get("email_smtp_port", preset["port"])))
        self.encryption_combo.setCurrentText(settings.get("email_encryption", preset["encryption"]))

        if sender:
            pw = CredentialManager.get_password(sender)
            self.password_input.setText(pw)

    def save_email_settings(self, user_details):
        provider = self.provider_combo.currentText()
        sender = self.sender_email_input.text().strip()
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        encryption = self.encryption_combo.currentText()
        password = self.password_input.text().strip()

        email_settings_dict = {
            "email_provider": provider,
            "email_sender_address": sender,
            "email_smtp_server": host,
            "email_smtp_port": port,
            "email_encryption": encryption
        }

        cached = SettingsService.get_cached_settings()
        cached.update(email_settings_dict)
        SettingsService.save_settings(user_details, cached)

        if sender and password:
            CredentialManager.set_password(sender, password)

        return True, "✓ Email configuration saved securely!"

    def run_connection_test(self):
        sender = self.sender_email_input.text().strip()
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        encryption = self.encryption_combo.currentText()
        password = self.password_input.text().strip()
        test_recip = self.test_recipient_input.text().strip()

        if not host or not port:
            self.show_test_result(False, "✕ SMTP Host and Port are required.")
            return

        if not sender:
            self.show_test_result(False, "✕ Sender Email Address is required.")
            return

        self.btn_test.setEnabled(False)
        self.test_progress.show()
        self.test_status_lbl.hide()

        self.test_worker = EmailTestWorker(
            sender_email=sender,
            password=password,
            smtp_host=host,
            smtp_port=port,
            encryption_type=encryption,
            send_test_mail=bool(test_recip),
            test_recipient=test_recip,
            parent=self
        )
        self.test_worker.finished.connect(self.on_test_finished)
        self.test_worker.start()

    def on_test_finished(self, success, message):
        self.test_progress.hide()
        self.btn_test.setEnabled(True)
        self.show_test_result(success, message)

    def show_test_result(self, success, message):
        self.test_status_lbl.setText(message)
        self.test_status_lbl.show()
        if success:
            self.test_status_lbl.setStyleSheet("""
                background-color: #F0FDF4;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Inter', sans-serif;
            """)
        else:
            self.test_status_lbl.setStyleSheet("""
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Inter', sans-serif;
            """)
