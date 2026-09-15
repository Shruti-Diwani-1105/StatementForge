import os
import re
import time
import ctypes
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QFrame, QFileDialog, QMessageBox,
    QProgressBar, QScrollArea, QWidget, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QThread, QMimeData
from PyQt6.QtGui import QCursor, QFont, QGuiApplication, QDesktopServices

from services.email_service import EmailService
from services.credential_manager import CredentialManager
from settings.settings_service import SettingsService
from settings.toast import Toast
from utils.user_session import UserSession
from workers.email_worker import EmailSendWorker


class GmailAutoPasteThread(QThread):
    """Background worker that waits for browser window to open and sends Ctrl+V to attach clipboard file in Gmail."""
    def run(self):
        time.sleep(2.8)
        # Send Ctrl+V using Windows keybd_event
        ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(0x56, 0, 0x0002, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)
        
        # Second backup paste after 1.5s in case of slow page rendering
        time.sleep(1.5)
        ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(0x56, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(0x56, 0, 0x0002, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)



class AttachmentCard(QFrame):
    """Card widget representing an attached file with size and remove button."""
    removed = pyqtSignal(str) # Emits filepath to remove

    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.init_ui()

    def init_ui(self):
        self.setObjectName("AttachmentCard")
        self.setStyleSheet("""
            QFrame#AttachmentCard {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QFrame#AttachmentCard:hover {
                background-color: #EFF6FF;
                border-color: #BFDBFE;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        filename = os.path.basename(self.filepath)
        ext = os.path.splitext(filename)[1].lower()

        # Icon badge based on extension
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if ext in [".xlsx", ".xls"]:
            bg_col, txt_col, type_name = "#F0FDF4", "#16A34A", "Excel File"
        elif ext == ".pdf":
            bg_col, txt_col, type_name = "#EFF6FF", "#2563EB", "PDF Document"
        elif ext == ".csv":
            bg_col, txt_col, type_name = "#FFFBEB", "#D97706", "CSV Spreadsheet"
        else:
            bg_col, txt_col, type_name = "#F1F5F9", "#475569", "Attachment"

        icon_lbl.setStyleSheet(f"background-color: {bg_col}; color: {txt_col}; font-weight: bold; border-radius: 6px; font-size: 11px; font-family: 'Inter', sans-serif;")
        icon_lbl.setText(ext.replace(".", "").upper()[:4])
        layout.addWidget(icon_lbl)

        # File details text
        details_lay = QVBoxLayout()
        details_lay.setSpacing(2)

        fn_lbl = QLabel(filename)
        fn_lbl.setStyleSheet("font-size: 12.5px; font-weight: 600; color: #0F172A; font-family: 'Inter', sans-serif;")
        fn_lbl.setToolTip(self.filepath)
        
        size_bytes = os.path.getsize(self.filepath) if os.path.exists(self.filepath) else 0
        if size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

        sub_lbl = QLabel(f"{type_name} • {size_str}")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-family: 'Inter', sans-serif;")

        details_lay.addWidget(fn_lbl)
        details_lay.addWidget(sub_lbl)
        layout.addLayout(details_lay, stretch=1)

        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(26, 26)
        remove_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        remove_btn.setToolTip("Remove attachment")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                font-weight: bold;
                font-size: 13px;
                border-radius: 13px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                color: #EF4444;
            }
        """)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.filepath))
        layout.addWidget(remove_btn)


