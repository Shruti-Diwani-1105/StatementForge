import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QFrame, QFileDialog, QMessageBox,
    QProgressBar, QScrollArea, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor, QFont, QIcon, QPixmap, QColor

from services.email_service import EmailService
from services.credential_manager import CredentialManager
from settings.settings_service import SettingsService
from utils.user_session import UserSession
from workers.email_worker import EmailSendWorker

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
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        filename = os.path.basename(self.filepath)
        ext = os.path.splitext(filename)[1].lower()

        # Icon badge based on extension
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if ext in [".xlsx", ".xls"]:
            bg_col, txt_col, type_name = "#F0FDF4", "#16A34A", "Excel File"
        elif ext == ".pdf":
            bg_col, txt_col, type_name = "#EFF6FF", "#2563EB", "PDF Document"
        elif ext == ".csv":
            bg_col, txt_col, type_name = "#FFFBEB", "#D97706", "CSV Spreadsheet"
        else:
            bg_col, txt_col, type_name = "#F1F5F9", "#475569", "Attachment"

        icon_lbl.setStyleSheet(f"background-color: {bg_col}; color: {txt_col}; font-weight: bold; border-radius: 6px; font-size: 11px;")
        icon_lbl.setText(ext.replace(".", "").upper()[:4])
        layout.addWidget(icon_lbl)

        # File details text
        details_lay = QVBoxLayout()
        details_lay.setSpacing(2)

        fn_lbl = QLabel(filename)
        fn_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")
        
        size_bytes = os.path.getsize(self.filepath) if os.path.exists(self.filepath) else 0
        if size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

        sub_lbl = QLabel(f"{type_name} • {size_str}")
        sub_lbl.setStyleSheet("font-size: 10px; color: #64748B;")

        details_lay.addWidget(fn_lbl)
        details_lay.addWidget(sub_lbl)
        layout.addLayout(details_lay, stretch=1)

        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        remove_btn.setToolTip("Remove attachment")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                font-weight: bold;
                font-size: 13px;
                border-radius: 12px;
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
                    if os.path.exists(p) and p not in self.attachment_paths:
                        self.attachment_paths.append(p)
            elif os.path.exists(default_attachment):
                self.attachment_paths.append(default_attachment)

        # Generate default subject & message
        self.default_subject, self.default_message = EmailService.generate_smart_template(
            report_type=self.report_type,
            period=self.period,
            bank_name=self.bank_name
        )
        if message:
            self.default_message = message

        if recipient:
            self.initial_recipient = recipient
        else:
            self.initial_recipient = ""

        self.init_ui()
        self.load_sender_credentials()

    def init_ui(self):
        self.setWindowTitle(f"Send Report via Email - StatementForge")
        self.setMinimumSize(620, 680)
        self.resize(680, 740)
        
        # Dialog styling matching StatementForge theme
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #0F172A;
            }
            QLabel {
                font-family: 'Times New Roman';
            }
            QLineEdit, QTextEdit {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #FFFFFF;
                color: #0F172A;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #0037b0;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title
        header_lay = QHBoxLayout()
        icon_box = QLabel("✉")
        icon_box.setFixedSize(36, 36)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet("""
            background-color: #EFF6FF;
            color: #0037b0;
            font-size: 18px;
            font-weight: bold;
            border-radius: 18px;
        """)
        header_lay.addWidget(icon_box)

        title_lay = QVBoxLayout()
        title_lay.setSpacing(2)
        title_lbl = QLabel("Send Report via Email")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        sub_lbl = QLabel(f"Report: {self.report_type}")
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        title_lay.addWidget(title_lbl)
        title_lay.addWidget(sub_lbl)
        header_lay.addLayout(title_lay, stretch=1)
        main_layout.addLayout(header_lay)

        # Sender configuration notice
        self.sender_notice = QLabel("Sender Email: Not configured (Set in Settings -> Email Configuration)")
        self.sender_notice.setStyleSheet("""
            background-color: #FFFBEB;
            color: #B45309;
            border: 1px solid #FDE68A;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 11px;
            font-weight: 600;
        """)
        main_layout.addWidget(self.sender_notice)

        # Form Container
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        form_lay = QVBoxLayout(form_frame)
        form_lay.setContentsMargins(16, 16, 16, 16)
        form_lay.setSpacing(12)

        # Recipient To
        to_lay = QHBoxLayout()
        lbl_to = QLabel("To:")
        lbl_to.setFixedWidth(60)
        lbl_to.setStyleSheet("font-weight: bold; color: #475569; font-size: 13px;")
        self.to_input = QLineEdit(self.initial_recipient)
        self.to_input.setPlaceholderText("recipient@example.com (comma separated for multiple)")
        to_lay.addWidget(lbl_to)
        to_lay.addWidget(self.to_input)
        form_lay.addLayout(to_lay)

        # CC
        cc_lay = QHBoxLayout()
        lbl_cc = QLabel("CC:")
        lbl_cc.setFixedWidth(60)
        lbl_cc.setStyleSheet("font-weight: bold; color: #64748B; font-size: 13px;")
        self.cc_input = QLineEdit()
        self.cc_input.setPlaceholderText("Optional CC email addresses")
        cc_lay.addWidget(lbl_cc)
        cc_lay.addWidget(self.cc_input)
        form_lay.addLayout(cc_lay)

        # BCC
        bcc_lay = QHBoxLayout()
        lbl_bcc = QLabel("BCC:")
        lbl_bcc.setFixedWidth(60)
        lbl_bcc.setStyleSheet("font-weight: bold; color: #64748B; font-size: 13px;")
        self.bcc_input = QLineEdit()
        self.bcc_input.setPlaceholderText("Optional BCC email addresses")
        bcc_lay.addWidget(lbl_bcc)
        bcc_lay.addWidget(self.bcc_input)
        form_lay.addLayout(bcc_lay)

        # Subject
        sub_lay = QHBoxLayout()
        lbl_sub = QLabel("Subject:")
        lbl_sub.setFixedWidth(60)
        lbl_sub.setStyleSheet("font-weight: bold; color: #475569; font-size: 13px;")
        self.subject_input = QLineEdit(self.default_subject)
        sub_lay.addWidget(lbl_sub)
        sub_lay.addWidget(self.subject_input)
        form_lay.addLayout(sub_lay)

        # Message Body
        lbl_msg = QLabel("Message:")
        lbl_msg.setStyleSheet("font-weight: bold; color: #475569; font-size: 13px;")
        form_lay.addWidget(lbl_msg)
        
        self.message_input = QTextEdit()
        self.message_input.setPlainText(self.default_message)
        self.message_input.setMinimumHeight(130)
        form_lay.addWidget(self.message_input)

        main_layout.addWidget(form_frame)

        # Attachment Section Header
        att_hdr_lay = QHBoxLayout()
        att_hdr_lbl = QLabel("Attachments")
        att_hdr_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #0F172A;")
        att_hdr_lay.addWidget(att_hdr_lbl)
        att_hdr_lay.addStretch()

        self.add_att_btn = QPushButton("+ Add Attachment")
        self.add_att_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_att_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #0037b0;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        self.add_att_btn.clicked.connect(self.browse_additional_attachment)
        att_hdr_lay.addWidget(self.add_att_btn)
        main_layout.addLayout(att_hdr_lay)

        # Attachments Container
        self.att_container = QWidget()
        self.att_layout = QVBoxLayout(self.att_container)
        self.att_layout.setContentsMargins(0, 0, 0, 0)
        self.att_layout.setSpacing(8)

        main_layout.addWidget(self.att_container)
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
        main_layout.addWidget(self.progress_bar)

        self.status_banner = QLabel("")
        self.status_banner.setWordWrap(True)
        self.status_banner.hide()
        main_layout.addWidget(self.status_banner)

        self.to_input.textChanged.connect(self.trigger_auto_save)
        self.cc_input.textChanged.connect(self.trigger_auto_save)
        self.bcc_input.textChanged.connect(self.trigger_auto_save)
        self.subject_input.textChanged.connect(self.trigger_auto_save)
        self.message_input.textChanged.connect(self.trigger_auto_save)

        # Footer Buttons & Gmail-style Draft status
        footer_lay = QHBoxLayout()
        
        self.draft_status_lbl = QLabel("Draft saved" if self.draft_id else "")
        self.draft_status_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-style: italic;")
        footer_lay.addWidget(self.draft_status_lbl)
        footer_lay.addStretch()

        self.discard_btn = QPushButton("🗑 Discard")
        self.discard_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.discard_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #FEF2F2; }
        """)
        self.discard_btn.clicked.connect(self.discard_draft_action)
        footer_lay.addWidget(self.discard_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #F8FAFC; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        footer_lay.addWidget(self.cancel_btn)

        self.draft_btn = QPushButton("💾 Save Draft")
        self.draft_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.draft_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF3C7;
                color: #B45309;
                border: 1px solid #FDE68A;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #FDE68A; }
        """)
        self.draft_btn.clicked.connect(self.save_draft_action)
        footer_lay.addWidget(self.draft_btn)

        self.send_btn = QPushButton("Send Email")
        self.send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0037b0;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #CBD5E1; color: #94A3B8; }
        """)
        self.send_btn.clicked.connect(self.send_email_action)
        footer_lay.addWidget(self.send_btn)

        main_layout.addLayout(footer_lay)

    def load_sender_credentials(self):
        """Loads saved SMTP credentials from Settings & OS Keyring."""
        user = UserSession.get_current_user()
        settings = SettingsService.get_cached_settings()

        self.sender_email = settings.get("email_sender_address") or (user.get("email") if user else "")
        self.smtp_host = settings.get("email_smtp_server") or ""
        self.smtp_port = settings.get("email_smtp_port") or "587"
        self.encryption_type = settings.get("email_encryption") or "STARTTLS"

        # Fetch password securely from keyring
        self.sender_password = CredentialManager.get_password(self.sender_email) if self.sender_email else ""

        if self.sender_email and self.smtp_host:
            self.sender_notice.setText(f"✓ Sender Email: {self.sender_email} ({self.smtp_host}:{self.smtp_port})")
            self.sender_notice.setStyleSheet("""
                background-color: #F0FDF4;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            """)
        else:
            self.sender_notice.setText("⚠ Email configuration incomplete. Please configure sender details under Email Center -> Email Configuration tab.")
            self.sender_notice.setStyleSheet("""
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            """)

    def refresh_attachment_cards(self):
        """Rebuilds the attachment list UI cards."""
        # Clear existing cards
        while self.att_layout.count():
            item = self.att_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.attachment_paths:
            empty_lbl = QLabel("No files attached. Use '+ Add Attachment' to include reports.")
            empty_lbl.setStyleSheet("font-size: 11px; color: #94A3B8; font-style: italic;")
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
        """Validates inputs and triggers background SMTP sending thread."""
        recipient = self.to_input.text().strip()
        cc = self.cc_input.text().strip()
        bcc = self.bcc_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.message_input.toPlainText().strip()

        # Input Validation
        val_ok, val_msg = EmailService.validate_inputs(
            recipient=recipient,
            sender_email=self.sender_email,
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            attachment_paths=self.attachment_paths
        )

        if not val_ok:
            self.show_status_banner(val_msg, is_error=True)
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
            QMessageBox.information(
                self,
                "Success",
                f"✓ Report sent successfully to:\n{meta['recipient']}\n\nReport: {meta['report_type']}"
            )
            self.emailSentSuccess.emit(meta)
            self.accept()
        else:
            self.show_status_banner(message, is_error=True)

    def show_status_banner(self, text, is_error=False):
        """Displays status message in the dialog."""
        self.status_banner.setText(text)
        self.status_banner.show()
        if is_error:
            self.status_banner.setStyleSheet("""
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            """)
        else:
            self.status_banner.setStyleSheet("""
                background-color: #F0FDF4;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            """)

    def trigger_auto_save(self):
        """Triggers Gmail-style auto-save timer after typing stops."""
        if self.is_discarded or self.is_sent:
            return
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
        """Explicitly saves current email composition as a Draft with receiver ID."""
        recipient = self.to_input.text().strip()
        cc = self.cc_input.text().strip()
        bcc = self.bcc_input.text().strip()
        subject = self.subject_input.text().strip()
        message = self.message_input.toPlainText()

        if not recipient:
            self.show_status_banner("✕ Please enter a recipient email (receiver ID) to save draft.", is_error=True)
            return

        from database.email_repository import EmailRepository
        user = UserSession.get_current_user()
        user_id = user.get("id") or user.get("username") if user else "guest"
        att_name = os.path.basename(self.attachment_paths[0]) if self.attachment_paths else "No attachment"

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

        QMessageBox.information(
            self,
            "Draft Saved",
            f"✓ Draft email saved successfully!\n\nReceiver ID: {recipient}\nSubject: {subject}"
        )
        self.emailSentSuccess.emit({"status": "Draft", "id": self.draft_id, "recipient": recipient})
        self.accept()