class EmailComposerDialog(QDialog):
    """
    Modern PyQt6 popup dialog for composing, sending, and saving draft report emails with multiple attachments.
    """
    emailSentSuccess = pyqtSignal(dict) # Emits result details on success/draft

    def __init__(self, report_type="Financial Report", default_attachment=None, period="", bank_name="", recipient="", message="", draft_id=None, parent=None):
        super().__init__(parent)
        self.report_type = report_type
        self.period = period
        self.bank_name = bank_name
        self.draft_id = draft_id
        self.is_discarded = False
        self.is_sent = False

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.perform_auto_save_draft)

        self.attachment_paths = []

        if default_attachment:
            if isinstance(default_attachment, list):
                for p in default_attachment:
                    if isinstance(p, str) and os.path.exists(p) and p not in self.attachment_paths:
                        self.attachment_paths.append(p)
            elif isinstance(default_attachment, str) and os.path.exists(default_attachment):
                self.attachment_paths.append(default_attachment)

        # Generate default subject & message
        self.default_subject, self.default_message = EmailService.generate_smart_template(
            report_type=self.report_type,
            period=self.period,
            bank_name=self.bank_name
        )
        if message:
            self.default_message = message

        if recipient and recipient.strip() != "External Mail App":
            self.initial_recipient = recipient.strip()
        else:
            self.initial_recipient = ""

        self.init_ui()
        self.load_sender_credentials()

    def init_ui(self):
        self.setWindowTitle("Send Report via Email - StatementForge")
        self.setMinimumSize(700, 700)
        self.resize(740, 780)
        
        # Dialog styling matching StatementForge theme
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QLabel {
                font-family: 'Inter', sans-serif;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #FFFFFF;
                color: #0F172A;
                font-size: 13px;
                font-family: 'Inter', sans-serif;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #0037b0;
            }
        """)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(24, 24, 24, 24)
        dialog_layout.setSpacing(16)

        # Header Title
        header_lay = QHBoxLayout()
        icon_box = QLabel("✉")
        icon_box.setFixedSize(38, 38)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet("""
            background-color: #EFF6FF;
            color: #0037b0;
            font-size: 18px;
            font-weight: bold;
            border-radius: 19px;
        """)
        header_lay.addWidget(icon_box)

        title_lay = QVBoxLayout()
        title_lay.setSpacing(2)
        title_lbl = QLabel("Send Report via Email")
        title_lbl.setStyleSheet("font-size: 19px; font-weight: 700; color: #0F172A; font-family: 'Manrope', sans-serif;")
        sub_lbl = QLabel(f"Report Type: {self.report_type}")
        sub_lbl.setStyleSheet("font-size: 12.5px; color: #64748B; font-family: 'Inter', sans-serif;")
        title_lay.addWidget(title_lbl)
        title_lay.addWidget(sub_lbl)
        header_lay.addLayout(title_lay, stretch=1)
        dialog_layout.addLayout(header_lay)

        # Scroll Area for Form Body to handle vertical responsiveness
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background-color: transparent;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        # Sender configuration notice banner
        self.sender_notice = QLabel("Sender Email: Loading...")
        self.sender_notice.setWordWrap(True)
        self.sender_notice.setStyleSheet("""
            background-color: #F8FAFC;
            color: #475569;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 600;
        """)
        scroll_layout.addWidget(self.sender_notice)

        # Form Container
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        form_lay = QVBoxLayout(form_frame)
        form_lay.setContentsMargins(18, 18, 18, 18)
        form_lay.setSpacing(14)

        # From Field (Configured Sender Email Account)
        from_lay = QHBoxLayout()
        lbl_from = QLabel("From:")
        lbl_from.setFixedWidth(70)
        lbl_from.setStyleSheet("font-weight: bold; color: #475569; font-size: 13px;")
        self.from_input = QLineEdit()
        self.from_input.setReadOnly(True)
        self.from_input.setPlaceholderText("Configured Sender Email Account")
        self.from_input.setStyleSheet("""
            QLineEdit {
                background-color: #F1F5F9;
                color: #334155;
                font-weight: 600;
                border: 1px solid #CBD5E1;
            }
        """)
        from_lay.addWidget(lbl_from)
        from_lay.addWidget(self.from_input)
        form_lay.addLayout(from_lay)

        # Recipient To Field
        to_lay = QHBoxLayout()
        lbl_to = QLabel("To:")
        lbl_to.setFixedWidth(70)
        lbl_to.setStyleSheet("font-weight: bold; color: #0F172A; font-size: 13px;")
        self.to_input = QLineEdit(self.initial_recipient)
        self.to_input.setPlaceholderText("recipient@example.com (e.g. kinjal@example.com)")
        to_lay.addWidget(lbl_to)
        to_lay.addWidget(self.to_input)
        form_lay.addLayout(to_lay)

        # CC
        cc_lay = QHBoxLayout()
        lbl_cc = QLabel("CC:")
        lbl_cc.setFixedWidth(70)
        lbl_cc.setStyleSheet("font-weight: bold; color: #64748B; font-size: 13px;")
        self.cc_input = QLineEdit()
        self.cc_input.setPlaceholderText("Optional CC recipient email addresses")
        cc_lay.addWidget(lbl_cc)
        cc_lay.addWidget(self.cc_input)
        form_lay.addLayout(cc_lay)

        # BCC
        bcc_lay = QHBoxLayout()
        lbl_bcc = QLabel("BCC:")
        lbl_bcc.setFixedWidth(70)
        lbl_bcc.setStyleSheet("font-weight: bold; color: #64748B; font-size: 13px;")
        self.bcc_input = QLineEdit()
        self.bcc_input.setPlaceholderText("Optional BCC recipient email addresses")
        bcc_lay.addWidget(lbl_bcc)
        bcc_lay.addWidget(self.bcc_input)
        form_lay.addLayout(bcc_lay)

        # Subject
        sub_lay = QHBoxLayout()
        lbl_sub = QLabel("Subject:")
        lbl_sub.setFixedWidth(70)
        lbl_sub.setStyleSheet("font-weight: bold; color: #0F172A; font-size: 13px;")
        self.subject_input = QLineEdit(self.default_subject)
        sub_lay.addWidget(lbl_sub)
        sub_lay.addWidget(self.subject_input)
        form_lay.addLayout(sub_lay)

        # Message Body
        lbl_msg = QLabel("Message:")
        lbl_msg.setStyleSheet("font-weight: bold; color: #0F172A; font-size: 13px;")
        form_lay.addWidget(lbl_msg)
        
        self.message_input = QTextEdit()
        self.message_input.setPlainText(self.default_message)
        self.message_input.setMinimumHeight(140)
        form_lay.addWidget(self.message_input)

        scroll_layout.addWidget(form_frame)

        # Attachment Section Header
        att_hdr_lay = QHBoxLayout()
        att_hdr_lbl = QLabel("Attachments")
        att_hdr_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #0F172A;")
        att_hdr_lay.addWidget(att_hdr_lbl)
        att_hdr_lay.addStretch()

        self.add_att_btn = QPushButton("+ Add Attachment")
        self.add_att_btn.setFixedHeight(32)
        self.add_att_btn.setMinimumWidth(130)
        self.add_att_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_att_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #0037b0;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 600;
                font-size: 12px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        self.add_att_btn.clicked.connect(self.browse_additional_attachment)
        att_hdr_lay.addWidget(self.add_att_btn)
        scroll_layout.addLayout(att_hdr_lay)

        # Attachments Container
        self.att_container = QWidget()
        self.att_layout = QVBoxLayout(self.att_container)
        self.att_layout.setContentsMargins(0, 0, 0, 0)
        self.att_layout.setSpacing(8)

        scroll_layout.addWidget(self.att_container)
        self.refresh_attachment_cards()

        # Status & Loading Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #E2E8F0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0037b0;
                border-radius: 2px;
            }
        """)
        self.progress_bar.hide()
        scroll_layout.addWidget(self.progress_bar)

        self.status_banner = QLabel("")
        self.status_banner.setWordWrap(True)
        self.status_banner.hide()
        scroll_layout.addWidget(self.status_banner)

        scroll_area.setWidget(scroll_content)
        dialog_layout.addWidget(scroll_area, stretch=1)

        self.to_input.textChanged.connect(self.trigger_auto_save)
        self.cc_input.textChanged.connect(self.trigger_auto_save)
        self.bcc_input.textChanged.connect(self.trigger_auto_save)
        self.subject_input.textChanged.connect(self.trigger_auto_save)
        self.message_input.textChanged.connect(self.trigger_auto_save)

        # Footer Action Bar (Fixed at bottom)
        footer_lay = QHBoxLayout()
        footer_lay.setSpacing(10)
        
        self.draft_status_lbl = QLabel("Draft saved" if self.draft_id else "")
        self.draft_status_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-style: italic;")
        footer_lay.addWidget(self.draft_status_lbl)
        footer_lay.addStretch()

        self.discard_btn = QPushButton("🗑 Discard")
        self.discard_btn.setFixedHeight(38)
        self.discard_btn.setMinimumWidth(90)
        self.discard_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.discard_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #FEF2F2; }
        """)
        self.discard_btn.clicked.connect(self.discard_draft_action)
        footer_lay.addWidget(self.discard_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 13px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #F8FAFC; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        footer_lay.addWidget(self.cancel_btn)

        self.draft_btn = QPushButton("💾 Save Draft")
        self.draft_btn.setFixedHeight(38)
        self.draft_btn.setMinimumWidth(110)
        self.draft_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.draft_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF3C7;
                color: #B45309;
                border: 1px solid #FDE68A;
                border-radius: 8px;
                padding: 0 18px;
                font-weight: 700;
                font-size: 13px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #FDE68A; }
        """)
        self.draft_btn.clicked.connect(self.save_draft_action)
        footer_lay.addWidget(self.draft_btn)

        self.webmail_btn = QPushButton("✉ Open in Mail App")
        self.webmail_btn.setFixedHeight(38)
        self.webmail_btn.setMinimumWidth(150)
        self.webmail_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.webmail_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #0037b0;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12.5px;
                font-family: 'Inter', sans-serif;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        self.webmail_btn.clicked.connect(self.open_webmail_action)
        footer_lay.addWidget(self.webmail_btn)

        dialog_layout.addLayout(footer_lay)

    def load_sender_credentials(self):
        """Loads saved SMTP credentials from Settings & OS Keyring, auto-inferring defaults if missing."""
        user = UserSession.get_current_user()
        settings = SettingsService.get_cached_settings()

        self.sender_email = settings.get("email_sender_address") or (user.get("email") if user else "") or "rajyagurukinjal27@gmail.com"
        inferred_host, inferred_port, inferred_enc = EmailService.infer_smtp_settings(self.sender_email)

        self.smtp_host = settings.get("email_smtp_server") or inferred_host
        self.smtp_port = settings.get("email_smtp_port") or inferred_port
        self.encryption_type = settings.get("email_encryption") or inferred_enc

        # Fetch password securely from keyring
        self.sender_password = CredentialManager.get_password(self.sender_email) if self.sender_email else ""
        self.update_webmail_button_label()

        if self.sender_email:
            self.from_input.setText(self.sender_email)
        else:
            self.from_input.setText("Not configured (Set in Application Settings)")

        if self.sender_email and self.smtp_host:
            self.sender_notice.setText(f"✓ Configured Sender: {self.sender_email} ({self.smtp_host}:{self.smtp_port})")
            self.sender_notice.setStyleSheet("""
                background-color: #F0FDF4;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            """)
        else:
            self.sender_notice.setText("⚠ Email configuration incomplete. Please configure your sender email address under Settings.")
            self.sender_notice.setStyleSheet("""
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            """)

    def refresh_attachment_cards(self):
        """Rebuilds the attachment list UI cards."""
        while self.att_layout.count():
            item = self.att_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.attachment_paths:
            empty_lbl = QLabel("No files attached. Use '+ Add Attachment' to include reports.")
            empty_lbl.setStyleSheet("font-size: 11.5px; color: #94A3B8; font-style: italic;")
            self.att_layout.addWidget(empty_lbl)
            return

        for path in self.attachment_paths:
            card = AttachmentCard(path, self)
            card.removed.connect(self.remove_attachment)
            self.att_layout.addWidget(card)

    def browse_additional_attachment(self):
        """Opens file dialog to select extra attachments."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Attachment Reports",
            "",
            "Supported Files (*.xlsx *.xls *.pdf *.csv);;Excel Files (*.xlsx *.xls);;PDF Files (*.pdf);;CSV Files (*.csv)"
        )
        if paths:
            for p in paths:
                if p not in self.attachment_paths:
                    self.attachment_paths.append(p)
            self.refresh_attachment_cards()

    def remove_attachment(self, filepath):
        """Removes an attachment from the list."""
        if filepath in self.attachment_paths:
            self.attachment_paths.remove(filepath)
            self.refresh_attachment_cards()

    def send_email_action(self):
        """Validates inputs, prompts for missing SMTP credentials, and triggers background SMTP sending thread."""
        recipient = self.to_input.text().strip()
        cc = self.cc_input.text().strip()
        bcc = self.bcc_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.message_input.toPlainText().strip()

        # Recipient Validation
        if not recipient:
            self.show_status_banner("Please enter a valid recipient email address.", is_error=True)
            return

        # Verify attachments exist and are non-empty before proceeding
        if self.attachment_paths:
            for path in self.attachment_paths:
                if not os.path.exists(path) or os.path.getsize(path) == 0 or not os.access(path, os.R_OK):
                    err_txt = f"Unable to attach the report because the file could not be found: {os.path.basename(path)}"
                    self.show_status_banner(err_txt, is_error=True)
                    QMessageBox.warning(self, "Attachment Error", err_txt)
                    return

        # Input Validation via EmailService
        val_ok, val_msg = EmailService.validate_inputs(
            recipient=recipient,
            sender_email=self.sender_email,
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            attachment_paths=self.attachment_paths
        )

        if not val_ok:
            if "recipient" in val_msg.lower():
                val_msg = "Please enter a valid recipient email address."
            self.show_status_banner(val_msg, is_error=True)
            return

        # Prompt for password if not configured or saved in keyring
        if not getattr(self, "sender_password", None):
            pwd, ok = QInputDialog.getText(
                self,
                "SMTP Authentication Required",
                f"Enter App Password / SMTP Password for sender:\n{self.sender_email}\n\n(For Gmail, generate a 16-character App Password at myaccount.google.com/apppasswords):",
                QLineEdit.EchoMode.Password
            )
            if ok and pwd and pwd.strip():
                self.sender_password = pwd.strip()
                if self.sender_email:
                    CredentialManager.set_password(self.sender_email, self.sender_password)
            else:
                self.show_status_banner("SMTP authentication password is required to send email.", is_error=True)
                return

        user = UserSession.get_current_user()
        user_id = user["id"] if user else "guest"

        # Lock UI & show progress bar
        self.send_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.show()
        self.show_status_banner("Sending report via SMTP...", is_error=False)

        # Launch background worker
        self.worker = EmailSendWorker(
            sender_email=self.sender_email,
            password=self.sender_password,
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            encryption_type=self.encryption_type,
            recipient=recipient,
            cc=cc,
            bcc=bcc,
            subject=subject,
            body=body,
            attachment_paths=self.attachment_paths,
            report_type=self.report_type,
            user_id=user_id,
            parent=self
        )

        self.worker.finished.connect(self.on_send_finished)
        self.worker.start()

    def on_send_finished(self, success, message, meta):
        """Handles background worker completion."""
        self.progress_bar.hide()
        self.send_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        if success:
            self.is_sent = True
            self.show_status_banner("✓ Report sent successfully!", is_error=False)
            
            # Auto-create Email Sent Successfully Notification
            try:
                from services.notification_service import NotificationService
                user = UserSession.get_current_user()
                u_id = user["id"] if user else "guest"
                att_name = os.path.basename(self.attachment_paths[0]) if self.attachment_paths else "Report Attachment"
                NotificationService.create_notification(
                    user_id=u_id,
                    category="email",
                    title="Email Sent Successfully",
                    message=f"Financial report email for statement attachment '{att_name}' dispatched successfully to '{meta['recipient']}'."
                )
                p = self.parent()
                while p:
                    if hasattr(p, "update_notification_badge"):
                        p.update_notification_badge()
                        break
                    p = p.parent()
            except Exception as e:
                print(f"EmailComposerDialog: Notification error: {e}")

            QMessageBox.information(
                self,
                "Success",
                f"✓ Report sent successfully to:\n{meta['recipient']}\n\nReport: {meta['report_type']}"
            )
            self.emailSentSuccess.emit(meta)
            self.accept()
        else:
            self.is_sent = False
            clean_err = "Unable to send email. Please verify your SMTP authentication settings and try again."
            self.show_status_banner(f"{clean_err} (Details: {message})", is_error=True)
            try:
                from services.notification_service import NotificationService
                user = UserSession.get_current_user()
                u_id = user["id"] if user else "guest"
                att_name = os.path.basename(self.attachment_paths[0]) if self.attachment_paths else "Report Attachment"
                NotificationService.create_notification(
                    user_id=u_id,
                    category="error",
                    title="Email Delivery Failed",
                    message=f"Email delivery failed for statement attachment '{att_name}' to '{meta.get('recipient')}': {message}"
                )
                p = self.parent()
                while p:
                    if hasattr(p, "update_notification_badge"):
                        p.update_notification_badge()
                        break
                    p = p.parent()
            except Exception:
                pass

            QMessageBox.warning(
                self,
                "SMTP Transmission Error",
                f"{clean_err}\n\nTechnical details from server:\n{message}"
            )

    def show_status_banner(self, text, is_error=False):
        """Displays status message in the dialog."""
        self.status_banner.setText(text)
        self.status_banner.show()
        if is_error:
            self.status_banner.setStyleSheet("""
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12.5px;
                font-weight: 600;
            """)
        else:
            self.status_banner.setStyleSheet("""
                background-color: #F0FDF4;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12.5px;
                font-weight: 600;
            """)

    def trigger_auto_save(self):
        """Triggers Gmail-style auto-save timer after typing stops."""
        if self.is_discarded or self.is_sent:
            return
        self.update_webmail_button_label()
        self.draft_status_lbl.setText("Saving draft...")
        self.auto_save_timer.start(1200)

    def perform_auto_save_draft(self):
        """Saves current state silently into EmailRepository as a Draft."""
        if self.is_discarded or self.is_sent:
            return

        recipient = self.to_input.text().strip()
        cc = self.cc_input.text().strip()
        bcc = self.bcc_input.text().strip()
        subject = self.subject_input.text().strip()
        message = self.message_input.toPlainText()

        if not recipient and not subject and not message:
            return

        from database.email_repository import EmailRepository
        user = UserSession.get_current_user()
        user_id = user.get("id") or user.get("username") if user else "guest"
        att_name = os.path.basename(self.attachment_paths[0]) if self.attachment_paths else "No attachment"

        was_new = (self.draft_id is None)
        self.draft_id = EmailRepository.save_email_log(
            user_id=user_id,
            recipient_email=recipient,
            cc=cc,
            bcc=bcc,
            subject=subject,
            report_type=self.report_type,
            attachment_name=att_name,
            attachment_paths=self.attachment_paths,
            status="Draft",
            error_message="",
            body=message,
            log_id=self.draft_id
        )
        self.draft_status_lbl.setText("Draft saved")

        if was_new:
            try:
                from services.notification_service import NotificationService
                NotificationService.create_notification(
                    user_id=user_id,
                    category="email",
                    title="Email Draft Created",
                    message=f"Email draft created for statement attachment '{att_name}' (Recipient: '{recipient or 'Unspecified'}')."
                )
                p = self.parent()
                while p:
                    if hasattr(p, "update_notification_badge"):
                        p.update_notification_badge()
                        break
                    p = p.parent()
            except Exception:
                pass

    def discard_draft_action(self):
        """Discards current draft and deletes it from repository if stored."""
        self.is_discarded = True
        self.auto_save_timer.stop()

        if self.draft_id:
            from database.email_repository import EmailRepository
            EmailRepository.delete_email_log(self.draft_id)

        self.emailSentSuccess.emit({"status": "Discarded", "id": self.draft_id})
        super().reject()

    def reject(self):
        """Auto-saves draft on close/cancel like Gmail unless discarded or sent."""
        if not self.is_discarded and not self.is_sent:
            self.perform_auto_save_draft()
        super().reject()

    def closeEvent(self, event):
        """Auto-saves draft when window is closed via window manager."""
        if not self.is_discarded and not self.is_sent:
            self.perform_auto_save_draft()
        super().closeEvent(event)

    def save_draft_action(self):
        """Explicitly saves current email composition as a Draft."""
        recipient = self.to_input.text().strip()
        cc = self.cc_input.text().strip()
        bcc = self.bcc_input.text().strip()
        subject = self.subject_input.text().strip()
        message = self.message_input.toPlainText()

        display_rec = recipient if recipient else "Draft (No recipient specified)"

        from database.email_repository import EmailRepository
        user = UserSession.get_current_user()
        user_id = user.get("id") or user.get("username") if user else "guest"
        att_name = os.path.basename(self.attachment_paths[0]) if self.attachment_paths else "No attachment"

        self.draft_id = EmailRepository.save_email_log(
            user_id=user_id,
            recipient_email=display_rec,
            cc=cc,
            bcc=bcc,
            subject=subject,
            report_type=self.report_type,
            attachment_name=att_name,
            attachment_paths=self.attachment_paths,
            status="Draft",
            error_message="",
            body=message,
            log_id=self.draft_id
        )

        self.draft_status_lbl.setText("✓ Draft saved")
        Toast.success(self, "✓ Draft email saved successfully!")

        QMessageBox.information(
            self,
            "Draft Saved",
            f"✓ Draft email saved successfully!\n\nRecipient: {display_rec}\nSubject: {subject or '(No subject)'}"
        )
        self.emailSentSuccess.emit({"status": "Draft", "id": self.draft_id, "recipient": display_rec})
        self.accept()

    def update_webmail_button_label(self):
        """Updates the webmail button label based on configured sender or recipient domain."""
        if not hasattr(self, "webmail_btn"):
            return
        recipient = self.to_input.text().strip() if hasattr(self, "to_input") else ""
        provider_name, _ = EmailService.get_webmail_compose_url(
            sender_email=getattr(self, "sender_email", ""),
            recipient=recipient
        )
        if "Google" in provider_name:
            self.webmail_btn.setText("✉ Open in Gmail")
        elif "Yahoo" in provider_name:
            self.webmail_btn.setText("✉ Open in Yahoo")
        elif "Outlook" in provider_name:
            self.webmail_btn.setText("✉ Open in Outlook")
        else:
            self.webmail_btn.setText("✉ Open in Mail App")

    def open_webmail_action(self):
        """Opens user's registered webmail provider with details pre-filled and automatically attaches the report file."""
        recipient = self.to_input.text().strip()
        cc = self.cc_input.text().strip()
        bcc = self.bcc_input.text().strip()
        subject = self.subject_input.text().strip()
        message = self.message_input.toPlainText()

        if not recipient or not EmailService.validate_email_address(recipient):
            self.show_status_banner("Please enter a valid recipient email address.", is_error=True)
            return

        # Verify attachments before proceeding
        if self.attachment_paths:
            for path in self.attachment_paths:
                if not os.path.exists(path) or os.path.getsize(path) == 0 or not os.access(path, os.R_OK):
                    err_text = "Unable to attach the report because the file could not be found."
                    self.show_status_banner(err_text, is_error=True)
                    QMessageBox.warning(self, "Attachment Error", err_text)
                    return

        provider_name, compose_url = EmailService.get_webmail_compose_url(
            sender_email=getattr(self, "sender_email", ""),
            recipient=recipient,
            subject=subject,
            body=message,
            cc=cc,
            bcc=bcc
        )

        # Log email item in repository as "In Mail"
        try:
            from database.email_repository import EmailRepository
            user = UserSession.get_current_user()
            user_id = user.get("id") or user.get("username") if user else "guest"
            att_name = os.path.basename(self.attachment_paths[0]) if self.attachment_paths else "No attachment"

            EmailRepository.save_email_log(
                user_id=user_id,
                recipient_email=recipient,
                cc=cc,
                bcc=bcc,
                subject=subject,
                report_type=self.report_type,
                attachment_name=att_name,
                attachment_paths=self.attachment_paths,
                status="In Mail",
                error_message="",
                body=message,
                log_id=self.draft_id
            )
        except Exception:
            pass

        # Set native file object on Clipboard so Ctrl+V in Gmail attaches the file instantly
        if self.attachment_paths:
            cb = QGuiApplication.clipboard()
            if cb:
                mime = QMimeData()
                urls = [QUrl.fromLocalFile(os.path.abspath(p)) for p in self.attachment_paths if os.path.exists(p)]
                mime.setUrls(urls)
                mime.setText(self.attachment_paths[0])
                cb.setMimeData(mime)
            
            # Start background thread to automatically send paste command to Gmail compose window once rendered
            self.paste_thread = GmailAutoPasteThread(parent=self)
            self.paste_thread.start()

            att_file_name = os.path.basename(self.attachment_paths[0])
            Toast.success(self, f"✓ File '{att_file_name}' attached! Gmail compose opening...")

        # Dispatch direct SMTP delivery in background if credentials available
        if getattr(self, "sender_email", "") and getattr(self, "sender_password", "") and EmailService.validate_email_address(self.sender_email):
            try:
                user = UserSession.get_current_user()
                user_id = user["id"] if user else "guest"
                self.worker = EmailSendWorker(
                    sender_email=self.sender_email,
                    password=getattr(self, "sender_password", ""),
                    smtp_host=getattr(self, "smtp_host", ""),
                    smtp_port=getattr(self, "smtp_port", "587"),
                    encryption_type=getattr(self, "encryption_type", "STARTTLS"),
                    recipient=recipient,
                    cc=cc,
                    bcc=bcc,
                    subject=subject,
                    body=message,
                    attachment_paths=self.attachment_paths,
                    report_type=self.report_type,
                    user_id=user_id,
                    parent=self
                )
                self.worker.start()
            except Exception as e:
                print(f"Webmail SMTP background dispatch notice: {e}")

        # Launch mail application / webmail URL with reliable fallbacks
        opened = False
        try:
            opened = QDesktopServices.openUrl(QUrl(compose_url))
        except Exception as e:
            print(f"QDesktopServices openUrl error: {e}")

        if not opened:
            import webbrowser
            try:
                webbrowser.open(compose_url)
                opened = True
            except Exception as e:
                print(f"webbrowser open error: {e}")

        if not opened and compose_url.startswith("mailto:"):
            # Fallback to webmail compose if native mailto fails on OS
            try:
                _, alt_url = EmailService.get_webmail_compose_url(
                    sender_email="gmail.com",
                    recipient=recipient,
                    subject=subject,
                    body=message,
                    cc=cc,
                    bcc=bcc
                )
                import webbrowser
                webbrowser.open(alt_url)
                opened = True
            except Exception:
                pass

        if not opened:
            QMessageBox.warning(
                self,
                "Mail Application Error",
                "Unable to open the mail application. Please check your default mail app settings."
            )
            return

        self.accept()
